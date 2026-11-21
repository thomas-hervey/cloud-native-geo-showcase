"""Unit tests for the OSM Overpass GT source adapter."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry


# ---------------------------------------------------------------------------
# Fixture: a minimal Overpass JSON response for a simple square polygon.
# The outer ring is a single way with 5 points (closed ring).
# ---------------------------------------------------------------------------
_SQUARE_WAY = {
    "type": "way",
    "ref": 1,
    "role": "outer",
    "geometry": [
        {"lat": 37.75, "lon": -122.45},
        {"lat": 37.76, "lon": -122.45},
        {"lat": 37.76, "lon": -122.44},
        {"lat": 37.75, "lon": -122.44},
        {"lat": 37.75, "lon": -122.45},  # closed
    ],
}

_OVERPASS_POLYGON_RESPONSE = {
    "elements": [
        {
            "type": "relation",
            "id": 123,
            "members": [_SQUARE_WAY],
            "tags": {"name": "Test Neighborhood", "boundary": "administrative"},
        }
    ]
}

_OVERPASS_EMPTY_RESPONSE = {"elements": []}


# ---------------------------------------------------------------------------
# Helper to avoid touching the real cache dir during tests
# ---------------------------------------------------------------------------
@pytest.fixture
def tmp_source(tmp_path, monkeypatch):
    """OsmOverpassSource with cache redirected to a temp directory."""
    import sources.osm_overpass as mod
    monkeypatch.setattr(mod, "_CACHE_DIR", tmp_path / "cache_osm_overpass")
    from sources.osm_overpass import OsmOverpassSource
    return OsmOverpassSource()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_get_polygon_returns_shapely_geometry(tmp_source):
    """A valid Overpass relation response produces a non-None BaseGeometry."""
    with patch("sources.osm_overpass.requests.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: _OVERPASS_POLYGON_RESPONSE,
        )
        mock_post.return_value.raise_for_status = lambda: None

        poly = tmp_source.get_polygon("Test Neighborhood")

    assert poly is not None
    assert isinstance(poly, BaseGeometry)
    assert poly.area > 0


def test_get_polygon_returns_none_when_no_elements(tmp_source):
    """An empty Overpass response returns None, not an error."""
    with patch("sources.osm_overpass.requests.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: _OVERPASS_EMPTY_RESPONSE,
        )
        mock_post.return_value.raise_for_status = lambda: None

        poly = tmp_source.get_polygon("Nonexistent Place")

    assert poly is None


def test_get_polygon_returns_none_on_network_error(tmp_source):
    """A requests exception returns None instead of propagating."""
    with patch("sources.osm_overpass.requests.post", side_effect=Exception("timeout")):
        poly = tmp_source.get_polygon("Anywhere")

    assert poly is None


def test_get_polygon_uses_cache_on_second_call(tmp_source, tmp_path):
    """Second call for the same place reads from cache, not the network."""
    with patch("sources.osm_overpass.requests.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: _OVERPASS_POLYGON_RESPONSE,
        )
        mock_post.return_value.raise_for_status = lambda: None

        tmp_source.get_polygon("Test Neighborhood")
        tmp_source.get_polygon("Test Neighborhood")  # second call

    assert mock_post.call_count == 1  # network called exactly once


def test_get_centroid_returns_point_for_valid_place(tmp_source):
    """get_centroid returns a Point when a polygon exists."""
    from shapely.geometry import Point
    with patch("sources.osm_overpass.requests.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: _OVERPASS_POLYGON_RESPONSE,
        )
        mock_post.return_value.raise_for_status = lambda: None

        centroid = tmp_source.get_centroid("Test Neighborhood")

    assert isinstance(centroid, Point)


def test_get_centroid_returns_none_when_no_polygon(tmp_source):
    """get_centroid returns None when no polygon exists."""
    with patch("sources.osm_overpass.requests.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: _OVERPASS_EMPTY_RESPONSE,
        )
        mock_post.return_value.raise_for_status = lambda: None

        centroid = tmp_source.get_centroid("Nowhere")

    assert centroid is None


def test_get_bbox_returns_dict_for_valid_place(tmp_source):
    """get_bbox returns a dict with west/south/east/north keys."""
    with patch("sources.osm_overpass.requests.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: _OVERPASS_POLYGON_RESPONSE,
        )
        mock_post.return_value.raise_for_status = lambda: None

        bbox = tmp_source.get_bbox("Test Neighborhood")

    assert bbox is not None
    assert set(bbox.keys()) == {"west", "south", "east", "north"}
    assert bbox["west"] < bbox["east"]
    assert bbox["south"] < bbox["north"]


def test_source_metadata():
    """OsmOverpassSource has correct name and source_type class attributes."""
    from sources.osm_overpass import OsmOverpassSource
    assert OsmOverpassSource.name == "osm_overpass"
    assert OsmOverpassSource.source_type == "gt"
