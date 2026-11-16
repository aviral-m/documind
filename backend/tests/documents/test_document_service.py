import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models import Document
from app.models.document import COMPLETED, FAILED, PENDING, PROCESSING
from app.services.document_service import (
    INTERRUPTED_MESSAGE,
    build_public_id,
    delete_document,
    recover_stuck_documents,
    sanitize_filename,
)
from app.services.extraction import (
    NO_TEXT_MESSAGE,
    TOO_MANY_PAGES_MESSAGE,
    ExtractionError,
    extract_pages,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("report.pdf", "report.pdf"),
        ("C:\\Users\\me\\Downloads\\report.pdf", "report.pdf"),
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("bad\x00name\x07.pdf", "badname.pdf"),
        ("", "document.pdf"),
        (None, "document.pdf"),
        ("a" * 300 + ".pdf", "a" * 255),
    ],
)
def test_sanitize_filename(raw, expected):
    assert sanitize_filename(raw) == expected


def test_public_id_is_built_from_user_and_document_ids():
    user_id = uuid.uuid4()
    document_id = uuid.uuid4()

    assert build_public_id(user_id, document_id) == f"documind/{user_id}/{document_id}"


def test_extract_pages_returns_text_per_page(make_pdf):
    pages = extract_pages(make_pdf(["alpha", "beta", "gamma"]), max_pages=500)

    assert len(pages) == 3
    assert "alpha" in pages[0]
    assert "gamma" in pages[2]


def test_extract_pages_rejects_too_many_pages(make_pdf):
    with pytest.raises(ExtractionError) as excinfo:
        extract_pages(make_pdf(["one", "two", "three"]), max_pages=2)

    assert excinfo.value.message == TOO_MANY_PAGES_MESSAGE.format(max_pages=2)


def test_extract_pages_rejects_image_only_or_blank_pdf(make_pdf):
    with pytest.raises(ExtractionError) as excinfo:
        extract_pages(make_pdf(["", ""]), max_pages=500)

    assert excinfo.value.message == NO_TEXT_MESSAGE


def test_extract_pages_rejects_bytes_that_are_not_a_pdf():
    with pytest.raises(ExtractionError):
        extract_pages(b"%PDF-1.4 not really a pdf", max_pages=500)


def add_document(db, user, status, updated_at):
    document = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        filename="doc.pdf",
        storage_path=f"documind/{user.id}/doc.pdf",
        size_bytes=10,
        status=status,
        updated_at=updated_at,
    )
    db.add(document)
    db.commit()
    return document


def test_recovery_fails_only_old_unfinished_documents(db, make_user):
    user = make_user()
    now = datetime.now(UTC)
    old = now - timedelta(hours=1)
    stale_pending = add_document(db, user, PENDING, old)
    stale_processing = add_document(db, user, PROCESSING, old)
    fresh_processing = add_document(db, user, PROCESSING, now)
    old_completed = add_document(db, user, COMPLETED, old)

    count = recover_stuck_documents(db, now=now)

    assert count == 2
    db.refresh(stale_pending)
    db.refresh(stale_processing)
    db.refresh(fresh_processing)
    db.refresh(old_completed)
    assert stale_pending.status == FAILED
    assert stale_pending.error_message == INTERRUPTED_MESSAGE
    assert stale_processing.status == FAILED
    assert fresh_processing.status == PROCESSING
    assert old_completed.status == COMPLETED


def test_deleting_document_whose_remote_file_is_already_gone(db, make_user, storage):
    user = make_user()
    document = add_document(db, user, COMPLETED, datetime.now(UTC))
    document_id = document.id

    delete_document(db, storage, user, document_id)

    assert db.get(Document, document_id) is None
