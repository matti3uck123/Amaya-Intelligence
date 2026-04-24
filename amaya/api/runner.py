"""Background runner that drives one rating through ingest → agents → scoring.

Pulls the pieces together and streams progress into the job's event bus.
Kept separate from routes so it can be unit-tested without HTTP.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from amaya import __version__
from amaya.agents import rate
from amaya.agents.completion import Completion
from amaya.api.jobs import RatingJob
from amaya.ingest import ingest
from amaya.ingest.classifier import Classifier
from amaya.methodology import load_methodology
from amaya.provenance import ProvenanceLedger
from amaya.schemas import Rating
from amaya.scoring import score as score_rating


async def run_rating_job(
    job: RatingJob,
    *,
    dataroom_path: Path,
    completion: Completion,
    classifier: Classifier,
    methodology_version: str = "v1.0",
    ledger: ProvenanceLedger | None = None,
    cleanup_dataroom: bool = False,
) -> None:
    """Execute the full pipeline, streaming events into the job.

    Never raises — any exception is captured into job.error and emitted
    as a terminal 'error' event so the SSE stream can close cleanly.
    """
    try:
        job.set_status("ingesting")
        ingest_result = ingest(dataroom_path, classifier=classifier)
        job.emit({
            "type": "ingest",
            "files_ingested": ingest_result.files_ingested,
            "files_skipped": ingest_result.files_skipped,
            "chunks": len(ingest_result.chunks),
            "summary": ingest_result.summary(),
        })

        job.set_status("rating")
        rating_input = await rate(
            rating_id=job.rating_id,
            company_name=job.company_name,
            sector=job.sector,
            ingest_result=ingest_result,
            completion=completion,
            analyst_notes=job.analyst_notes,
            on_progress=job.record_agent_event,
        )

        job.set_status("scoring")
        methodology = load_methodology(methodology_version)
        result = score_rating(rating_input, methodology)
        rating = Rating(
            input=rating_input,
            result=result,
            issued_at=datetime.now(timezone.utc),
            methodology_version=methodology.version,
            pipeline_version=__version__,
        )

        if ledger is not None:
            bundle = ledger.seal(rating)
            job.record_sealed(bundle["seal"]["digest"], str(ledger.root))

        job.record_rating(rating)
        job.set_status("done")

    except Exception as exc:
        job.record_error(f"{type(exc).__name__}: {exc}")

    finally:
        if cleanup_dataroom and job._temp_dir is not None:
            shutil.rmtree(job._temp_dir, ignore_errors=True)
            job._temp_dir = None
        job.finalize()
