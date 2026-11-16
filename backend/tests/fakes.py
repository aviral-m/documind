import math
import re
import zlib

from app.models.document_chunk import EMBEDDING_DIMENSIONS


def vector_for(text: str) -> list[float]:
    """Bag-of-words vector: texts sharing words are close. Deterministic, no network."""
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        vector[zlib.crc32(word.encode()) % EMBEDDING_DIMENSIONS] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


class FakeEmbedder:
    """In-memory stand-in for GeminiEmbedder. No network."""

    def __init__(self) -> None:
        self.document_calls: list[list[str]] = []
        self.query_calls: list[str] = []
        self.fail_with: Exception | None = None

    def embed_documents(self, texts):
        self.document_calls.append(list(texts))
        if self.fail_with:
            raise self.fail_with
        return [vector_for(text) for text in texts]

    def embed_query(self, text):
        self.query_calls.append(text)
        if self.fail_with:
            raise self.fail_with
        return vector_for(text)
