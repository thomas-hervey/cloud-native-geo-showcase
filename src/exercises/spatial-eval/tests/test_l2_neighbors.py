"""Tests for L2 neighbor adjacency metrics."""
from __future__ import annotations

import pytest
from metrics.neighbor_metrics import neighbor_jaccard


def test_perfect_overlap() -> None:
    a = ["Mission", "Castro", "Noe Valley"]
    b = ["Mission", "Castro", "Noe Valley"]
    assert neighbor_jaccard(a, b) == pytest.approx(1.0)


def test_no_overlap() -> None:
    a = ["Mission", "Castro"]
    b = ["Richmond", "Sunset"]
    assert neighbor_jaccard(a, b) == pytest.approx(0.0)


def test_partial_overlap() -> None:
    a = ["Mission", "Castro", "Noe Valley"]
    b = ["Castro", "Noe Valley", "SoMa"]
    # intersection = {Castro, Noe Valley} = 2
    # union = {Mission, Castro, Noe Valley, SoMa} = 4
    assert neighbor_jaccard(a, b) == pytest.approx(2 / 4)


def test_empty_a_nonempty_b() -> None:
    """If A is empty but B is not, Jaccard = 0 (not NULL)."""
    assert neighbor_jaccard([], ["Mission"]) == pytest.approx(0.0)


def test_nonempty_a_empty_b() -> None:
    assert neighbor_jaccard(["Mission"], []) == pytest.approx(0.0)


def test_both_empty_returns_none() -> None:
    """Both lists empty → NULL (undefined similarity)."""
    assert neighbor_jaccard([], []) is None


def test_order_independent() -> None:
    a = ["Mission", "Castro"]
    b = ["Castro", "Mission"]
    assert neighbor_jaccard(a, b) == pytest.approx(1.0)


def test_case_sensitive() -> None:
    """Neighbor names are case-sensitive — 'mission' ≠ 'Mission'."""
    a = ["mission"]
    b = ["Mission"]
    assert neighbor_jaccard(a, b) == pytest.approx(0.0)
