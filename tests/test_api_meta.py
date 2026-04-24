"""Health, methodology, and verify endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from amaya import __version__
from amaya.provenance import ProvenanceLedger
from amaya.schemas import (
    ChainAssessment,
    ChainPositionScore,
    DimensionScore,
    Rating,
    RatingInput,
    ScoringResult,
)


def test_health_returns_version(api_client) -> None:
    r = api_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": __version__}


def test_methodology_returns_v1(api_client) -> None:
    r = api_client.get("/methodology")
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == "1.0.0"
    assert "layers" in body["raw"]
    assert "circuit_breakers" in body["raw"]
    assert "grades" in body["raw"]


def test_verify_roundtrip(api_client, tmp_path: Path) -> None:
    ledger_dir = tmp_path / "verify-ledger"
    ledger = ProvenanceLedger(ledger_dir)

    rating_input = RatingInput(
        rating_id="adi-verify-001",
        company_name="Acme",
        dimension_scores=[
            DimensionScore(code=c, score=5, rationale="r")
            for c in ["MCS", "CPS", "SCAE", "CLS", "VPR", "WCI",
                      "RMV", "TSR", "LAL", "SPS", "ANCR", "DIM"]
        ],
        chain=ChainAssessment(positions=[
            ChainPositionScore(position=p, score=5)
            for p in ["upstream", "downstream", "lateral", "end_consumer"]
        ]),
    )
    rating = Rating(
        input=rating_input,
        result=ScoringResult(
            raw_score=50.0, chain_modifier=1.0, adjusted_score=50.0,
            final_score=50.0, grade="C", grade_label="C",
            grade_action="continue", methodology_version="1.0.0",
        ),
        issued_at=datetime.now(timezone.utc),
        methodology_version="1.0.0",
        pipeline_version=__version__,
    )
    ledger.seal(rating)

    r = api_client.post(
        "/verify",
        json={"rating_id": "adi-verify-001", "ledger_path": str(ledger_dir)},
    )
    assert r.status_code == 200
    assert r.json() == {"rating_id": "adi-verify-001", "verified": True}


def test_verify_missing_ledger_404(api_client, tmp_path: Path) -> None:
    r = api_client.post(
        "/verify",
        json={"rating_id": "x", "ledger_path": str(tmp_path / "nope")},
    )
    assert r.status_code == 404
