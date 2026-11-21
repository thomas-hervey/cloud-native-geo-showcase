"""Tab 4 — Source Config: alias editor, coverage matrices, prompt experiments.

Delegates the prompt experiment run/display logic to ui.experiments.
"""
from __future__ import annotations
from corpus import place_alias_lookup

import json
import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st

import config
from model_registry import display_name as model_display_name
from prompt_config import PROMPT_VERSION, SPATIAL_SYSTEM_PROMPT, build_bbox_user_prompt
from prompt_variants import DEFAULT_PROMPT_VARIANTS
from sources.coverage_utils import coverage_symbol
from ui import experiments as exp_ui
from ui.auth import is_admin_authenticated


# ── Private helpers ────────────────────────────────────────────────────────────

def _load_alias_config() -> dict[str, dict[str, str | None]]:
    if not config.ALIASES_PATH.exists():
        return {}
    payload = json.loads(config.ALIASES_PATH.read_text())
    return {k: v for k, v in payload.items() if not k.startswith("_")}


def _cache_status(query: str, cache_dir: Path) -> str:
    """Return ✅ / ❌ null / ⏳ based on whether a cache file exists and has data."""
    safe = query.lower().replace(" ", "_").replace("/", "-")
    f = cache_dir / f"{safe}.json"
    if not f.exists():
        return "⏳"
    try:
        return "❌ null" if json.loads(f.read_text()) is None else "✅"
    except (json.JSONDecodeError, OSError):
        return "⏳"


def _gt_alias_label(place: str, source_name: str, alias_config: dict) -> str:
    place_entry = alias_config.get(place, {})
    raw_label = place_entry.get(source_name)
    if isinstance(raw_label, str) and raw_label.strip():
        return raw_label.strip()
    return place


def _truncate_label(label: str, max_len: int = config.MATRIX_HEATMAP_CELL_TRUNCATE) -> str:
    label = " ".join(label.split())
    if len(label) <= max_len:
        return label
    return f"{label[:max_len - 1]}…"


def _format_matrix_cell(status: str, label: str | None = None) -> str:
    if not label:
        return status
    return f"{status} {_truncate_label(label)}"


def _style_coverage_matrix(df: pd.DataFrame, gt_source_names: list[str]) -> pd.io.formats.style.Styler:
    """Apply pastel backgrounds to cells and color-coded headers."""
    from ui.colors import get_color_for_source

    def _get_cell_style(val):
        if not isinstance(val, str) or val.startswith("Total"):
            return ""

        # The icon symbol part is at the start (e.g. "⬠ ⬚ •" or "⬠ •")
        # We count the unique geometry icons present
        icons = ["⬠", "⬚", "•"]
        count = sum(1 for icon in icons if icon in val)

        if count == 3:
            return "background-color: #d1e7ff; color: #004085"  # Pastel Blue
        if count == 2:
            return "background-color: #d4edda; color: #155724"  # Pastel Green
        if count == 1:
            return "background-color: #fff3cd; color: #856404"  # Pastel Yellow
        if val.startswith("—"):
            return "background-color: #f8d7da; color: #721c24"  # Pastel Red
        return ""

    style_cols = [c for c in df.columns if c != "Place"]
    styler = df.style.map(_get_cell_style, subset=style_cols)

    # Header styling
    header_styles = []
    for col in style_cols:
        color = get_color_for_source(col, gt_source_names, config.GT_COLORS)
        header_styles.append({
            "selector": f"th.col{df.columns.get_loc(col)}",
            "props": [
                ("background-color", f"{color}33"),  # 20% opacity for heading
                ("border-bottom", f"3px solid {color}"),
            ]
        })
    return styler.set_table_styles(header_styles, overwrite=False)


