import uuid

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.db.chunk_queries import search_chunks
from app.db.session import build_engine
from app.models import Document, DocumentPage, User
from app.models.document import COMPLETED, INDEX_PENDING
from app.rag.embeddings import GeminiEmbedder
from app.services.indexing_service import index_document

pytestmark = pytest.mark.integration

# Each document has one topic per page. Each question names the page it should find.
DOCUMENTS = [
    [
        "Refunds are processed within fourteen days after the returned item arrives.",
        "Shipping to overseas addresses takes three to five weeks by sea freight.",
        "Warranty claims require the original receipt and the serial number.",
    ],
    [
        "Employees accrue twenty days of paid leave each calendar year.",
        "Expense reports must be submitted within thirty days of the purchase.",
        "The office is closed on public holidays and during the winter shutdown.",
    ],
]

QUESTIONS = [
    (0, 0, "How long do refunds take after the item is returned?"),
    (0, 1, "How long does overseas shipping take by sea?"),
    (0, 2, "What do I need for a warranty claim?"),
    (1, 0, "How many days of paid leave do employees get?"),
    (1, 1, "When must expense reports be submitted?"),
]


@pytest.fixture
def eval_setup():
    settings = get_settings()
    if not settings.test_database_url:
        pytest.skip("TEST_DATABASE_URL is not set")
    if not settings.gemini_api_key:
        pytest.skip("GEMINI_API_KEY is not set")
    engine = build_engine(settings.test_database_url)
    Base.metadata.create_all(engine)
    yield settings, sessionmaker(bind=engine, expire_on_commit=False), engine
    engine.dispose()


def test_expected_page_is_in_the_top_three_for_most_questions(eval_setup):
    # A regression smoke check against the real Gemini API and Postgres, not a benchmark.
    settings, session_factory, _ = eval_setup
    embedder = GeminiEmbedder(
        settings.gemini_api_key,
        settings.embedding_model,
        settings.embedding_dimensions,
        settings.embedding_batch_size,
    )
    user_id = uuid.uuid4()
    document_ids: list[uuid.UUID] = []

    with session_factory() as db:
        db.add(User(id=user_id, email=f"{user_id}@example.com", is_verified=True))
        db.commit()
        for number, pages in enumerate(DOCUMENTS):
            document_id = uuid.uuid4()
            document_ids.append(document_id)
            db.add(
                Document(
                    id=document_id,
                    user_id=user_id,
                    filename=f"eval-{number}.pdf",
                    storage_path=f"eval/{document_id}",
                    size_bytes=1,
                    page_count=len(pages),
                    status=COMPLETED,
                    index_status=INDEX_PENDING,
                )
            )
            db.add_all(
                DocumentPage(document_id=document_id, page_number=page, text=text)
                for page, text in enumerate(pages, start=1)
            )
        db.commit()

    try:
        for document_id in document_ids:
            index_document(session_factory, settings, embedder, document_id)

        passed = 0
        with session_factory() as db:
            for document_index, page, question in QUESTIONS:
                hits = search_chunks(
                    db,
                    user_id,
                    [document_ids[document_index]],
                    embedder.embed_query(question),
                    top_k=3,
                )
                if page in [hit.page_number for hit in hits]:
                    passed += 1

        assert passed >= 4, f"Only {passed} of {len(QUESTIONS)} questions found the page"
    finally:
        with session_factory() as db:
            db.query(User).filter(User.id == user_id).delete()
            db.commit()
