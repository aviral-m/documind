import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

QueryText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class SearchRequest(BaseModel):
    query: QueryText
    document_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievedChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    text: str
    document_id: uuid.UUID
    filename: str
    page_number: int
    chunk_index: int
    distance: float


class SearchResponse(BaseModel):
    results: list[RetrievedChunkOut]
