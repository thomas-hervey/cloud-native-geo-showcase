"""Tab 2 — GT Source Agreement (pairwise GT-vs-GT)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config


def render_tab(
    valid_df: pd.DataFrame,
    selected_place: str,
) -> None:
    """Render the pairwise GT source agreement table for the selected place."""
    st.header("Ground Truth Source Agreement (pairwise)")
    st.subheader(f"Selected Place: {selected_place}")
    st.caption(config.METRIC_EXPLANATIONS["gt"])

    gt_data = valid_df[
        (valid_df["place"] == selected_place)
        & ~valid_df["source_a"].str.startswith("llm:")
    ]

    if gt_data.empty:
        st.info("No GT-vs-GT comparisons yet. Run `run_gt_comparison.py` first.")
        return

    gt_cols = [c for c in [
        "source_a", "source_b", "iou", "overlap_a", "overlap_b",
        "de9im_label", "hausdorff_m", "centroid_err_m",
    ] if c in gt_data.columns]
    gt_summary = gt_data[gt_cols].round(3)

    # DE-9IM label → distinct background colors per relationship type
    _DE9IM_COLORS: dict[str, str] = {
        "equals":    "#c3e6cb",  # green        — perfect match
        "contains":  "#2c7bb6",  # dark blue    — A contains B (A is bigger)
        "within":    "#abd9e9",  # light blue   — A is within B (A is smaller)
        "covers":    "#4a90d9",  # medium blue  — A covers B
        "coveredby": "#d0ecf8",  # pale blue    — A is covered by B
        "overlaps":  "#ffc107",  # amber        — partial overlap
        "crosses":   "#fd7e14",  # orange       — line/area crossing
        "touches":   "#d8b4fe",  # purple       — edge contact only
        "disjoint":  "#f5c6cb",  # red          — no overlap
    }
    _DE9IM_TEXT: dict[str, str] = {
        "contains":  "color:#fff;",
        "covers":    "color:#fff;",
    }

    def _style_de9im(val: str) -> str:
        key = str(val).lower()
        bg = _DE9IM_COLORS.get(key, "")
        txt = _DE9IM_TEXT.get(key, "")
        return f"background-color:{bg};{txt}" if bg else ""

    styler = gt_summary.style
    if "iou" in gt_summary.columns:
        styler = styler.background_gradient(
            cmap="YlGn", subset=["iou"], vmin=0, vmax=1)
    if "overlap_a" in gt_summary.columns and "overlap_b" in gt_summary.columns:
        styler = styler.background_gradient(
            cmap="Blues", subset=["overlap_a", "overlap_b"], vmin=0, vmax=1)
    if "hausdorff_m" in gt_summary.columns:
        styler = styler.background_gradient(
            cmap="OrRd", subset=["hausdorff_m"])
    if "centroid_err_m" in gt_summary.columns:
        styler = styler.background_gradient(
            cmap="OrRd", subset=["centroid_err_m"])
    if "de9im_label" in gt_summary.columns:
        styler = styler.map(_style_de9im, subset=["de9im_label"])

    # Null cells from gradient cmaps render black — reset them to transparent
    styler = styler.highlight_null(props="background-color: transparent; color: #aaa;")

    try:
        st.dataframe(styler, width="stretch")
    except Exception:
        st.dataframe(gt_summary, width="stretch")

    # Color scale legend
    _continuous = [
        ("IoU", "YlGn", "0", "1", "low overlap → high overlap"),
        ("Overlap A/B", "Blues", "0", "1", "low coverage → full coverage"),
        ("Hausdorff / Centroid Err (m)", "OrRd", "min", "max", "low error → high error"),
    ]
    _de9im_legend = [
        (label, color, txt)
        for label, color, txt in [
            ("equals",    _DE9IM_COLORS["equals"],    ""),
            ("contains",  _DE9IM_COLORS["contains"],  "color:#fff"),
            ("within",    _DE9IM_COLORS["within"],    ""),
            ("covers",    _DE9IM_COLORS["covers"],    "color:#fff"),
            ("coveredby", _DE9IM_COLORS["coveredby"], ""),
            ("overlaps",  _DE9IM_COLORS["overlaps"],  ""),
            ("touches",   _DE9IM_COLORS["touches"],   ""),
            ("disjoint",  _DE9IM_COLORS["disjoint"],  ""),
        ]
    ]

    grad_html = "<div style='display:flex;flex-wrap:wrap;gap:16px;align-items:center;margin:6px 0 4px'>"
    for label, cmap_name, lo, hi, hint in _continuous:
        _CMAP_CSS = {
            "YlGn":  "linear-gradient(to right,#ffffcc,#006837)",
            "Blues": "linear-gradient(to right,#eff3ff,#084594)",
            "OrRd":  "linear-gradient(to right,#fff7ec,#b30000)",
        }
        grad = _CMAP_CSS.get(cmap_name, "linear-gradient(to right,#eee,#333)")
        grad_html += (
            f"<div style='display:flex;align-items:center;gap:5px;font-size:0.78rem'>"
            f"<span style='white-space:nowrap;color:#555'>{label}</span>"
            f"<span style='font-size:0.72rem;color:#888'>{lo}</span>"
            f"<div style='width:80px;height:10px;border-radius:3px;background:{grad};border:1px solid #ddd'></div>"
            f"<span style='font-size:0.72rem;color:#888'>{hi}</span>"
            f"</div>"
        )
    grad_html += "</div>"

    de9im_html = "<div style='display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:2px 0 8px'>"
    de9im_html += "<span style='font-size:0.78rem;color:#555;margin-right:2px'>DE-9IM:</span>"
    for label, bg, txt_style in _de9im_legend:
        de9im_html += (
            f"<span style='background:{bg};{txt_style};padding:2px 7px;"
            f"border-radius:4px;font-size:0.76rem;border:1px solid #ccc'>{label}</span>"
        )
    de9im_html += "</div>"

    st.markdown(grad_html + de9im_html, unsafe_allow_html=True)

    st.caption(
        "Low IoU between ground truth sources = high semantic ambiguity for this place. "
        "LLM performance should be interpreted in this context."
    )
