import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

DocumentStatus = Literal["pending", "processing", "completed", "failed"]
IndexStatus = Literal["pending", "indexing", "indexed", "failed"]


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    status: DocumentStatus
    page_count: int | None
    size_bytes: int
    error_message: str | None
    index_status: IndexStatus | None
    index_error: str | None
    chunk_count: int | None
    created_at: datetime
    updated_at: datetime
