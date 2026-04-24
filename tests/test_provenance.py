"""Provenance ledger tests — immutability, hash chain integrity."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from amaya.provenance import ProvenanceLedger
from amaya.schemas import Rating
from amaya.scoring import score
from tests.conftest import make_rating


def _make_rating_obj(methodology, rating_id="r1"):
    rinput = make_rating(dim_scores=7, chain_scores=6, rating_id=rating_id)
    result = score(rinput, methodology)
    return Rating(
        input=rinput, result=result,
        issued_at=datetime.now(timezone.utc),
        methodology_version=methodology.version,
    )


def test_seal_and_verify_roundtrip(tmp_path, methodology):
    ledger = ProvenanceLedger(tmp_path)
    rating = _make_rating_obj(methodology)
    bundle = ledger.seal(rating)
    assert "seal" in bundle
    assert ledger.verify(rating.input.rating_id) is True


def test_sealed_bundle_is_read_only(tmp_path, methodology):
    ledger = ProvenanceLedger(tmp_path)
    rating = _make_rating_obj(methodology)
    ledger.seal(rating)
    bundle_path = tmp_path / f"{rating.input.rating_id}.json"
    mode = bundle_path.stat().st_mode & 0o777
    assert mode == 0o444


def test_cannot_seal_same_rating_twice(tmp_path, methodology):
    ledger = ProvenanceLedger(tmp_path)
    rating = _make_rating_obj(methodology, rating_id="r-dup")
    ledger.seal(rating)
    with pytest.raises(FileExistsError):
        ledger.seal(rating)


def test_tampering_invalidates_verification(tmp_path, methodology):
    import json
    ledger = ProvenanceLedger(tmp_path)
    rating = _make_rating_obj(methodology, rating_id="r-tamper")
    ledger.seal(rating)
    bundle_path = tmp_path / "r-tamper.json"
    bundle_path.chmod(0o644)
    data = json.loads(bundle_path.read_text())
    data["result"]["final_score"] = 99.9
    bundle_path.write_text(json.dumps(data, indent=2, sort_keys=True))
    assert ledger.verify("r-tamper") is False


def test_hash_chain_links_ratings(tmp_path, methodology):
    import json
    ledger = ProvenanceLedger(tmp_path)
    for i in range(3):
        ledger.seal(_make_rating_obj(methodology, rating_id=f"r-{i}"))

    entries = [json.loads(line) for line in (tmp_path / "hash_chain.jsonl").open()]
    assert len(entries) == 3
    assert entries[0]["prev_hash"] is None
    assert entries[1]["prev_hash"] == entries[0]["chain_hash"]
    assert entries[2]["prev_hash"] == entries[1]["chain_hash"]
