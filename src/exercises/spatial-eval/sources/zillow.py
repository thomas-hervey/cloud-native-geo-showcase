"""Zillow ZillowNeighborhoods GT adapter — consumer real-estate delineation."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from geometry_source import register_gt
from sources.name_utils import load_source_aliases

if TYPE_CHECKING:
    import geopandas as gpd

_DATA_PATH = Path(__file__).parent.parent / "data" / "reference" / "zillow_sf.geojson"
_DOWNLOAD_MSG = """
[zillow] Data file not found: data/reference/zillow_sf.geojson

Source: Zillow Neighborhood Boundaries for San Francisco (2017)
File: SF_Neighborhoods_2017_Zillow.geojson
Note: Zillow no longer distributes this file publicly. The project copy was
obtained from the 2017 ZillowNeighborhoods release. Contact the project
maintainer for a copy or use an alternative GT source.

zillow source will return None for all places until file is present.
"""

_NAME_CANDIDATES = ("name", "neighborhood", "regionname", "nhood", "label")


@register_gt("zillow")
class ZillowSource:
    """SF neighborhood boundaries from Zillow ZillowNeighborhoods (~2019)."""

    name = "zillow"
    source_type = "gt"

    def __init__(self) -> None:
        self._gdf: "gpd.GeoDataFrame | None" = None
        if _DATA_PATH.exists():
            import geopandas as gpd
            self._gdf = gpd.read_file(_DATA_PATH)
            self._gdf.columns = [c.lower() for c in self._gdf.columns]
        else:
            print(_DOWNLOAD_MSG)
        self._aliases: dict[str, str] = load_source_aliases("zillow")

    def _name_col(self) -> str:
        assert self._gdf is not None
        for col in _NAME_CANDIDATES:
            if col in self._gdf.columns:
                return col
        return self._gdf.select_dtypes(include="object").columns[0]

    def _match(self, place: str) -> "gpd.GeoDataFrame | None":
        if self._gdf is None:
            return None
        # If the JSON has an alias for this corpus name, use it directly.
        # Otherwise fall back to the corpus name with "the " stripped.
        if place in self._aliases:
            query = self._aliases[place].lower().strip()
        else:
            query = place.lower().strip().removeprefix("the ")
        col = self._name_col()
        col_lower = self._gdf[col].str.lower()
        # Exact match first: prevents "mission" matching "Outer Mission", "Mission Bay"
        exact = self._gdf[col_lower == query]
        if not exact.empty:
            return exact
        # Substring fallback: handles "richmond" → "Inner Richmond" + "Outer Richmond"
        return self._gdf[col_lower.str.contains(query, na=False, regex=False)]

    def get_polygon(self, place: str) -> BaseGeometry | None:
        candidates = self._match(place)
        if candidates is None or candidates.empty:
            return None
        return candidates.geometry.union_all()

    def get_centroid(self, place: str) -> Point | None:
        poly = self.get_polygon(place)
        return poly.centroid if poly else None

    def get_bbox(self, place: str) -> dict[str, float] | None:
        poly = self.get_polygon(place)
        if poly is None:
            return None
        minx, miny, maxx, maxy = poly.bounds
        return {"west": minx, "south": miny, "east": maxx, "north": maxy}
