"""End-to-end pipeline tests against the synthetic Colabor data room."""
from __future__ import annotations

from pathlib import Path

import pytest

from amaya.ingest import ingest
from amaya.ingest.classifier import KeywordClassifier

SAMPLE_ROOM = Path(__file__).parent.parent / "examples" / "sample_dataroom"


def test_sample_dataroom_exists() -> None:
    assert SAMPLE_ROOM.is_dir()
    files = list(SAMPLE_ROOM.glob("*.txt"))
    assert len(files) >= 11


def test_ingest_sample_dataroom_classifies_every_file() -> None:
    result = ingest(SAMPLE_ROOM)
    assert result.files_ingested >= 11
    assert len(result.chunks) >= 11
    assert all(c.section in {
        "CORP", "FIN", "PROD", "CUST", "COMP", "TEAM",
        "OPS", "LEGAL", "MKT", "AI", "GOV", "OTHER",
    } for c in result.chunks)


def test_ingest_sample_dataroom_hits_all_major_sections() -> None:
    """Sanity check that KeywordClassifier picks the obvious section
    for each curated source file — if this ever fails, either the
    source document changed or the taxonomy keywords regressed."""
    result = ingest(SAMPLE_ROOM)
    by_file: dict[str, str] = {}
    for c in result.chunks:
        # keep the first chunk's classification per file
        by_file.setdefault(c.raw.source_file, c.section)

    expected = {
        "02-financials.txt": "FIN",
        "03-product-tech.txt": "PROD",
        "04-customers.txt": "CUST",
        "05-competitive.txt": "COMP",
        "06-leadership.txt": "TEAM",
        "07-operations.txt": "OPS",
        "08-legal.txt": "LEGAL",
        "09-market.txt": "MKT",
        "10-ai-strategy.txt": "AI",
        "11-governance.txt": "GOV",
    }
    for filename, section in expected.items():
        assert by_file.get(filename) == section, (
            f"{filename}: expected {section}, got {by_file.get(filename)}"
        )


def test_ingest_result_summary_sums_to_chunk_count() -> None:
    result = ingest(SAMPLE_ROOM)
    assert sum(result.summary().values()) == len(result.chunks)


def test_ingest_by_section_partitions_chunks() -> None:
    result = ingest(SAMPLE_ROOM)
    grouped = result.by_section()
    total = sum(len(v) for v in grouped.values())
    assert total == len(result.chunks)


def test_ingest_uses_keyword_classifier_by_default() -> None:
    r1 = ingest(SAMPLE_ROOM)
    r2 = ingest(SAMPLE_ROOM, classifier=KeywordClassifier())
    assert r1.summary() == r2.summary()


def test_ingest_single_file(tmp_path: Path) -> None:
    f = tmp_path / "finance.txt"
    f.write_text("Revenue was $100M. EBITDA margin improved to 15%.")
    result = ingest(f)
    assert result.files_ingested == 1
    assert len(result.chunks) == 1
    assert result.chunks[0].section == "FIN"


def test_ingest_nonexistent_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ingest(tmp_path / "nothing")


def test_ingest_records_skipped_files(tmp_path: Path) -> None:
    (tmp_path / "doc.txt").write_text("Revenue hit $10M.")
    (tmp_path / "image.png").write_bytes(b"\x89PNG\x00")
    result = ingest(tmp_path)
    assert "image.png" in result.files_skipped
    assert result.files_ingested == 1


def test_ingest_produces_evidence_refs_compatible_with_scoring() -> None:
    """The classified chunks must convert cleanly into EvidenceRef
    objects — that's the contract Session 3 agents will rely on."""
    result = ingest(SAMPLE_ROOM)
    refs = [c.to_evidence_ref() for c in result.chunks]
    assert all(r.source_id for r in refs)
    assert all(r.locator for r in refs)
    assert all(len(r.snippet) <= 500 for r in refs)
