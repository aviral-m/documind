import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import Document, DocumentChunk, DocumentPage
from app.models.document import (
    COMPLETED,
    INDEX_FAILED,
    INDEX_INDEXED,
    INDEX_INDEXING,
    INDEX_PENDING,
    PENDING,
)
from app.rag.embeddings import EMBEDDING_FAILED_MESSAGE, EmbeddingError
from app.services.document_service import (
    INDEX_INTERRUPTED_MESSAGE,
    ReindexRejected,
    recover_stuck_documents,
    request_reindex,
)
from app.services.indexing_service import (
    GENERIC_INDEX_FAILURE_MESSAGE,
    NO_CHUNKS_MESSAGE,
    index_document,
)


def add_document(db, user, pages, status=COMPLETED, index_status=INDEX_PENDING, updated_at=None):
    document = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        filename="policy.pdf",
        storage_path=f"documind/{user.id}/policy.pdf",
        size_bytes=10,
        page_count=len(pages),
        status=status,
        index_status=index_status,
        updated_at=updated_at or datetime.now(UTC),
    )
    db.add(document)
    db.add_all(
        DocumentPage(document_id=document.id, page_number=number, text=text)
        for number, text in enumerate(pages, start=1)
    )
    db.commit()
    return document


def chunk_rows(db, document_id):
    return db.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    ).all()


PAGES = [
    "Refunds are processed within fourteen days of the return.",
    "Shipping to overseas addresses takes three to five weeks.",
]


def test_completed_document_is_indexed_with_chunks_and_settings(
    db, make_user, session_factory, settings, embedder
):
    user = make_user()
    document = add_document(db, user, PAGES)

    index_document(session_factory, settings, embedder, document.id)

    db.refresh(document)
    rows = chunk_rows(db, document.id)
    assert document.index_status == INDEX_INDEXED
    assert document.index_error is None
    assert document.chunk_count == len(rows) == 2
    assert document.embedding_model == settings.embedding_model
    assert document.chunk_target_chars == settings.chunk_target_chars
    assert document.chunk_overlap_chars == settings.chunk_overlap_chars
    assert document.indexed_at is not None
    assert [(row.page_number, row.chunk_index) for row in rows] == [(1, 0), (2, 1)]
    assert all(len(row.embedding) == 768 for row in rows)


def test_reindexing_replaces_chunks_without_duplicates(
    db, make_user, session_factory, settings, embedder
):
    user = make_user()
    document = add_document(db, user, PAGES)

    index_document(session_factory, settings, embedder, document.id)
    index_document(session_factory, settings, embedder, document.id)

    db.refresh(document)
    assert document.chunk_count == len(chunk_rows(db, document.id)) == 2


def test_embedding_failure_marks_failed_and_leaves_no_chunks(
    db, make_user, session_factory, settings, embedder
):
    user = make_user()
    document = add_document(db, user, PAGES)
    embedder.fail_with = EmbeddingError(EMBEDDING_FAILED_MESSAGE)

    index_document(session_factory, settings, embedder, document.id)

    db.refresh(document)
    assert document.index_status == INDEX_FAILED
    assert document.index_error == EMBEDDING_FAILED_MESSAGE
    assert chunk_rows(db, document.id) == []


def test_unexpected_error_gives_a_generic_message(
    db, make_user, session_factory, settings, embedder
):
    user = make_user()
    document = add_document(db, user, PAGES)
    embedder.fail_with = RuntimeError("secret internal detail")

    index_document(session_factory, settings, embedder, document.id)

    db.refresh(document)
    assert document.index_status == INDEX_FAILED
    assert document.index_error == GENERIC_INDEX_FAILURE_MESSAGE
    assert "secret" not in document.index_error


def test_failed_reindex_removes_the_previous_chunks(
    db, make_user, session_factory, settings, embedder
):
    user = make_user()
    document = add_document(db, user, PAGES)
    index_document(session_factory, settings, embedder, document.id)
    embedder.fail_with = EmbeddingError(EMBEDDING_FAILED_MESSAGE)

    index_document(session_factory, settings, embedder, document.id)

    assert chunk_rows(db, document.id) == []


def test_document_that_is_not_completed_is_not_indexed(
    db, make_user, session_factory, settings, embedder
):
    user = make_user()
    document = add_document(db, user, PAGES, status=PENDING, index_status=None)

    index_document(session_factory, settings, embedder, document.id)

    db.refresh(document)
    assert document.index_status is None
    assert embedder.document_calls == []


def test_pages_without_text_fail_with_a_clear_message(
    db, make_user, session_factory, settings, embedder
):
    user = make_user()
    document = add_document(db, user, ["   ", ""])

    index_document(session_factory, settings, embedder, document.id)

    db.refresh(document)
    assert document.index_status == INDEX_FAILED
    assert document.index_error == NO_CHUNKS_MESSAGE
    assert embedder.document_calls == []


def test_reindex_is_refused_while_indexing_is_running(db, make_user, settings):
    user = make_user()
    document = add_document(db, user, PAGES, index_status=INDEX_INDEXING)

    with pytest.raises(ReindexRejected):
        request_reindex(db, settings, user, document.id)


def test_reindex_is_refused_when_already_current(db, make_user, settings):
    user = make_user()
    document = add_document(db, user, PAGES, index_status=INDEX_INDEXED)
    document.embedding_model = settings.embedding_model
    document.chunk_target_chars = settings.chunk_target_chars
    document.chunk_overlap_chars = settings.chunk_overlap_chars
    db.commit()

    with pytest.raises(ReindexRejected):
        request_reindex(db, settings, user, document.id)


def test_reindex_is_allowed_when_the_chunk_settings_changed(db, make_user, settings):
    user = make_user()
    document = add_document(db, user, PAGES, index_status=INDEX_INDEXED)
    document.embedding_model = settings.embedding_model
    document.chunk_target_chars = 500
    document.chunk_overlap_chars = settings.chunk_overlap_chars
    db.commit()

    request_reindex(db, settings, user, document.id)

    db.refresh(document)
    assert document.index_status == INDEX_PENDING


def test_reindex_is_allowed_after_a_failed_index(db, make_user, settings):
    user = make_user()
    document = add_document(db, user, PAGES, index_status=INDEX_FAILED)

    request_reindex(db, settings, user, document.id)

    db.refresh(document)
    assert document.index_status == INDEX_PENDING
    assert document.index_error is None


def test_stale_indexing_is_marked_failed_at_startup(db, make_user):
    user = make_user()
    now = datetime.now(UTC)
    stale = add_document(
        db, user, PAGES, index_status=INDEX_INDEXING, updated_at=now - timedelta(hours=1)
    )
    fresh = add_document(db, user, PAGES, index_status=INDEX_INDEXING, updated_at=now)

    recover_stuck_documents(db, now=now)

    db.refresh(stale)
    db.refresh(fresh)
    assert stale.index_status == INDEX_FAILED
    assert stale.index_error == INDEX_INTERRUPTED_MESSAGE
    assert fresh.index_status == INDEX_INDEXING


def test_deleting_a_document_removes_its_chunks(
    db, make_user, session_factory, settings, embedder, storage
):
    from app.services.document_service import delete_document

    user = make_user()
    document = add_document(db, user, PAGES)
    index_document(session_factory, settings, embedder, document.id)
    document_id = document.id

    delete_document(db, storage, user, document_id)

    assert db.scalars(select(DocumentChunk)).all() == []
