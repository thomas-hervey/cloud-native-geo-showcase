"""Tab 4 — Leaderboard: global average rankings, Bradley-Terry pairwise ranking,
and a coverage grid showing model x place run counts.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from model_registry import display_name as model_display_name
from scripts.bradley_terry import rank_models


def render_tab(valid_df: pd.DataFrame, reference_gt: str) -> None:
    """Render the leaderboard tab.

    Args:
        valid_df: Full valid DataFrame from app.py (not pre-filtered).
        reference_gt: The currently selected reference ground truth source.
    """
    st.header("Model Leaderboard")
    st.caption(config.METRIC_EXPLANATIONS["leaderboard"])

    # Filter to selected GT, LLM sources only.
    df = valid_df[
        (valid_df["source_b"] == reference_gt)
        & valid_df["source_a"].str.startswith("llm:")
    ].copy()

    if df.empty:
        st.info("No LLM results yet. Run `python run.py batch-eval` first.")
        return

    models = df["source_a"].unique()
    n_models = len(models)

    # ── Section 1: Global Rankings (always shown) ───────────────────────────
    st.subheader("Global Rankings")
    summary = (
        df.groupby("source_a")
        .agg(
            avg_composite=("composite_score", "mean"),
            std_composite=("composite_score", "std"),
            avg_iou=("iou", "mean"),
            avg_centroid_err=("centroid_err_m", "mean"),
            n_places=("place", "nunique"),
            n_runs=("run_id", "count"),
        )
        .round(3)
        .sort_values("avg_composite", ascending=False)
        .reset_index()
    )
    summary.insert(0, "Model", summary["source_a"].map(model_display_name))
    st.dataframe(
        summary[
            ["Model", "avg_composite", "std_composite", "avg_iou", "avg_centroid_err", "n_places", "n_runs"]
        ].rename(
            columns={
                "avg_composite": "Avg Composite",
                "std_composite": "Std Dev",
                "avg_iou": "Avg IoU",
                "avg_centroid_err": "Avg Centroid Err (m)",
                "n_places": "Places",
                "n_runs": "Runs",
            }
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Avg Composite and Avg IoU are means across all runs and places for each model. "
        "Std Dev measures run-to-run consistency — lower = more reliable."
    )

    # ── Section 2: Bradley-Terry Ranking (conditional on >=2 models) ────────
    st.subheader("Bradley-Terry Ranking")

    if n_models < 2:
        st.info("Run evaluations with at least one additional model to unlock BT ranking.")
    else:
        # Determine shared place coverage for the warning threshold.
        avg = df.groupby(["source_a", "place"])["composite_score"].mean().reset_index()
        place_model_counts = avg.groupby("place")["source_a"].count()
        shared_places = place_model_counts[place_model_counts >= 2].index
        # n_shared_obs: count of (model, place) pairs that participate in BT comparisons
        n_shared_obs = int(avg[avg["place"].isin(shared_places)].shape[0])

        bt_result = rank_models(df)

        if bt_result.empty:
            if len(shared_places) == 0:
                st.warning(
                    "No shared place coverage between models. "
                    "Run evaluations for the same places with different models to enable BT ranking."
                )
            else:
                st.warning(
                    "Bradley-Terry fitting failed with current data. "
                    "Global average ranking above is the best available estimate."
                )
        else:
            if n_shared_obs < 5:
                st.warning(
                    "Results are directional — collect more data for reliable ranking."
                )
            bt_display = bt_result.copy()
            bt_display.insert(0, "Model", bt_display["source_a"].map(model_display_name))
            st.dataframe(
                bt_display[["Model", "bt_score"]].rename(
                    columns={"bt_score": "BT Skill Score"}
                ).round(4),
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "Higher skill score = stronger relative performance. "
                "Wider gaps are more meaningful than absolute values."
            )

    # ── Section 3: Coverage Grid (always shown) ─────────────────────────────
    _render_coverage_grid(df)


def _render_coverage_grid(df: pd.DataFrame) -> None:
    """Section 3: Coverage Grid — run counts per model x place."""
    st.subheader("Coverage Grid")
    run_counts = (
        df.groupby(["source_a", "place"])
        .size()
        .unstack(fill_value=0)
    )
    run_counts.index = run_counts.index.map(model_display_name)
    try:
        st.dataframe(
            run_counts.style.background_gradient(cmap="Greens", vmin=0),
            width="stretch",
        )
    except Exception:
        st.dataframe(run_counts, width="stretch")