def _style_llm_coverage_matrix(df: pd.DataFrame, known_models: list[str]) -> pd.io.formats.style.Styler:
    """Apply pastel backgrounds to LLM cells and color-coded headers."""
    from ui.colors import get_color_for_source

    def _get_cell_style(val):
        if not isinstance(val, str) or val.startswith("Total"):
            return ""

        if "⏳" in val:
            return "background-color: #e9ecef; color: #495057"  # Pastel Grey

        icons = ["⬠", "⬚", "•"]
        count = sum(1 for icon in icons if icon in val)

        if count == 3:
            return "background-color: #d1e7ff; color: #004085"  # Pastel Blue
        if count == 2:
            return "background-color: #d4edda; color: #155724"  # Pastel Green
        if count == 1:
            return "background-color: #fff3cd; color: #856404"  # Pastel Yellow
        if "—" in val or count == 0:
            return "background-color: #f8d7da; color: #721c24"  # Pastel Red
        return ""

    style_cols = [c for c in df.columns if c != "Place"]
    styler = df.style.map(_get_cell_style, subset=style_cols)

    # Header styling (mapping model names back to original IDs for color lookup)
    from model_registry import load_models
    try:
        models_data = load_models()
        display_to_id = {model_display_name(
            m["model_id"]): m["model_id"] for m in models_data}
    except Exception:
        display_to_id = {}

    header_styles = []
    for col in style_cols:
        model_id = display_to_id.get(col, col)
        color = get_color_for_source(model_id, known_models, config.LLM_COLORS)
        header_styles.append({
            "selector": f"th.col{df.columns.get_loc(col)}",
            "props": [
                ("background-color", f"{color}33"),  # 20% opacity
                ("border-bottom", f"3px solid {color}"),
            ]
        })
    return styler.set_table_styles(header_styles, overwrite=False)


def _llm_cache_path(place: str, model: str, run: int, variant_id: str | None = None) -> Path:
    safe_place = place.lower().replace(" ", "_").replace("/", "-")
    safe_model = model.replace("/", "-").replace(":", "-")
    safe_variant = ""
    if variant_id:
        safe_variant = f"__variant-{variant_id.replace('/', '-').replace(':', '-')}"
    return config.LLM_RESPONSES_DIR / f"{safe_place}__{safe_model}__run{run}{safe_variant}.json"


def _llm_coverage_summary(place: str, model: str, runs: int, variant_ids: list[str]) -> tuple[str, str, str | None]:
    """Return (status_emoji, icons_str, resolved_label)."""
    attempted = valid_runs = 0
    resolved_labels: list[str] = []

    # Track which geometries are found across all valid runs for this place/model
    has_poly = has_bbox = has_point = False

    selected_variants = variant_ids or ["baseline_v2"]

    for run in range(1, runs + 1):
        safe_place = place.lower().replace(" ", "_").replace("/", "-")
        bare_model = model.removeprefix("llm:")
        safe_model = bare_model.replace("/", "-").replace(":", "-")
        prefix = f"{safe_place}__{safe_model}__run{run}"

        # Build candidate cache files for the selected variants.
        # Legacy no-suffix files are mapped to baseline_v2.
        cache_files = []
        for variant_id in selected_variants:
            if variant_id == "baseline_v2":
                legacy_path = config.LLM_RESPONSES_DIR / f"{prefix}.json"
                if legacy_path.exists():
                    cache_files.append(legacy_path)

            path = config.LLM_RESPONSES_DIR / \
                f"{prefix}__variant-{variant_id}.json"
            if path.exists():
                cache_files.append(path)

        if not cache_files:
            continue
        attempted += 1

        run_is_valid = False
        run_resolved_labels = []

        for cache_path in cache_files:
            try:
                payload = json.loads(cache_path.read_text())
            except (json.JSONDecodeError, OSError):
                continue

            if payload.get("_valid"):
                run_is_valid = True
                # Check for geometry presence
                # geojson variants could be FeatureCollection (features) or Feature (geometry) or directly polygon
                if any(k in payload for k in ["polygon", "geometry", "feature", "features", "polygon_wkt"]):
                    has_poly = True
                elif payload.get("type", "").lower() in ["feature", "featurecollection", "polygon", "multipolygon"]:
                    has_poly = True

                if all(payload.get(k) is not None for k in ["bbox_north", "bbox_south", "bbox_east", "bbox_west"]):
                    has_bbox = True
                if payload.get("centroid_lat") is not None and payload.get("centroid_lon") is not None:
                    has_point = True

                rp = payload.get("resolved_place") or payload.get(
                    "place") or payload.get("_place")
                if isinstance(rp, str) and rp.strip():
                    run_resolved_labels.append(rp.strip())

        if run_is_valid:
            valid_runs += 1
            resolved_labels.extend(run_resolved_labels)

    icons = ""
    if has_poly:
        icons += "⬠"
    if has_bbox:
        icons += "⬚"
    if has_point:
        icons += "•"
    icons_str = icons if icons else "—"

    resolved_label = None
    if resolved_labels:
        unique = list(dict.fromkeys(resolved_labels))
        resolved_label = unique[0] if len(
            unique) == 1 else f"{unique[0]} (+{len(unique) - 1})"

    if valid_runs > 0:
        run_ratio = "" if valid_runs == runs else f" [{valid_runs}/{runs}]"
        return run_ratio, icons_str, resolved_label
    if attempted > 0:
        return "", icons_str, resolved_label
    return "⏳", "—", None


