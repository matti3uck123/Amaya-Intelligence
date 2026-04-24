"""Provenance ledger — signed, reconstructable rating bundles.

Every rating writes a bundle with:
  - source evidence hashes
  - methodology version
  - agent trajectory (provided externally; this module seals whatever is given)
  - per-dimension scoring
  - final composition
  - SHA-256 seal

Brief calls for AWS KMS + S3 Object Lock. Path A uses local WORM-style
storage: write-once files whose hash is committed to a hash chain file.
When we move to Path B, the hash chain becomes the input to KMS signing.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import Rating


class ProvenanceLedger:
    """Local filesystem ledger. One bundle per rating, immutable after seal."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.chain_file = self.root / "hash_chain.jsonl"

    def seal(
        self,
        rating: Rating,
        source_evidence: list[dict[str, Any]] | None = None,
        agent_trajectory: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        bundle = {
            "rating_id": rating.input.rating_id,
            "company_name": rating.input.company_name,
            "methodology_version": rating.methodology_version,
            "pipeline_version": rating.pipeline_version,
            "issued_at": rating.issued_at.isoformat(),
            "sealed_at": datetime.now(timezone.utc).isoformat(),
            "input": rating.input.model_dump(),
            "result": rating.result.model_dump(),
            "source_evidence": source_evidence or [],
            "agent_trajectory": agent_trajectory or [],
        }

        serialized = json.dumps(bundle, sort_keys=True, separators=(",", ":"),
                                default=str).encode("utf-8")
        bundle_hash = hashlib.sha256(serialized).hexdigest()
        bundle["seal"] = {"algorithm": "sha256", "digest": bundle_hash}

        bundle_path = self.root / f"{rating.input.rating_id}.json"
        if bundle_path.exists():
            raise FileExistsError(
                f"Bundle {rating.input.rating_id} already sealed. "
                f"Ratings are immutable — issue a new rating_id to supersede."
            )

        bundle_path.write_text(json.dumps(bundle, indent=2, sort_keys=True,
                                          default=str))
        bundle_path.chmod(0o444)  # read-only

        self._append_chain(rating.input.rating_id, bundle_hash)
        return bundle

    def verify(self, rating_id: str) -> bool:
        """Recompute the hash of a stored bundle and confirm it matches."""
        bundle_path = self.root / f"{rating_id}.json"
        if not bundle_path.exists():
            return False
        bundle = json.loads(bundle_path.read_text())
        recorded = bundle.pop("seal")
        serialized = json.dumps(bundle, sort_keys=True, separators=(",", ":"),
                                default=str).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest() == recorded["digest"]

    def _append_chain(self, rating_id: str, bundle_hash: str) -> None:
        prev_hash = self._tail_hash()
        entry = {
            "rating_id": rating_id,
            "bundle_hash": bundle_hash,
            "prev_hash": prev_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        entry["chain_hash"] = hashlib.sha256(
            json.dumps(entry, sort_keys=True).encode("utf-8")
        ).hexdigest()
        with self.chain_file.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def _tail_hash(self) -> str | None:
        if not self.chain_file.exists():
            return None
        with self.chain_file.open() as f:
            lines = f.readlines()
        if not lines:
            return None
        return json.loads(lines[-1])["chain_hash"]


def hash_file(path: Path) -> str:
    """SHA-256 of a source file — used for evidence provenance."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
