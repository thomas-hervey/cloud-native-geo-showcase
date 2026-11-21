"""Tests for scripts.bradley_terry.rank_models."""
from __future__ import annotations

import pandas as pd

from scripts.bradley_terry import rank_models


def test_rank_models_returns_correct_order():
    """A always beats B and C; B always beats C → BT output: A > B > C."""
    records = []
    places = [f"place_{i}" for i in range(5)]
    for place in places:
        records += [
            {"source_a": "llm:a", "place": place, "composite_score": 0.9},
            {"source_a": "llm:b", "place": place, "composite_score": 0.5},
            {"source_a": "llm:c", "place": place, "composite_score": 0.2},
        ]
    df = pd.DataFrame(records)
    result = rank_models(df)

    assert not result.empty, "Expected non-empty result for 3 models with shared coverage"
    assert list(result["source_a"]) == ["llm:a", "llm:b", "llm:c"], (
        f"Expected A > B > C, got {list(result['source_a'])}"
    )


def test_rank_models_insufficient_data_returns_empty():
    """Single model input should return empty DataFrame — can't compute pairwise."""
    df = pd.DataFrame({
        "source_a": ["llm:a", "llm:a"],
        "place": ["place_1", "place_2"],
        "composite_score": [0.8, 0.7],
    })
    result = rank_models(df)
    assert result.empty, "Expected empty DataFrame for single-model input"


def test_rank_models_no_shared_places_returns_empty():
    """Two models on disjoint places produce no pairs → empty DataFrame."""
    df = pd.DataFrame({
        "source_a": ["llm:a", "llm:b"],
        "place": ["place_1", "place_2"],  # each model only covers one place
        "composite_score": [0.8, 0.7],
    })
    result = rank_models(df)
    assert result.empty, "Expected empty DataFrame when models share no places"


def test_rank_models_handles_ties():
    """All models tied on all places produce no wins → empty DataFrame, no exception."""
    records = []
    for place in ["place_1", "place_2"]:
        for model in ["llm:a", "llm:b", "llm:c"]:
            records.append({"source_a": model, "place": place, "composite_score": 0.5})
    df = pd.DataFrame(records)

    result = rank_models(df)  # must not raise
    assert result.empty, "Expected empty DataFrame when all scores are tied (no pairs)"


def test_rank_models_averages_multiple_runs():
    """Per-place averaging collapses multiple runs before constructing pairs.

    model_a: avg(1.0, 0.0, 0.0) = 0.333; model_b: avg(0.5, 0.5, 0.5) = 0.500
    After averaging, model_b has higher score on place_1 → model_b wins.
    This verifies that a single high run by model_a doesn't dominate.
    """
    df = pd.DataFrame({
        "source_a": ["llm:a"] * 3 + ["llm:b"] * 3,
        "place": ["place_1"] * 6,
        "composite_score": [1.0, 0.0, 0.0, 0.5, 0.5, 0.5],
    })
    result = rank_models(df)

    assert len(result) == 2, "Expected both models in result"
    assert result.iloc[0]["source_a"] == "llm:b", (
        "model_b should rank first: avg 0.5 > avg 0.333 for model_a"
    )
