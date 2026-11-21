"""Color and emoji utilities for the spatial-eval Streamlit app.

All color constants are sourced from ui/theme.py.
This module provides helper functions for mapping sources and models
to display colors and emoji indicators.
"""
from __future__ import annotations

import config
from ui.theme import MODEL_COLOR_SEQUENCE, color_for_model


def color_to_emoji(hex_color: str) -> str:
    """Map a hex color string to a colored emoji circle for legend indicators.

    Falls back to '●' for unknown colors.
    """
    return config.COLOR_EMOJI.get(hex_color, "●")


def get_color_for_source(
    source_name: str,
    source_list: list[str],
    color_palette: list[str] | None = None,
) -> str:
    """Return the display colour for a source or model.

    Lookup priority:
      1. Explicit entry in config.COLOR_MAP (named GT sources)
      2. Index in source_list → MODEL_COLOR_SEQUENCE (positional fallback)
    """
    if source_name in config.COLOR_MAP:
        return config.COLOR_MAP[source_name]
    palette = color_palette or MODEL_COLOR_SEQUENCE
    return color_for_model(source_name, source_list) if not color_palette else (
        palette[source_list.index(source_name) % len(palette)]
        if source_name in source_list else palette[0]
    )
