"""Structural tests on the prompt library.

These don't test LLM output — we can't mock the model's judgment. They
test that the prompt assembly code produces well-formed prompts that
include the rubric, the evidence, and the instruction to call the
right tool. If any of these ever fail, we shipped a broken prompt and
every downstream rating is invalid."""
from __future__ import annotations

from amaya.agents.prompts import (
    CHAIN_SPECS,
    DIMENSION_SPECS,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_chain_prompt,
    build_dimension_prompt,
    chain_tool_schema,
    dimension_tool_schema,
    format_evidence,
)
from amaya.ingest.types import ClassifiedChunk, RawChunk


def _chunk(section: str, text: str, filename: str = "doc.txt") -> ClassifiedChunk:
    return ClassifiedChunk(
        section=section,
        section_confidence=0.9,
        raw=RawChunk(
            source_file=filename,
            source_id="a" * 64,
            kind="document",
            locator="page=1",
            text=text,
        ),
    )


# ---------- spec coverage ----------


def test_all_12_dimensions_have_specs() -> None:
    codes = {"MCS", "CPS", "SCAE", "CLS", "VPR", "WCI", "RMV", "TSR", "LAL", "SPS", "ANCR", "DIM"}
    assert set(DIMENSION_SPECS.keys()) == codes


def test_all_4_chain_positions_have_specs() -> None:
    positions = {"upstream", "downstream", "lateral", "end_consumer"}
    assert set(CHAIN_SPECS.keys()) == positions


def test_every_dimension_rubric_covers_rubric_anchors() -> None:
    for code, spec in DIMENSION_SPECS.items():
        scores = {score for score, _ in spec.rubric}
        # Must include both extremes so the agent knows the polarity
        assert 10 in scores, f"{code} rubric missing 10-anchor"
        assert 1 in scores, f"{code} rubric missing 1-anchor"


def test_every_chain_rubric_covers_rubric_anchors() -> None:
    for position, spec in CHAIN_SPECS.items():
        scores = {score for score, _ in spec.rubric}
        assert 10 in scores, f"{position} rubric missing 10-anchor"
        assert 1 in scores, f"{position} rubric missing 1-anchor"


def test_every_dimension_declares_evidence_sections() -> None:
    for code, spec in DIMENSION_SPECS.items():
        assert spec.evidence_sections, f"{code} declares no evidence sections"


def test_prompt_version_pinned() -> None:
    assert PROMPT_VERSION == "1.0.0"


# ---------- prompt assembly ----------


def test_build_dimension_prompt_includes_rubric_and_evidence() -> None:
    spec = DIMENSION_SPECS["MCS"]
    chunks = [_chunk("MKT", "Category is shrinking 30% by 2030."),
              _chunk("COMP", "AI-native competitors replicating feature set.")]
    evidence = format_evidence(chunks)
    prompt = build_dimension_prompt(spec, "Colabor", "Food Distribution", evidence)
    assert "Market Category Stability" in prompt
    assert "1-10" in prompt
    assert "Category is shrinking" in prompt
    assert "submit_MCS_score" in prompt
    assert "Colabor" in prompt
    assert "Food Distribution" in prompt


def test_build_chain_prompt_includes_rubric_and_evidence() -> None:
    spec = CHAIN_SPECS["upstream"]
    chunks = [_chunk("OPS", "Suppliers adopting AI-driven direct channels.")]
    evidence = format_evidence(chunks)
    prompt = build_chain_prompt(spec, "Colabor", "Food Distribution", evidence)
    assert "Upstream" in prompt
    assert "1-10" in prompt
    assert "suppliers" in prompt.lower()
    assert "submit_upstream_score" in prompt


def test_format_evidence_numbers_chunks() -> None:
    chunks = [_chunk("FIN", "Revenue $100M"), _chunk("FIN", "EBITDA $20M")]
    formatted = format_evidence(chunks)
    assert "[1]" in formatted
    assert "[2]" in formatted
    assert "Revenue $100M" in formatted


def test_format_evidence_empty_is_readable() -> None:
    formatted = format_evidence([])
    assert formatted  # must not be empty — model needs to know it's empty
    assert "no evidence" in formatted.lower() or "No evidence" in formatted


# ---------- tool schemas ----------


def test_dimension_tool_schema_requires_all_fields() -> None:
    schema = dimension_tool_schema("MCS")
    required = set(schema["required"])
    assert required == {"score", "rationale", "confidence", "evidence_indices"}
    assert schema["properties"]["score"]["minimum"] == 1
    assert schema["properties"]["score"]["maximum"] == 10
    assert schema["properties"]["confidence"]["minimum"] == 0.0
    assert schema["properties"]["confidence"]["maximum"] == 1.0


def test_chain_tool_schema_requires_score_and_rationale() -> None:
    schema = chain_tool_schema("upstream")
    required = set(schema["required"])
    assert required == {"score", "rationale"}
    assert schema["properties"]["score"]["minimum"] == 1
    assert schema["properties"]["score"]["maximum"] == 10


def test_system_prompt_sets_analyst_framing() -> None:
    assert "Amaya Intelligence" in SYSTEM_PROMPT
    assert "confidence" in SYSTEM_PROMPT.lower()
    assert "rationale" in SYSTEM_PROMPT.lower()
