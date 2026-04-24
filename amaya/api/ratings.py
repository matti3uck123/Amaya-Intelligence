"""Rating endpoints — create (upload or from-path), poll, list, SSE events."""
from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from sse_starlette.sse import EventSourceResponse

from amaya.agents.completion import Completion
from amaya.api.deps import get_classifier, get_completion, get_registry
from amaya.api.jobs import JobRegistry, RatingJob
from amaya.api.runner import run_rating_job
from amaya.api.schemas import (
    RatingAcceptedResponse,
    RatingCreateFromPathRequest,
    RatingListItem,
    RatingProgress,
    RatingStatusResponse,
)
from amaya.ingest.classifier import Classifier
from amaya.provenance import ProvenanceLedger

router = APIRouter(prefix="/ratings", tags=["ratings"])


@router.post("", response_model=RatingAcceptedResponse, status_code=202)
async def create_rating_from_upload(
    request: Request,
    company: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File(description="Data-room documents")],
    sector: Annotated[str, Form()] = "",
    notes: Annotated[str, Form()] = "",
    rating_id: Annotated[str | None, Form()] = None,
    methodology: Annotated[str, Form()] = "v1.0",
    seal: Annotated[bool, Form()] = False,
    completion: Completion = Depends(get_completion),
    classifier: Classifier = Depends(get_classifier),
    registry: JobRegistry = Depends(get_registry),
) -> RatingAcceptedResponse:
    """Upload a data room and kick off a rating job.

    Files are written to a temp directory; the ingest pipeline walks it
    exactly like it would walk any local folder. Temp dir is cleaned
    when the job terminates.
    """
    if not files:
        raise HTTPException(400, "at least one file is required")

    temp_dir = Path(tempfile.mkdtemp(prefix="amaya-upload-"))
    for upload in files:
        if not upload.filename:
            continue
        # Flatten any path components the client sent — we only want the basename.
        safe_name = Path(upload.filename).name
        (temp_dir / safe_name).write_bytes(await upload.read())

    job = _create_and_schedule(
        registry=registry,
        request=request,
        dataroom_path=temp_dir,
        company=company,
        sector=sector,
        notes=notes,
        rating_id=rating_id,
        methodology=methodology,
        seal=seal,
        completion=completion,
        classifier=classifier,
        cleanup_dataroom=True,
    )
    return _accepted(job, request)


@router.post("/from-path", response_model=RatingAcceptedResponse, status_code=202)
async def create_rating_from_path(
    body: RatingCreateFromPathRequest,
    request: Request,
    completion: Completion = Depends(get_completion),
    classifier: Classifier = Depends(get_classifier),
    registry: JobRegistry = Depends(get_registry),
) -> RatingAcceptedResponse:
    """Rate a data room that already lives on the server's filesystem.

    Convenient for demos where the sample data room is bundled with the
    server, and for CLI-style usage. Not appropriate for multi-tenant
    deployments.
    """
    path = Path(body.path).expanduser().resolve()
    if not path.exists():
        raise HTTPException(404, f"path not found: {body.path}")

    job = _create_and_schedule(
        registry=registry,
        request=request,
        dataroom_path=path,
        company=body.company,
        sector=body.sector,
        notes=body.notes,
        rating_id=body.rating_id,
        methodology=body.methodology,
        seal=body.seal,
        completion=completion,
        classifier=classifier,
        cleanup_dataroom=False,
    )
    return _accepted(job, request)


@router.get("", response_model=list[RatingListItem])
async def list_ratings(
    registry: JobRegistry = Depends(get_registry),
) -> list[RatingListItem]:
    """Every rating the server has seen this session."""
    items: list[RatingListItem] = []
    for job in registry.list_all():
        grade = job.rating.result.grade if job.rating else None
        final = job.rating.result.final_score if job.rating else None
        items.append(
            RatingListItem(
                rating_id=job.rating_id,
                company_name=job.company_name,
                sector=job.sector,
                status=job.status,
                created_at=job.created_at,
                grade=grade,
                final_score=final,
            )
        )
    # Newest first — mirrors how a dashboard would render.
    items.sort(key=lambda i: i.created_at, reverse=True)
    return items


