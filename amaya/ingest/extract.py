"""File → RawChunk extraction. Supports PDF, DOCX, TXT, MD."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

import pdfplumber
from docx import Document as DocxDocument

from amaya.ingest.types import RawChunk

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}

_MAX_CHARS = 1500
_OVERLAP_CHARS = 150


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def extract_file(path: Path) -> list[RawChunk]:
    """Extract all chunks from one file. Returns [] for unsupported types."""
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        return []
    source_id = hash_file(path)
    if suffix == ".pdf":
        return list(_extract_pdf(path, source_id))
    if suffix == ".docx":
        return list(_extract_docx(path, source_id))
    return list(_extract_text(path, source_id))


def extract_path(path: Path) -> tuple[list[RawChunk], list[str]]:
    """Extract from a file or recursively from a directory.

    Returns (chunks, skipped_filenames).
    """
    chunks: list[RawChunk] = []
    skipped: list[str] = []
    if path.is_file():
        if path.suffix.lower() in SUPPORTED_SUFFIXES:
            chunks.extend(extract_file(path))
        else:
            skipped.append(path.name)
        return chunks, skipped
    for child in sorted(path.rglob("*")):
        if not child.is_file() or child.name.startswith("."):
            continue
        if child.suffix.lower() not in SUPPORTED_SUFFIXES:
            skipped.append(str(child.relative_to(path)))
            continue
        chunks.extend(extract_file(child))
    return chunks, skipped


def _extract_pdf(path: Path, source_id: str) -> Iterable[RawChunk]:
    with pdfplumber.open(path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            for chunk_text in _chunk(text):
                yield RawChunk(
                    source_file=path.name,
                    source_id=source_id,
                    kind="document",
                    locator=f"page={page_num}",
                    text=chunk_text,
                )


def _extract_docx(path: Path, source_id: str) -> Iterable[RawChunk]:
    doc = DocxDocument(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    full_text = "\n\n".join(paragraphs)
    for idx, chunk_text in enumerate(_chunk(full_text), start=1):
        yield RawChunk(
            source_file=path.name,
            source_id=source_id,
            kind="document",
            locator=f"chunk={idx}",
            text=chunk_text,
        )


def _extract_text(path: Path, source_id: str) -> Iterable[RawChunk]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    for idx, chunk_text in enumerate(_chunk(raw), start=1):
        yield RawChunk(
            source_file=path.name,
            source_id=source_id,
            kind="document",
            locator=f"chunk={idx}",
            text=chunk_text,
        )


def _chunk(text: str, max_chars: int = _MAX_CHARS, overlap: int = _OVERLAP_CHARS) -> list[str]:
    """Paragraph-aware chunker with sentence fallback + overlap.

    - Split on blank lines first (paragraphs are the natural semantic unit).
    - Pack paragraphs greedily until max_chars.
    - For paragraphs that are themselves > max_chars, sentence-split them.
    - Between chunks keep a small character overlap so boundary evidence
      still appears in at least one chunk.
    """
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    for p in paragraphs:
        if len(p) <= max_chars:
            pieces.append(p)
        else:
            pieces.extend(_split_sentences(p, max_chars))

    chunks: list[str] = []
    buf = ""
    for piece in pieces:
        if not buf:
            buf = piece
            continue
        if len(buf) + 2 + len(piece) <= max_chars:
            buf = f"{buf}\n\n{piece}"
        else:
            chunks.append(buf)
            tail = buf[-overlap:] if overlap and len(buf) > overlap else ""
            buf = f"{tail} {piece}".strip() if tail else piece
    if buf:
        chunks.append(buf)
    return chunks


def _split_sentences(text: str, max_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out: list[str] = []
    buf = ""
    for s in sentences:
        if len(s) > max_chars:
            # pathologically long sentence — hard-split on char count
            for i in range(0, len(s), max_chars):
                out.append(s[i : i + max_chars])
            continue
        if not buf:
            buf = s
            continue
        if len(buf) + 1 + len(s) <= max_chars:
            buf = f"{buf} {s}"
        else:
            out.append(buf)
            buf = s
    if buf:
        out.append(buf)
    return out
