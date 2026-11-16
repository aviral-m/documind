import math
from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors

from app.rag.embeddings import (
    EMBEDDING_FAILED_MESSAGE,
    MAX_ATTEMPTS,
    NOT_CONFIGURED_MESSAGE,
    EmbeddingError,
    GeminiEmbedder,
)

DIMENSIONS = 768


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    def embed_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": list(contents), "config": config})
        outcome = self.outcomes.pop(0) if self.outcomes else None
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=[3.0, 4.0] + [0.0] * (DIMENSIONS - 2)) for _ in contents
            ]
        )


def make_embedder(outcomes, batch_size=100):
    models = FakeModels(outcomes)
    sleeps = []
    embedder = GeminiEmbedder(
        api_key="test-key",
        model="gemini-embedding-001",
        dimensions=DIMENSIONS,
        batch_size=batch_size,
        client=SimpleNamespace(models=models),
        sleep=sleeps.append,
    )
    return embedder, models, sleeps


def task_of(call):
    task = call["config"].task_type
    return getattr(task, "value", task)


def rate_limited():
    return genai_errors.APIError(429, {"error": {"message": "slow down"}})


def test_documents_are_sent_in_batches_with_the_document_task_type():
    embedder, models, _ = make_embedder([], batch_size=100)

    vectors = embedder.embed_documents([f"text {number}" for number in range(250)])

    assert [len(call["contents"]) for call in models.calls] == [100, 100, 50]
    assert all(task_of(call) == "RETRIEVAL_DOCUMENT" for call in models.calls)
    assert all(call["config"].output_dimensionality == DIMENSIONS for call in models.calls)
    assert len(vectors) == 250


def test_queries_use_the_query_task_type():
    embedder, models, _ = make_embedder([])

    embedder.embed_query("what is the refund policy?")

    assert len(models.calls) == 1
    assert task_of(models.calls[0]) == "RETRIEVAL_QUERY"


def test_vectors_are_normalized_to_unit_length():
    embedder, _, _ = make_embedder([])

    vector = embedder.embed_query("anything")

    assert math.isclose(sum(value * value for value in vector), 1.0)
    assert math.isclose(vector[0], 0.6)


def test_rate_limit_is_retried_with_backoff_then_succeeds():
    embedder, models, sleeps = make_embedder([rate_limited()])

    vector = embedder.embed_query("hello")

    assert len(models.calls) == 2
    assert sleeps == [1]
    assert len(vector) == DIMENSIONS


def test_persistent_server_errors_give_up_after_the_attempt_limit():
    unavailable = genai_errors.APIError(503, {"error": {"message": "busy"}})
    embedder, models, sleeps = make_embedder([unavailable] * MAX_ATTEMPTS)

    with pytest.raises(EmbeddingError) as excinfo:
        embedder.embed_query("hello")

    assert excinfo.value.message == EMBEDDING_FAILED_MESSAGE
    assert len(models.calls) == MAX_ATTEMPTS
    assert len(sleeps) == MAX_ATTEMPTS - 1


def test_other_api_errors_fail_without_retrying():
    bad_request = genai_errors.APIError(400, {"error": {"message": "bad input"}})
    embedder, models, sleeps = make_embedder([bad_request])

    with pytest.raises(EmbeddingError):
        embedder.embed_query("hello")

    assert len(models.calls) == 1
    assert sleeps == []


def test_wrong_dimension_from_the_api_is_an_error():
    class ShortModels:
        def embed_content(self, **kwargs):
            return SimpleNamespace(embeddings=[SimpleNamespace(values=[1.0, 2.0])])

    embedder = GeminiEmbedder(
        api_key="test-key",
        model="gemini-embedding-001",
        dimensions=DIMENSIONS,
        batch_size=10,
        client=SimpleNamespace(models=ShortModels()),
    )

    with pytest.raises(EmbeddingError):
        embedder.embed_query("hello")


def test_missing_api_key_is_reported_clearly():
    embedder = GeminiEmbedder(
        api_key="", model="gemini-embedding-001", dimensions=DIMENSIONS, batch_size=10
    )

    with pytest.raises(EmbeddingError) as excinfo:
        embedder.embed_query("hello")

    assert excinfo.value.message == NOT_CONFIGURED_MESSAGE
