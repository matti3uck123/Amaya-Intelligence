"""HTTP request/response models — thin DTOs over domain types."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from amaya.api.jobs import JobStatus
from amaya.schemas import Rating


class RatingCreateFromPathRequest(BaseModel):
    """Body for `POST /ratings/from-path` — server-local demo shortcut."""

    path: str = Field(description="Absolute or server-relative data-room path")
    company: str
    sector: str = ""
    notes: str = ""
    rating_id: str | None = None
    methodology: str = "v1.0"
    seal: bool = False


class RatingAcceptedResponse(BaseModel):
    """202 response after a rating job has been scheduled."""

    rating_id: str
    status: JobStatus
    created_at: datetime
    events_url: str
    detail_url: str


class RatingProgress(BaseModel):
    dimensions_done: int
    dimensions_total: int = 12
    chain_done: int
    chain_total: int = 4


class RatingStatusResponse(BaseModel):
    rating_id: str
    company_name: str
    sector: str
    status: JobStatus
    created_at: datetime
    progress: RatingProgress
    rating: Rating | None = None
    error: str | None = None
    sealed_digest: str | None = None


class RatingListItem(BaseModel):
    rating_id: str
    company_name: str
    sector: str
    status: JobStatus
    created_at: datetime
    grade: str | None = None
    final_score: float | None = None


class VerifyRequest(BaseModel):
    rating_id: str
    ledger_path: str


class VerifyResponse(BaseModel):
    rating_id: str
    verified: bool


class MethodologyResponse(BaseModel):
    version: str
    raw: dict[str, Any]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
