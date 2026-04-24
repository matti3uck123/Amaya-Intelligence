"""One dimension agent: classified evidence → DimensionScore."""
from __future__ import annotations

from typing import Sequence

from amaya.agents.completion import Completion
from amaya.agents.prompts import (
    DIMENSION_SPECS,
    SYSTEM_PROMPT,
    build_dimension_prompt,
    dimension_tool_schema,
    format_evidence,
)
from amaya.ingest.types import ClassifiedChunk
from amaya.schemas import DimensionCode, DimensionScore, EvidenceRef


async def score_dimension(
    code: DimensionCode,
    company_name: str,
    sector: str,
    evidence_chunks: Sequence[ClassifiedChunk],
    completion: Completion,
) -> DimensionScore:
    """Score one ADI dimension from the provided evidence.

    `evidence_chunks` should already be filtered to the sections that
    feed this dimension (see sections_for_dimension). The agent reads
    all provided chunks — it is the orchestrator's job to pre-filter.
    """
    spec = DIMENSION_SPECS[code]
    evidence_text = format_evidence(evidence_chunks)
    user_message = build_dimension_prompt(spec, company_name, sector, evidence_text)
    tool_name = f"submit_{code}_score"
    tool_schema = dimension_tool_schema(code)

    response = await completion.complete(
        system=SYSTEM_PROMPT,
        user_message=user_message,
        tool_name=tool_name,
        tool_schema=tool_schema,
    )

    score = int(response["score"])
    if not 1 <= score <= 10:
        raise ValueError(f"{code} agent returned score {score}, must be 1-10")
    confidence = float(response.get("confidence", 0.8))
    confidence = max(0.0, min(1.0, confidence))
    rationale = str(response["rationale"]).strip()
    evidence_indices = response.get("evidence_indices", []) or []

    evidence_refs: list[EvidenceRef] = []
    for idx in evidence_indices:
        try:
            idx_int = int(idx)
        except (TypeError, ValueError):
            continue
        if 1 <= idx_int <= len(evidence_chunks):
            evidence_refs.append(evidence_chunks[idx_int - 1].to_evidence_ref())

    return DimensionScore(
        code=code,
        score=score,
        rationale=rationale,
        confidence=confidence,
        evidence=evidence_refs,
    )
