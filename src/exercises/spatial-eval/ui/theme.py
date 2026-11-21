"""Single source of truth for all color constants in the spatial-eval app.

Import from here instead of using inline hex strings or config.COLOR_MAP.
Every file in ui/ must use these constants — no hardcoded colors elsewhere.
"""
from __future__ import annotations

# ── Cognitive taxonomy level colors ───────────────────────────────────────────
LEVEL_COLORS: dict[str, str] = {
    "L1": "#4A90D9",   # blue   — geometry identification
    "L2": "#E67E22",   # orange — topology relations
    "L3": "#27AE60",   # green  — symbolic rules
    "L4": "#8E44AD",   # purple — causal prediction
    "L5": "#C0392B",   # red    — planning
}

# ── Geometry overlay colors ────────────────────────────────────────────────────
GT_COLOR: str = "#2ECC71"      # ground truth polygon (green)
LLM_COLOR: str = "#E74C3C"     # LLM prediction polygon (red)

# ── Multi-model color sequence (for charts with multiple models) ──────────────
MODEL_COLOR_SEQUENCE: list[str] = [
    "#3498DB",  # blue
    "#E74C3C",  # red
    "#2ECC71",  # green
    "#F39C12",  # orange
    "#9B59B6",  # purple
    "#1ABC9C",  # teal
    "#E67E22",  # dark orange
    "#34495E",  # dark gray
]

# ── Confidence level colors ────────────────────────────────────────────────────
CONFIDENCE_COLORS: dict[str, str] = {
    "high":   "#27AE60",
    "medium": "#F39C12",
    "low":    "#E74C3C",
}

_LEVEL_DEFAULT = MODEL_COLOR_SEQUENCE[0]


def color_for_level(level: str) -> str:
    """Return the hex color for a cognitive level string (e.g. 'L1').

    Returns the first MODEL_COLOR_SEQUENCE entry for unknown levels.
    """
    return LEVEL_COLORS.get(level, _LEVEL_DEFAULT)


def color_for_model(model: str, model_list: list[str]) -> str:
    """Return the hex color for a model by its position in model_list.

    Cycles through MODEL_COLOR_SEQUENCE if model_list is longer.
    """
    try:
        idx = model_list.index(model)
    except ValueError:
        idx = 0
    return MODEL_COLOR_SEQUENCE[idx % len(MODEL_COLOR_SEQUENCE)]
