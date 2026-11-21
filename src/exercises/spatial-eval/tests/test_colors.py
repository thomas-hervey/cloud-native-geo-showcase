"""Tests for ui/colors.py source color helper."""
from __future__ import annotations

import pytest

from ui.colors import get_color_for_source
import config


def test_named_gt_source_uses_color_map() -> None:
    """Named GT sources in config.COLOR_MAP return their fixed color."""
    color = get_color_for_source("sf_planning", [], None)
    assert color == config.COLOR_MAP["sf_planning"]


def test_unknown_source_returns_sequence_color() -> None:
    """Unknown source falls back to MODEL_COLOR_SEQUENCE by position."""
    models = ["model_a", "model_b"]
    color_a = get_color_for_source("model_a", models, None)
    color_b = get_color_for_source("model_b", models, None)
    assert color_a != color_b
    assert color_a.startswith("#")
    assert color_b.startswith("#")


def test_custom_palette_respected() -> None:
    """When color_palette is provided, it takes priority over MODEL_COLOR_SEQUENCE."""
    palette = ["#aabbcc", "#ddeeff"]
    models = ["m0", "m1"]
    assert get_color_for_source("m0", models, palette) == "#aabbcc"
    assert get_color_for_source("m1", models, palette) == "#ddeeff"
