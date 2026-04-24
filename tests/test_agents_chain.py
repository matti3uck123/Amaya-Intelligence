"""Chain-agent tests with a mocked Completion."""
from __future__ import annotations

import asyncio

import pytest

from amaya.agents.chain import score_chain_position
from amaya.agents.completion import StubCompletion
from amaya.ingest.types import ClassifiedChunk, RawChunk


def _chunk(text: str) -> ClassifiedChunk:
    return ClassifiedChunk(
        section="OPS",
        section_confidence=0.9,
        raw=RawChunk(
            source_file="ops.txt",
            source_id="c" * 64,
            kind="document",
            locator="page=1",
            text=text,
        ),
    )


def test_chain_agent_happy_path() -> None:
    async def _go():
        evidence = [_chunk("Upstream suppliers adopting AI.")]
        stub = StubCompletion(
            responder=lambda *_: {"score": 4, "rationale": "Evidence [1]."}
        )
        result = await score_chain_position("upstream", "X", "Sector", evidence, stub)
        assert result.position == "upstream"
        assert result.score == 4
        assert "[1]" in result.rationale

    asyncio.run(_go())


def test_chain_agent_rejects_out_of_range() -> None:
    async def _go():
        stub = StubCompletion(responder=lambda *_: {"score": 0, "rationale": "r"})
        with pytest.raises(ValueError):
            await score_chain_position("upstream", "X", "", [], stub)

    asyncio.run(_go())


def test_chain_agent_uses_correct_tool_name() -> None:
    async def _go():
        stub = StubCompletion(responder=lambda *_: {"score": 5, "rationale": "r"})
        await score_chain_position("downstream", "X", "", [], stub)
        assert stub.calls[0]["tool_name"] == "submit_downstream_score"

    asyncio.run(_go())
