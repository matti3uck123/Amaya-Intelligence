"""Shared fixtures for scoring tests."""
from __future__ import annotations

import pytest

from amaya.methodology import Methodology, load_methodology
from amaya.schemas import (
    ChainAssessment,
    ChainPositionScore,
    DimensionScore,
    RatingInput,
)

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
