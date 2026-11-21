"""Tests for the progress tracker data helpers (no Streamlit dependency)."""
from __future__ import annotations

import pytest

from ui.progress_tracker import (
    TAXONOMY_LEVELS,
    build_progress_rows,
)


def test_taxonomy_levels_are_ordered() -> None:
    assert TAXONOMY_LEVELS == ["L1", "L2", "L3", "L4", "L5"]


def test_build_progress_rows_empty_coverage() -> None:
    rows = build_progress_rows({})
    assert len(rows) == 5
    for row in rows:
        assert row["count"] == 0
        assert row["fraction"] == 0.0


def test_build_progress_rows_with_data() -> None:
    coverage = {"L1": 40, "L2": 5}
    rows = build_progress_rows(coverage)
    l1_row = next(r for r in rows if r["level"] == "L1")
    l2_row = next(r for r in rows if r["level"] == "L2")
    l3_row = next(r for r in rows if r["level"] == "L3")

    assert l1_row["count"] == 40
    assert l2_row["count"] == 5
    assert l3_row["count"] == 0

    # fraction = count / max_count
    assert l1_row["fraction"] == 1.0
    assert l2_row["fraction"] == pytest.approx(5 / 40)
    assert l3_row["fraction"] == 0.0


def test_build_progress_rows_single_entry() -> None:
    rows = build_progress_rows({"L3": 10})
    l3 = next(r for r in rows if r["level"] == "L3")
    assert l3["fraction"] == 1.0  # it's the max
