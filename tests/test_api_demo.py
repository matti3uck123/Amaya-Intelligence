"""Session 6 — demo seeding, PDF endpoint, /demo/reset."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from amaya.api import create_app
from amaya.api.deps import get_completion, reset_registry

FLAGSHIP_ID = "adi-2026Q2-colabor-001"


def _seeded_client(tmp_path: Path) -> TestClient:
    reset_registry()
    app = create_app(ledger_root=tmp_path / "ledger", seed=True)
    # No completion needed — seeding doesn't invoke the agent layer.
    return TestClient(app)


def test_seed_preloads_colabor_flagship(tmp_path: Path):
    with _seeded_client(tmp_path) as client:
        r = client.get("/ratings")
        assert r.status_code == 200
        ratings = r.json()
        assert len(ratings) == 1
        flagship = ratings[0]
        assert flagship["rating_id"] == FLAGSHIP_ID
        assert flagship["status"] == "done"
        assert flagship["company_name"] == "Colabor Group"
        assert flagship["grade"] is not None
        assert flagship["final_score"] is not None
    reset_registry()


def test_create_app_without_seed_is_empty(tmp_path: Path):
    reset_registry()
    app = create_app(ledger_root=tmp_path / "ledger", seed=False)
    with TestClient(app) as client:
        r = client.get("/ratings")
        assert r.status_code == 200
        assert r.json() == []
    reset_registry()


def test_flagship_detail_returns_complete_rating(tmp_path: Path):
    with _seeded_client(tmp_path) as client:
        r = client.get(f"/ratings/{FLAGSHIP_ID}")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "done"
        assert body["rating"] is not None
        assert body["rating"]["result"]["grade"] in {"A+", "A", "B+", "B", "C+", "C", "D", "F"}
        # 12 dimensions + 4 chain positions all present
        assert len(body["rating"]["input"]["dimension_scores"]) == 12
        assert len(body["rating"]["input"]["chain"]["positions"]) == 4
    reset_registry()


def test_pdf_endpoint_returns_pdf_bytes(tmp_path: Path):
    with _seeded_client(tmp_path) as client:
        r = client.get(f"/ratings/{FLAGSHIP_ID}/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content.startswith(b"%PDF-")
        assert f'amaya-{FLAGSHIP_ID}.pdf' in r.headers.get("content-disposition", "")
    reset_registry()


def test_pdf_endpoint_404s_for_unknown_id(tmp_path: Path):
    with _seeded_client(tmp_path) as client:
        r = client.get("/ratings/does-not-exist/pdf")
        assert r.status_code == 404
    reset_registry()


def test_pdf_endpoint_409s_for_incomplete_job(api_client):
    """A pending job has no Rating — PDF endpoint should refuse rather than crash."""
    from amaya.api.deps import get_registry

    registry = get_registry()
    job = registry.create(company_name="Incomplete Co", rating_id="adi-pending-001")
    # leave status as "pending", rating as None
    assert job.rating is None

    r = api_client.get(f"/ratings/{job.rating_id}/pdf")
    assert r.status_code == 409
    assert "not complete" in r.json()["detail"]


def test_demo_reset_with_seed_wipes_and_reseeds(tmp_path: Path):
    with _seeded_client(tmp_path) as client:
        # Create an extra non-flagship entry so reset has something to drop.
        from amaya.api.deps import get_registry

        get_registry().create(
            company_name="Ad-hoc Co",
            rating_id="adi-adhoc-001",
        )
        pre = client.get("/ratings").json()
        ids = {it["rating_id"] for it in pre}
        assert FLAGSHIP_ID in ids
        assert "adi-adhoc-001" in ids

        r = client.post("/demo/reset")
        assert r.status_code == 200
        payload = r.json()
        assert payload["seed_enabled"] is True
        assert FLAGSHIP_ID in payload["seeded"]
        assert "adi-adhoc-001" in payload["dropped"]

        post = client.get("/ratings").json()
        post_ids = {it["rating_id"] for it in post}
        assert post_ids == {FLAGSHIP_ID}  # only flagships remain
    reset_registry()


def test_demo_reset_without_seed_just_wipes(api_client):
    """api_client fixture builds an unseeded app; reset should clear all."""
    from amaya.api.deps import get_registry

    registry = get_registry()
    registry.create(company_name="A", rating_id="adi-a-001")
    registry.create(company_name="B", rating_id="adi-b-001")

    r = api_client.post("/demo/reset")
    assert r.status_code == 200
    body = r.json()
    assert body["seed_enabled"] is False
    assert set(body["dropped"]) == {"adi-a-001", "adi-b-001"}
    assert body["seeded"] == []

    assert api_client.get("/ratings").json() == []
