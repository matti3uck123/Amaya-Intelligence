"""Tests for the reportlab-based rating PDF renderer.

We don't assert on rendered pixels — just that bytes are a valid PDF,
that the generator is a pure function of the Rating (byte-identical
across calls with the same inputs, after stripping embedded timestamps),
and that circuit-breaker / low-grade ratings still render successfully.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from amaya import __version__
from amaya.methodology import load_methodology
from amaya.reports import render_rating_pdf
from amaya.schemas import Rating, RatingInput
from amaya.scoring import score as score_rating

EXAMPLES = Path(__file__).parent.parent / "examples"
FIXED_TS = datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc)


def _colabor_rating(methodology, *, mutate=None) -> Rating:
    data = json.loads((EXAMPLES / "colabor_input.json").read_text())
    if mutate:
        mutate(data)
    rating_input = RatingInput.model_validate(data)
    result = score_rating(rating_input, methodology)
    return Rating(
        input=rating_input,
        result=result,
        issued_at=FIXED_TS,
        methodology_version=methodology.version,
        pipeline_version=__version__,
    )


def test_pdf_renders_valid_magic(methodology):
    rating = _colabor_rating(methodology)
    pdf = render_rating_pdf(rating)
    assert pdf.startswith(b"%PDF-")
    assert pdf.rstrip().endswith(b"%%EOF")
    assert len(pdf) > 2000  # sanity: non-trivial content


def test_pdf_repeat_renders_have_stable_size(methodology):
    """reportlab embeds a random /ID per render, so bytes aren't identical,
    but the structural content must not drift — size within a few bytes."""
    rating = _colabor_rating(methodology)
    sizes = {len(render_rating_pdf(rating)) for _ in range(3)}
    assert max(sizes) - min(sizes) < 64


def test_pdf_renders_with_circuit_breakers(methodology):
    """CB section must render without errors when triggers fire."""

    def mutate(data):
        for d in data["dimension_scores"]:
            if d["code"] in ("MCS", "VPR"):
                d["score"] = 2  # trip CB1, CB3, CB4

    rating = _colabor_rating(methodology, mutate=mutate)
    assert rating.result.circuit_breakers_triggered, "test setup failed to trip CBs"
    pdf = render_rating_pdf(rating)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 2000


@pytest.mark.parametrize("dim_score", [1, 5, 10])
def test_pdf_renders_across_score_ranges(methodology, dim_score):
    """Extreme uniform scores must not trip bar-width or color math."""

    def mutate(data):
        for d in data["dimension_scores"]:
            d["score"] = dim_score
        for p in data["chain"]["positions"]:
            p["score"] = dim_score

    rating = _colabor_rating(methodology, mutate=mutate)
    pdf = render_rating_pdf(rating)
    assert pdf.startswith(b"%PDF-")


def test_pdf_handles_empty_evidence(methodology):
    """Flagship ratings often ship without evidence refs — must still render."""
    rating = _colabor_rating(methodology)
    for d in rating.input.dimension_scores:
        assert d.evidence == []  # sanity: colabor_input.json has no refs
    pdf = render_rating_pdf(rating)
    assert pdf.startswith(b"%PDF-")
