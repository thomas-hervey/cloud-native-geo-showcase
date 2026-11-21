"""Sidebar rendering for the spatial-eval Streamlit app.

render_sidebar() is the main entry point. It returns the user's current
selections as named values so app.py can pass them downstream to map and tab
renderers without relying on module-level variables.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from geometry_source import list_gt_sources
from model_registry import display_name as model_display_name, load_models
from ui.colors import color_to_emoji, get_color_for_source


def _load_and_filter_sources() -> tuple[list[str], list[str]]:
    """Load GT sources and return (ordered_filtered, all_ordered)."""
    all_gt = list_gt_sources()
    ordered_all = [s for s in config.GT_UI_ORDER if s in all_gt]
    ordered_rest = sorted(s for s in all_gt if s not in ordered_all)
    all_ordered = ordered_all + ordered_rest
    filtered = [s for s in all_ordered if s not in config.EXCLUDED_GT_SOURCES]
    return filtered, all_ordered


def _categorize_models(all_models: list[str]) -> tuple[list[str], list[str]]:
    """Split into registry-known models and unrecognised legacy models.

    all_models contains source_a values like "llm:claude-haiku-4-5"; the
    registry stores bare model_ids like "claude-haiku-4-5", so strip the
    prefix for the lookup while preserving the original value in the lists.
    """
    registry_ids = {m["model_id"] for m in load_models()}
    known = [m for m in all_models if m.removeprefix("llm:") in registry_ids]
    legacy = [m for m in all_models if m.removeprefix("llm:") not in registry_ids]
    return known, legacy


def _format_timestamp(value: pd.Timestamp | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    return value.strftime("%Y-%m-%d %H:%M")


def _status_badge(status: str) -> str:
    return {
        "current": "✅ current",
        "partial": "🟡 partial",
        "stale": "🟠 stale",
        "missing": "🔴 missing",
    }.get(status, status)


def build_freshness_summary(
    valid_df: pd.DataFrame,
    gt_sources: list[str],
    all_places: list[str],
    all_llm_sources: list[str],
) -> pd.DataFrame:
    """Summarise freshness/completeness of LLM evals per reference GT source."""
    is_llm = valid_df["source_a"].str.startswith("llm:")
    llm_rows = valid_df[is_llm].copy()
    gt_rows = valid_df[~is_llm].copy()
    n_run_ids = llm_rows["run_id"].nunique() if not llm_rows.empty else 0
    expected_rows = len(all_places) * len(all_llm_sources) * max(n_run_ids, 1)

    summary_rows: list[dict] = []
    for gt_source in gt_sources:
        gt_llm_rows = llm_rows[llm_rows["source_b"] == gt_source]
        gt_gt_rows = gt_rows[
            (gt_rows["source_a"] == gt_source) | (
                gt_rows["source_b"] == gt_source)
        ]
        latest_llm = gt_llm_rows["created_at_ts"].max(
        ) if not gt_llm_rows.empty else None
        latest_gt = gt_gt_rows["created_at_ts"].max(
        ) if not gt_gt_rows.empty else None
        llm_count = int(len(gt_llm_rows))
        coverage_pct = (llm_count / expected_rows *
                        100) if expected_rows else 0.0

        if llm_count == 0:
            status = "missing"
        elif latest_gt is not None and latest_llm is not None and latest_llm < latest_gt:
            status = "stale"
        elif expected_rows and llm_count < expected_rows:
            status = "partial"
        else:
            status = "current"

        summary_rows.append(
            {
                "reference_gt": gt_source,
                "status": status,
                "llm_rows": llm_count,
                "expected_rows": expected_rows,
                "coverage_pct": round(coverage_pct, 1),
                "latest_llm_eval": _format_timestamp(latest_llm),
                "latest_gt_refresh": _format_timestamp(latest_gt),
            }
        )

    return pd.DataFrame(summary_rows)


def _gt_availability_status(source_name: str, place: str) -> dict[str, bool]:
    from sources.coverage_utils import get_gt_coverage

    return get_gt_coverage(source_name, place)


def _llm_availability_status(
    model: str, place: str, reference_gt: str, valid_df: pd.DataFrame
) -> dict[str, bool]:
    mdl_rows = valid_df[
        (valid_df["source_a"] == model)
        & (valid_df["source_b"] == reference_gt)
        & (valid_df["place"] == place)
    ]
    if mdl_rows.empty:
        return {"poly": False, "bbox": False, "point": False}

    has_poly = "geom_a" in mdl_rows.columns and mdl_rows["geom_a"].notna().any()

    missing_bbox_cols = [c for c in config.BBOX_COLS_A if c not in mdl_rows.columns]
    if missing_bbox_cols:
        has_bbox = False
    else:
        bbox_avg = mdl_rows[config.BBOX_COLS_A].mean()
        has_bbox = (
            not bbox_avg.isna().any()
            and bbox_avg["bbox_east_a"] > bbox_avg["bbox_west_a"]
            and bbox_avg["bbox_north_a"] > bbox_avg["bbox_south_a"]
        )

    missing_centroid_cols = [c for c in config.CENTROID_COLS_A if c not in mdl_rows.columns]
    if missing_centroid_cols:
        has_point = False
    else:
        cx = mdl_rows[config.CENTROID_COLS_A[0]].mean()
        cy = mdl_rows[config.CENTROID_COLS_A[1]].mean()
        has_point = pd.notna(cx) and pd.notna(cy)

    return {
        "poly": bool(has_poly),
        "bbox": bool(has_bbox),
        "point": bool(has_point),
    }


def render_checkbox_group(
    items: list[str],
    color_getter,
    location: str,
    key_prefix: str,
    defaults: dict | None = None,
    label_fn=None,
    disabled: dict[str, bool] | None = None,
) -> list[str]:
    """Render a list of colour-coded checkboxes and return checked items."""
    selected = []
    defaults = defaults or {}
    disabled = disabled or {}
    st_loc = st.sidebar if location == "sidebar" else st

    for item in items:
        label = label_fn(item) if label_fn else item
        color = color_getter(item)
        emoji = color_to_emoji(color)
        col1, col2 = st_loc.columns([0.08, 0.92])
        with col1:
            st.write(emoji)
        with col2:
            if st.checkbox(
                label,
                value=defaults.get(item, False),
                key=f"{key_prefix}_{item}",
                disabled=disabled.get(item, False),
            ):
                selected.append(item)

    return selected


def render_sidebar(
    valid_df: pd.DataFrame,
    all_places_list: list[str],
    active_corpus_places: list[str],
    all_llm_sources: list[str],
) -> tuple[
    str,
    str,
    list[str],
    list[str],
    list[str],
    pd.Series | None,
    list[str],
    dict[str, bool],
    list[int],
    list[str],
]:
    """Render the full sidebar and return current user selections."""
    gt_sources, _ = _load_and_filter_sources()

    freshness_df = build_freshness_summary(
        valid_df, gt_sources, all_places_list, all_llm_sources)

    st.sidebar.header("Settings")

    selected_place = st.sidebar.selectbox("Place", all_places_list)

    _is_llm = valid_df["source_a"].str.startswith("llm:")
    _default_gt_idx = next(
        (i for i, s in enumerate(gt_sources)
         if s in valid_df[_is_llm]["source_b"].unique()),
        gt_sources.index(
            config.PRIMARY_GT_SOURCE) if config.PRIMARY_GT_SOURCE in gt_sources else 0,
    )
    reference_gt = st.sidebar.selectbox(
        "Reference Ground Truth", gt_sources, index=_default_gt_idx)

    selected_freshness = freshness_df[freshness_df["reference_gt"]
                                      == reference_gt]
    selected_freshness_row = selected_freshness.iloc[0] if not selected_freshness.empty else None

    with st.sidebar.expander("Data freshness", expanded=False):
        st.caption(
            "Computed from data/results.db. Refreshes automatically after rerunning eval scripts.")
        if selected_freshness_row is not None:
            st.markdown(
                f"**{reference_gt}**: {_status_badge(str(selected_freshness_row['status']))}")
            st.caption(
                f"LLM rows: {int(selected_freshness_row['llm_rows'])}/{int(selected_freshness_row['expected_rows'])} "
                f"({selected_freshness_row['coverage_pct']:.1f}%)"
            )
            st.caption(
                f"Latest LLM eval: {selected_freshness_row['latest_llm_eval']}")
            st.caption(
                f"Latest GT refresh: {selected_freshness_row['latest_gt_refresh']}")

        freshness_display = freshness_df.copy()
        freshness_display["status"] = freshness_display["status"].map(
            _status_badge)
        freshness_display = freshness_display.rename(
            columns={
                "reference_gt": "Reference Ground Truth",
                "status": "Status",
                "llm_rows": "LLM rows",
                "expected_rows": "Expected",
                "coverage_pct": "Coverage %",
                "latest_llm_eval": "Latest LLM eval",
                "latest_gt_refresh": "Latest GT refresh",
            }
        )
        st.dataframe(freshness_display, width="stretch", hide_index=True)

    if selected_freshness_row is not None:
        selected_status = str(selected_freshness_row["status"])
        if selected_status == "stale":
            st.warning(
                f"{reference_gt} ground truth was refreshed after its last LLM eval. "
                "Rerun batch eval for this reference GT with cache enabled to recompute metrics without new model calls."
            )
        elif selected_status == "partial":
            st.info(
                f"{reference_gt} has partial LLM coverage in the database. "
                "Some model/place/run combinations are still missing."
            )
        elif selected_status == "missing":
            st.error(
                f"{reference_gt} has no LLM comparisons yet. Run batch eval for this GT before using it as a reference."
            )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Layers")

    st.sidebar.markdown("**Geometry Types**")
    show_poly = st.sidebar.checkbox("⬠ Polygons", value=True)
    show_bbox = st.sidebar.checkbox("⬚ Bounding Boxes", value=True)
    show_point = st.sidebar.checkbox("• Centroids", value=False)
    geom_toggles = {"poly": show_poly,
                    "bbox": show_bbox, "centroid": show_point}

    st.sidebar.markdown("**Experiment Runs**")
    # Runs are scoped by the Evaluation Period selector; all runs within it are shown.
    selected_runs: list[str] = []
    st.sidebar.caption("All runs in the selected evaluation period are shown.")

    st.sidebar.markdown("**Prompt Variants**")
    if "variant_id" in valid_df.columns:
        available_variants = sorted(
            valid_df["variant_id"].fillna("baseline_v2").replace(
                "", "baseline_v2").unique().tolist()
        )
    else:
        available_variants = ["baseline_v2"]

    if not available_variants:
        selected_variants = ["baseline_v2"]
        st.sidebar.caption(
            "No variant metadata found. Defaulting to baseline_v2.")
    else:
        default_variants = ["baseline_v2"] if "baseline_v2" in available_variants else [
            available_variants[0]]
        selected_variants = st.sidebar.multiselect(
            "Select prompt variants",
            options=available_variants,
            default=default_variants,
            label_visibility="collapsed",
        )

    st.sidebar.markdown("---")

    st.sidebar.markdown("**Ground Truth Sources**")

    def color_getter_gt(src): return get_color_for_source(
        src, gt_sources, config.GT_COLORS)

    def _fmt_icons(status: dict[str, bool]) -> str:
        icons = []
        if status["poly"]:
            icons.append("⬠")
        if status["bbox"]:
            icons.append("⬚")
        if status["point"]:
            icons.append("•")
        return " ".join(icons) if icons else "—"

    gt_status_by_source = {src: _gt_availability_status(
        src, selected_place) for src in gt_sources}
    gt_disabled = {src: not any(status.values())
                   for src, status in gt_status_by_source.items()}
    gt_defaults = {src: any(status.values())
                   for src, status in gt_status_by_source.items()}
    active_gt_sources = render_checkbox_group(
        gt_sources,
        color_getter_gt,
        "sidebar",
        "gt",
        defaults=gt_defaults,
        label_fn=lambda s: f"{'[ref] ' if s == reference_gt else ''}{s} · {_fmt_icons(gt_status_by_source[s])}",
        disabled=gt_disabled,
    )
    st.sidebar.caption(f"Primary reference: {config.PRIMARY_GT_SOURCE}")

    known_models, legacy_models = _categorize_models(all_llm_sources)

    st.sidebar.markdown("**LLM Models**")

    def color_getter_llm(mdl): return get_color_for_source(
        mdl, known_models, config.LLM_COLORS)
    llm_status_by_model = {
        mdl: _llm_availability_status(
            mdl, selected_place, reference_gt, valid_df)
        for mdl in known_models
    }
    llm_disabled = {mdl: not any(status.values())
                    for mdl, status in llm_status_by_model.items()}
    default_models = {
        m: (any(llm_status_by_model[m].values())
            and i < config.NUM_DEFAULT_MODELS)
        for i, m in enumerate(known_models)
    }
    active_llm_sources = render_checkbox_group(
        known_models,
        color_getter_llm,
        "sidebar",
        "llm",
        defaults=default_models,
        label_fn=lambda m: f"{model_display_name(m)} · {_fmt_icons(llm_status_by_model[m])}",
        disabled=llm_disabled,
    )
    st.sidebar.caption("Geometries: ⬠ poly, ⬚ bbox, • point")

    if legacy_models:
        with st.sidebar.expander(f"Legacy models ({len(legacy_models)})", expanded=False):
            st.caption("Models from past eval runs not in current registry.")

            def color_getter_legacy(_): return config.LLM_COLORS[len(
                known_models) % len(config.LLM_COLORS)]
            legacy_selected = render_checkbox_group(
                legacy_models,
                color_getter_legacy,
                "expander",
                "llm_legacy",
            )
            active_llm_sources.extend(legacy_selected)

    return (
        selected_place,
        reference_gt,
        active_gt_sources,
        active_llm_sources,
        known_models,
        selected_freshness_row,
        gt_sources,
        geom_toggles,
        selected_runs,
        selected_variants,
    )
