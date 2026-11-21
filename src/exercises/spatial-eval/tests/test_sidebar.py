"""Tests for ui/sidebar.py — focuses on _llm_availability_status which has no
Streamlit dependency and operates purely on DataFrames."""
from __future__ import annotations

import pandas as pd
import pytest

from ui.sidebar import _llm_availability_status

MODEL = "llm:test-model"
PLACE = "Golden Gate Park"
GT = "osm"


def _base_row(**overrides) -> dict:
    """Minimal row with all geometry columns present and valid."""
    row = {
        "source_a": MODEL,
        "source_b": GT,
        "place": PLACE,
        "geom_a": "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))",
        "bbox_west_a": -122.5,
        "bbox_south_a": 37.7,
        "bbox_east_a": -122.4,
        "bbox_north_a": 37.8,
        "centroid_lon_a": -122.45,
        "centroid_lat_a": 37.75,
    }
    row.update(overrides)
    return row


def _df(*rows: dict) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


# ── No matching rows ─────────────────────────────────────────────────────────

def test_no_matching_rows_returns_all_false():
    df = _df(_base_row())
    result = _llm_availability_status("llm:other-model", PLACE, GT, df)
    assert result == {"poly": False, "bbox": False, "point": False}


# ── Missing columns (the bug that triggered these tests) ─────────────────────

def test_missing_bbox_cols_returns_bbox_false_no_exception():
    df = _df({
        "source_a": MODEL, "source_b": GT, "place": PLACE,
        "geom_a": "POLYGON((0 0,1 0,1 1,0 1,0 0))",
        "centroid_lon_a": -122.45, "centroid_lat_a": 37.75,
        # bbox columns absent (mirrors The Mission data)
    })
    result = _llm_availability_status(MODEL, PLACE, GT, df)
    assert result["bbox"] is False
    assert result["poly"] is True
    assert result["point"] is True


def test_missing_centroid_cols_returns_point_false_no_exception():
    df = _df({
        "source_a": MODEL, "source_b": GT, "place": PLACE,
        "geom_a": "POLYGON((0 0,1 0,1 1,0 1,0 0))",
        "bbox_west_a": -122.5, "bbox_south_a": 37.7,
        "bbox_east_a": -122.4, "bbox_north_a": 37.8,
        # centroid columns absent
    })
    result = _llm_availability_status(MODEL, PLACE, GT, df)
    assert result["point"] is False
    assert result["poly"] is True
    assert result["bbox"] is True


def test_missing_all_geometry_cols_returns_all_false_no_exception():
    df = _df({"source_a": MODEL, "source_b": GT, "place": PLACE})
    result = _llm_availability_status(MODEL, PLACE, GT, df)
    assert result == {"poly": False, "bbox": False, "point": False}


# ── Happy path ────────────────────────────────────────────────────────────────

def test_full_columns_all_valid_returns_all_true():
    df = _df(_base_row())
    result = _llm_availability_status(MODEL, PLACE, GT, df)
    assert result == {"poly": True, "bbox": True, "point": True}


def test_null_geom_a_returns_poly_false():
    df = _df(_base_row(geom_a=None))
    result = _llm_availability_status(MODEL, PLACE, GT, df)
    assert result["poly"] is False
    assert result["bbox"] is True
    assert result["point"] is True


def test_inverted_bbox_returns_bbox_false():
    """east <= west or north <= south means bbox is degenerate."""
    df = _df(_base_row(bbox_east_a=-122.6, bbox_west_a=-122.4))  # east < west
    result = _llm_availability_status(MODEL, PLACE, GT, df)
    assert result["bbox"] is False


def test_null_centroid_returns_point_false():
    df = _df(_base_row(centroid_lon_a=None))
    result = _llm_availability_status(MODEL, PLACE, GT, df)
    assert result["point"] is False


def test_filters_by_place_and_gt():
    """Rows for a different place or GT source must not contribute."""
    df = _df(
        _base_row(),
        _base_row(place="The Mission", geom_a=None),
        _base_row(source_b="google", geom_a=None),
    )
    result = _llm_availability_status(MODEL, PLACE, GT, df)
    assert result["poly"] is True  # only the first row matches
