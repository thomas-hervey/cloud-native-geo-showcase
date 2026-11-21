"""Prompt experiment UI for the spatial-eval Streamlit app.

render_prompt_experiments() is the single entry point called by source_config.py.
The actual LLM call loop (run_experiment) contains no Streamlit calls so it is
independently testable.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Callable

import pandas as pd
import streamlit as st
from shapely.geometry import box

import config
from corpus import place_alias_lookup
from db_protocol import EvalDBProtocol
from geometry_source import load_gt_source
from models import comparison_record_from_metrics
from llm_client import estimate_cost, query_model, parse_bbox_response, parse_geojson_polygon_response
from metrics.spatial_comparison import compare_geometries
from model_registry import display_name as model_display_name, load_models
from prompt_config import PROMPT_VERSION, SPATIAL_SYSTEM_PROMPT
from prompt_variants import DEFAULT_PROMPT_VARIANTS, build_variant_user_prompt
from ui.auth import is_admin_authenticated, admin_configured_token, admin_bypass_enabled


# ── Cost estimation (Streamlit-facing wrapper) ─────────────────────────────────

def _estimate_experiment_cost(
    models: list[str], total_calls_per_model: int, is_polygon: bool = False
) -> tuple[pd.DataFrame, float]:
    """Return a per-model cost DataFrame and total USD estimate."""
    rows_raw = estimate_cost(
        models, total_calls_per_model, is_polygon=is_polygon)
    total_usd = sum(cost for _, cost in rows_raw)
    cost_rows = [
        {"Model": model_display_name(
            mid), "Calls": total_calls_per_model, "Estimated USD": round(cost, 4)}
        for mid, cost in rows_raw
    ]
    return pd.DataFrame(cost_rows), total_usd


# ── LLM call loop (no Streamlit dependencies) ──────────────────────────────────

def run_experiment(
    exp_id: str,
    places: list[str],
    models: list[str],
    variant_ids: list[str],
    reference_gt: str,
    runs: int,
    use_cache: bool,
    alias_lookup: dict[str, list[str]],
    tier_lookup: dict[str, int | None],
    db: EvalDBProtocol,
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[int, int]:
    """Run the experiment loop and persist results to the DB.

    Args:
        progress_callback: Optional callable(done_calls, total_calls).

    Returns:
        (done_calls, failures) counts.
    """
    reference_source = load_gt_source(reference_gt)
    total_calls = len(places) * len(models) * len(variant_ids) * runs
    done_calls = failures = 0

    for place in places:
        ref_polygon = reference_source.get_polygon(place)
        for model in models:
            for variant_id in variant_ids:
                for run_idx in range(1, runs + 1):
                    prompt_text = build_variant_user_prompt(
                        place, alias_lookup.get(place, []), variant_id)
                    prompt_hash = hashlib.sha256(
                        prompt_text.encode("utf-8")).hexdigest()

                    result = query_model(
                        place, model,
                        run=run_idx,
                        use_cache=use_cache,
                        prompt_variant_id=variant_id,
                        user_prompt_override=prompt_text,
                    )

                    parsed = result if isinstance(result, dict) else None
                    is_valid = bool(parsed and parsed.get("_valid"))
                    comparison = None
                    if is_valid and ref_polygon is not None:
                        assert parsed is not None
                        if "polygon_wkt" in parsed:
                            from shapely import wkt
                            pred_poly = wkt.loads(parsed["polygon_wkt"])
                        else:
                            pred_poly = box(
                                float(parsed["bbox_west"]), float(
                                    parsed["bbox_south"]),
                                float(parsed["bbox_east"]), float(
                                    parsed["bbox_north"]),
                            )
                        comparison = compare_geometries(pred_poly, ref_polygon)

                    if not is_valid or comparison is None:
                        failures += 1

                    record = comparison_record_from_metrics(
                        metrics=comparison,
                        run_id=exp_id,
                        place=place,
                        source_a=f"llm:{model}",
                        source_b=reference_gt,
                        variant_id=variant_id,
                        geom_a=parsed.get("polygon_wkt") if parsed else None,
                        model_id=model,
                        prompt_text=prompt_text,
                        raw_response=parsed.get("_raw") if parsed else None,
                        notes=(
                            parsed.get("_error") if parsed
                            else (
                                "missing_reference_geometry"
                                if is_valid and comparison is None
                                else "invalid_or_missing_geometry"
                            )
                        ),
                        valid=bool(is_valid and comparison is not None),
                    )
                    db.insert_comparison(record)

                    done_calls += 1
                    if progress_callback:
                        progress_callback(done_calls, total_calls)

    return done_calls, failures


# ── Debugging tools ────────────────────────────────────────────────────────────

def _render_raw_response_debugger(df: pd.DataFrame, key_prefix: str) -> None:
    """Render an interactive inspector for raw LLM responses and errors."""
    if df.empty:
        return

    with st.expander("🔍 Raw Response Debugger", expanded=False):
        st.caption(
            "Inspect the exact text returned by the LLM to debug parsing or logic errors.")

        # Filter for rows that have raw data
        inspect_df = df.copy()
        if "raw_response" not in inspect_df.columns:
            st.warning("No raw response data available in this result set.")
            return

        # Create a display label for the selection
        inspect_df["_display_label"] = inspect_df.apply(
            lambda r: f"{r.get('place', 'Unknown')} | {model_display_name(r.get('model_id', 'Unknown'))} | {r.get('variant_id', 'Unknown')} | run {r.get('run_id', '?')} " + (
                "✅" if bool(r.get("valid")) else "❌"),
            axis=1
        )

        # Try to find the index of the first failure to make it the default
        # SQLITE store 0/1, so bitwise ~ on integers results in -1/-2, which trips up pandas indexing
        failures = inspect_df[inspect_df["valid"] == 0]
        default_idx = 0
        if not failures.empty:
            first_failure_label = failures["_display_label"].iloc[0]
            default_idx = inspect_df["_display_label"].tolist().index(
                first_failure_label)

        selected_label = st.selectbox(
            "Select a result to inspect",
            options=inspect_df["_display_label"].tolist(),
            index=default_idx,
            key=f"{key_prefix}_debugger_select"
        )

        selected_row = inspect_df[inspect_df["_display_label"]
                                  == selected_label].iloc[0]

        if not selected_row["valid"]:
            st.error(
                f"**Error Message:** {selected_row.get('notes', 'Unknown error')}")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Raw LLM Response:**")
            st.code(selected_row.get("raw_response",
                    "No raw response stored."), language="json")

        with c2:
            st.markdown("**Sent Prompt:**")
            st.code(selected_row.get("prompt_text",
                    "Prompt text not available."), language="text")


def _render_manual_result_uploader(
    all_places: list[str],
    all_models: list[str],
    db: EvalDBProtocol,
    reference_gt: str,
    is_admin: bool,
    key_prefix: str
) -> None:
    """Render a UI for manually pasting and saving LLM results."""
    with st.expander("📥 Manual Result Uploader", expanded=False):
        if not is_admin:
            st.warning("Read-only mode: manual result uploader is disabled.")
            return

        st.markdown("""
        **Bypass API Truncation**: If a model generates a complex polygon that gets truncated in the API,
        you can ask the same prompt in Claude/GPT Web UI, then paste the full JSON response here.
        """)

        c1, c2, c3 = st.columns(3)
        with c1:
            m_place = st.selectbox(
                "Place", options=all_places, key=f"{key_prefix}_m_place")
        with c2:
            m_model = st.selectbox(
                "Model", options=all_models, key=f"{key_prefix}_m_model")
        with c3:
            m_variant = st.selectbox("Variant", options=[
                                     "geojson_polygon", "baseline_v2"], key=f"{key_prefix}_m_variant")

        m_json = st.text_area("Paste Raw JSON Response:",
                              height=300, key=f"{key_prefix}_m_json")
        m_run = st.number_input(
            "Run Index", min_value=1, max_value=100, value=1, key=f"{key_prefix}_m_run")

        if st.button("Save Manual Result", key=f"{key_prefix}_m_save", use_container_width=True):
            if not m_json.strip():
                st.error("Please paste a JSON response.")
                return

            # Parsing logic
            parsed = None
            if m_variant == "geojson_polygon":
                parsed = parse_geojson_polygon_response(m_json)
            else:
                parsed = parse_bbox_response(m_json)

            if not parsed:
                st.error(
                    "Failed to parse the pasted JSON. Ensure it matches the requested schema and coordinates are within SF.")
                return

            # Geometry comparison logic
            ref_src = load_gt_source(reference_gt)
            ref_polygon = ref_src.get_polygon(m_place)
            comparison = None
            pred_poly = None

            if m_variant == "geojson_polygon" and "geometry" in parsed:
                coords = parsed["geometry"].get("coordinates", [])
                if coords:
                    from shapely.geometry import Polygon
                    try:
                        pred_poly = Polygon(coords[0])
                        if ref_polygon:
                            from metrics.spatial_comparison import compare_geometries
                            comparison = compare_geometries(
                                pred_poly, ref_polygon)
                    except Exception as e:
                        st.error(f"Invalid geometry: {e}")
                        return
            else:
                # BBox
                try:
                    from shapely.geometry import box
                    pred_poly = box(
                        parsed["bbox_west"], parsed["bbox_south"], parsed["bbox_east"], parsed["bbox_north"])
                    if ref_polygon:
                        from metrics.spatial_comparison import compare_geometries
                        comparison = compare_geometries(pred_poly, ref_polygon)
                except Exception as e:
                    st.error(f"Invalid bounding box: {e}")
                    return

            run_id = f"manual_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            record = comparison_record_from_metrics(
                metrics=comparison,
                run_id=run_id,
                place=m_place,
                source_a=f"llm:{m_model}",
                source_b=reference_gt,
                variant_id=m_variant,
                geom_a=pred_poly.wkt if pred_poly else None,
                model_id=m_model,
                prompt_text="Manually imported from external LLM session.",
                raw_response=m_json,
                notes=None,
                valid=True,
            )
            db.insert_comparison(record)

            # Save JSON cache for coverage matrix
            import json
            safe_place = m_place.lower().replace(" ", "_").replace("/", "-")
            safe_model = m_model.replace("/", "-").replace(":", "-")
            safe_variant = ""
            if m_variant != "baseline_v2":
                safe_variant = f"__variant-{m_variant.replace('/', '-').replace(':', '-')}"
            cache_path = config.LLM_RESPONSES_DIR / \
                f"{safe_place}__{safe_model}__run{m_run}{safe_variant}.json"

            cache_payload = {
                "_raw": m_json,
                "_valid": True,
                "_error": None,
                "place": m_place,
                "resolved_place": parsed.get("resolved_place"),
            }
            cache_payload.update(parsed)
            cache_path.write_text(json.dumps(cache_payload, indent=2))

            st.success(
                f"Successfully saved manual result for {m_place} ({m_model})!")
            st.balloons()
            st.rerun()


# ── Public Streamlit UI ────────────────────────────────────────────────────────

def render_prompt_experiments(
    all_corpus_places: list[str],
    selected_place: str,
    reference_gt: str,
    known_models: list[str],
    gt_sources: list[str],
    active_corpus: list[dict],
    db: EvalDBProtocol,
) -> None:
    """Render the full Prompt Experiments section inside the Source Config tab."""
    st.markdown("---")
    st.subheader("Prompt Experiments")

    alias_lookup = place_alias_lookup()

    # Admin token input
    st.markdown("### Admin Controls")
    configured_token = admin_configured_token()
    if configured_token and not admin_bypass_enabled():
        st.text_input(
            "Admin token",
            type="password",
            key="prompt_experiment_admin_token",
            help="Required to run prompt experiments from this app.",
        )

    is_admin, admin_message = is_admin_authenticated()
    if is_admin:
        st.success(admin_message)
    else:
        if "Invalid" in admin_message:
            st.error(admin_message)
        else:
            st.info(admin_message)

    # Manual result uploader
    _render_manual_result_uploader(
        all_corpus_places, known_models, db, reference_gt, is_admin, "admin")

    with st.expander("💻 Command Line Pipeline & Help", expanded=False):
        if not is_admin:
            st.warning("Read-only mode: CLI commands and pipeline help are hidden.")
        else:
            st.markdown("""
            The spatial evaluation pipeline is driven by the `run.py` CLI script. You can run `uv run python run.py --help` in your terminal for full details.

            **Core Pipeline Steps:**
            * `uv run python run.py gt-compare`: Run GT-vs-GT pairwise comparison across all active paths. Run once initially, or when adding a new Ground Truth source.
            * `uv run python run.py batch-eval`: Run all models × all places against the specified GT sources. This is your daily eval driver (idempotent, safe to rerun).
            * `uv run python run.py audit`: Pre-eval coverage audit to check which GT sources have polygons for each active corpus place.

            **Analysis & Verification:**
            * `uv run python run.py leaderboard`: Print models ranked by composite score for a given GT source.
            * `uv run python run.py analysis`: Print per-metric summary (iou, centroid_error_m, composite, gt-vs-gt).
            * `uv run python run.py smoke`: Single-place smoke test. Run before a full batch-eval to verify APIs.
            * `uv run python run.py prompt-exp`: CLI version of the prompt experiment runner.
            """)

    # Admin run controls
    with st.expander("Admin run controls", expanded=True):
        if not is_admin:
            st.warning("Run controls are locked in read-only mode.")
        else:
            variant_options = {
                v.variant_id: v for v in DEFAULT_PROMPT_VARIANTS}
            variant_ids = list(variant_options.keys())
            default_variant = [
                "baseline_v2"] if "baseline_v2" in variant_options else variant_ids[:1]

            exp_places = st.multiselect(
                "Places", options=all_corpus_places,
                default=[
                    selected_place] if selected_place in all_corpus_places else all_corpus_places[:1],
                help="Recommended: 1-3 places for low-cost targeted checks.",
            )
            from model_registry import load_models, default_models
            _registry_ids = [m["model_id"] for m in load_models()]
            _model_opts = _registry_ids if _registry_ids else known_models
            _model_defaults = (default_models() or _model_opts)[:1]
            exp_models = st.multiselect(
                "Models", options=_model_opts, default=_model_defaults,
                format_func=model_display_name, help="Recommended: 1-2 models.",
            )
            exp_variants = st.multiselect(
                "Prompt variants", options=variant_ids, default=default_variant,
                format_func=lambda v: f"{variant_options[v].label} ({v})",
            )
            exp_reference_gt = st.selectbox(
                "Reference Ground Truth", options=gt_sources,
                index=gt_sources.index(
                    reference_gt) if reference_gt in gt_sources else 0,
            )
            exp_runs = int(st.number_input("Runs per combination",
                           min_value=1, max_value=2, value=1, step=1))
            exp_use_cache = st.checkbox("Use cache when available", value=True)

            max_ui_calls = 24
            total_calls = len(exp_places) * len(exp_models) * \
                len(exp_variants) * exp_runs
            st.caption(
                f"Planned calls: {total_calls} (limit {max_ui_calls}) = "
                f"{len(exp_places)} place(s) × {len(exp_models)} model(s) × "
                f"{len(exp_variants)} variant(s) × {exp_runs} run(s)."
            )

            if exp_models:
                per_model_calls = len(exp_places) * \
                    len(exp_variants) * exp_runs
                is_poly = any(v == "geojson_polygon" for v in exp_variants)
                cost_df, total_est_usd = _estimate_experiment_cost(
                    exp_models, per_model_calls, is_polygon=is_poly)
                st.dataframe(cost_df, width="stretch", hide_index=True)
                st.caption(
                    f"Estimated total cost: ${total_est_usd:.4f} (Polygons use higher token estimates)")

            confirm_paid_calls = st.checkbox(
                "I understand this can trigger paid model API calls.")

            if st.button("Run prompt experiment", type="primary"):
                if not exp_places or not exp_models or not exp_variants:
                    st.error(
                        "Select at least one place, model, and prompt variant.")
                elif total_calls == 0:
                    st.error("No calls planned. Adjust selections.")
                elif total_calls > max_ui_calls:
                    st.error(
                        f"Planned calls ({total_calls}) exceed UI safety cap ({max_ui_calls}). "
                        "Reduce selection size or run experiments from CLI."
                    )
                elif not confirm_paid_calls:
                    st.error(
                        "Confirm cost acknowledgment before running experiments.")
                else:
                    exp_id = datetime.now(timezone.utc).strftime(
                        "exp-%Y%m%d-%H%M%S")
                    tier_lookup = {entry["name"]: entry.get(
                        "tier") for entry in active_corpus}
                    progress = st.progress(
                        0.0, text="Starting prompt experiment run…")

                    def _progress_cb(done: int, total: int) -> None:
                        progress.progress(
                            done / total, text=f"Completed {done}/{total} calls")

                    done_calls, failures = run_experiment(
                        exp_id=exp_id,
                        places=exp_places,
                        models=exp_models,
                        variant_ids=exp_variants,
                        reference_gt=exp_reference_gt,
                        runs=exp_runs,
                        use_cache=exp_use_cache,
                        alias_lookup=alias_lookup,
                        tier_lookup=tier_lookup,
                        db=db,
                        progress_callback=_progress_cb,
                    )
                    st.success(
                        f"Stored experiment {exp_id} with {done_calls} run(s). "
                        f"{failures} row(s) were invalid or missing geometry."
                    )

                    # Display the immediate results of this specific experiment run
                    run_records = db.fetch_comparisons(run_id=exp_id)
                    run_records = [r for r in run_records if r.source_a.startswith("llm:")]
                    run_results = pd.DataFrame([r.model_dump() for r in run_records])
                    if not run_results.empty:
                        run_results["Model"] = run_results["model_id"].apply(
                            model_display_name)
                        st.markdown(f"**Results for {exp_id}**")
                        cols_to_show = ["place", "Model", "variant_id", "run_id",
                                        "valid", "notes", "iou", "composite_score"]
                        st.dataframe(
                            run_results[[
                                c for c in cols_to_show if c in run_results.columns]],
                            width="stretch",
                            hide_index=True,
                        )
                        _render_raw_response_debugger(
                            run_results, "immediate_run")

    # Recent experiment results
    st.markdown("### Recent results")
    if not is_admin:
        st.warning("Read-only mode: recent experiment results and raw response debugger are hidden.")
    else:
        recent_records = db.fetch_comparisons(source_b=reference_gt)
        recent_records = [r for r in recent_records if r.source_a.startswith("llm:")][:500]
        recent_experiments = pd.DataFrame([r.model_dump() for r in recent_records])
        if recent_experiments.empty:
            st.info("No prompt experiment rows stored yet.")
        else:
            recent_experiments["Model"] = recent_experiments["model_id"].apply(
                model_display_name)
            st.dataframe(
                recent_experiments[[
                    c for c in [
                        "created_at", "run_id", "variant_id", "place", "Model",
                        "source_b", "valid", "notes", "iou", "composite_score",
                    ] if c in recent_experiments.columns
                ]],
                width="stretch",
                hide_index=True,
            )
            _render_raw_response_debugger(recent_experiments, "recent_pool")
            valid_experiments = recent_experiments[recent_experiments["valid"] == True]  # noqa: E712
            if not valid_experiments.empty:
                summary = (
                    valid_experiments
                    .groupby(["place", "Model", "variant_id"], as_index=False)[["iou", "composite_score"]]
                    .mean()
                    .round(3)
                )
                st.markdown(
                    "**Variant comparison summary (mean over stored runs)**")
                st.dataframe(summary, width="stretch", hide_index=True)

    # Variant catalog
    st.markdown("---")
    st.markdown("**Prompt Variant Catalog**")
    if not is_admin:
        st.warning("Read-only mode: prompt variant catalog and rendering tools are hidden.")
    else:
        preview_place_idx = all_corpus_places.index(
            selected_place) if selected_place in all_corpus_places else 0
        preview_place = st.selectbox(
            "Prompt preview place",
            options=all_corpus_places,
            index=preview_place_idx,
            key="prompt_variant_preview_place",
            help="Used to render each prompt variant against a specific neighborhood name and aliases.",
        )
        preview_place_value = preview_place or (
            all_corpus_places[0] if all_corpus_places else "")

        variant_catalog_rows = [
            {
                "Variant ID": v.variant_id,
                "Label": v.label,
                "Description": v.description,
                "Has Extra Guidance": "Yes" if v.guidance_suffix else "No",
            }
            for v in DEFAULT_PROMPT_VARIANTS
        ]
        st.dataframe(pd.DataFrame(variant_catalog_rows),
                     width="stretch", hide_index=True)

        with st.expander("Show rendered prompt text for each variant", expanded=False):
            st.markdown("**System prompt (shared across variants)**")
            st.code(SPATIAL_SYSTEM_PROMPT, language="text")
            for variant in DEFAULT_PROMPT_VARIANTS:
                with st.expander(f"{variant.label} ({variant.variant_id})", expanded=False):
                    st.caption(variant.description)
                    st.code(
                        build_variant_user_prompt(preview_place_value, alias_lookup.get(
                            preview_place_value, []), variant.variant_id),
                        language="text",
                    )
