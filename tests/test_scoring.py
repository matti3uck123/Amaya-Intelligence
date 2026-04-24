"""Scoring engine tests — every circuit breaker, every grade, determinism."""
from __future__ import annotations

import pytest

from amaya.scoring import score
from tests.conftest import make_rating


def test_all_tens_gives_a_plus(methodology):
    r = make_rating(dim_scores=10, chain_scores=10)
    result = score(r, methodology)
    assert result.raw_score == 100.0
    assert result.chain_modifier == 1.15
    assert result.final_score == 100.0  # capped at 100
    assert result.grade == "A+"
    assert result.circuit_breakers_triggered == []


def test_all_ones_floor_is_ten_times_point_seven(methodology):
    r = make_rating(dim_scores=1, chain_scores=1)
    result = score(r, methodology)
    assert result.raw_score == 10.0
    assert result.chain_modifier == 0.70
    assert result.final_score == pytest.approx(7.0, abs=0.01)
    assert result.grade == "F"


def test_midpoint_scoring_no_circuit_breaker(methodology):
    r = make_rating(dim_scores=5, chain_scores=5)
    result = score(r, methodology)
    assert result.raw_score == 50.0
    assert 0.70 <= result.chain_modifier <= 1.15
    assert result.grade in {"C+", "C"}
    assert result.circuit_breakers_triggered == []


def test_cb1_market_category_collapse(methodology):
    # MCS=2 triggers CB1 → cap 35, even if everything else is 10
    dims = {c: 10 for c in ["CPS", "SCAE", "CLS", "VPR", "WCI", "RMV", "TSR",
                            "LAL", "SPS", "ANCR", "DIM"]}
    dims["MCS"] = 2
    r = make_rating(dim_scores=dims, chain_scores=10)
    result = score(r, methodology)
    triggered = {cb.code for cb in result.circuit_breakers_triggered}
    assert "CB1" in triggered
    assert result.final_score <= 35
    assert result.grade == "D"


def test_cb2_client_profile_collapse(methodology):
    dims = {c: 10 for c in ["MCS", "SCAE", "CLS", "VPR", "WCI", "RMV", "TSR",
                            "LAL", "SPS", "ANCR", "DIM"]}
    dims["CPS"] = 1
    r = make_rating(dim_scores=dims, chain_scores=10)
    result = score(r, methodology)
    assert "CB2" in {cb.code for cb in result.circuit_breakers_triggered}
    assert result.final_score <= 45


def test_cb3_value_proposition_replicated(methodology):
    dims = {c: 10 for c in ["MCS", "CPS", "SCAE", "CLS", "WCI", "RMV", "TSR",
                            "LAL", "SPS", "ANCR", "DIM"]}
    dims["VPR"] = 2
    r = make_rating(dim_scores=dims, chain_scores=10)
    result = score(r, methodology)
    assert "CB3" in {cb.code for cb in result.circuit_breakers_triggered}
    assert result.final_score <= 40


def test_cb4_terminal_condition_dominates(methodology):
    """CB4 has lowest cap (20) and should win when it fires with CB1+CB3."""
    dims = {c: 10 for c in ["CPS", "SCAE", "CLS", "WCI", "RMV", "TSR",
                            "LAL", "SPS", "ANCR", "DIM"]}
    dims["MCS"] = 1
    dims["VPR"] = 1
    r = make_rating(dim_scores=dims, chain_scores=10)
    result = score(r, methodology)
    triggered = {cb.code for cb in result.circuit_breakers_triggered}
    assert triggered >= {"CB1", "CB3", "CB4"}
    assert result.final_score <= 20
    assert result.grade == "F"


def test_cb_boundary_mcs_equals_3_does_not_fire(methodology):
    dims = {c: 10 for c in ["CPS", "SCAE", "CLS", "VPR", "WCI", "RMV", "TSR",
                            "LAL", "SPS", "ANCR", "DIM"]}
    dims["MCS"] = 3
    r = make_rating(dim_scores=dims, chain_scores=10)
    result = score(r, methodology)
    assert result.circuit_breakers_triggered == []


def test_missing_dimension_raises(methodology):
    from amaya.schemas import (ChainAssessment, ChainPositionScore,
                               DimensionScore, RatingInput)
    r = RatingInput(
        rating_id="r1",
        company_name="Acme",
        dimension_scores=[DimensionScore(code="MCS", score=5, rationale="x")],  # type: ignore
        chain=ChainAssessment(positions=[
            ChainPositionScore(position="upstream", score=5)  # type: ignore
        ]),
    )
    with pytest.raises(ValueError, match="Missing"):
        score(r, methodology)


def test_determinism_same_input_same_output(methodology):
    r = make_rating(dim_scores=7, chain_scores=6)
    a = score(r, methodology)
    b = score(r, methodology)
    assert a.model_dump() == b.model_dump()


def test_chain_modifier_range(methodology):
    """Chain modifier must stay in [0.70, 1.15]."""
    for chain_value in range(1, 11):
        r = make_rating(dim_scores=5, chain_scores=chain_value)
        result = score(r, methodology)
        assert 0.70 <= result.chain_modifier <= 1.15


def test_final_score_bounded_0_to_100(methodology):
    for dim_val, chain_val in [(1, 1), (10, 10), (5, 5), (1, 10), (10, 1)]:
        r = make_rating(dim_scores=dim_val, chain_scores=chain_val)
        result = score(r, methodology)
        assert 0 <= result.final_score <= 100


def test_colabor_like_rating_produces_c_range(methodology):
    """Sanity check against a live rating from the deck: Colabor C- · 45.9.
    We don't know the full dimension map, but MCS=6, CLS=4, TSR=6, ANCR=1
    with middling other dims should land in the C band.
    """
    dims = {
        "MCS": 6, "CPS": 5, "SCAE": 5, "CLS": 4,
        "VPR": 4, "WCI": 4, "RMV": 4, "TSR": 6,
        "LAL": 5, "SPS": 4, "ANCR": 1, "DIM": 4,
    }
    r = make_rating(dim_scores=dims, chain_scores=5)
    result = score(r, methodology)
    assert result.grade in {"C", "C+", "D"}, f"got {result.grade} / {result.final_score}"
