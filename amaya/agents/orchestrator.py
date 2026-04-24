"""The full rating pipeline: data room → RatingInput.

Runs 12 dimension agents + 4 chain agents in parallel against the
supplied Completion. Returns a validated RatingInput that the Session 1
scoring engine can consume directly. The caller decides whether to
score and seal from there.

Chain-agent evidence selection: we deliberately feed chain agents
everything the ingest found in MKT, COMP, OPS, CUST, and CORP — these
agents are reasoning about structural position, not product details.
"""
from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Sequence

from amaya.agents.chain import score_chain_position
from amaya.agents.completion import Completion
from amaya.agents.dimension import score_dimension
from amaya.agents.prompts import DIMENSION_SPECS
from amaya.ingest.sections import SectionCode
from amaya.ingest.types import ClassifiedChunk, IngestResult
from amaya.schemas import (
    ChainAssessment,
    ChainPosition,
    ChainPositionScore,
    DimensionCode,
    DimensionScore,
    RatingInput,
)

DIMENSION_CODES: tuple[DimensionCode, ...] = (
    "MCS", "CPS", "SCAE", "CLS",
    "VPR", "WCI", "RMV", "TSR",
    "LAL", "SPS", "ANCR", "DIM",
)

CHAIN_POSITIONS: tuple[ChainPosition, ...] = (
    "upstream", "downstream", "lateral", "end_consumer",
)

CHAIN_EVIDENCE_SECTIONS: tuple[SectionCode, ...] = (
    "MKT", "COMP", "OPS", "CUST", "CORP",
)


ProgressCallback = Callable[[str, str], None]
"""Called as (event, name). Events: 'start' | 'done' | 'error'."""


async def rate(
    rating_id: str,
    company_name: str,
    sector: str,
    ingest_result: IngestResult,
    completion: Completion,
    *,
    analyst_notes: str = "",
    on_progress: ProgressCallback | None = None,
) -> RatingInput:
    """Run the full agent pipeline and assemble a RatingInput.

    Runs all 16 agents concurrently. If any agent raises, the whole
    call raises — we do not half-rate.
    """
    chunks_by_section = ingest_result.by_section()
    dim_tasks = [
        _run_dimension(
            code, company_name, sector, chunks_by_section, completion, on_progress
        )
        for code in DIMENSION_CODES
    ]
    chain_tasks = [
        _run_chain(
            position, company_name, sector, chunks_by_section, completion, on_progress
        )
        for position in CHAIN_POSITIONS
    ]

    dimension_scores = await asyncio.gather(*dim_tasks)
    chain_scores = await asyncio.gather(*chain_tasks)

    return RatingInput(
        rating_id=rating_id,
        company_name=company_name,
        sector=sector,
        analyst_notes=analyst_notes,
        dimension_scores=list(dimension_scores),
        chain=ChainAssessment(positions=list(chain_scores)),
    )


async def _run_dimension(
    code: DimensionCode,
    company_name: str,
    sector: str,
    chunks_by_section: dict[str, list[ClassifiedChunk]],
    completion: Completion,
    on_progress: ProgressCallback | None,
) -> DimensionScore:
    spec = DIMENSION_SPECS[code]
    evidence = _collect_evidence(chunks_by_section, spec.evidence_sections)
    if on_progress:
        on_progress("start", code)
    try:
        result = await score_dimension(code, company_name, sector, evidence, completion)
    except Exception:
        if on_progress:
            on_progress("error", code)
        raise
    if on_progress:
        on_progress("done", code)
    return result


async def _run_chain(
    position: ChainPosition,
    company_name: str,
    sector: str,
    chunks_by_section: dict[str, list[ClassifiedChunk]],
    completion: Completion,
    on_progress: ProgressCallback | None,
) -> ChainPositionScore:
    evidence = _collect_evidence(chunks_by_section, CHAIN_EVIDENCE_SECTIONS)
    if on_progress:
        on_progress("start", position)
    try:
        result = await score_chain_position(
            position, company_name, sector, evidence, completion
        )
    except Exception:
        if on_progress:
            on_progress("error", position)
        raise
    if on_progress:
        on_progress("done", position)
    return result


def _collect_evidence(
    chunks_by_section: dict[str, list[ClassifiedChunk]],
    sections: Sequence[SectionCode],
) -> list[ClassifiedChunk]:
    out: list[ClassifiedChunk] = []
    for section in sections:
        out.extend(chunks_by_section.get(section, []))
    return out
