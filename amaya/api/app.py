"""FastAPI app factory.

Everything hangs off `create_app()` so tests and uvicorn both go through
the same entry point. `ledger_root` is stored on app.state; routes read
it when a client asks to seal a rating.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from amaya import __version__
from amaya.api.deps import get_registry
from amaya.api.ratings import router as ratings_router
from amaya.api.schemas import (
    HealthResponse,
    MethodologyResponse,
    VerifyRequest,
    VerifyResponse,
)
from amaya.api.seed import seed_flagship_ratings
from amaya.methodology import load_methodology
from amaya.provenance import ProvenanceLedger


def create_app(
    *,
    ledger_root: Path | None = None,
    allow_origins: list[str] | None = None,
    seed: bool = False,
) -> FastAPI:
    """Build a FastAPI app.

    - ledger_root: if set, clients can request `seal=true` on rating
      creation and hit `/verify` against the same ledger. Default None
      means sealing is disabled (tests and stateless demos).
    - allow_origins: CORS list. Default None → permissive '*' so the
      dashboard can talk to the API during local demos.
    - seed: if True, pre-load flagship ratings (e.g. Colabor) at
      startup so the dashboard opens on a realized rating. Intended for
      demo deployments; tests leave this False to keep fixtures clean.
    """
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app.state.seed_enabled:
            seed_flagship_ratings(get_registry())
        yield

    app = FastAPI(
        title="Amaya Intelligence — ADI API",
        description="AI Durability Index ratings as a service.",
        version=__version__,
        lifespan=lifespan,
    )

    app.state.ledger_root = ledger_root
    app.state.seed_enabled = seed

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins or ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(_meta_router())
    app.include_router(ratings_router)
    app.include_router(_demo_router())

    return app


def _meta_router() -> APIRouter:
    router = APIRouter(tags=["meta"])

    @router.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(version=__version__)

    @router.get("/methodology", response_model=MethodologyResponse)
    def methodology(version: str = "v1.0") -> MethodologyResponse:
        m = load_methodology(version)
        return MethodologyResponse(version=m.version, raw=m.raw_yaml)

    @router.post("/verify", response_model=VerifyResponse)
    def verify(body: VerifyRequest) -> VerifyResponse:
        ledger_path = Path(body.ledger_path).expanduser().resolve()
        if not ledger_path.exists():
            raise HTTPException(404, f"ledger not found: {body.ledger_path}")
        ledger = ProvenanceLedger(ledger_path)
        ok = ledger.verify(body.rating_id)
        return VerifyResponse(rating_id=body.rating_id, verified=ok)

    return router


def _demo_router() -> APIRouter:
    """Demo-only endpoints — wipe and reseed flagships between prospects."""
    from amaya.api.jobs import JobRegistry

    router = APIRouter(prefix="/demo", tags=["demo"])

    @router.post("/reset")
    def reset(
        request: Request,
        registry: JobRegistry = Depends(get_registry),
    ) -> dict:
        """Drop every rating and re-seed flagships (if seeding is enabled)."""
        rating_ids = [job.rating_id for job in registry.list_all()]
        for rid in rating_ids:
            registry.drop(rid)

        seeded: list[str] = []
        if request.app.state.seed_enabled:
            seeded = seed_flagship_ratings(registry)
        return {
            "dropped": rating_ids,
            "seeded": seeded,
            "seed_enabled": request.app.state.seed_enabled,
        }

    return router
