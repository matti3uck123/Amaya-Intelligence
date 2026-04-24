"""FastAPI app factory.

Everything hangs off `create_app()` so tests and uvicorn both go through
the same entry point. `ledger_root` is stored on app.state; routes read
it when a client asks to seal a rating.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from amaya import __version__
from amaya.api.ratings import router as ratings_router
from amaya.api.schemas import (
    HealthResponse,
    MethodologyResponse,
    VerifyRequest,
    VerifyResponse,
)
from amaya.methodology import load_methodology
from amaya.provenance import ProvenanceLedger


def create_app(
    *,
    ledger_root: Path | None = None,
    allow_origins: list[str] | None = None,
) -> FastAPI:
    """Build a FastAPI app.

    - ledger_root: if set, clients can request `seal=true` on rating
      creation and hit `/verify` against the same ledger. Default None
      means sealing is disabled (tests and stateless demos).
    - allow_origins: CORS list. Default None → permissive '*' so the
      dashboard can talk to the API during local demos.
    """
    app = FastAPI(
        title="Amaya Intelligence — ADI API",
        description="AI Durability Index ratings as a service.",
        version=__version__,
    )

    app.state.ledger_root = ledger_root

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins or ["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(_meta_router())
    app.include_router(ratings_router)

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
