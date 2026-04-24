"""Tests for the classifier layer."""
from __future__ import annotations

import pytest

from amaya.ingest.classifier import (
    AnthropicClassifier,
    KeywordClassifier,
    _parse_response,
)
from amaya.ingest.sections import SECTIONS, sections_for_dimension
from amaya.ingest.types import RawChunk


def _chunk(text: str, source_file: str = "doc.txt") -> RawChunk:
    return RawChunk(
        source_file=source_file,
        source_id="deadbeef",
        kind="document",
        locator="chunk=1",
        text=text,
    )


# ---------- KeywordClassifier ----------


def test_keyword_classifier_financials() -> None:
    c = KeywordClassifier()
    result = c.classify(
        _chunk("Revenue of $50M with gross margin of 45%. EBITDA positive.")
    )
    assert result.section == "FIN"
    assert result.section_confidence > 0


def test_keyword_classifier_ai_strategy() -> None:
    c = KeywordClassifier()
    result = c.classify(
        _chunk(
            "Our AI strategy focuses on LLM-based tooling and generative AI. "
            "MLOps maturity is improving."
        )
    )
    assert result.section == "AI"


def test_keyword_classifier_leadership() -> None:
    c = KeywordClassifier()
    result = c.classify(
        _chunk(
            "CEO Jane Doe joined in 2020. Previously CTO at Acme. "
            "Cofounder and board member since inception."
        )
    )
    assert result.section == "TEAM"


def test_keyword_classifier_customers() -> None:
    c = KeywordClassifier()
    result = c.classify(
        _chunk(
            "Customer retention is 94%. Top 10 logos by ARR. Churn rate 8%. "
            "Master service agreement renewed annually."
        )
    )
    assert result.section == "CUST"


def test_keyword_classifier_operations() -> None:
    c = KeywordClassifier()
    result = c.classify(
        _chunk(
            "Three warehouse facilities. Supplier network of 2000 vendors. "
            "Fleet of refrigerated delivery trucks. Last mile optimization."
        )
    )
    assert result.section == "OPS"


def test_keyword_classifier_empty_text_is_other() -> None:
    c = KeywordClassifier()
    result = c.classify(_chunk("Lorem ipsum dolor sit amet consectetur."))
    assert result.section == "OTHER"
    assert result.section_confidence == 0.0


def test_keyword_classifier_is_deterministic() -> None:
    c = KeywordClassifier()
    text = "Revenue ARR gross margin EBITDA cap table"
    a = c.classify(_chunk(text))
    b = c.classify(_chunk(text))
    assert a.section == b.section
    assert a.section_confidence == b.section_confidence


def test_classified_chunk_converts_to_evidence_ref() -> None:
    c = KeywordClassifier()
    result = c.classify(_chunk("Revenue of $50M."))
    ref = result.to_evidence_ref()
    assert ref.source_id == "deadbeef"
    assert ref.locator == "chunk=1"
    assert "Revenue" in ref.snippet


def test_confidence_is_in_range() -> None:
    c = KeywordClassifier()
    result = c.classify(_chunk("revenue arr cac ltv mrr ebitda"))
    assert 0.0 <= result.section_confidence <= 1.0


# ---------- sections taxonomy ----------


def test_twelve_sections_defined() -> None:
    assert len(SECTIONS) == 12


def test_every_dimension_has_at_least_one_feeding_section() -> None:
    all_dimensions = {
        "MCS", "CPS", "SCAE", "CLS",
        "VPR", "WCI", "RMV", "TSR",
        "LAL", "SPS", "ANCR", "DIM",
    }
    for d in all_dimensions:
        assert sections_for_dimension(d), f"no section feeds {d}"


def test_other_has_no_feeds() -> None:
    assert SECTIONS["OTHER"].feeds_dimensions == ()


# ---------- _parse_response (Anthropic parser) ----------


def test_parse_response_valid() -> None:
    section, conf = _parse_response('{"section": "FIN", "confidence": 0.9}')
    assert section == "FIN"
    assert conf == 0.9


def test_parse_response_with_surrounding_text() -> None:
    section, conf = _parse_response(
        'Sure! Here is the JSON: {"section": "AI", "confidence": 0.75} — hope that helps.'
    )
    assert section == "AI"
    assert conf == 0.75


def test_parse_response_invalid_section_falls_back_to_other() -> None:
    section, _ = _parse_response('{"section": "GARBAGE", "confidence": 0.5}')
    assert section == "OTHER"


def test_parse_response_missing_json_falls_back() -> None:
    section, conf = _parse_response("sorry, I cannot classify this")
    assert section == "OTHER"
    assert conf == 0.0


def test_parse_response_clips_confidence() -> None:
    _, conf = _parse_response('{"section": "FIN", "confidence": 2.5}')
    assert conf == 1.0
    _, conf = _parse_response('{"section": "FIN", "confidence": -0.3}')
    assert conf == 0.0


def test_anthropic_classifier_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicClassifier()
