import math

import pytest

from app.core.config import get_settings
from app.rag.embeddings import GeminiEmbedder

pytestmark = pytest.mark.integration


@pytest.fixture
def gemini():
    settings = get_settings()
    if not settings.gemini_api_key:
        pytest.skip("GEMINI_API_KEY is not set")
    return GeminiEmbedder(
        settings.gemini_api_key,
        settings.embedding_model,
        settings.embedding_dimensions,
        settings.embedding_batch_size,
    )


def test_gemini_returns_normalized_vectors_of_the_column_size(gemini):
    vectors = gemini.embed_documents(["Refunds are processed within fourteen days.", "Hello."])

    assert [len(vector) for vector in vectors] == [768, 768]
    assert all(math.isclose(sum(v * v for v in vector), 1.0, rel_tol=1e-6) for vector in vectors)


def test_related_query_is_closer_than_unrelated_text(gemini):
    documents = gemini.embed_documents(
        ["Refunds are processed within fourteen days.", "Penguins live in Antarctica."]
    )
    query = gemini.embed_query("How long do refunds take?")

    def similarity(a, b):
        return sum(x * y for x, y in zip(a, b, strict=True))

    assert similarity(query, documents[0]) > similarity(query, documents[1])
