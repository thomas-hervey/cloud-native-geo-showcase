"""Leaderboard section: how each model moved between two evaluation periods."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from model_registry import display_name, load_models
from run_period import compare_periods, period_label


def render_section(
    valid_df: pd.DataFrame,
    baseline: str,
    current: str,
    reference_gt: str,
    variants: list[str],
) -> None:
    """Render a per-model period comparison table.

    Args:
        valid_df: Valid rows from all periods, with a ``period`` column.
        baseline: Earlier period id.
        current: Period currently selected in the sidebar.
        reference_gt: GT source to score against.
        variants: Prompt variants selected in the sidebar.
    """
    base_label, cur_label = period_label(baseline), period_label(current)
    st.subheader(f"{cur_label} vs {base_label}")
    successors = {m["model_id"]: m["successor_of"] for m in load_models() if m.get("successor_of")}
    table = compare_periods(valid_df, baseline, current, reference_gt, variants or ["baseline_v2"],
                            successors)
    if table.empty:
        st.info(f"No model has results against {reference_gt} in both {base_label} and {cur_label}.")
        return

    model_label = [
        display_name(m) if m == b else f"{display_name(m)} (vs {display_name(b)})"
        for m, b in zip(table["model"], table["baseline_model"])
    ]
    view = pd.DataFrame({
        "Model": model_label,
        "Places": table["places"],
        f"IoU {base_label}": table["iou_baseline"].round(3),
        f"IoU {cur_label}": table["iou_current"].round(3),
        "Δ IoU": table["iou_delta"].round(3),
        f"Centroid err (m) {base_label}": table["err_baseline"].round(0),
        f"Centroid err (m) {cur_label}": table["err_current"].round(0),
        "Δ err (m)": table["err_delta"].round(0),
    })
    st.dataframe(
        view.style.map(_delta_color, subset=["Δ IoU"])
                  .map(lambda v: _delta_color(-v), subset=["Δ err (m)"]),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Medians over all runs, restricted to places each model answered in both periods. "
        "Positive Δ IoU and negative Δ error mean the model got better."
    )


def _delta_color(value: float) -> str:
    if pd.isna(value) or value == 0:
        return ""
    return "color: #1a7f37" if value > 0 else "color: #cf222e"