def _build_llm_coverage_matrix(
    places: list[str], models: list[str], runs: int, variant_ids: list[str]
) -> pd.DataFrame:
    coverage_rows = []
    for place in places:
        row: dict[str, str] = {"Place": place}
        for model in models:
            status, icons_str, resolved_label = _llm_coverage_summary(
                place, model, runs, variant_ids)
            # Combine icons + status + label
            parts = [icons_str]
            if status:
                parts.append(status)
            if resolved_label:
                parts.append(resolved_label)
            row[model_display_name(model)] = " ".join(parts)
        coverage_rows.append(row)

    df = pd.DataFrame(coverage_rows)
    totals: dict[str, str] = {"Place": f"Total ⬠ / {len(places)}"}
    for model in models:
        col = model_display_name(model)
        totals[col] = str(df[col].astype(str).str.contains("⬠").sum())
    return pd.concat([df, pd.DataFrame([totals])], ignore_index=True)


# ── Sub-section renderers ──────────────────────────────────────────────────────

def _render_alias_editor(
    all_corpus_places: list[str],
    selected_place: str,
    is_cloud: bool,
) -> None:
    st.header("Per-Source Query Aliases")
    st.caption(config.METRIC_EXPLANATIONS["config"])
    st.caption(
        f"'Corpus Name' is the canonical place name from `data/places.json` — your "
        f"{len(all_corpus_places)}-place active evaluation set. "
        "Each row shows how that name maps to each data source's internal query string or GeoJSON key. "
        "OSM and Wikidata are API sources with editable query strings; "
        "CTH, SF Planning, and Zillow use committed GeoJSON files (no external URL to verify — "
        "edit `data/source_aliases.json` directly to update their mappings). "
        "Click Save to persist OSM/Wikidata changes."
    )

    if is_cloud:
        st.warning(
            "⚠️ **Save is disabled on Streamlit Community Cloud.** "
            "Edit `data/source_aliases.json` locally and commit the file to update the config."
        )

    raw_aliases: dict = {}
    if config.ALIASES_PATH.exists():
        raw_aliases = {
            k: v for k, v in json.loads(config.ALIASES_PATH.read_text()).items()
            if not k.startswith("_")
        }

    rows_cfg = []
    for place in all_corpus_places:
        entry = raw_aliases.get(place, {})
        osm_q = entry.get("osm", place)
        wd_q = entry.get("wikidata", place)
        osm_cache = _cache_status(osm_q, config.CACHE_OSM)
        wd_cache = _cache_status(wd_q, config.CACHE_WIKIDATA)
        rows_cfg.append({
            "Corpus Name": place,
            "SF Planning Name": entry.get("sf_planning", place),
            "CTH Name": entry.get("click_that_hood", place),
            "OSM Query": osm_q,
            "OSM Overpass Query": entry.get("osm_overpass", place),
            "Zillow Name": entry.get("zillow", place),
            "Wikidata Label (excluded)": wd_q,
            "API Cache": f"OSM {osm_cache}  WD {wd_cache}",
        })

    cfg_df = pd.DataFrame(rows_cfg)
    edited = st.data_editor(
        cfg_df,
        column_config={
            "Corpus Name":       st.column_config.TextColumn(disabled=True),
            "SF Planning Name":  st.column_config.TextColumn(disabled=True, label="sf_planning"),
            "CTH Name":          st.column_config.TextColumn(disabled=True, label="click_that_hood"),
            "OSM Query":         st.column_config.TextColumn(label="osm"),
            "OSM Overpass Query": st.column_config.TextColumn(disabled=True, label="osm_overpass (read-only)"),
            "Zillow Name":       st.column_config.TextColumn(disabled=True, label="zillow"),
            "Wikidata Label (excluded)": st.column_config.TextColumn(label="Wikidata Label (excluded from eval)"),
            "API Cache":         st.column_config.TextColumn(
                disabled=True, width="small",
                help="OSM and Wikidata cache status. ✅ cached  ⏳ not yet fetched  ❌ null result",
            ),
        },
        width="stretch",
        hide_index=True,
    )

    # Prompt preview
    prompt_place = selected_place if selected_place in all_corpus_places else (
        all_corpus_places[0] if all_corpus_places else None)
    if prompt_place is not None and config.PLACES_JSON_PATH.exists():
        place_entries = json.loads(
            config.PLACES_JSON_PATH.read_text()).get("places", [])
        alias_lookup = {e["name"]: e.get("aliases", [])
                        for e in place_entries if e.get("name")}
        with st.expander("Prompt preview", expanded=False):
            st.badge(f"Current prompt version: {PROMPT_VERSION}")
            st.markdown(f"**Selected place:** {prompt_place}")
            st.markdown("**System prompt**")
            st.code(SPATIAL_SYSTEM_PROMPT, language="text")
            st.markdown("**User prompt**")
            st.code(build_bbox_user_prompt(prompt_place,
                    alias_lookup.get(prompt_place, [])), language="text")

    # Verify links
    st.markdown("**Verify in browser:**")
    link_rows = []
    for _, r in edited.iterrows():
        osm_url = f"https://nominatim.openstreetmap.org/ui/search.html?q={quote_plus(r['OSM Query'] + ', San Francisco')}"
        wd_url = f"https://www.wikidata.org/w/index.php?search={quote_plus(r['Wikidata Label (excluded)'])}"
        link_rows.append(
            f"**{r['Corpus Name']}** — [OSM 🔗]({osm_url}) [Wikidata 🔗]({wd_url})")
    with st.expander("Show verify links for all places", expanded=False):
        st.markdown("\n\n".join(link_rows))
        st.caption(
            "OSM and Wikidata links open the external search UI so you can confirm the query "
            "resolves to the correct neighborhood. CTH, SF Planning, and Zillow use local GeoJSON "
            "files — no external URL applies."
        )

    # Save button (local only)
    if not is_cloud:
        if st.button("💾 Save aliases.json"):
            updated: dict = {
                "_note": raw_aliases.get("_note", "Manually verified — use this tab to review and update."),
                "_todo": raw_aliases.get("_todo", "Long-term: replace with a sync script that auto-generates this mapping and flags mismatches."),
            }
            for _, r in edited.iterrows():
                place = r["Corpus Name"]
                existing = raw_aliases.get(place, {})
                updated[place] = {
                    "osm":             r["OSM Query"],
                    "wikidata":        r["Wikidata Label (excluded)"],
                    "click_that_hood": existing.get("click_that_hood", r.get("CTH Name", place)),
                    "sf_planning":     existing.get("sf_planning", r.get("SF Planning Name", place)),
                    "osm_overpass":    existing.get("osm_overpass", r.get("OSM Overpass Query", place)),
                    "zillow":          existing.get("zillow", r.get("Zillow Name", place)),
                }
            config.ALIASES_PATH.write_text(json.dumps(
                updated, indent=2, ensure_ascii=False) + "\n")
            st.success(
                f"Saved {len(edited)} entries to `data/source_aliases.json`.")
            st.cache_data.clear()


