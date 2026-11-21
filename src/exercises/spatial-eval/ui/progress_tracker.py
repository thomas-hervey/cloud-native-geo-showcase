"""Cognitive taxonomy progress tracker for the spatial-eval Streamlit app.

Shows how many experiment runs exist per cognitive level (L1–L5),
computed live from the EvalDB. Rendered above the map in app.py.

Data helpers are pure functions (no Streamlit) so they can be unit tested.
The render_progress_panel() function takes a coverage dict and renders
the panel using Streamlit — call it from app.py after loading the DB.
"""
from __future__ import annotations

TAXONOMY_LEVELS: list[str] = ["L1", "L2", "L3", "L4", "L5"]

LEVEL_LABELS: dict[str, str] = {
    "L1": "Geometry Identification",
    "L2": "Topology Relations",
    "L3": "Symbolic Rules",
    "L4": "Causal Prediction",
    "L5": "Planning / Goal-Oriented",
}


def build_progress_rows(coverage: dict[str, int]) -> list[dict]:
    """Convert a {cognitive_level: count} dict to display rows.

    Each row has: level, label, count, fraction (0.0–1.0 relative to max).
    All five levels always appear (count=0 if absent from coverage).
    """
    max_count = max(coverage.values(), default=0)
    rows = []
    for level in TAXONOMY_LEVELS:
        count = coverage.get(level, 0)
        fraction = (count / max_count) if max_count > 0 else 0.0
        rows.append({
            "level": level,
            "label": LEVEL_LABELS[level],
            "count": count,
            "fraction": fraction,
        })
    return rows


def render_progress_panel(coverage: dict[str, int]) -> None:
    """Render the cognitive taxonomy progress panel in Streamlit.

    Call this from app.py with the result of EvalDB.get_experiment_coverage().
    """
    import streamlit as st
    from ui.theme import color_for_level

    rows = build_progress_rows(coverage)
    total = sum(r["count"] for r in rows)

    with st.expander(f"Experiment Progress — {total} LLM runs total", expanded=True):
        for row in rows:
            col_label, col_bar, col_count = st.columns([2, 5, 1])
            with col_label:
                color = color_for_level(row["level"])
                st.markdown(
                    f"<span style='color:{color}; font-weight:600'>"
                    f"{row['level']}</span> {row['label']}",
                    unsafe_allow_html=True,
                )
            with col_bar:
                st.progress(row["fraction"])
            with col_count:
                st.markdown(f"**{row['count']}**")
