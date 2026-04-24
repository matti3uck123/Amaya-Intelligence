"""Methodology registry tests — weights sum, grade bands contiguous."""
from __future__ import annotations

import pytest

from amaya.methodology import load_methodology


def test_loads_v1_0(methodology):
    assert methodology.version == "1.0.0"
    assert len(methodology.dimensions) == 12


def test_dimension_weights_sum_to_one(methodology):
    total = sum(d.weight for d in methodology.dimensions.values())
    assert abs(total - 1.0) < 1e-9


def test_layer_weights_sum_to_one(methodology):
    layers: dict[str, float] = {}
    for d in methodology.dimensions.values():
        layers[d.layer] = layers.get(d.layer, 0) + d.weight
    assert abs(sum(layers.values()) - 1.0) < 1e-9
    assert abs(layers["external_pressure"] - 0.40) < 1e-9
    assert abs(layers["internal_resilience"] - 0.35) < 1e-9
    assert abs(layers["adaptive_capacity"] - 0.25) < 1e-9


def test_grade_bands_contiguous_and_cover_0_to_100(methodology):
    bands = sorted(methodology.grades, key=lambda g: g.min)
    assert bands[0].min == 0
    assert bands[-1].max == 100
    for i in range(len(bands) - 1):
        assert bands[i].max + 1 == bands[i + 1].min, \
            f"Gap between {bands[i].grade} and {bands[i + 1].grade}"


def test_grade_for_boundary_values(methodology):
    assert methodology.grade_for(100).grade == "A+"
    assert methodology.grade_for(90).grade == "A+"
    assert methodology.grade_for(89).grade == "A"
    assert methodology.grade_for(80).grade == "A"
    assert methodology.grade_for(25).grade == "D"
    assert methodology.grade_for(24).grade == "F"
    assert methodology.grade_for(0).grade == "F"


def test_circuit_breaker_definitions(methodology):
    codes = {cb.code for cb in methodology.circuit_breakers}
    assert codes == {"CB1", "CB2", "CB3", "CB4"}
    caps = {cb.code: cb.cap for cb in methodology.circuit_breakers}
    assert caps == {"CB1": 35, "CB2": 45, "CB3": 40, "CB4": 20}


def test_unknown_methodology_raises():
    with pytest.raises(FileNotFoundError):
        load_methodology("v9.9")