def _render_gt_coverage_matrix(
    all_corpus_places: list[str],
    gt_source_names: list[str],
    alias_config: dict,
) -> None:
    st.markdown("---")
    st.subheader("Ground Truth Coverage Matrix")
    st.markdown("""
    <div style="display: flex; gap: 10px; margin-bottom: 10px; font-size: 0.8rem;">
        <div style="background-color: #d1e7ff; padding: 2px 8px; border-radius: 4px; color: #004085;">🟦 3 types (⬠⬚•)</div>
        <div style="background-color: #d4edda; padding: 2px 8px; border-radius: 4px; color: #155724;">🟩 2 types</div>
        <div style="background-color: #fff3cd; padding: 2px 8px; border-radius: 4px; color: #856404;">🟨 1 type</div>
        <div style="background-color: #f8d7da; padding: 2px 8px; border-radius: 4px; color: #721c24;">🟥 Missing</div>
        <div style="padding: 2px 8px;">⬠ poly, ⬚ bbox, • point, — none</div>
    </div>
    """, unsafe_allow_html=True)
    st.caption(
        "Results are cached until you click Refresh. Colored blocks indicate level of geometric coverage.")
    if "coverage_matrix" not in st.session_state:
        st.session_state["coverage_matrix"] = None
    if "coverage_needs_refresh" not in st.session_state:
        st.session_state["coverage_needs_refresh"] = False

    if st.button("🔄 Refresh coverage"):
        st.session_state["coverage_matrix"] = None
        st.session_state["coverage_needs_refresh"] = True

    if st.session_state["coverage_matrix"] is None:
        if not st.session_state["coverage_needs_refresh"]:
            st.info("Click **Refresh coverage** to audit all ground truth sources.")
        else:
            with st.spinner("Auditing ground truth sources…"):
                coverage_rows = []
                for place in all_corpus_places:
                    row: dict[str, str] = {"Place": place}
                    for src_name in gt_source_names:
                        try:
                            symbol = coverage_symbol(src_name, place)
                            alias_label = _gt_alias_label(
                                place, src_name, alias_config)
                            row[src_name] = _format_matrix_cell(
                                symbol, alias_label)
                        except Exception:
                            row[src_name] = "⚠️"
                    coverage_rows.append(row)

                cov_df = pd.DataFrame(coverage_rows)
                src_cols = [c for c in cov_df.columns if c != "Place"]
                totals: dict[str, str] = {
                    "Place": f"Total ⬠ / {len(all_corpus_places)}"}
                for col in src_cols:
                    totals[col] = str(cov_df[col].astype(
                        str).str.contains("⬠").sum())
                cov_df = pd.concat(
                    [cov_df, pd.DataFrame([totals])], ignore_index=True)
                st.session_state["coverage_matrix"] = cov_df
                st.session_state["coverage_needs_refresh"] = False

    if st.session_state["coverage_matrix"] is not None:
        # Set index BEFORE styling because Styler objects don't have set_index()
        df_to_style = st.session_state["coverage_matrix"].set_index("Place")
        styled_df = _style_coverage_matrix(df_to_style, gt_source_names)
        st.table(styled_df)


