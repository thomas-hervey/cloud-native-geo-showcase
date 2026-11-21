"""Tests for prompt variant builder."""
from __future__ import annotations

import pytest
from prompt_variants import build_variant_user_prompt


def test_l2_neighbors_variant_returns_neighbor_prompt() -> None:
    prompt = build_variant_user_prompt("Mission", [], "l2_neighbors")
    assert "neighbors" in prompt.lower()
    assert "Mission" in prompt


def test_baseline_v2_variant_returns_bbox_prompt() -> None:
    prompt = build_variant_user_prompt("Mission", [], "baseline_v2")
    assert "bounding box" in prompt.lower()


def test_geojson_polygon_variant_returns_polygon_prompt() -> None:
    prompt = build_variant_user_prompt("Mission", [], "geojson_polygon")
    assert "polygon" in prompt.lower()
