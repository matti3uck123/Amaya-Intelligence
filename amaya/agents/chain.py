"""One chain-position agent: classified evidence → ChainPositionScore."""
from __future__ import annotations

from typing import Sequence

from amaya.agents.completion import Completion
from amaya.agents.prompts import (
    CHAIN_SPECS,
    SYSTEM_PROMPT,
    build_chain_prompt,
    chain_tool_schema,
    format_evidence,
)
from amaya.ingest.types import ClassifiedChunk
from amaya.schemas import ChainPosition, ChainPositionScore


async def score_chain_position(
    position: ChainPosition,
    company_name: str,
    sector: str,
    evidence_chunks: Sequence[ClassifiedChunk],
    completion: Completion,
) -> ChainPositionScore:
    """Score one of the four chain positions from the provided evidence.

    Chain-position agents see a broader evidence mix than dimension
    agents — the MKT + COMP + OPS + CUST sections are all relevant.
    """
    spec = CHAIN_SPECS[position]
    evidence_text = format_evidence(evidence_chunks)
    user_message = build_chain_prompt(spec, company_name, sector, evidence_text)
    tool_name = f"submit_{position}_score"
    tool_schema = chain_tool_schema(position)

    response = await completion.complete(
        system=SYSTEM_PROMPT,
        user_message=user_message,
        tool_name=tool_name,
        tool_schema=tool_schema,
    )

    score = int(response["score"])
    if not 1 <= score <= 10:
        raise ValueError(f"{position} agent returned score {score}, must be 1-10")
    rationale = str(response.get("rationale", "")).strip()

    return ChainPositionScore(position=position, score=score, rationale=rationale)
