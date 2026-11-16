import logging
import math
import time
from collections.abc import Callable, Sequence
from typing import Any, Protocol

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

logger = logging.getLogger(__name__)

DOCUMENT_TASK = "RETRIEVAL_DOCUMENT"
QUERY_TASK = "RETRIEVAL_QUERY"
RETRYABLE_CODES = frozenset({429, 500, 502, 503, 504})
BACKOFF_SECONDS = (1, 2, 4, 8)
MAX_ATTEMPTS = len(BACKOFF_SECONDS) + 1
NOT_CONFIGURED_MESSAGE = "Document search isn't configured yet."
EMBEDDING_FAILED_MESSAGE = "The embedding service is unavailable. Please try again later."


class EmbeddingError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class Embedder(Protocol):
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class GeminiEmbedder:
    """Gemini embeddings at a fixed output size, L2-normalized.

    gemini-embedding-001 needs manual normalization below 3072 dimensions.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        dimensions: int,
        batch_size: int,
        *,
        client: Any = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._batch_size = batch_size
        self._client = client
        self._sleep = sleep

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = list(texts[start : start + self._batch_size])
            vectors.extend(self._embed(batch, DOCUMENT_TASK))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], QUERY_TASK)[0]

    def _get_client(self) -> Any:
        if self._client is None:
            if not self._api_key:
                raise EmbeddingError(NOT_CONFIGURED_MESSAGE)
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = self._get_client().models.embed_content(
                    model=self._model,
                    contents=texts,
                    config=types.EmbedContentConfig(
                        task_type=task_type, output_dimensionality=self._dimensions
                    ),
                )
            except genai_errors.APIError as exc:
                if exc.code in RETRYABLE_CODES and attempt < len(BACKOFF_SECONDS):
                    logger.warning("Embedding call failed with %s; retrying", exc.code)
                    self._sleep(BACKOFF_SECONDS[attempt])
                    continue
                logger.exception("Embedding call failed")
                raise EmbeddingError(EMBEDDING_FAILED_MESSAGE) from exc
            return self._vectors(response, texts)
        raise EmbeddingError(EMBEDDING_FAILED_MESSAGE)

    def _vectors(self, response: Any, texts: list[str]) -> list[list[float]]:
        embeddings = response.embeddings or []
        if len(embeddings) != len(texts):
            raise EmbeddingError(EMBEDDING_FAILED_MESSAGE)
        vectors = []
        for item in embeddings:
            values = list(item.values or [])
            if len(values) != self._dimensions:
                raise EmbeddingError(EMBEDDING_FAILED_MESSAGE)
            vectors.append(_normalize(values))
        return vectors


def _normalize(values: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise EmbeddingError(EMBEDDING_FAILED_MESSAGE)
    return [value / norm for value in values]
