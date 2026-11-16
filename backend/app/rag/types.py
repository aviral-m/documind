import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    chunk_index: int
    page_number: int
    text: str


@dataclass(frozen=True)
class SearchHit:
    text: str
    document_id: uuid.UUID
    filename: str
    page_number: int
    chunk_index: int
    distance: float


@dataclass(frozen=True)
class RetrievedChunk:
    rank: int
    text: str
    document_id: uuid.UUID
    filename: str
    page_number: int
    chunk_index: int
    distance: float
