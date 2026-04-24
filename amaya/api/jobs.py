"""In-memory job registry + SSE event bus.

A RatingJob tracks the state machine of one rating run:

    pending → ingesting → rating → scoring → done
                                            → failed

Every state transition and every agent start/done event is pushed through
`emit()`. Subscribers get their own asyncio.Queue, primed with the full
history so late connections (e.g. a reloading dashboard tab) still see
every event. When the job is terminal, a None sentinel is enqueued to
signal end-of-stream.

No persistence. The ledger on disk is the durable record; the registry
is ephemeral session state for the server process.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from amaya.schemas import Rating

JobStatus = Literal[
    "pending",
    "ingesting",
    "rating",
    "scoring",
    "done",
    "failed",
]

TERMINAL: frozenset[JobStatus] = frozenset({"done", "failed"})


@dataclass
class RatingJob:
    rating_id: str
    company_name: str
    sector: str
    analyst_notes: str = ""
    status: JobStatus = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Progress tracking (not authoritative — use status for state)
    dimensions_done: int = 0
    chain_done: int = 0

    # Results
    rating: Rating | None = None
    error: str | None = None
    sealed_digest: str | None = None

    # Event stream
    history: list[dict[str, Any]] = field(default_factory=list)
    _subscribers: list[asyncio.Queue[dict[str, Any] | None]] = field(default_factory=list)

    # Housekeeping
    _temp_dir: Path | None = None
    _task: asyncio.Task[Any] | None = None

    def emit(self, event: dict[str, Any]) -> None:
        """Append to history and fan out to all live subscribers."""
        self.history.append(event)
        for q in self._subscribers:
            q.put_nowait(event)

    def subscribe(self) -> asyncio.Queue[dict[str, Any] | None]:
        """Return a queue seeded with full history + live tail.

        If the job is already terminal, the sentinel is enqueued after
        the history so the consumer sees every event then cleanly closes.
        """
        q: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        for event in self.history:
            q.put_nowait(event)
        if self.status in TERMINAL:
            q.put_nowait(None)
        else:
            self._subscribers.append(q)
        return q

    def finalize(self) -> None:
        """Mark all subscribers as done — they'll drain history then exit."""
        for q in self._subscribers:
            q.put_nowait(None)
        self._subscribers.clear()

    def set_status(self, status: JobStatus) -> None:
        self.status = status
        self.emit({"type": "status", "status": status})

    def record_agent_event(self, event: str, name: str) -> None:
        if event == "done":
            # Rough progress counter — chain positions are the 4 known strings.
            if name in {"upstream", "downstream", "lateral", "end_consumer"}:
                self.chain_done += 1
            else:
                self.dimensions_done += 1
        self.emit({"type": "agent", "event": event, "name": name})

    def record_rating(self, rating: Rating) -> None:
        self.rating = rating
        self.emit({
            "type": "rating",
            "rating": rating.model_dump(mode="json"),
        })

    def record_error(self, error: str) -> None:
        self.error = error
        self.status = "failed"
        self.emit({"type": "error", "error": error})

    def record_sealed(self, digest: str, ledger_root: str) -> None:
        self.sealed_digest = digest
        self.emit({
            "type": "sealed",
            "digest": digest,
            "ledger_root": ledger_root,
        })


class JobRegistry:
    """Process-local store of rating jobs, keyed by rating_id.

    Safe for the single-process uvicorn deployment the demo runs on.
    For multi-worker production you'd swap this for Redis + a shared
    event bus; the interface is small enough to do that cleanly.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, RatingJob] = {}

    def create(
        self,
        *,
        company_name: str,
        sector: str = "",
        analyst_notes: str = "",
        rating_id: str | None = None,
    ) -> RatingJob:
        rid = rating_id or _generate_rating_id()
        if rid in self._jobs:
            raise ValueError(f"rating_id already in use: {rid}")
        job = RatingJob(
            rating_id=rid,
            company_name=company_name,
            sector=sector,
            analyst_notes=analyst_notes,
        )
        self._jobs[rid] = job
        return job

    def get(self, rating_id: str) -> RatingJob | None:
        return self._jobs.get(rating_id)

    def list_all(self) -> list[RatingJob]:
        return list(self._jobs.values())

    def drop(self, rating_id: str) -> None:
        self._jobs.pop(rating_id, None)


def _generate_rating_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"adi-{stamp}-{uuid.uuid4().hex[:8]}"
