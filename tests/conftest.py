"""Shared fixtures — scoring core + API layer."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import pytest

from amaya.methodology import Methodology, load_methodology
from amaya.schemas import (
    ChainAssessment,
    ChainPositionScore,
    DimensionScore,
    RatingInput,
)

SAMPLE_ROOM = Path(__file__).parent.parent / "examples" / "sample_dataroom"

ALL_DIMS = ["MCS", "CPS", "SCAE", "CLS", "VPR", "WCI", "RMV", "TSR",
            "LAL", "SPS", "ANCR", "DIM"]


@pytest.fixture
def methodology() -> Methodology:
    return load_methodology("v1.0")


def make_rating(
    dim_scores: dict[str, int] | int = 5,
    chain_scores: dict[str, int] | int = 5,
    rating_id: str = "rating-test",
) -> RatingInput:
    if isinstance(dim_scores, int):
        dim_scores = {c: dim_scores for c in ALL_DIMS}
    if isinstance(chain_scores, int):
        chain_scores = {
            "upstream": chain_scores, "downstream": chain_scores,
            "lateral": chain_scores, "end_consumer": chain_scores,
        }
    return RatingInput(
        rating_id=rating_id,
        company_name="Acme Co",
        dimension_scores=[
            DimensionScore(code=c, score=s, rationale="test")  # type: ignore[arg-type]
            for c, s in dim_scores.items()
        ],
        chain=ChainAssessment(positions=[
            ChainPositionScore(position=p, score=s)  # type: ignore[arg-type]
            for p, s in chain_scores.items()
        ]),
    )


@pytest.fixture
def make_rating_fixture():
    return make_rating


# ---------- API-layer fixtures ----------


def _deterministic_responder(
    score_by_tool: dict[str, int] | None = None,
) -> Callable[[str, str], dict[str, Any]]:
    score_by_tool = score_by_tool or {}

    def responder(tool_name: str, _user: str) -> dict[str, Any]:
        score = score_by_tool.get(tool_name, 5)
        core = tool_name.removeprefix("submit_").removesuffix("_score")
        is_chain = core in {"upstream", "downstream", "lateral", "end_consumer"}
        resp: dict[str, Any] = {"score": score, "rationale": f"r for {tool_name}"}
        if not is_chain:
            resp["confidence"] = 0.8
            resp["evidence_indices"] = []
        return resp

    return responder


@pytest.fixture
def sample_dataroom() -> Path:
    return SAMPLE_ROOM


@pytest.fixture
def stub_completion_factory():
    """Returns a builder so tests can customize scores."""
    from amaya.agents.completion import StubCompletion

    def _build(scores: dict[str, int] | None = None) -> StubCompletion:
        return StubCompletion(responder=_deterministic_responder(scores))

    return _build


@pytest.fixture
def api_client(stub_completion_factory, tmp_path: Path):
    """TestClient with stubbed Completion and a fresh per-test ledger dir."""
    from fastapi.testclient import TestClient

    from amaya.api import create_app
    from amaya.api.deps import get_completion, reset_registry

    reset_registry()
    app = create_app(ledger_root=tmp_path / "ledger")
    app.dependency_overrides[get_completion] = lambda: stub_completion_factory()
    with TestClient(app) as client:
        yield client
    reset_registry()
