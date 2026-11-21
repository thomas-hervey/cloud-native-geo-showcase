"""Unit tests for WikidataSource point fallback behavior."""
from __future__ import annotations

from unittest.mock import patch

from shapely.geometry import Point, Polygon

from sources.wikidata import WikidataSource


def test_cache_path_uses_schema_version_suffix() -> None:
    src = WikidataSource()
    path = src._cache_path("Mid-Market")
    assert path.name.endswith("__v2.json")


def test_coord_point_parses_wkt_point() -> None:
    point = WikidataSource._coord_point("Point(-122.4194 37.7749)")
    assert point is not None
    assert isinstance(point, Point)
    assert round(point.x, 4) == -122.4194
    assert round(point.y, 4) == 37.7749


def test_coord_point_returns_none_for_invalid_or_non_point() -> None:
    assert WikidataSource._coord_point("not-a-geometry") is None
    assert WikidataSource._coord_point("LINESTRING (0 0, 1 1)") is None


def test_get_centroid_prefers_polygon_when_available() -> None:
    src = WikidataSource()
    poly = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])

    with patch.object(WikidataSource, "get_polygon", return_value=poly), patch.object(WikidataSource, "_fetch") as fetch:
        centroid = src.get_centroid("Any Place")

    assert centroid is not None
    assert isinstance(centroid, Point)
    assert centroid.x == 1 and centroid.y == 1
    fetch.assert_not_called()


def test_get_centroid_falls_back_to_p625_point_when_polygon_missing() -> None:
    src = WikidataSource()

    with patch.object(WikidataSource, "get_polygon", return_value=None), patch.object(
        WikidataSource,
        "_fetch",
        return_value={"geoshape": None, "coord_wkt": "Point(-122.4105 37.7822)"},
    ):
        centroid = src.get_centroid("Mid-Market")

    assert centroid is not None
    assert isinstance(centroid, Point)
    assert round(centroid.x, 4) == -122.4105
    assert round(centroid.y, 4) == 37.7822


def test_get_centroid_returns_none_when_no_polygon_or_coord() -> None:
    src = WikidataSource()

    with patch.object(WikidataSource, "get_polygon", return_value=None), patch.object(
        WikidataSource,
        "_fetch",
        return_value={"geoshape": None, "coord_wkt": None},
    ):
        centroid = src.get_centroid("Unknown")

    assert centroid is None
