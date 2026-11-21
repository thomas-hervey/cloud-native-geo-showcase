"""Centralized configuration for the spatial-eval exercise.

All path constants, map defaults, UI settings, and color palettes live here.
Every other module (app.py, llm_client.py, corpus.py, ui/, scripts/) imports
from this module rather than re-declaring these values locally.

To extend the eval framework:
  - Add a new model color → COLOR_MAP
  - Add a new GT source ordering → GT_UI_ORDER
  - Change the map viewport → SF_CENTER, SF_DEFAULT_ZOOM
  - Update display strings → METRIC_EXPLANATIONS
"""
from __future__ import annotations

from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
ALIASES_PATH = DATA_DIR / "source_aliases.json"
CACHE_OSM = DATA_DIR / "reference" / "cache_osm"
CACHE_WIKIDATA = DATA_DIR / "reference" / "cache_wikidata"
LLM_RESPONSES_DIR = DATA_DIR / "llm_responses"
PLACES_JSON_PATH = DATA_DIR / "places.json"
MODELS_JSON_PATH = DATA_DIR / "models.json"
RESULTS_DB_PATH = DATA_DIR / "results.db"
DUCKDB_PATH = DATA_DIR / "eval.duckdb"

# ── Map defaults ──────────────────────────────────────────────────────────────
SF_CENTER = (37.77, -122.44)   # (lat, lon)
SF_DEFAULT_LAT, SF_DEFAULT_LON = SF_CENTER
SF_DEFAULT_ZOOM = 13
MAP_W, MAP_H = 900, 520
METRES_PER_DEG: float = 111_320  # approximate metres per degree at equator

# ── UI / display settings ─────────────────────────────────────────────────────
PRIMARY_GT_SOURCE = "sf_planning"

# Folium built-in basemap. OpenStreetMap needs no API key; CARTO's
# basemaps.cartocdn.com tiles now render an "API KEY REQUIRED" watermark.
BASEMAP_TILES = "OpenStreetMap"
EXCLUDED_GT_SOURCES: set[str] = set()
# Legacy model runs to suppress from the UI (not removed from DB)
EXCLUDED_MODELS: set[str] = {"groq/llama-3.1-8b-instant"}
# Number of LLM model layer checkboxes that default to ON
NUM_DEFAULT_MODELS = 3
# Preferred display order for GT sources in the sidebar
GT_UI_ORDER: list[str] = [
    "sf_planning",
    "click_that_hood",
    "osm",
    "osm_overpass",
    "zillow",
    "wikidata",
]

# ── Color palettes ─────────────────────────────────────────────────────────────
# Index-based fallbacks when a source/model is not in COLOR_MAP
GT_COLORS: list[str] = ["#2166ac", "#4dac26", "#d01c8b", "#f1b6da", "#f0c419"]
LLM_COLORS: list[str] = ["#e41a1c", "#ff7f00", "#a65628", "#984ea3", "#f781bf", "#999999", "#ffff33"]

# Explicit per-source/model color assignments.
# Add new model colors here — emoji is derived automatically (see COLOR_EMOJI below).
COLOR_MAP: dict[str, str] = {
    # GT sources
    "sf_planning":      "#2166ac",  # blue
    "click_that_hood":  "#4dac26",  # green
    "osm":              "#d01c8b",  # purple/magenta
    "osm_overpass":     "#f1b6da",  # pink
    "zillow":           "#f0c419",  # yellow
    # LLM models
    # (extend as new models are benchmarked — add here AND in data/models.json)
}

# Emoji indicators derived from COLOR_MAP entries.
# This dict is built at import time so adding a color above just requires
# adding its emoji here — only one place to update.
COLOR_EMOJI: dict[str, str] = {
    "#2166ac": "🔵",   # blue          (sf_planning)
    "#4dac26": "🟢",   # green         (click_that_hood)
    "#d01c8b": "🟣",   # purple/magenta (osm)
    "#f1b6da": "🌸",   # pink          (osm_overpass)
    "#f0c419": "🟨",   # yellow        (zillow)
    "#e41a1c": "🔴",   # red
    "#ff7f00": "🟠",   # orange
    "#a65628": "🟫",   # brown
    "#984ea3": "🟪",   # purple
    "#f781bf": "🌷",   # pink/tulip
    "#999999": "⚪",   # gray
    "#ffff33": "🟨",   # yellow
}

# ── Metric help text ──────────────────────────────────────────────────────────
METRIC_EXPLANATIONS: dict[str, str] = {
    "llm": (
        "**IoU** (Intersection over Union, 0–1): How much the bounding boxes overlap. "
        "**Centroid Error** (meters): Distance between predicted and actual neighborhood centers. "
        "**Composite**: Weighted average of all metrics. Higher is better for all."
    ),
    "gt": (
        "**IoU** (0–1): Overlap between two ground truth sources. "
        "Low values indicate places with ambiguous or contested boundaries. "
        "**DE-9IM**: Topological relationship (e.g., 'overlaps', 'contains')."
    ),
    "heatmap": (
        "**IoU** (intersection over union) per model (row) and place (column), averaged across runs. "
        "Intersection over union is the area of overlap between the predicted and reference "
        "bounding boxes, divided by the area of their union. "
        "🟩 Green = high agreement (>0.6). 🟥 Red = poor agreement (<0.3). "
        "Models and places with low heatmap coverage may indicate incomplete evaluation."
    ),
    "leaderboard": (
        "Global average rankings across all places, plus Bradley-Terry pairwise ranking. "
        "BT skill score (log scale, higher = better) reflects relative model performance from "
        "head-to-head comparisons on shared places. Point estimates only — collect more data "
        "for reliable ranking. Coverage Grid shows run counts per model x place."
    ),
    "config": (
        "Verify that each data source maps the corpus place name correctly. "
        "Green checkmarks (✅) indicate cached/verified results; "
        "⏳ means the source hasn't been queried yet."
    ),
}

# ── DataFrame column name constants ──────────────────────────────────────────
BBOX_COLS_A: list[str] = ["bbox_west_a", "bbox_south_a", "bbox_east_a", "bbox_north_a"]
CENTROID_COLS_A: list[str] = ["centroid_lon_a", "centroid_lat_a"]
MATRIX_HEATMAP_CELL_TRUNCATE: int = 36