def _render_llm_coverage_matrix(
    all_corpus_places: list[str],
    known_models: list[str],
    df_all: pd.DataFrame,
    selected_variants: list[str],
) -> None:
    st.markdown("---")
    st.subheader("LLM Coverage Matrix")
    st.markdown("""
    <div style="display: flex; gap: 10px; margin-bottom: 10px; font-size: 0.8rem;">
        <div style="background-color: #d1e7ff; padding: 2px 8px; border-radius: 4px; color: #004085;">🟦 3 types (⬠⬚•)</div>
        <div style="background-color: #d4edda; padding: 2px 8px; border-radius: 4px; color: #155724;">🟩 2 types</div>
        <div style="background-color: #fff3cd; padding: 2px 8px; border-radius: 4px; color: #856404;">🟨 1 type</div>
        <div style="background-color: #f8d7da; padding: 2px 8px; border-radius: 4px; color: #721c24;">🟥 Missing</div>
        <div style="background-color: #e9ecef; padding: 2px 8px; border-radius: 4px; color: #495057;">⏳ No Cache</div>
        <div style="padding: 2px 8px;">⬠ poly, ⬚ bbox, • point, — none</div>
    </div>
    """, unsafe_allow_html=True)
    st.caption(
        "Based on cached responses in `data/llm_responses`. Cells show status and resolved neighborhood name.")
    llm_models_for_coverage = [
        m for m in known_models if m not in config.EXCLUDED_MODELS]
    _llm_mask = df_all["source_a"].str.startswith("llm:")
    llm_run_count = int(df_all[_llm_mask]["run_id"].nunique()) if _llm_mask.any() else 0

    if "llm_coverage_matrix" not in st.session_state:
        st.session_state["llm_coverage_matrix"] = None
    if "llm_coverage_signature" not in st.session_state:
        st.session_state["llm_coverage_signature"] = None

    llm_signature = (
        tuple(all_corpus_places),
        tuple(llm_models_for_coverage),
        llm_run_count,
        tuple(selected_variants),
    )
    if st.session_state["llm_coverage_signature"] != llm_signature:
        st.session_state["llm_coverage_matrix"] = None
        st.session_state["llm_coverage_signature"] = llm_signature

    if not llm_models_for_coverage or llm_run_count == 0:
        st.info("No cached LLM runs found yet.")
        return

    if st.session_state["llm_coverage_matrix"] is None:
        if not st.button("🔄 Load LLM coverage"):
            st.info("LLM coverage matrix is large. Click above to load.")
        else:
            with st.spinner("Auditing cached LLM responses…"):
                st.session_state["llm_coverage_matrix"] = _build_llm_coverage_matrix(
                    all_corpus_places, llm_models_for_coverage, llm_run_count, selected_variants
                )
            st.rerun()
    else:
        if st.button("🔄 Refresh LLM coverage"):
            with st.spinner("Auditing cached LLM responses…"):
                st.session_state["llm_coverage_matrix"] = _build_llm_coverage_matrix(
                    all_corpus_places, llm_models_for_coverage, llm_run_count, selected_variants
                )

    if st.session_state["llm_coverage_matrix"] is not None:
        # Set index BEFORE styling because Styler objects don't have set_index()
        df_to_style = st.session_state["llm_coverage_matrix"].set_index(
            "Place")
        styled_df = _style_llm_coverage_matrix(df_to_style, known_models)
        st.table(styled_df)


