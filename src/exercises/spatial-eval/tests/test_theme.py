"""Tests for ui/theme.py color constants."""
from __future__ import annotations

import pytest

from ui.theme import (
    LEVEL_COLORS,
    GT_COLOR,
    LLM_COLOR,
    MODEL_COLOR_SEQUENCE,
    CONFIDENCE_COLORS,
    color_for_level,
    color_for_model,
)


def test_all_five_levels_defined() -> None:
    for level in ("L1", "L2", "L3", "L4", "L5"):
        assert level in LEVEL_COLORS, f"Missing level: {level}"


def test_level_colors_are_valid_hex() -> None:
    for level, color in LEVEL_COLORS.items():
        assert color.startswith("#"), f"{level} color not a hex string: {color}"
        assert len(color) == 7, f"{level} color wrong length: {color}"


def test_gt_and_llm_colors_defined() -> None:
    assert GT_COLOR.startswith("#")
    assert LLM_COLOR.startswith("#")


def test_model_color_sequence_non_empty() -> None:
    assert len(MODEL_COLOR_SEQUENCE) >= 4


def test_confidence_colors_cover_all_levels() -> None:
    for key in ("high", "medium", "low"):
        assert key in CONFIDENCE_COLORS


def test_color_for_level_returns_correct_color() -> None:
    assert color_for_level("L1") == LEVEL_COLORS["L1"]
    assert color_for_level("L2") == LEVEL_COLORS["L2"]


def test_color_for_level_unknown_returns_default() -> None:
    result = color_for_level("L99")
    assert result.startswith("#")


def test_color_for_model_cycles_sequence() -> None:
    models = ["m0", "m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8"]
    colors = [color_for_model(m, models) for m in models]
    n = len(MODEL_COLOR_SEQUENCE)
    if len(models) > n:
        assert colors[0] == colors[n]
