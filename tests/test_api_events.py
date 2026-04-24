"""SSE event-stream tests.

The TestClient supports streaming responses; we split the SSE body into
event blocks and assert the key progress markers show up.
"""
from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient


def _parse_sse(body: str) -> list[dict]:
    """Minimal SSE parser — enough for our structured events."""
    # sse-starlette uses CRLF; normalize before splitting on blank lines.
    normalized = body.replace("\r\n", "\n")
    events = []
    for block in normalized.strip().split("\n\n"):
        event_type: str | None = None
        data_lines: list[str] = []
        for line in block.splitlines():
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if not data_lines:
            continue
        try:
            payload = json.loads("\n".join(data_lines))
        except json.JSONDecodeError:
            continue
        payload["_event"] = event_type
        events.append(payload)
    return events


def _wait_done(client: TestClient, rating_id: str, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/ratings/{rating_id}")
        if r.json()["status"] in {"done", "failed"}:
            return
        time.sleep(0.01)
    raise AssertionError("timeout")


def test_events_stream_replays_full_history_when_job_done(
    api_client, sample_dataroom
) -> None:
    """Most deterministic path: wait for the job to finish, then
    subscribe. SSE should replay every event from history and close.
    """
    r = api_client.post(
        "/ratings/from-path",
        json={
            "path": str(sample_dataroom),
            "company": "X",
            "rating_id": "adi-events-1",
        },
    )
    assert r.status_code == 202

    _wait_done(api_client, "adi-events-1")

    r = api_client.get("/ratings/adi-events-1/events")
    assert r.status_code == 200
    events = _parse_sse(r.text)

    # We should see status transitions, all 16 agent starts + dones,
    # an ingest summary, a rating payload, and the terminal status.
    statuses = [e["status"] for e in events if e.get("type") == "status"]
    assert "ingesting" in statuses
    assert "rating" in statuses
    assert "scoring" in statuses
    assert "done" in statuses

    agent_starts = [e for e in events if e.get("type") == "agent" and e.get("event") == "start"]
    agent_dones = [e for e in events if e.get("type") == "agent" and e.get("event") == "done"]
    assert len(agent_starts) == 16
    assert len(agent_dones) == 16

    rating_events = [e for e in events if e.get("type") == "rating"]
    assert len(rating_events) == 1
    assert "grade" in rating_events[0]["rating"]["result"]


def test_events_includes_ingest_summary(api_client, sample_dataroom) -> None:
    r = api_client.post(
        "/ratings/from-path",
        json={
            "path": str(sample_dataroom),
            "company": "X",
            "rating_id": "adi-events-ingest",
        },
    )
    assert r.status_code == 202
    _wait_done(api_client, "adi-events-ingest")

    r = api_client.get("/ratings/adi-events-ingest/events")
    events = _parse_sse(r.text)
    ingest_events = [e for e in events if e.get("type") == "ingest"]
    assert len(ingest_events) == 1
    assert ingest_events[0]["files_ingested"] > 0
    assert ingest_events[0]["chunks"] > 0


def test_events_unknown_rating_returns_404(api_client) -> None:
    r = api_client.get("/ratings/nope/events")
    assert r.status_code == 404
