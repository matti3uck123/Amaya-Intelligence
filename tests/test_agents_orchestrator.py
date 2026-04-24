"""End-to-end orchestrator tests.

These wire the full pipeline — ingest → 12 dimension agents + 4 chain
agents → scoring engine → sealed rating — with a stubbed Completion.
No network, no API key, but exercises every layer's integration point.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from amaya import __version__
from amaya.agents import rate
from amaya.agents.completion import StubCompletion
from amaya.agents.orchestrator import CHAIN_POSITIONS, DIMENSION_CODES
from amaya.ingest import ingest
from amaya.methodology import load_methodology
from amaya.schemas import Rating
from amaya.scoring import score as score_rating

SAMPLE_ROOM = Path(__file__).parent.parent / "examples" / "sample_dataroom"


def _deterministic_responder(score_by_tool: dict[str, int]) -> Any:
    """Respond to every tool call with a fixed score.

    score_by_tool lets tests override specific agents; unlisted tools
    get a neutral 5.
    """

    def _responder(tool_name: str, _user: str) -> dict[str, Any]:
        score = score_by_tool.get(tool_name, 5)
        is_chain = tool_name.startswith("submit_") and tool_name.endswith("_score") and "_" in tool_name[7:-6]
        # chain tool names: submit_upstream_score etc; dim tool names: submit_MCS_score etc.
        # Dimension schema wants evidence_indices and confidence; chain doesn't.
        resp = {"score": score, "rationale": f"Stub rationale for {tool_name}."}
        if not _is_chain_tool(tool_name):
            resp["confidence"] = 0.8
            resp["evidence_indices"] = [1]
        return resp

    return _responder


def _is_chain_tool(tool_name: str) -> bool:
    core = tool_name.removeprefix("submit_").removesuffix("_score")
    return core in {"upstream", "downstream", "lateral", "end_consumer"}


def test_rate_runs_all_16_agents() -> None:
    async def _go():
        ingest_result = ingest(SAMPLE_ROOM)
        stub = StubCompletion(responder=_deterministic_responder({}))
        events: list[tuple[str, str]] = []

        rating_input = await rate(
            rating_id="adi-test-001",
            company_name="Colabor",
            sector="Food Distribution",
            ingest_result=ingest_result,
            completion=stub,
            on_progress=lambda ev, name: events.append((ev, name)),
        )

        assert len(stub.calls) == 16
        assert len(rating_input.dimension_scores) == 12
        assert len(rating_input.chain.positions) == 4
        dim_codes = {d.code for d in rating_input.dimension_scores}
        assert dim_codes == set(DIMENSION_CODES)
        chain_positions = {p.position for p in rating_input.chain.positions}
        assert chain_positions == set(CHAIN_POSITIONS)

        # every agent should emit exactly one start and one done
        start_events = [name for ev, name in events if ev == "start"]
        done_events = [name for ev, name in events if ev == "done"]
        assert len(start_events) == 16
        assert len(done_events) == 16

    asyncio.run(_go())


def test_rate_input_feeds_cleanly_into_scoring_engine() -> None:
    """The most important integration: agent output must be a valid
    RatingInput for the Session 1 scoring engine."""

    async def _go():
        ingest_result = ingest(SAMPLE_ROOM)
        # Colabor-like scores: soft on external pressure, weak on adaptive capacity
        tool_scores = {
            "submit_MCS_score": 6, "submit_CPS_score": 5,
            "submit_SCAE_score": 5, "submit_CLS_score": 4,
            "submit_VPR_score": 6, "submit_WCI_score": 4,
            "submit_RMV_score": 4, "submit_TSR_score": 6,
            "submit_LAL_score": 5, "submit_SPS_score": 4,
            "submit_ANCR_score": 1, "submit_DIM_score": 4,
            "submit_upstream_score": 5, "submit_downstream_score": 4,
            "submit_lateral_score": 4, "submit_end_consumer_score": 6,
        }
        stub = StubCompletion(responder=_deterministic_responder(tool_scores))

        rating_input = await rate(
            rating_id="adi-test-colabor",
            company_name="Colabor Group",
            sector="Food Distribution",
            ingest_result=ingest_result,
            completion=stub,
        )

        # Feed into scoring engine
        methodology = load_methodology("v1.0")
        result = score_rating(rating_input, methodology)

        # Colabor should land in the C/D range — not A+, not F
        assert 25 <= result.final_score <= 55, (
            f"expected C/D band, got {result.final_score} ({result.grade})"
        )
        assert result.grade in {"C+", "C", "D"}
        # ANCR=1 means MCS=6 doesn't trigger CB1. Check no CBs fire at these scores.
        assert not result.circuit_breakers_triggered

    asyncio.run(_go())


def test_rate_emits_rating_object_assembleable() -> None:
    async def _go():
        from datetime import datetime, timezone

        ingest_result = ingest(SAMPLE_ROOM)
        stub = StubCompletion(responder=_deterministic_responder({}))
        rating_input = await rate(
            rating_id="adi-test-002",
            company_name="X",
            sector="",
            ingest_result=ingest_result,
            completion=stub,
        )
        methodology = load_methodology("v1.0")
        result = score_rating(rating_input, methodology)
        rating = Rating(
            input=rating_input,
            result=result,
            issued_at=datetime.now(timezone.utc),
            methodology_version=methodology.version,
            pipeline_version=__version__,
        )
        assert rating.result.methodology_version == "1.0.0"
        assert rating.input.rating_id == "adi-test-002"

    asyncio.run(_go())


def test_rate_propagates_agent_errors() -> None:
    """If any agent raises, the whole rate() call raises — no half-ratings."""

    async def _go():
        ingest_result = ingest(SAMPLE_ROOM)

        def _responder(tool_name: str, _user: str) -> dict[str, Any]:
            if tool_name == "submit_MCS_score":
                raise RuntimeError("simulated API failure")
            return {
                "score": 5,
                "rationale": "r",
                "confidence": 0.5,
                "evidence_indices": [],
            }

        stub = StubCompletion(responder=_responder)
        with pytest.raises(RuntimeError, match="simulated"):
            await rate(
                rating_id="adi-test-fail",
                company_name="X",
                sector="",
                ingest_result=ingest_result,
                completion=stub,
            )

    asyncio.run(_go())


def test_rate_runs_agents_in_parallel() -> None:
    """Rough check that agents run concurrently, not sequentially.

    If they ran sequentially against a responder that sleeps 50ms,
    total would be ~800ms (16 * 50). In parallel, ~50ms. We assert
    under 500ms as a conservative proxy.
    """
    import time

    async def _go():
        ingest_result = ingest(SAMPLE_ROOM)

        async def _async_sleep_responder(tool_name: str, _user: str) -> dict[str, Any]:
            await asyncio.sleep(0.05)
            resp: dict[str, Any] = {"score": 5, "rationale": "r"}
            if not _is_chain_tool(tool_name):
                resp["confidence"] = 0.8
                resp["evidence_indices"] = []
            return resp

        class AsyncStub:
            def __init__(self) -> None:
                self.calls: list[dict[str, Any]] = []

            async def complete(self, system: str, user_message: str, tool_name: str, tool_schema: dict[str, Any]) -> dict[str, Any]:
                self.calls.append({"tool_name": tool_name})
                return await _async_sleep_responder(tool_name, user_message)

        stub = AsyncStub()
        t0 = time.perf_counter()
        await rate(
            rating_id="adi-test-parallel",
            company_name="X",
            sector="",
            ingest_result=ingest_result,
            completion=stub,
        )
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.5, f"agents not running in parallel: elapsed={elapsed:.3f}s"

    asyncio.run(_go())
