"""Pydantic schemas for ADI ratings.

These are the contracts between the scoring engine, the provenance ledger,
and any upstream producers (dimension agents, analyst workbench, CLI).
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, conint, confloat

DimensionCode = Literal[
    "MCS", "CPS", "SCAE", "CLS",
    "VPR", "WCI", "RMV", "TSR",
    "LAL", "SPS", "ANCR", "DIM",
]

ChainPosition = Literal["upstream", "downstream", "lateral", "end_consumer"]

Grade = Literal["A+", "A", "B+", "B", "C+", "C", "D", "F"]


class EvidenceRef(BaseModel):
    """Pointer to the evidence that produced a score.

    Either a document hash + span, or an interview utterance timestamp.
    """
    source_id: str = Field(description="Document SHA-256 or interview ID")
    kind: Literal["document", "interview", "external"] = "document"
    locator: str = Field(description="page:line, start_ms-end_ms, or URL")
    snippet: str = Field(default="", description="Verbatim quote — max 500 chars")


class DimensionScore(BaseModel):
    code: DimensionCode
    score: conint(ge=1, le=10)
    rationale: str
    confidence: confloat(ge=0.0, le=1.0) = 0.8
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ChainPositionScore(BaseModel):
    position: ChainPosition
    score: conint(ge=1, le=10)
    rationale: str = ""


class ChainAssessment(BaseModel):
    positions: list[ChainPositionScore]

    def by_position(self) -> dict[str, int]:
        return {p.position: p.score for p in self.positions}


class CircuitBreakerTrigger(BaseModel):
    code: str
    description: str
    cap: int


class ScoringResult(BaseModel):
    """Deterministic output of the scoring engine."""
    raw_score: float
    chain_modifier: float
    adjusted_score: float
    final_score: float
    grade: Grade
    grade_label: str
    grade_action: str
    circuit_breakers_triggered: list[CircuitBreakerTrigger] = Field(default_factory=list)
    methodology_version: str


class RatingInput(BaseModel):
    """Inputs the scoring engine consumes. Everything upstream of this is the
    LangGraph pipeline; everything downstream is deterministic."""
    rating_id: str
    company_name: str
    sector: str = ""
    dimension_scores: list[DimensionScore]
    chain: ChainAssessment
    analyst_notes: str = ""

    def dim_map(self) -> dict[str, int]:
        return {d.code: d.score for d in self.dimension_scores}


class Rating(BaseModel):
    """The full rating artifact — input + result + metadata.

    This is what gets sealed into the provenance bundle.
    """
    input: RatingInput
    result: ScoringResult
    issued_at: datetime
    methodology_version: str
    pipeline_version: str = "0.1.0"
