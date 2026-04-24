"""Dimension agent tests with a mocked Completion."""
from __future__ import annotations

import asyncio

import pytest

from amaya.agents.completion import StubCompletion
from amaya.agents.dimension import score_dimension
from amaya.ingest.types import ClassifiedChunk, RawChunk


def _chunk(section: str, text: str) -> ClassifiedChunk:
    return ClassifiedChunk(
        section=section,
        section_confidence=0.9,
        raw=RawChunk(
            source_file="doc.txt",
            source_id="b" * 64,
            kind="document",
            locator="page=1",
            text=text,
        ),
    )


def test_score_dimension_happy_path() -> None:
    async def _go():
        evidence = [_chunk("MKT", "Category shrinking 30%.")]
        stub = StubCompletion(
            responder=lambda tool, _: {
                "score": 4,
                "rationale": "Evidence [1] shows contracting category.",
                "confidence": 0.85,
                "evidence_indices": [1],
            }
        )
        result = await score_dimension("MCS", "Colabor", "Food", evidence, stub)
        assert result.code == "MCS"
        assert result.score == 4
        assert result.confidence == 0.85
        assert "[1]" in result.rationale
        assert len(result.evidence) == 1
        assert result.evidence[0].source_id == "b" * 64

    asyncio.run(_go())


def test_score_dimension_clips_confidence_out_of_range() -> None:
    async def _go():
        evidence = [_chunk("MKT", "x")]
        stub = StubCompletion(
            responder=lambda *_: {
                "score": 5,
                "rationale": "r",
                "confidence": 1.5,  # out of range
                "evidence_indices": [],
            }
        )
        result = await score_dimension("MCS", "X", "", evidence, stub)
        assert result.confidence == 1.0

    asyncio.run(_go())


def test_score_dimension_rejects_out_of_range_score() -> None:
    async def _go():
        evidence = [_chunk("MKT", "x")]
        stub = StubCompletion(
            responder=lambda *_: {
                "score": 11,
                "rationale": "r",
                "confidence": 0.5,
                "evidence_indices": [],
            }
        )
        with pytest.raises(ValueError, match="must be 1-10"):
            await score_dimension("MCS", "X", "", evidence, stub)

    asyncio.run(_go())


def test_score_dimension_ignores_invalid_evidence_indices() -> None:
    async def _go():
        evidence = [_chunk("MKT", "a"), _chunk("MKT", "b")]
        stub = StubCompletion(
            responder=lambda *_: {
                "score": 6,
                "rationale": "r",
                "confidence": 0.7,
                "evidence_indices": [1, 99, "garbage", 2],
            }
        )
        result = await score_dimension("MCS", "X", "", evidence, stub)
        # only 1 and 2 are valid (1-indexed)
        assert len(result.evidence) == 2

    asyncio.run(_go())


def test_score_dimension_passes_system_prompt() -> None:
    async def _go():
        evidence = [_chunk("MKT", "x")]
        stub = StubCompletion(
            responder=lambda *_: {
                "score": 5,
                "rationale": "r",
                "confidence": 0.5,
                "evidence_indices": [],
            }
        )
        await score_dimension("MCS", "X", "", evidence, stub)
        call = stub.calls[0]
        assert "Amaya Intelligence" in call["system"]
        assert "submit_MCS_score" == call["tool_name"]
        assert "Market Category Stability" in call["user_message"]

    asyncio.run(_go())


def test_score_dimension_with_empty_evidence() -> None:
    async def _go():
        stub = StubCompletion(
            responder=lambda *_: {
                "score": 5,
                "rationale": "no evidence provided; conservative midpoint",
                "confidence": 0.2,
                "evidence_indices": [],
            }
        )
        result = await score_dimension("MCS", "X", "", [], stub)
        assert result.score == 5
        assert result.confidence == 0.2
        assert result.evidence == []

    asyncio.run(_go())
