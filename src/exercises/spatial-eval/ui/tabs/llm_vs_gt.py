"""Tab 1 — LLM vs Ground Truth metric table."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from model_registry import display_name as model_display_name


def render_tab(
    valid_df: pd.DataFrame,
    selected_place: str,
    reference_gt: str,
) -> None:
    """Render the LLM vs Ground Truth performance table."""
    st.header(f"LLM Performance vs {reference_gt}")
    st.subheader(f"Selected Place: {selected_place} | Reference GT: {reference_gt}")
    st.caption(config.METRIC_EXPLANATIONS["llm"])

    llm_data = valid_df[
        (valid_df["place"] == selected_place)
        & (valid_df["source_b"] == reference_gt)
        & valid_df["source_a"].str.startswith("llm:")
    ]

    if llm_data.empty:
        st.info(f"No LLM results for {selected_place} vs {reference_gt}. Run batch eval first.")
        return

    metric_cols = [c for c in ["iou", "overlap_a", "overlap_b",
                               "centroid_err_m", "hausdorff_m", "composite_score"]
                   if c in llm_data.columns]
    summary = (
        llm_data.groupby("source_a")[metric_cols]
        .mean()
        .round(3)
        .reset_index()
    )
    de9im_mode = (
        llm_data.groupby("source_a")["de9im_label"]
        .agg(lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "?")
        .reset_index()
        .rename(columns={"de9im_label": "typical_relation"})
    )
    summary = summary.merge(de9im_mode, on="source_a")
    
    geom_col = next((c for c in ["geom_a", "polygon_wkt_a"] if c in llm_data.columns), None)
    if geom_col:
        polygon_counts = (
            llm_data.groupby("source_a")[geom_col]
            .apply(lambda x: f"{x.notna().sum()}/{len(x)} runs")
            .reset_index()
            .rename(columns={geom_col: "Polygon Support"})
        )
        summary = summary.merge(polygon_counts, on="source_a")

    summary.insert(0, "Model", summary["source_a"].apply(model_display_name))
    st.dataframe(summary.drop(columns=["source_a"]), width="stretch")
    n_runs = llm_data.groupby("source_a")["run_id"].nunique()
    run_counts = ", ".join(f"{model_display_name(m)}: {n}" for m, n in n_runs.items())
    st.caption(
        f"Numeric metrics are averaged across all runs per model ({run_counts}). "
        "Typical relation is the most common DE-9IM label across runs."
    )
