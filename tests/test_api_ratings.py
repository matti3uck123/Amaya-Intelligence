"""End-to-end API tests against the full pipeline with stubbed Completion."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient


def _wait_done(client: TestClient, rating_id: str, timeout: float = 5.0) -> dict:
    """Poll GET /ratings/{id} until status is terminal or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/ratings/{rating_id}")
        assert r.status_code == 200, r.text
        body = r.json()
        if body["status"] in {"done", "failed"}:
            return body
        time.sleep(0.01)
    raise AssertionError(f"rating {rating_id} did not finish within {timeout}s")


def test_create_rating_from_path_runs_full_pipeline(api_client, sample_dataroom) -> None:
    r = api_client.post(
        "/ratings/from-path",
        json={
            "path": str(sample_dataroom),
            "company": "Colabor",
            "sector": "Food Distribution",
        },
    )
    assert r.status_code == 202
    body = r.json()
    assert body["status"] in {"pending", "ingesting", "rating", "scoring", "done"}
    assert body["rating_id"].startswith("adi-")
    assert body["events_url"].endswith("/events")

    final = _wait_done(api_client, body["rating_id"])
    assert final["status"] == "done"
    assert final["rating"] is not None
    assert final["rating"]["result"]["grade"]
    assert final["progress"]["dimensions_done"] == 12
    assert final["progress"]["chain_done"] == 4


def test_create_rating_from_upload_runs_full_pipeline(api_client, sample_dataroom) -> None:
    files = []
    for p in sample_dataroom.iterdir():
        if p.is_file() and p.suffix in {".txt", ".md"}:
            files.append(("files", (p.name, p.read_bytes(), "text/plain")))

    assert files, "sample dataroom has no txt/md files to upload"

    r = api_client.post(
        "/ratings",
        files=files,
        data={"company": "UploadCo", "sector": "SaaS"},
    )
    assert r.status_code == 202, r.text
    rating_id = r.json()["rating_id"]

    final = _wait_done(api_client, rating_id)
    assert final["status"] == "done"
    assert final["rating"]["input"]["company_name"] == "UploadCo"


def test_create_rating_with_explicit_id(api_client, sample_dataroom) -> None:
    r = api_client.post(
        "/ratings/from-path",
        json={
            "path": str(sample_dataroom),
            "company": "X",
            "rating_id": "adi-custom-42",
        },
    )
    assert r.status_code == 202
    assert r.json()["rating_id"] == "adi-custom-42"

    _wait_done(api_client, "adi-custom-42")


def test_duplicate_rating_id_returns_409(api_client, sample_dataroom) -> None:
    body = {
        "path": str(sample_dataroom),
        "company": "X",
        "rating_id": "adi-dup-001",
    }
    r1 = api_client.post("/ratings/from-path", json=body)
    assert r1.status_code == 202
    r2 = api_client.post("/ratings/from-path", json=body)
    assert r2.status_code == 409


def test_from_path_with_missing_path_returns_404(api_client, tmp_path) -> None:
    r = api_client.post(
        "/ratings/from-path",
        json={"path": str(tmp_path / "nope"), "company": "X"},
    )
    assert r.status_code == 404


def test_list_ratings_returns_newest_first(api_client, sample_dataroom) -> None:
    ids = []
    for i in range(3):
        r = api_client.post(
            "/ratings/from-path",
            json={
                "path": str(sample_dataroom),
                "company": f"Co{i}",
                "rating_id": f"adi-list-{i}",
            },
        )
        assert r.status_code == 202
        ids.append(r.json()["rating_id"])

    for rid in ids:
        _wait_done(api_client, rid)

    r = api_client.get("/ratings")
    assert r.status_code == 200
    listing = r.json()
    assert len(listing) == 3
    # Newest first
    assert [i["rating_id"] for i in listing] == list(reversed(ids))
    for item in listing:
        assert item["grade"] is not None
        assert 0 <= item["final_score"] <= 100


def test_get_unknown_rating_returns_404(api_client) -> None:
    r = api_client.get("/ratings/does-not-exist")
    assert r.status_code == 404


def test_delete_rating(api_client, sample_dataroom) -> None:
    r = api_client.post(
        "/ratings/from-path",
        json={"path": str(sample_dataroom), "company": "X", "rating_id": "adi-del-1"},
    )
    assert r.status_code == 202
    _wait_done(api_client, "adi-del-1")

    r = api_client.delete("/ratings/adi-del-1")
    assert r.status_code == 204

    r = api_client.get("/ratings/adi-del-1")
    assert r.status_code == 404


def test_upload_with_no_files_returns_400(api_client) -> None:
    r = api_client.post("/ratings", data={"company": "X"})
    # FastAPI 422 when the multipart files field is absent entirely.
    assert r.status_code in {400, 422}


def test_seal_requires_configured_ledger(sample_dataroom, stub_completion_factory) -> None:
    """Server started without --ledger must reject seal=true."""
    from fastapi.testclient import TestClient

    from amaya.api import create_app
    from amaya.api.deps import get_completion, reset_registry

    reset_registry()
    app = create_app(ledger_root=None)
    app.dependency_overrides[get_completion] = lambda: stub_completion_factory()
    with TestClient(app) as client:
        r = client.post(
            "/ratings/from-path",
            json={
                "path": str(sample_dataroom),
                "company": "X",
                "seal": True,
            },
        )
        assert r.status_code == 400
        assert "ledger" in r.json()["detail"].lower()
    reset_registry()


def test_seal_writes_bundle_and_verifies(api_client, sample_dataroom) -> None:
    r = api_client.post(
        "/ratings/from-path",
        json={
            "path": str(sample_dataroom),
            "company": "Colabor",
            "rating_id": "adi-seal-1",
            "seal": True,
        },
    )
    assert r.status_code == 202

    final = _wait_done(api_client, "adi-seal-1")
    assert final["status"] == "done"
    assert final["sealed_digest"], "sealed_digest should be populated after sealing"

    # Pull ledger path off the app state.
    ledger_root = api_client.app.state.ledger_root
    r = api_client.post(
        "/verify",
        json={"rating_id": "adi-seal-1", "ledger_path": str(ledger_root)},
    )
    assert r.status_code == 200
    assert r.json()["verified"] is True
