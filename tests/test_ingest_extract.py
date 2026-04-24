"""Tests for the text extractor layer."""
from __future__ import annotations

from pathlib import Path

import pytest

from amaya.ingest.extract import (
    SUPPORTED_SUFFIXES,
    _chunk,
    extract_file,
    extract_path,
    hash_file,
)


def test_hash_is_deterministic(tmp_path: Path) -> None:
    f = tmp_path / "x.txt"
    f.write_text("hello world")
    assert hash_file(f) == hash_file(f)


def test_hash_changes_with_content(tmp_path: Path) -> None:
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("aaa")
    b.write_text("bbb")
    assert hash_file(a) != hash_file(b)


def test_chunk_short_text_returns_one_chunk() -> None:
    chunks = _chunk("Short paragraph.\n\nAnother short one.")
    assert len(chunks) == 1
    assert "Short paragraph" in chunks[0]
    assert "Another short one" in chunks[0]


def test_chunk_empty_returns_empty() -> None:
    assert _chunk("") == []
    assert _chunk("    \n   ") == []


def test_chunk_long_paragraph_splits_on_sentences() -> None:
    sentences = ". ".join(f"Sentence number {i} here" for i in range(200)) + "."
    chunks = _chunk(sentences, max_chars=500)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 700  # max_chars plus overlap slack


def test_chunk_preserves_paragraph_boundaries() -> None:
    text = "Para one.\n\nPara two.\n\nPara three."
    chunks = _chunk(text, max_chars=1500)
    assert len(chunks) == 1
    assert "Para one" in chunks[0]
    assert "Para three" in chunks[0]


def test_extract_txt_file(tmp_path: Path) -> None:
    f = tmp_path / "sample.txt"
    f.write_text("This is a financials document.\n\nRevenue: $100M.")
    chunks = extract_file(f)
    assert len(chunks) == 1
    assert chunks[0].source_file == "sample.txt"
    assert chunks[0].kind == "document"
    assert chunks[0].locator.startswith("chunk=")
    assert "Revenue" in chunks[0].text


def test_extract_md_file(tmp_path: Path) -> None:
    f = tmp_path / "sample.md"
    f.write_text("# Heading\n\nSome body content.")
    chunks = extract_file(f)
    assert len(chunks) == 1
    assert "body content" in chunks[0].text


def test_extract_unsupported_returns_empty(tmp_path: Path) -> None:
    f = tmp_path / "sample.xyz"
    f.write_text("whatever")
    assert extract_file(f) == []


def test_extract_path_directory_walks_recursively(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("alpha content")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("bravo content")
    (tmp_path / "ignored.bin").write_bytes(b"\x00\x01")

    chunks, skipped = extract_path(tmp_path)
    filenames = {c.source_file for c in chunks}
    assert filenames == {"a.txt", "b.txt"}
    assert "ignored.bin" in skipped


def test_extract_path_ignores_dotfiles(tmp_path: Path) -> None:
    (tmp_path / ".DS_Store").write_text("noise")
    (tmp_path / "real.txt").write_text("substance")
    chunks, _ = extract_path(tmp_path)
    assert len(chunks) == 1
    assert chunks[0].source_file == "real.txt"


def test_extract_same_file_twice_yields_same_source_id(tmp_path: Path) -> None:
    f = tmp_path / "a.txt"
    f.write_text("same content")
    a = extract_file(f)
    b = extract_file(f)
    assert a[0].source_id == b[0].source_id


def test_supported_suffixes_are_lowercase() -> None:
    assert all(s == s.lower() for s in SUPPORTED_SUFFIXES)


def test_nonexistent_path_raises_via_pipeline(tmp_path: Path) -> None:
    from amaya.ingest.pipeline import ingest

    with pytest.raises(FileNotFoundError):
        ingest(tmp_path / "nope")
