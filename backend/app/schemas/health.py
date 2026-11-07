from typing import Literal

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    status: Literal["ok"]


class DatabaseHealthResponse(BaseModel):
    status: Literal["ok"]
    database: Literal["connected"]
    latency_ms: float
