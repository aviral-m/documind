import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.db.chunk_queries import replace_document_chunks, search_chunks
from app.db.session import build_engine
from app.models import Document, DocumentChunk, User
from app.models.document import COMPLETED, INDEX_INDEXED
from app.rag.types import Chunk
from tests.fakes import vector_for

pytestmark = pytest.mark.integration


@pytest.fixture
def pg_session():
    url = get_settings().test_database_url
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    engine = build_engine(url)
    connection = engine.connect()
    has_vector = connection.execute(
        text("select 1 from pg_extension where extname = 'vector'")
    ).scalar()
    if not has_vector:
        connection.close()
        engine.dispose()
        pytest.skip("The vector extension is not installed on TEST_DATABASE_URL")
    Base.metadata.create_all(connection)
    # Everything runs inside one transaction that is rolled back, so nothing is kept.
    outer = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False)()
    yield session
    session.close()
    outer.rollback()
    connection.close()
    engine.dispose()


def make_user(session: Session) -> User:
    user = User(email=f"{uuid.uuid4()}@example.com", is_verified=True)
    session.add(user)
    session.flush()
    return user


def make_document(session: Session, user: User, filename: str) -> Document:
    document = Document(
        id=uuid.uuid4(),
        user_id=user.id,
        filename=filename,
        storage_path=f"documind/{user.id}/{filename}",
        size_bytes=1,
        status=COMPLETED,
        index_status=INDEX_INDEXED,
    )
    session.add(document)
    session.flush()
    return document


def load(session: Session, document: Document, texts: list[str]) -> None:
    chunks = [
        Chunk(chunk_index=index, page_number=index + 1, text=value)
        for index, value in enumerate(texts)
    ]
    replace_document_chunks(session, document.id, chunks, [vector_for(v) for v in texts])


def test_nearest_chunk_is_returned_first(pg_session):
    user = make_user(pg_session)
    document = make_document(pg_session, user, "policy.pdf")
    load(pg_session, document, ["Shipping takes five weeks.", "Refunds take fourteen days."])

    hits = search_chunks(
        pg_session, user.id, [document.id], vector_for("how long do refunds take"), top_k=2
    )

    assert hits[0].text == "Refunds take fourteen days."
    assert hits[0].filename == "policy.pdf"
    assert hits[0].page_number == 2
    assert hits[0].distance <= hits[1].distance


def test_results_are_limited_to_the_selected_documents(pg_session):
    user = make_user(pg_session)
    selected = make_document(pg_session, user, "selected.pdf")
    other = make_document(pg_session, user, "other.pdf")
    load(pg_session, selected, ["Refunds take fourteen days."])
    load(pg_session, other, ["Refunds take thirty days in another policy."])

    hits = search_chunks(pg_session, user.id, [selected.id], vector_for("refunds"), top_k=5)

    assert [hit.document_id for hit in hits] == [selected.id]


def test_another_users_documents_are_never_returned(pg_session):
    owner = make_user(pg_session)
    intruder = make_user(pg_session)
    document = make_document(pg_session, owner, "private.pdf")
    load(pg_session, document, ["Confidential refund terms."])

    hits = search_chunks(pg_session, intruder.id, [document.id], vector_for("refund"), top_k=5)

    assert hits == []


def test_top_k_is_respected(pg_session):
    user = make_user(pg_session)
    document = make_document(pg_session, user, "long.pdf")
    load(pg_session, document, [f"Clause {number} covers refunds." for number in range(12)])

    hits = search_chunks(pg_session, user.id, [document.id], vector_for("refunds"), top_k=4)

    assert len(hits) == 4


def test_filtered_search_returns_enough_results_next_to_other_documents(pg_session):
    # HNSW search can miss results when most rows are filtered out. This checks it doesn't.
    user = make_user(pg_session)
    selected = make_document(pg_session, user, "selected.pdf")
    load(pg_session, selected, [f"Selected clause {n} about refunds." for n in range(5)])
    for number in range(3):
        noisy = make_document(pg_session, user, f"noisy-{number}.pdf")
        load(pg_session, noisy, [f"Noise {n} about refunds." for n in range(200)])

    hits = search_chunks(pg_session, user.id, [selected.id], vector_for("refunds"), top_k=5)

    assert len(hits) == 5
    assert {hit.document_id for hit in hits} == {selected.id}


def test_replacing_chunks_leaves_no_old_rows(pg_session):
    user = make_user(pg_session)
    document = make_document(pg_session, user, "policy.pdf")
    load(pg_session, document, ["first", "second", "third"])

    load(pg_session, document, ["only"])

    rows = pg_session.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == document.id)
    ).all()
    assert [row.text for row in rows] == ["only"]


def test_deleting_a_document_removes_its_chunks(pg_session):
    user = make_user(pg_session)
    document = make_document(pg_session, user, "policy.pdf")
    load(pg_session, document, ["some text"])

    pg_session.delete(document)
    pg_session.flush()

    assert pg_session.scalars(select(DocumentChunk)).all() == []
