"""Streamlit visualization for the SF spatial reasoning eval.

Run:  streamlit run app.py

This file is a thin orchestrator. All business logic, UI helpers, and
rendering functions live in:
  config.py     — constants and path definitions
  ui/auth.py    — admin token authentication
  ui/colors.py  — color/emoji helpers
  ui/sidebar.py — sidebar rendering and layer selection
  ui/map_view.py — Folium layer builders and map renderer
  ui/experiments.py — prompt experiment run loop and results display
  ui/tabs/      — one module per metric tab
"""
from __future__ import annotations
import os
from ui.sidebar import render_sidebar
import ui.tabs.source_config as tab_source_config
import ui.tabs.heatmap as tab_heatmap
import ui.tabs.leaderboard as tab_leaderboard
import ui.tabs.gt_agreement as tab_gt_agreement
import ui.tabs.llm_vs_gt as tab_llm_vs_gt
import ui.map_view as map_view
from db_duckdb import EvalDB
from corpus import load_corpus
from ui.progress_tracker import render_progress_panel
from ui.period_filter import render_period_filter
import ui.tabs.period_compare as period_compare
from run_period import available_periods, filter_to_period, with_period

import pandas as pd
import streamlit as st


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="SF LLM Spatial Eval", layout="wide")
st.title("Where do LLMs think neighborhoods are?")
st.subheader(
    "Comparing LLM bounding box predictions against authoritative SF neighborhood boundaries.")

st.info("""
**Project Status:** This app demonstrates preliminary comparisons of LLMs' understanding of neighborhood bounding boxes against ground truth data, using geometric metrics of precision. 

**Next Steps:** We will compare if and what an LLM can render using full polygon geometry.
""", icon="🚀")

st.markdown("""
**Note on Geometries:** Standard LLM prompts ask for a simple *Bounding Box* (a rectangle) for simplicity.
However, Ground Truth (GT) sources provide detailed, irregular *Polygons*.
We now support simultaneous visualization of **Polygons**, **Bounding Boxes**, and **Centroids**.
Use the "Show Secondary Geometries" toggle in the sidebar to overlay boxes and points on top of the neighborhood shapes.
""")
st.caption("Author: Thomas Hervey")

# ── Load data ──────────────────────────────────────────────────────────────────
is_cloud = os.environ.get("STREAMLIT_SERVER_HEADLESS",
                          "false").lower() == "true"
db = EvalDB()
records = db.fetch_comparisons()

if not records:
    st.warning("No results yet. Run `python run.py batch-eval` first.")
    st.stop()

df = pd.DataFrame([r.model_dump() for r in records])
df["created_at_ts"] = pd.to_datetime(df["created_at"], errors="coerce")

# Legacy rows without explicit prompt variant should be treated as baseline.
if "variant_id" not in df.columns:
    df["variant_id"] = "baseline_v2"
else:
    df["variant_id"] = df["variant_id"].fillna(
        "baseline_v2").replace("", "baseline_v2")

# ── Evaluation period (run date) ───────────────────────────────────────────────
df_all = with_period(df)
period_sel = render_period_filter(available_periods(df_all))
df = filter_to_period(df_all, period_sel.current)

valid = df[df["valid"] == True]

coverage = db.get_experiment_coverage()
render_progress_panel(coverage)

active_corpus = load_corpus()
active_corpus_places = sorted(
    (entry["name"] for entry in active_corpus), key=str.casefold)
eval_valid = valid[valid["place"].isin(active_corpus_places)]
eval_valid_all_periods = df_all[df_all["valid"].fillna(False).astype(bool)
                                & df_all["place"].isin(active_corpus_places)]
all_llm_sources = (
    sorted(eval_valid[eval_valid["source_a"].str.startswith("llm:")]["source_a"].unique())
    if not eval_valid[eval_valid["source_a"].str.startswith("llm:")].empty
    else []
)
all_places_list = [p for p in active_corpus_places if p in set(
    eval_valid["place"].unique())]

if not all_places_list:
    st.warning(
        "No valid comparisons in database. Run `python run.py batch-eval` first.")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
(
    selected_place,
    reference_gt,
    active_gt_sources,
    active_llm_sources,
    known_models,
    _freshness_row,  # freshness alerts rendered inside render_sidebar
    all_gt_sources,
    geom_toggles,
    selected_runs,
    selected_variants,
) = render_sidebar(
    valid_df=eval_valid,
    all_places_list=all_places_list,
    active_corpus_places=active_corpus_places,
    all_llm_sources=all_llm_sources,
)

if selected_place is None or reference_gt is None:
    st.warning("Please select both a place and a reference GT source.")
    st.stop()

# ── Map ────────────────────────────────────────────────────────────────────────
map_view.render_map_section(
    selected_place=selected_place,
    reference_gt=reference_gt,
    active_gt_sources=active_gt_sources,
    active_llm_sources=active_llm_sources,
    known_models=known_models,
    df=df,
    valid_df=eval_valid,
    geom_toggles=geom_toggles,
    selected_runs=selected_runs,
    selected_variants=selected_variants,
)

# ── Metric tabs ────────────────────────────────────────────────────────────────
tab_llm, tab_gt, tab_heat, tab_lb, tab_cfg = st.tabs(
    ["LLM vs Ground Truth", "GT Agreement", "IoU Heatmap", "Leaderboard", "⚙️ Source Config"]
)

with tab_llm:
    tab_llm_vs_gt.render_tab(eval_valid, selected_place, reference_gt)

with tab_gt:
    tab_gt_agreement.render_tab(eval_valid, selected_place)

with tab_heat:
    tab_heatmap.render_tab(eval_valid, reference_gt)

with tab_lb:
    if period_sel.baseline and period_sel.current:
        period_compare.render_section(
            eval_valid_all_periods,
            baseline=period_sel.baseline,
            current=period_sel.current,
            reference_gt=reference_gt,
            variants=selected_variants,
        )
    tab_leaderboard.render_tab(eval_valid, reference_gt)

with tab_cfg:
    tab_source_config.render_tab(
        all_corpus_places=active_corpus_places,
        active_corpus_places=active_corpus_places,
        selected_place=selected_place,
        reference_gt=reference_gt,
        known_models=known_models,
        gt_sources=all_gt_sources,
        active_corpus=active_corpus,
        df_all=df_all,
        db=db,
        selected_variants=selected_variants,
    )
