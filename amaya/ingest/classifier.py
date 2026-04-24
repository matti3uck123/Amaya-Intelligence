"""Chunk → section classifier.

Two implementations share the Classifier protocol:

KeywordClassifier
    Deterministic, offline, no API. Scores each chunk against each
    section's keyword list and picks the best match. Ships by default —
    the ingest pipeline runs today with zero external dependencies.

AnthropicClassifier
    Calls Claude Haiku (fast, cheap: ~$0.003 per chunk). Used when
    ANTHROPIC_API_KEY is set. Higher accuracy on edge cases.

Both return ClassifiedChunk with a 0-1 confidence. The pipeline stores
the confidence so the dashboard can flag low-confidence classifications
for analyst review.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Protocol

from amaya.ingest.sections import SECTIONS, SectionCode
from amaya.ingest.types import ClassifiedChunk, RawChunk


class Classifier(Protocol):
    def classify(self, chunk: RawChunk) -> ClassifiedChunk: ...


# ---------- KeywordClassifier ----------


@dataclass
class KeywordClassifier:
    """Fast deterministic classifier.

    Strategy: each section has a vocab. For a chunk, count how many of
    each section's keywords appear (case-insensitive, whole-word). The
    section with the most hits wins; ties are broken by higher keyword
    density (hits / len(keywords)). Chunks with zero hits fall to OTHER.

    Confidence = (winner_hits - runner_up_hits) / winner_hits, clipped
    to [0.15, 1.0]. So a chunk that exclusively matches one section
    gets high confidence; one that matches two sections about equally
    gets low confidence and can be flagged for LLM rescoring.
    """

    min_confidence: float = 0.15

    def classify(self, chunk: RawChunk) -> ClassifiedChunk:
        text_lower = chunk.text.lower()
        scores: dict[SectionCode, int] = {}
        for code, spec in SECTIONS.items():
            if code == "OTHER" or not spec.keywords:
                continue
            hits = 0
            for kw in spec.keywords:
                pattern = r"\b" + re.escape(kw.lower()) + r"\b"
                if re.search(pattern, text_lower):
                    hits += 1
            if hits:
                scores[code] = hits

        if not scores:
            return ClassifiedChunk(section="OTHER", section_confidence=0.0, raw=chunk)

        ranked = sorted(
            scores.items(),
            key=lambda kv: (kv[1], kv[1] / max(len(SECTIONS[kv[0]].keywords), 1)),
            reverse=True,
        )
        winner, win_hits = ranked[0]
        runner_up_hits = ranked[1][1] if len(ranked) > 1 else 0
        confidence = (win_hits - runner_up_hits) / win_hits
        confidence = max(self.min_confidence, min(1.0, confidence))
        return ClassifiedChunk(
            section=winner, section_confidence=round(confidence, 3), raw=chunk
        )


# ---------- AnthropicClassifier ----------


_CLASSIFY_SYSTEM = """You classify short text excerpts from a company's data room into one of 12 sections.

Return ONLY a JSON object: {"section": "<CODE>", "confidence": <0.0-1.0>}.

Sections:
- CORP: Corporate Overview — pitch deck, mission, company description
- FIN: Financials — revenue, P&L, cap table, unit economics
- PROD: Product & Technology — features, architecture, tech stack
- CUST: Customers & Contracts — customer lists, contracts, retention
- COMP: Competitive Landscape — competitor analysis, positioning
- TEAM: Leadership & Team — exec bios, org chart, headcount
- OPS: Operations & Supply Chain — logistics, fulfillment, vendors
- LEGAL: Legal, IP & Regulatory — patents, contracts, compliance
- MKT: Market Analysis — TAM/SAM, industry reports, trends
- AI: AI Strategy & Roadmap — AI/ML strategy, model deployment
- GOV: Governance & Board — board materials, committees
- OTHER: none of the above

Pick the single best fit. Confidence is your certainty (0.5 = genuinely ambiguous)."""


@dataclass
class AnthropicClassifier:
    """Uses Claude Haiku via the Anthropic API.

    Requires ANTHROPIC_API_KEY in env or passed explicitly. The model
    id is pinned so rating provenance records exactly which classifier
    version produced each chunk's section label.
    """

    model: str = "claude-haiku-4-5-20251001"
    api_key: str | None = None
    max_retries: int = 2

    def __post_init__(self) -> None:
        key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "AnthropicClassifier requires ANTHROPIC_API_KEY — "
                "set env var or pass api_key explicitly."
            )
        # Import lazily so tests that only use KeywordClassifier don't
        # pay the anthropic import cost.
        from anthropic import Anthropic

        self._client = Anthropic(api_key=key)

    def classify(self, chunk: RawChunk) -> ClassifiedChunk:
        excerpt = chunk.text[:2000]
        response = self._client.messages.create(
            model=self.model,
            max_tokens=60,
            system=_CLASSIFY_SYSTEM,
            messages=[{"role": "user", "content": excerpt}],
        )
        content = response.content[0].text.strip() if response.content else "{}"
        section, confidence = _parse_response(content)
        return ClassifiedChunk(
            section=section, section_confidence=confidence, raw=chunk
        )


_VALID_CODES = set(SECTIONS.keys())


def _parse_response(text: str) -> tuple[SectionCode, float]:
    match = re.search(r"\{.*?\}", text, flags=re.DOTALL)
    if not match:
        return "OTHER", 0.0
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return "OTHER", 0.0
    section = str(data.get("section", "OTHER")).upper()
    if section not in _VALID_CODES:
        section = "OTHER"
    try:
        confidence = float(data.get("confidence", 0.5))
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))
    return section, confidence  # type: ignore[return-value]
