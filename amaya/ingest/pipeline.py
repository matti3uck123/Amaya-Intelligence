"""Top-level ingest orchestrator.

`ingest(path, classifier=...)` is the single entry point. It walks a
file or directory, extracts every supported document into chunks,
classifies each chunk into one of the 12 sections, and returns an
`IngestResult` that downstream (Session 3 agents, or the dashboard)
can consume.
"""
from __future__ import annotations

from pathlib import Path

from amaya.ingest.classifier import Classifier, KeywordClassifier
from amaya.ingest.extract import extract_path
from amaya.ingest.types import ClassifiedChunk, IngestResult


def ingest(
    path: Path | str,
    classifier: Classifier | None = None,
) -> IngestResult:
    """Run the full ingest pipeline on a data-room path."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Ingest path does not exist: {path}")

    raw_chunks, skipped = extract_path(path)
    clf = classifier or KeywordClassifier()
    classified: list[ClassifiedChunk] = [clf.classify(c) for c in raw_chunks]

    files_ingested = len({c.raw.source_file for c in classified})
    return IngestResult(
        source_path=str(path),
        files_ingested=files_ingested,
        files_skipped=skipped,
        chunks=classified,
    )
