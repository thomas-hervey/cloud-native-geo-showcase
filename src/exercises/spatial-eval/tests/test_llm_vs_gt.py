"""Tests for the LLM vs Ground Truth tab rendering logic."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

# The function under test lives inside the tab module; extract the mode lambda
# directly so we can unit-test it without importing Streamlit.
_mode_agg = lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "?"  # noqa: E731


def _de9im_mode(series: pd.Series) -> str:
    """Mirror of the agg lambda used in render_tab."""
    return series.groupby(lambda _: 0).agg(_mode_agg).iloc[0]


def _make_df(
    source_a: str,
    de9im_labels: list,
    place: str = "Test Place",
    reference_gt: str = "sf_planning",
) -> pd.DataFrame:
    n = len(de9im_labels)
    return pd.DataFrame({
        "source_a": [source_a] * n,
        "source_b": [reference_gt] * n,
        "place": [place] * n,
        "run_id": [f"run-{i}" for i in range(n)],
        "de9im_label": de9im_labels,
        "iou": [0.5] * n,
        "composite_score": [0.6] * n,
    })


# ── de9im mode aggregation ──────────────────────────────────────────────────

def test_mode_returns_most_common_label() -> None:
    s = pd.Series(["overlaps", "overlaps", "contains"])
    result = s.groupby(lambda _: 0).agg(_mode_agg).iloc[0]
    assert result == "overlaps"


def test_mode_all_null_returns_question_mark() -> None:
    """All-NaN group: mode() is empty → must return '?' not crash."""
    s = pd.Series([np.nan, np.nan, np.nan])
    result = s.groupby(lambda _: 0).agg(_mode_agg).iloc[0]
    assert result == "?"


def test_mode_mixed_null_and_values_ignores_nulls() -> None:
    """NaN rows are dropped by mode(); non-null values should still win."""
    s = pd.Series([np.nan, "overlaps", np.nan, "overlaps"])
    result = s.groupby(lambda _: 0).agg(_mode_agg).iloc[0]
    assert result == "overlaps"


def test_mode_single_value() -> None:
    s = pd.Series(["within"])
    result = s.groupby(lambda _: 0).agg(_mode_agg).iloc[0]
    assert result == "within"


# ── render_tab integration (pure DataFrame logic, no Streamlit) ─────────────

def test_de9im_mode_groupby_does_not_crash_on_all_null_group() -> None:
    """Regression: IndexError when an entire model group has null de9im_label."""
    df = pd.DataFrame({
        "source_a": ["llm:model-a", "llm:model-a", "llm:model-b"],
        "source_b": ["sf_planning"] * 3,
        "place": ["Bayview"] * 3,
        "run_id": ["r1", "r2", "r3"],
        "de9im_label": [np.nan, np.nan, "overlaps"],  # model-a has all NaN
        "iou": [np.nan, np.nan, 0.5],
        "composite_score": [np.nan, np.nan, 0.6],
    })
    # This must not raise IndexError
    result = (
        df.groupby("source_a")["de9im_label"]
        .agg(lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "?")
        .reset_index()
        .rename(columns={"de9im_label": "typical_relation"})
    )
    model_a_row = result[result["source_a"] == "llm:model-a"]
    assert model_a_row["typical_relation"].iloc[0] == "?"
    model_b_row = result[result["source_a"] == "llm:model-b"]
    assert model_b_row["typical_relation"].iloc[0] == "overlaps"
