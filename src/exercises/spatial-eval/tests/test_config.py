"""Tests for the centralized config module."""
from __future__ import annotations

import config


def test_config_paths_exist():
    # Only verify paths expected to exist out-of-the-box
    assert config.DATA_DIR.exists()
    assert config.PLACES_JSON_PATH.exists()
    assert config.DATA_DIR.is_dir()


def test_config_ui_constants():
    assert "sf_planning" in config.GT_UI_ORDER
    # Ensure color maps are correctly formatted
    for name, hexcode in config.COLOR_MAP.items():
        assert hexcode.startswith("#")
        assert len(hexcode) == 7 or len(hexcode) == 9 # #RRGGBB or #RRGGBBAA


def test_config_metric_explanations():
    assert "llm" in config.METRIC_EXPLANATIONS
    assert "gt" in config.METRIC_EXPLANATIONS
    assert "heatmap" in config.METRIC_EXPLANATIONS
    assert "config" in config.METRIC_EXPLANATIONS