@router.get("/{rating_id}", response_model=RatingStatusResponse)
async def get_rating(
    rating_id: str,
    registry: JobRegistry = Depends(get_registry),
) -> RatingStatusResponse:
    job = _require(registry, rating_id)
    return _status_response(job)


@router.get("/{rating_id}/events")
async def rating_events(
    rating_id: str,
    request: Request,
    registry: JobRegistry = Depends(get_registry),
) -> EventSourceResponse:
    """SSE stream of every event a job emits.

    Replays the full event history on connect, then tails live events
    until the job terminates. Closes cleanly when the job is done.
    """
    job = _require(registry, rating_id)
    queue = job.subscribe()

    async def event_source():
        try:
            while True:
                if await request.is_disconnected():
                    return
                event = await queue.get()
                if event is None:
                    return
                yield {
                    "event": event.get("type", "message"),
                    "data": json.dumps(event),
                }
        except asyncio.CancelledError:  # client disconnected mid-wait
            return

    return EventSourceResponse(event_source())


@router.delete("/{rating_id}", status_code=204)
async def delete_rating(
    rating_id: str,
    registry: JobRegistry = Depends(get_registry),
) -> JSONResponse:
    """Drop a job from the registry (does not touch sealed bundles)."""
    if registry.get(rating_id) is None:
        raise HTTPException(404, "rating not found")
    registry.drop(rating_id)
    return JSONResponse(content=None, status_code=204)


@router.get("/{rating_id}/pdf")
async def rating_pdf(
    rating_id: str,
    registry: JobRegistry = Depends(get_registry),
) -> Response:
    """One-page leave-behind PDF for a completed rating.

    Generated deterministically from the stored `Rating` — same object
    sealed in the ledger. Prospects get the paper artifact; analysts
    get byte-identical proof the screen view and the PDF view came from
    the same rating.
    """
    job = _require(registry, rating_id)
    if job.rating is None:
        raise HTTPException(409, f"rating {rating_id} is not complete (status={job.status})")

    from amaya.reports import render_rating_pdf  # lazy import — reportlab is heavy

    pdf_bytes = render_rating_pdf(job.rating)
    filename = f"amaya-{rating_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


# ---------- helpers ----------


def _require(registry: JobRegistry, rating_id: str) -> RatingJob:
    job = registry.get(rating_id)
    if job is None:
        raise HTTPException(404, "rating not found")
    return job


def _create_and_schedule(
    *,
    registry: JobRegistry,
    request: Request,
    dataroom_path: Path,
    company: str,
    sector: str,
    notes: str,
    rating_id: str | None,
    methodology: str,
    seal: bool,
    completion: Completion,
    classifier: Classifier,
    cleanup_dataroom: bool,
) -> RatingJob:
    try:
        job = registry.create(
            company_name=company,
            sector=sector,
            analyst_notes=notes,
            rating_id=rating_id,
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc

    if cleanup_dataroom:
        job._temp_dir = dataroom_path

    ledger: ProvenanceLedger | None = None
    if seal:
        ledger_root = request.app.state.ledger_root
        if ledger_root is None:
            raise HTTPException(
                400,
                "server has no --ledger configured; cannot seal this rating",
            )
        ledger = ProvenanceLedger(ledger_root)

    task = asyncio.create_task(
        run_rating_job(
            job,
            dataroom_path=dataroom_path,
            completion=completion,
            classifier=classifier,
            methodology_version=methodology,
            ledger=ledger,
            cleanup_dataroom=cleanup_dataroom,
        )
    )
    job._task = task
    return job


def _accepted(job: RatingJob, request: Request) -> RatingAcceptedResponse:
    base = str(request.url_for("get_rating", rating_id=job.rating_id))
    return RatingAcceptedResponse(
        rating_id=job.rating_id,
        status=job.status,
        created_at=job.created_at,
        detail_url=base,
        events_url=base + "/events",
    )


def _status_response(job: RatingJob) -> RatingStatusResponse:
    return RatingStatusResponse(
        rating_id=job.rating_id,
        company_name=job.company_name,
        sector=job.sector,
        status=job.status,
        created_at=job.created_at,
        progress=RatingProgress(
            dimensions_done=job.dimensions_done,
            chain_done=job.chain_done,
        ),
        rating=job.rating,
        error=job.error,
        sealed_digest=job.sealed_digest,
    )
