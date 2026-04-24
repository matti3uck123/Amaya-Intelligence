"""Document ingest pipeline — raw files → classified evidence chunks."""
from amaya.ingest.sections import SECTIONS, SectionCode, SectionSpec
from amaya.ingest.types import ClassifiedChunk, IngestResult, RawChunk
from amaya.ingest.extract import extract_file, extract_path
from amaya.ingest.classifier import (
    Classifier,
    KeywordClassifier,
    AnthropicClassifier,
)
from amaya.ingest.pipeline import ingest

__all__ = [
    "SECTIONS",
    "SectionCode",
    "SectionSpec",
    "ClassifiedChunk",
    "IngestResult",
    "RawChunk",
    "extract_file",
    "extract_path",
    "Classifier",
    "KeywordClassifier",
    "AnthropicClassifier",
    "ingest",
]
