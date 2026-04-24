"""Types flowing through the ingest pipeline.

RawChunk    — text extracted from a file, with source metadata
ClassifiedChunk — a RawChunk tagged with a section + confidence
IngestResult — the full output: every classified chunk from a data room
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from amaya.ingest.sections import SectionCode
from amaya.schemas import EvidenceRef


class RawChunk(BaseModel):
    """Text extracted from one document, one logical span."""
    source_file: str = Field(description="Original filename, e.g. 'pitch-deck.pdf'")
    source_id: str = Field(description="SHA-256 of the source file")
    kind: str = Field(default="document", description="'document' | 'interview' | 'external'")
    locator: str = Field(description="'page=3' or 'lines=42-58' etc.")
    text: str = Field(description="Verbatim extracted text")


class ClassifiedChunk(BaseModel):
    """A RawChunk assigned to one of the 12 data-room sections."""
    section: SectionCode
    section_confidence: float = Field(ge=0.0, le=1.0)
    raw: RawChunk

    def to_evidence_ref(self, max_snippet: int = 500) -> EvidenceRef:
        """Convert to the scoring-engine EvidenceRef contract."""
        return EvidenceRef(
            source_id=self.raw.source_id,
            kind="document" if self.raw.kind == "document" else self.raw.kind,
            locator=self.raw.locator,
            snippet=self.raw.text[:max_snippet],
        )


class IngestResult(BaseModel):
    """Full output of `ingest(path)`."""
    source_path: str
    files_ingested: int
    files_skipped: list[str] = Field(default_factory=list)
    chunks: list[ClassifiedChunk]

    def by_section(self) -> dict[str, list[ClassifiedChunk]]:
        out: dict[str, list[ClassifiedChunk]] = {}
        for c in self.chunks:
            out.setdefault(c.section, []).append(c)
        return out

    def summary(self) -> dict[str, int]:
        """{section_code: chunk_count} — useful for the CLI/demo UI."""
        counts: dict[str, int] = {}
        for c in self.chunks:
            counts[c.section] = counts.get(c.section, 0) + 1
        return counts
