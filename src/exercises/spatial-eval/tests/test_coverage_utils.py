"""Unit tests for sources.coverage_utils.coverage_symbol."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from shapely.geometry import Point, Polygon


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_source(polygon=None, centroid=None, bbox=None):
    src = MagicMock()
    src.get_polygon.return_value = polygon
    src.get_centroid.return_value = centroid
    src.get_bbox.return_value = bbox
    return src


_SQUARE = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
_POINT  = Point(0.5, 0.5)
_BBOX   = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]) # Dummy for bbox


# ---------------------------------------------------------------------------
# Tests: polygon present
# ---------------------------------------------------------------------------

def test_returns_poly_icon_when_polygon_found():
    """⬠ when get_polygon returns a geometry, regardless of source type."""
    with patch("sources.coverage_utils.load_gt_source", return_value=_mock_source(polygon=_SQUARE)):
        from sources.coverage_utils import coverage_symbol
        assert "⬠" in coverage_symbol("sf_planning", "The Mission")


def test_returns_poly_icon_for_api_source_with_polygon():
    """⬠ even for API sources when a polygon is available."""
    with patch("sources.coverage_utils.load_gt_source", return_value=_mock_source(polygon=_SQUARE)):
        from sources.coverage_utils import coverage_symbol
        assert "⬠" in coverage_symbol("osm", "The Mission")


# ---------------------------------------------------------------------------
# Tests: point-only (API sources)
# ---------------------------------------------------------------------------

def test_returns_pin_when_api_source_has_centroid_only():
    """• for an API source that returns a centroid but no polygon."""
    with patch("sources.coverage_utils.load_gt_source", return_value=_mock_source(polygon=None, centroid=_POINT)):
        from sources.coverage_utils import coverage_symbol
        assert "•" in coverage_symbol("osm", "Mid-Market")
        assert "⬠" not in coverage_symbol("osm", "Mid-Market")


def test_returns_pin_for_osm_overpass_centroid_only():
    """• for osm_overpass when polygon is missing but centroid exists."""
    with patch("sources.coverage_utils.load_gt_source", return_value=_mock_source(polygon=None, centroid=_POINT)):
        from sources.coverage_utils import coverage_symbol
        assert "•" in coverage_symbol("osm_overpass", "Mid-Market")


def test_returns_pin_for_wikidata_centroid_only():
    """• for wikidata when polygon is missing but centroid exists."""
    with patch("sources.coverage_utils.load_gt_source", return_value=_mock_source(polygon=None, centroid=_POINT)):
        from sources.coverage_utils import coverage_symbol
        assert "•" in coverage_symbol("wikidata", "Chinatown")


# ---------------------------------------------------------------------------
# Tests: missing (—)
# ---------------------------------------------------------------------------

def test_returns_dash_when_local_source_has_no_polygon():
    """— for a local source with no polygon, point, or bbox."""
    mock_src = _mock_source(polygon=None, centroid=None, bbox=None)
    with patch("sources.coverage_utils.load_gt_source", return_value=mock_src):
        from sources.coverage_utils import coverage_symbol
        result = coverage_symbol("sf_planning", "The Panhandle")
    assert result == "—"


def test_returns_dash_when_api_source_has_no_geometries():
    """— for an API source with no geometries whatsoever."""
    with patch("sources.coverage_utils.load_gt_source", return_value=_mock_source(polygon=None, centroid=None, bbox=None)):
        from sources.coverage_utils import coverage_symbol
        assert coverage_symbol("osm", "Unknown Place") == "—"


def test_returns_multiple_icons_when_all_exist():
    """⬠ ⬚ • when all geometries are available."""
    mock_src = _mock_source(polygon=_SQUARE, centroid=_POINT, bbox=_BBOX)
    with patch("sources.coverage_utils.load_gt_source", return_value=mock_src):
        from sources.coverage_utils import coverage_symbol
        result = coverage_symbol("click_that_hood", "The Dogpatch")
    
    assert "⬠" in result
    assert "⬚" in result
    assert "•" in result
