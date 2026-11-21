"""Tab 3 — IoU Heatmap (all places × all LLM sources)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config


def render_tab(
    eval_valid: pd.DataFrame,
    reference_gt: str,
) -> None:
    """Render the IoU heatmap for all places × LLM sources."""
    st.header("IoU Heatmap: All Places × All LLM Sources")
    st.subheader(f"Heatmap Scope: All places | Reference GT: {reference_gt}")
    st.caption(config.METRIC_EXPLANATIONS["heatmap"])

    ref_filter = eval_valid[eval_valid["source_b"] == reference_gt]
    if ref_filter.empty:
        st.info(f"No data for reference GT: {reference_gt}")
        return

    filtered_ref = ref_filter[~ref_filter["source_a"].isin(config.EXCLUDED_MODELS)]
    llm_pivot = (
        filtered_ref[filtered_ref["source_a"].str.startswith("llm:")]
        .groupby(["place", "source_a"])["iou"]
        .mean()
        .unstack(fill_value=0)
    )

    if llm_pivot.empty:
        st.info("No LLM data available for heatmap.")
        return

    st.markdown(f"**LLM models vs {reference_gt}**")
    try:
        st.dataframe(
            llm_pivot.style.background_gradient(cmap="RdYlGn", vmin=0, vmax=1),
            width="stretch",
        )
    except ImportError:
        st.warning("Matplotlib is not available, so the color heatmap is disabled.")
        st.dataframe(llm_pivot.round(3), width="stretch")
    st.caption(
        "Each cell = mean IoU across all runs for that model × place combination. "
        "Cells showing 0 mean no evaluation data exists for that combination — not a true IoU of zero."
    )
