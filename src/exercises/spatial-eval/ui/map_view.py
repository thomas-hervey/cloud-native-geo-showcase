"""Folium map layer builders and renderer for the spatial-eval Streamlit app.

Each builder (build_gt_layers, build_llm_layers) returns a list of layer dicts.
render_map_section() orchestrates all selected layers → Folium map → st_folium.
"""
from __future__ import annotations

import folium
import pandas as pd
import streamlit as st
from shapely.geometry import box
from streamlit_folium import st_folium

import config
from ui.colors import get_color_for_source


# ── Layer builders ─────────────────────────────────────────────────────────────

def build_gt_layers(
    source_name: str,
    selected_place: str,
    reference_gt: str,
    df: pd.DataFrame,
    active_gt_sources: list[str],
) -> list[dict]:
    """Build a list of GT layers (Polygon, BBox, Centroid)."""
    from geometry_source import load_gt_source
    try:
        source = load_gt_source(source_name)
    except Exception:
        return []

    layers = []
    color = get_color_for_source(
        source_name, active_gt_sources, config.GT_COLORS)
    tooltip_html = f"<b>{source_name}</b> (Ground Truth)"

    # Polygon
    poly = source.get_polygon(selected_place)
    if poly:
        layers.append({
            "name": f"{source_name} (Poly)",
            "geom": poly,
            "color": color,
            "weight": 2.5 if source_name == reference_gt else 1.5,
            "fill_opacity": 0.15 if source_name == reference_gt else 0.05,
            "tooltip": tooltip_html,
            "area": poly.area,
            "layer_type": "poly",
            "source_name": source_name,
            "layer_kind": "gt",
        })

    # BBox (Secondary)
    bbox = source.get_bbox(selected_place)
    if bbox:
        bbox_poly = box(bbox["west"], bbox["south"],
                        bbox["east"], bbox["north"])
        layers.append({
            "name": f"{source_name} (BBox)",
            "geom": bbox_poly,
            "color": color,
            "weight": 1.5,
            "fill_opacity": 0.0,
            "tooltip": f"{tooltip_html} - Bounding Box",
            "area": bbox_poly.area,
            "layer_type": "bbox",
            "dash_array": "5, 5",
            "source_name": source_name,
            "layer_kind": "gt",
        })

    # Centroid (Secondary)
    centroid = source.get_centroid(selected_place)
    if centroid:
        layers.append({
            "name": f"{source_name} (Centroid)",
            "geom": None,
            "centroid": centroid,
            "color": color,
            "tooltip": tooltip_html,
            "area": 0.0,
            "layer_type": "centroid",
            "source_name": source_name,
            "layer_kind": "gt",
        })

    return layers


def build_llm_layers(
    mdl: str,
    selected_place: str,
    reference_gt: str,
    valid_df: pd.DataFrame,
    known_models: list[str],
    selected_runs: list[str],
    selected_variants: list[str],
) -> list[dict]:
    """Build a list of LLM layers (Polygon, BBox, Centroid)."""
    working_df = valid_df.copy()
    if "variant_id" not in working_df.columns:
        working_df["variant_id"] = "baseline_v2"
    else:
        working_df["variant_id"] = working_df["variant_id"].fillna(
            "baseline_v2").replace("", "baseline_v2")

    mask = (
        (working_df["source_a"] == mdl)
        & (working_df["source_b"] == reference_gt)
        & (working_df["variant_id"].isin(selected_variants))
        & (working_df["place"] == selected_place)
    )
    # [] means "all runs"; otherwise filter by run_id
    if selected_runs:
        mask = mask & working_df["run_id"].isin(selected_runs)
    mdl_rows = working_df[mask]
    if mdl_rows.empty:
        return []

    layers = []
    color = get_color_for_source(mdl, known_models, config.LLM_COLORS)
    from model_registry import display_name as model_display_name

    unique_run_variants = (
        mdl_rows[["run_id", "variant_id"]]
        .drop_duplicates()
        .sort_values(["run_id", "variant_id"])
        .itertuples(index=False, name=None)
    )
    for run_id, variant_id in unique_run_variants:
        run_row = mdl_rows[(mdl_rows["run_id"] == run_id) & (
            mdl_rows["variant_id"] == variant_id)].iloc[0]
        run_label = str(run_id).split("-")[-1]  # extract run1/run2/run3 suffix
        tooltip_base = f"<b>{model_display_name(mdl)}</b> ({run_label}… · {variant_id})"

        avg_iou = run_row.get("iou")
        de9im_str = run_row.get("de9im_label", "?")
        tooltip_metrics = ""
        if pd.notna(avg_iou):
            tooltip_metrics = f"<br>IoU: {avg_iou:.3f} | {de9im_str}"

        _meta = {
            "run_id": run_id,
            "variant_id": variant_id,
            "run_label": run_label,
            "model_id": mdl,
            "iou": avg_iou,
            "de9im_label": de9im_str,
            "layer_kind": "llm",
        }

        # Polygon (from WKT)
        first_wkt = run_row.get("geom_a") if "geom_a" in run_row else None
        if first_wkt and pd.notna(first_wkt):
            from shapely import wkt
            poly = wkt.loads(str(first_wkt))
            layers.append({
                "name": f"{mdl} ({run_label} {variant_id} Poly)",
                "geom": poly,
                "color": color,
                "weight": 2,
                "fill_opacity": 0.08,
                "tooltip": tooltip_base + tooltip_metrics,
                "area": poly.area,
                "layer_type": "poly",
                **_meta,
            })

        # BBox
        bbox_cols = config.BBOX_COLS_A
        if all(c in run_row for c in bbox_cols):
            b = run_row[bbox_cols]
            if not b.isna().any() and b["bbox_east_a"] > b["bbox_west_a"] and b["bbox_north_a"] > b["bbox_south_a"]:
                bbox_poly = box(b["bbox_west_a"], b["bbox_south_a"],
                                b["bbox_east_a"], b["bbox_north_a"])
                layers.append({
                    "name": f"{mdl} ({run_label} {variant_id} BBox)",
                    "geom": bbox_poly,
                    "color": color,
                    "weight": 1.5,
                    "fill_opacity": 0.0,
                    "tooltip": f"{tooltip_base} - Bounding Box{tooltip_metrics}",
                    "area": bbox_poly.area,
                    "layer_type": "bbox",
                    "dash_array": "5, 5",
                    **_meta,
                })

        # Centroid
        cx_col, cy_col = config.CENTROID_COLS_A
        if cx_col in run_row and cy_col in run_row:
            cx, cy = run_row[cx_col], run_row[cy_col]
            if pd.notna(cx) and pd.notna(cy):
                layers.append({
                    "name": f"{mdl} ({run_label} {variant_id} Centroid)",
                    "geom": None,
                    "centroid_xy": (cy, cx),
                    "color": color,
                    "tooltip": f"{tooltip_base} - Centroid{tooltip_metrics}",
                    "area": 0.0,
                    "layer_type": "centroid",
                    **_meta,
                })

    return layers


