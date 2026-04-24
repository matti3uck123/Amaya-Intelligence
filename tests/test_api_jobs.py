"""Unit tests for the job registry + event bus."""
from __future__ import annotations

import asyncio

import pytest

from amaya.api.jobs import JobRegistry, RatingJob


def test_registry_creates_unique_id() -> None:
    r = JobRegistry()
    j1 = r.create(company_name="A")
    j2 = r.create(company_name="B")
    assert j1.rating_id != j2.rating_id
    assert r.get(j1.rating_id) is j1
    assert r.get(j2.rating_id) is j2


def test_registry_rejects_duplicate_explicit_id() -> None:
    r = JobRegistry()
    r.create(company_name="A", rating_id="fixed")
    with pytest.raises(ValueError):
        r.create(company_name="B", rating_id="fixed")


def test_emit_appends_history() -> None:
    job = RatingJob(rating_id="r1", company_name="X", sector="")
    job.emit({"type": "status", "status": "ingesting"})
    job.emit({"type": "agent", "event": "start", "name": "MCS"})
    assert len(job.history) == 2
    assert job.history[0]["status"] == "ingesting"


def test_subscribe_replays_history_then_streams_live() -> None:
    async def _go():
        job = RatingJob(rating_id="r1", company_name="X", sector="")
        job.emit({"type": "status", "status": "ingesting"})
        q = job.subscribe()

        # History replay available immediately.
        first = await asyncio.wait_for(q.get(), timeout=0.1)
        assert first["status"] == "ingesting"

        # Live event flows through the queue.
        job.emit({"type": "agent", "event": "start", "name": "MCS"})
        live = await asyncio.wait_for(q.get(), timeout=0.1)
        assert live["name"] == "MCS"

        # finalize pushes the None sentinel to existing subscribers.
        job.finalize()
        sentinel = await asyncio.wait_for(q.get(), timeout=0.1)
        assert sentinel is None

    asyncio.run(_go())


def test_subscribe_after_terminal_sends_history_and_sentinel() -> None:
    async def _go():
        job = RatingJob(rating_id="r1", company_name="X", sector="")
        job.emit({"type": "status", "status": "done"})
        job.status = "done"

        q = job.subscribe()
        e1 = await asyncio.wait_for(q.get(), timeout=0.1)
        e2 = await asyncio.wait_for(q.get(), timeout=0.1)
        assert e1["status"] == "done"
        assert e2 is None

    asyncio.run(_go())


def test_record_agent_event_counts_dimensions_and_chain() -> None:
    job = RatingJob(rating_id="r1", company_name="X", sector="")
    job.record_agent_event("start", "MCS")
    job.record_agent_event("done", "MCS")
    job.record_agent_event("done", "upstream")
    assert job.dimensions_done == 1
    assert job.chain_done == 1