# ── DB Explorer ────────────────────────────────────────────────────────────────

def _render_db_explorer(db, is_cloud: bool, is_admin: bool) -> None:
    """Render a local-only DB explorer shortcut at the bottom of Source Config."""
    st.markdown("---")
    with st.expander("🗄️ DB Explorer", expanded=False):
        if is_cloud:
            st.info("DB Explorer is only available when running locally.")
            return

        if not is_admin:
            st.warning("Read-only mode: DB Explorer and file paths are hidden for security.")
            return

        db_path = config.DUCKDB_PATH.resolve()
        st.markdown(f"**Database:** `{db_path}`")

        # Row counts from coverage dict
        coverage = db.get_experiment_coverage()
        total = sum(coverage.values())
        st.markdown(f"**Total rows:** {total:,} comparisons")
        if coverage:
            level_summary = "  |  ".join(
                f"{lvl}: {n:,}" for lvl, n in sorted(coverage.items()))
            st.caption(f"By cognitive level — {level_summary}")

        st.markdown("**Open in DuckDB UI** (run in terminal):")
        st.code(f"duckdb --ui {db_path}", language="bash")
        st.caption(
            "DuckDB UI opens an in-browser SQL explorer at http://localhost:4213. "
            "Requires DuckDB ≥ 1.1."
        )


# ── Public entry point ─────────────────────────────────────────────────────────

def render_tab(
    all_corpus_places: list[str],
    active_corpus_places: list[str],
    selected_place: str,
    reference_gt: str,
    known_models: list[str],
    gt_sources: list[str],
    active_corpus: list[dict],
    df_all: pd.DataFrame,
    db,
    selected_variants: list[str],
) -> None:
    """Render the full Source Config tab."""
    is_cloud = os.environ.get(
        "STREAMLIT_SERVER_HEADLESS", "false").lower() == "true"

    _render_alias_editor(all_corpus_places, selected_place, is_cloud)

    from geometry_source import list_gt_sources
    gt_source_names = [s for s in config.GT_UI_ORDER if s in list_gt_sources()]
    alias_config = _load_alias_config()
    _render_gt_coverage_matrix(
        all_corpus_places, gt_source_names, alias_config)

    _render_llm_coverage_matrix(
        all_corpus_places, known_models, df_all, selected_variants)

    is_admin, _ = is_admin_authenticated()

    exp_ui.render_prompt_experiments(
        all_corpus_places=all_corpus_places,
        selected_place=selected_place,
        reference_gt=reference_gt,
        known_models=known_models,
        gt_sources=gt_sources,
        active_corpus=active_corpus,
        db=db,
    )

    _render_db_explorer(db, is_cloud, is_admin)
