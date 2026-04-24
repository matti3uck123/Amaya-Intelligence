"""Methodology registry loader.

The registry lives as versioned YAML files under `methodology/`. Each rating
pins a methodology version. Old ratings never recalculate when the methodology
changes — this is the Moody's property: ratings are reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


DEFAULT_REGISTRY_DIR = Path(__file__).parent.parent / "methodology"


@dataclass(frozen=True)
class DimensionSpec:
    code: str
    name: str
    weight: float
    layer: str


@dataclass(frozen=True)
class CircuitBreakerSpec:
    code: str
    description: str
    trigger: dict[str, dict[str, int]]
    cap: int

    def fires(self, dim_scores: dict[str, int]) -> bool:
        for dim_code, condition in self.trigger.items():
            score = dim_scores.get(dim_code)
            if score is None:
                return False
            for op, threshold in condition.items():
                if op == "lte" and not (score <= threshold):
                    return False
                elif op == "gte" and not (score >= threshold):
                    return False
                elif op == "eq" and not (score == threshold):
                    return False
        return True


@dataclass(frozen=True)
class GradeBand:
    grade: str
    min: int
    max: int
    label: str
    action: str

    def contains(self, score: float) -> bool:
        return self.min <= score <= self.max


@dataclass(frozen=True)
class ChainModifierSpec:
    low: float
    high: float
    position_weights: dict[str, float]

    def compute(self, position_scores: dict[str, int]) -> float:
        """Map chain position scores (1-10) to modifier in [low, high].

        A position_score of 1 → low end (contraction). 10 → high end (tailwind).
        Weighted mean across positions, then linearly mapped.
        """
        if not position_scores:
            return 1.0
        total_weight = 0.0
        weighted_sum = 0.0
        for position, score in position_scores.items():
            w = self.position_weights.get(position, 0.0)
            total_weight += w
            weighted_sum += score * w
        if total_weight == 0:
            return 1.0
        mean_normalized = (weighted_sum / total_weight - 1) / 9  # 0..1
        return round(self.low + (self.high - self.low) * mean_normalized, 4)


@dataclass(frozen=True)
class Methodology:
    version: str
    name: str
    dimensions: dict[str, DimensionSpec]
    circuit_breakers: list[CircuitBreakerSpec]
    grades: list[GradeBand]
    chain_modifier: ChainModifierSpec
    raw_yaml: dict[str, Any]

    def validate_weights(self) -> None:
        """Dimension weights must sum to 1.0 (±0.001)."""
        total = sum(d.weight for d in self.dimensions.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Dimension weights sum to {total:.4f}, expected 1.0")

    def grade_for(self, score: float) -> GradeBand:
        for band in self.grades:
            if band.contains(score):
                return band
        raise ValueError(f"No grade band contains score {score}")


def load_methodology(version: str = "v1.0", registry_dir: Path | None = None) -> Methodology:
    registry_dir = registry_dir or DEFAULT_REGISTRY_DIR
    path = registry_dir / f"{version}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Methodology {version} not found at {path}")
    with path.open() as f:
        data = yaml.safe_load(f)

    dimensions: dict[str, DimensionSpec] = {}
    for layer_name, layer in data["layers"].items():
        for code, dim in layer["dimensions"].items():
            dimensions[code] = DimensionSpec(
                code=code, name=dim["name"], weight=dim["weight"], layer=layer_name
            )

    breakers = [
        CircuitBreakerSpec(code=code, description=spec["description"],
                           trigger=spec["trigger"], cap=spec["cap"])
        for code, spec in data["circuit_breakers"].items()
    ]

    grades = [
        GradeBand(grade=g["grade"], min=g["min"], max=g["max"],
                  label=g["label"], action=g["action"])
        for g in data["grades"]
    ]

    cm = data["chain_modifier"]
    chain_modifier = ChainModifierSpec(
        low=cm["range"][0],
        high=cm["range"][1],
        position_weights={pos: spec["weight"] for pos, spec in cm["positions"].items()},
    )

    m = Methodology(
        version=data["version"],
        name=data["name"],
        dimensions=dimensions,
        circuit_breakers=breakers,
        grades=grades,
        chain_modifier=chain_modifier,
        raw_yaml=data,
    )
    m.validate_weights()
    return m