# ── Map renderer ───────────────────────────────────────────────────────────────

def render_folium_layers(layers: list[dict]) -> folium.Map:
    """Render layer dicts onto a Folium map and return it."""
    lat, lon = config.SF_CENTER
    zoom = config.SF_DEFAULT_ZOOM

    if not layers:
        return folium.Map(location=[lat, lon], zoom_start=zoom, tiles=config.BASEMAP_TILES)

    # Find first poly to fit bounds (prefer GT)
    first_poly = next((l for l in layers if l.get(
        "layer_type") == "poly" and l.get("geom")), None)
    if not first_poly:
        first_poly = next((l for l in layers if l.get("geom")), None)

    if first_poly and hasattr(first_poly["geom"], "bounds"):
        b = first_poly["geom"].bounds  # (west, south, east, north)
        m = folium.Map(tiles=config.BASEMAP_TILES)
        m.fit_bounds([[b[1], b[0]], [b[3], b[2]]])
    else:
        m = folium.Map(location=[lat, lon],
                       zoom_start=zoom, tiles=config.BASEMAP_TILES)

    for layer in layers:
        if layer.get("geom") is not None:
            folium.GeoJson(
                layer["geom"].__geo_interface__,
                style_function=lambda _, c=layer["color"], w=layer["weight"], fo=layer["fill_opacity"], da=layer.get("dash_array"): {
                    "color": c, "weight": w, "fillColor": c, "fillOpacity": fo, "dashArray": da,
                },
                highlight_function=lambda _: {
                    "weight": 4, "fillOpacity": 0.35},
                tooltip=folium.Tooltip(layer["tooltip"], sticky=True),
            ).add_to(m)

        if layer.get("centroid"):
            c = layer["centroid"]
            folium.CircleMarker(
                location=[c.y, c.x],
                radius=4, color=layer["color"], fill=True,
                fill_opacity=0.9, weight=2,
                tooltip=folium.Tooltip(layer["tooltip"], sticky=True),
            ).add_to(m)

        if layer.get("centroid_xy"):
            lat_c, lon_c = layer["centroid_xy"]
            folium.CircleMarker(
                location=[lat_c, lon_c],
                radius=4, color=layer["color"], fill=True,
                fill_opacity=0.8, weight=1,
                tooltip=folium.Tooltip(layer["tooltip"], sticky=True),
            ).add_to(m)

    return m


def _extract_geojson_from_layers(layers: list[dict]) -> dict | None:
    """Convert a list of folium layer dicts into a GeoJSON FeatureCollection payload."""
    features = []
    for lyr in layers:
        feature = {
            "type": "Feature",
            "properties": {
                "name": lyr["name"],
                "layer_type": lyr["layer_type"]
            },
            "geometry": None
        }
        if lyr.get("geom"):
            feature["geometry"] = lyr["geom"].__geo_interface__
            features.append(feature)
        elif lyr.get("centroid_xy") or lyr.get("centroid"):
            x, y = None, None
            if lyr.get("centroid_xy"):
                y, x = lyr["centroid_xy"]
            elif lyr.get("centroid"):
                x, y = lyr["centroid"].x, lyr["centroid"].y
            if x is not None and y is not None:
                feature["geometry"] = {"type": "Point", "coordinates": [x, y]}
                features.append(feature)

    if features:
        return {
            "type": "FeatureCollection",
            "features": features
        }
    return None


