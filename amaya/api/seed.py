"""Flagship demo ratings — pre-loaded into the registry at server startup.

When `create_app(seed=True)` is used, or `POST /demo/reset` is hit, this
module produces a RatingJob in the terminal 'done' state so the dashboard
opens on a fully-realized rating instead of an empty ratings list.

The seed is deterministic: it loads an analyst-prepared `RatingInput`
from disk, runs it through the same `scoring.score()` function the live
pipeline uses, and stores the resulting `Rating`. No LLM calls, no
external services — the flagship renders identically on every boot.

Evidence refs on flagship ratings come from the analyst-prepared JSON
itself; they are not inferred. If the JSON has no evidence, the
dashboard's dimension detail shows the 'no evidence references
recorded' fallback, which is honest — the flagship was hand-scored.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from amaya import __version__
from amaya.api.jobs import JobRegistry, RatingJob
from amaya.methodology import load_methodology
from amaya.schemas import Rating, RatingInput
from amaya.scoring import score as score_rating

FLAGSHIP_DIR = Path(__file__).resolve().parent.parent.parent / "examples"

# (input_json_filename, company_name, sector, rating_id)
FLAGSHIPS: list[tuple[str, str, str, str]] = [
    (
        "colabor_input.json",
        "Colabor Group",
        "Food Distribution",
        "adi-2026Q2-colabor-001",
    ),
]


def seed_flagship_ratings(
    registry: JobRegistry,
    *,
    flagship_dir: Path | None = None,
    methodology_version: str = "v1.0",
) -> list[str]:
    """Populate the registry with pre-scored flagship ratings.

    Returns the list of rating_ids that were seeded. Silently skips any
    flagship whose JSON file is missing (e.g. someone deleted examples/
    for a lighter bundle).
    """
    root = flagship_dir or FLAGSHIP_DIR
    methodology = load_methodology(methodology_version)
    seeded: list[str] = []

    for filename, company, sector, rating_id in FLAGSHIPS:
        path = root / filename
        if not path.exists():
            continue
        if registry.get(rating_id) is not None:
            continue  # already seeded this run

        data = json.loads(path.read_text())
        data.setdefault("rating_id", rating_id)
        data.setdefault("company_name", company)
        data.setdefault("sector", sector)
        rating_input = RatingInput.model_validate(data)

        result = score_rating(rating_input, methodology)
        rating = Rating(
            input=rating_input,
            result=result,
            issued_at=datetime.now(timezone.utc),
            methodology_version=methodology.version,
            pipeline_version=__version__,
        )

        job = registry.create(
            company_name=company,
            sector=sector,
            analyst_notes=rating_input.analyst_notes,
            rating_id=rating_id,
        )
        # Fast-forward the job to terminal 'done' state. We populate the
        # event history as if the pipeline had run, so a dashboard that
        # opens this rating cold still sees a realistic SSE replay.
        _replay_synthetic_events(job, rating)
        seeded.append(rating_id)

    return seeded


def _replay_synthetic_events(job: RatingJob, rating: Rating) -> None:
    """Populate a job's history as if the full pipeline had streamed."""
    job.set_status("ingesting")
    job.emit(
        {
            "type": "ingest",
            "files_ingested": 0,
            "files_skipped": [],
            "chunks": 0,
            "summary": {"flagship": 1},
        }
    )
    job.set_status("rating")
    for dim in rating.input.dimension_scores:
        job.emit({"type": "agent", "event": "start", "name": dim.code})
        job.record_agent_event("done", dim.code)
    for p in rating.input.chain.positions:
        job.emit({"type": "agent", "event": "start", "name": p.position})
        job.record_agent_event("done", p.position)
    job.set_status("scoring")
    job.record_rating(rating)
    job.set_status("done")
    job.finalize()
