"""Neighbor set similarity metrics for L2 topology experiments.

neighbor_jaccard(a, b) computes Jaccard similarity (|A∩B| / |A∪B|)
over two lists of neighbor place names. Returns None when both lists
are empty (undefined similarity), 0.0 when only one is empty.
"""
from __future__ import annotations


def neighbor_jaccard(
    a: list[str],
    b: list[str],
) -> float | None:
    """Compute Jaccard similarity between two neighbor lists.

    Args:
        a: LLM-predicted neighbor names.
        b: Ground-truth neighbor names.

    Returns:
        float in [0, 1], or None if both lists are empty.
    """
    set_a = set(a)
    set_b = set(b)

    if not set_a and not set_b:
        return None  # undefined

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    return intersection / union if union > 0 else 0.0
