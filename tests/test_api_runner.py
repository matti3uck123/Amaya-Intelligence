"""Unit tests for the background runner — no HTTP involved."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from amaya.agents.completion import StubCompletion
from amaya.api.jobs import RatingJob
from amaya.api.runner import run_rating_job
from amaya.ingest import KeywordClassifier

SAMPLE_ROOM = Path(__file__).parent.parent / "examples" / "sample_dataroom"


def _responder(tool_name: str, _user: str) -> dict[str, Any]:
    core = tool_name.removeprefix("submit_").removesuffix("_score")
    is_chain = core in {"upstream", "downstream", "lateral", "end_consumer"}
    resp: dict[str, Any] = {"score": 5, "rationale": "r"}
    if not is_chain:
        resp["confidence"] = 0.8
        resp["evidence_indices"] = []
    return resp


def test_runner_drives_job_to_done() -> None:
    async def _go():
        job = RatingJob(rating_id="adi-run-1", company_name="X", sector="")
        await run_rating_job(
            job,
            dataroom_path=SAMPLE_ROOM,
            completion=StubCompletion(responder=_responder),
            classifier=KeywordClassifier(),
        )
        assert job.status == "done"
        assert job.rating is not None
        assert job.rating.result.grade
        assert job.dimensions_done == 12
        assert job.chain_done == 4
        # History should include: status×4, ingest, agents × 32, rating, status=done
        types = [e.get("type") for e in job.history]
        assert types.count("status") >= 4
        assert types.count("agent") == 32
        assert types.count("rating") == 1

    asyncio.run(_go())


def test_runner_captures_errors_as_failed() -> None:
    async def _go():
        job = RatingJob(rating_id="adi-run-err", company_name="X", sector="")

        def bad(tool_name: str, _user: str) -> dict[str, Any]:
            raise RuntimeError("kaboom")

        await run_rating_job(
            job,
            dataroom_path=SAMPLE_ROOM,
            completion=StubCompletion(responder=bad),
            classifier=KeywordClassifier(),
        )
        assert job.status == "failed"
        assert job.error is not None
        assert "kaboom" in job.error
        assert job.rating is None

    asyncio.run(_go())


def test_runner_seals_when_ledger_supplied(tmp_path: Path) -> None:
    from amaya.provenance import ProvenanceLedger

    async def _go():
        job = RatingJob(rating_id="adi-run-seal", company_name="X", sector="")
        ledger = ProvenanceLedger(tmp_path / "ledger")
        await run_rating_job(
            job,
            dataroom_path=SAMPLE_ROOM,
            completion=StubCompletion(responder=_responder),
            classifier=KeywordClassifier(),
            ledger=ledger,
        )
        assert job.status == "done"
        assert job.sealed_digest
        assert (tmp_path / "ledger" / "adi-run-seal.json").exists()
        assert ledger.verify("adi-run-seal") is True

    asyncio.run(_go())