def _find_clicked_layer(map_data: dict | None, layers: list[dict]) -> dict | None:
    """Spatial-match the click coordinates to the topmost containing layer."""
    if not map_data:
        return None
    clicked = map_data.get("last_object_clicked")
    if not clicked or not isinstance(clicked, dict):
        return None
    lat = clicked.get("lat")
    lng = clicked.get("lng")
    if lat is None or lng is None:
        return None

    from shapely.geometry import Point
    click_pt = Point(lng, lat)  # x=lng, y=lat

    # Polygon/bbox layers: pick the smallest containing area (visually on top)
    containing = [
        lyr for lyr in layers
        if lyr.get("geom") is not None and lyr["geom"].contains(click_pt)
    ]
    if containing:
        return min(containing, key=lambda l: l["area"])

    # Centroid fallback: nearest within ~0.005° (~500 m)
    TOL = 0.005
    for lyr in layers:
        if lyr.get("centroid_xy"):
            lat_c, lng_c = lyr["centroid_xy"]
            if abs(lat - lat_c) < TOL and abs(lng - lng_c) < TOL:
                return lyr
        elif lyr.get("centroid"):
            c = lyr["centroid"]
            if abs(lat - c.y) < TOL and abs(lng - c.x) < TOL:
                return lyr

    return None


def _render_side_panel(layer: dict | None) -> None:
    """Render click-info panel for a single map layer."""
    if layer is None:
        st.caption("Click a layer on the map to see details here.")
        return

    layer_kind = layer.get("layer_kind", "")
    layer_type = layer.get("layer_type", "")

    type_label = {"poly": "Polygon", "bbox": "Bounding Box", "centroid": "Centroid"}.get(layer_type, layer_type)

    if layer_kind == "gt":
        source = layer.get("source_name", layer["name"])
        st.markdown(f"**{source}**")
        st.caption("Ground Truth")
        st.markdown(f"Geometry: **{type_label}**")

    elif layer_kind == "llm":
        from model_registry import display_name as model_display_name
        mdl = layer.get("model_id", "")
        run_id = layer.get("run_id", "")
        variant_id = layer.get("variant_id", "")
        iou = layer.get("iou")
        de9im = layer.get("de9im_label", "?")

        st.markdown(f"**{model_display_name(mdl)}**")
        st.caption("LLM Prediction")
        st.markdown(f"Geometry: **{type_label}**")
        st.markdown(f"Run: `{run_id}`")
        st.markdown(f"Variant: `{variant_id}`")
        if iou is not None and pd.notna(iou):
            st.metric("IoU", f"{iou:.3f}")
        if de9im and de9im != "?":
            st.markdown(f"DE-9IM: **{de9im}**")
    else:
        st.markdown(f"**{layer['name']}**")


def render_map_section(
    selected_place: str,
    reference_gt: str,
    active_gt_sources: list[str],
    active_llm_sources: list[str],
    known_models: list[str],
    df: pd.DataFrame,
    valid_df: pd.DataFrame,
    geom_toggles: dict[str, bool],
    selected_runs: list[int],
    selected_variants: list[str],
) -> None:
    """Build layers, sort by area, render map, and display via st_folium."""
    import json
    st.subheader(f"Map: {selected_place}")

    layers: list[dict] = []

    # GT layers
    for src_name in active_gt_sources:
        all_src_layers = build_gt_layers(
            src_name, selected_place, reference_gt, df, active_gt_sources)
        for lyr in all_src_layers:
            if geom_toggles.get(lyr["layer_type"], False):
                layers.append(lyr)

    # LLM layers
    for mdl in active_llm_sources:
        all_mdl_layers = build_llm_layers(
            mdl,
            selected_place,
            reference_gt,
            valid_df,
            known_models,
            selected_runs,
            selected_variants,
        )
        for lyr in all_mdl_layers:
            if geom_toggles.get(lyr["layer_type"], False):
                layers.append(lyr)

    # Sort largest → smallest so smaller polygons render on top
    layers.sort(key=lambda la: la["area"], reverse=True)

    m = render_folium_layers(layers)

    # Two-column layout: map (left) + info panel (right)
    map_col, info_col = st.columns([3, 1])

    with map_col:
        map_data = st_folium(
            m,
            width=None,  # fill the column
            height=config.MAP_H,
        )

    with info_col:
        st.markdown("**Layer Info**")
        clicked_layer = _find_clicked_layer(map_data, layers)
        _render_side_panel(clicked_layer)

    if layers:
        geojson_payload = _extract_geojson_from_layers(layers)
        if geojson_payload:
            st.download_button(
                label="📥 Download Map Layers as GeoJSON",
                data=json.dumps(geojson_payload, indent=2),
                file_name=f"{selected_place.replace(' ', '_')}_layers.geojson",
                mime="application/geo+json"
            )
