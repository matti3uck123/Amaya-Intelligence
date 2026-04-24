"""Deterministic scoring engine.

No LLM. No randomness. Same input + same methodology version → same output,
forever. This is what makes an ADI rating auditable three years later.
"""
from __future__ import annotations

from .methodology import Methodology
from .schemas import (
    CircuitBreakerTrigger,
    RatingInput,
    ScoringResult,
)


def score(rating_input: RatingInput, methodology: Methodology) -> ScoringResult:
    dim_scores = rating_input.dim_map()
    _assert_all_dimensions_present(dim_scores, methodology)

    raw = _compute_raw_score(dim_scores, methodology)
    chain_mod = methodology.chain_modifier.compute(rating_input.chain.by_position())
    chain_mod = _apply_chain_escalation(rating_input.chain.by_position(),
                                        chain_mod, methodology)

    adjusted = raw * chain_mod

    triggered, cap = _evaluate_circuit_breakers(dim_scores, methodology)
    final = min(adjusted, cap) if cap is not None else adjusted
    final = max(0.0, min(100.0, final))
    final = round(final, 2)

    band = methodology.grade_for(final)

    return ScoringResult(
        raw_score=round(raw, 2),
        chain_modifier=chain_mod,
        adjusted_score=round(adjusted, 2),
        final_score=final,
        grade=band.grade,  # type: ignore[arg-type]
        grade_label=band.label,
        grade_action=band.action,
        circuit_breakers_triggered=triggered,
        methodology_version=methodology.version,
    )


def _assert_all_dimensions_present(
    dim_scores: dict[str, int], methodology: Methodology
) -> None:
    missing = set(methodology.dimensions) - set(dim_scores)
    if missing:
        raise ValueError(f"Missing dimension scores: {sorted(missing)}")
    extra = set(dim_scores) - set(methodology.dimensions)
    if extra:
        raise ValueError(f"Unknown dimension codes: {sorted(extra)}")


def _compute_raw_score(dim_scores: dict[str, int], methodology: Methodology) -> float:
    total = 0.0
    for code, spec in methodology.dimensions.items():
        total += dim_scores[code] * spec.weight
    return total * 10.0  # scores 1-10 × weights summing to 1.0 → 10-100


def _apply_chain_escalation(
    position_scores: dict[str, int],
    base_modifier: float,
    methodology: Methodology,
) -> float:
    if not position_scores:
        return base_modifier
    escalation = methodology.raw_yaml.get("chain_modifier", {}).get("escalation", {})
    terminal = escalation.get("terminal_collapse", {})
    tailwind = escalation.get("ai_tailwind", {})
    if terminal and all(s <= terminal.get("all_positions_lte", 0)
                        for s in position_scores.values()):
        return terminal["forced_modifier"]
    if tailwind and all(s >= tailwind.get("all_positions_gte", 11)
                        for s in position_scores.values()):
        return tailwind["forced_modifier"]
    return base_modifier


def _evaluate_circuit_breakers(
    dim_scores: dict[str, int], methodology: Methodology
) -> tuple[list[CircuitBreakerTrigger], int | None]:
    triggered: list[CircuitBreakerTrigger] = []
    lowest_cap: int | None = None
    for cb in methodology.circuit_breakers:
        if cb.fires(dim_scores):
            triggered.append(CircuitBreakerTrigger(
                code=cb.code, description=cb.description, cap=cb.cap
            ))
            if lowest_cap is None or cb.cap < lowest_cap:
                lowest_cap = cb.cap
    return triggered, lowest_cap
