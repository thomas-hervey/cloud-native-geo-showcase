"""ClickThatHood GT adapter — 37 SF neighborhood polygons."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry

from geometry_source import register_gt
from sources.name_utils import load_source_aliases

if TYPE_CHECKING:
    import geopandas as gpd

_DATA_PATH = Path(__file__).parent.parent / "data" / "reference" / "datasf_neighborhoods.geojson"


@register_gt("click_that_hood")
class ClickThatHoodSource:
    """SF neighborhoods from click_that_hood (37 polygons, 'nhood' column)."""

    name = "click_that_hood"
    source_type = "gt"

    def __init__(self) -> None:
        import geopandas as gpd
        self._gdf = gpd.read_file(_DATA_PATH)
        self._gdf.columns = [c.lower() for c in self._gdf.columns]
        self._aliases: dict[str, str] = load_source_aliases("click_that_hood")

    def _match(self, place: str) -> "gpd.GeoDataFrame":
        # Check if there's an alias for this corpus place name.
        # Normalize the alias the same way as the place: lowercase, strip, remove "the ".
        if place in self._aliases:
            query = self._aliases[place].lower().strip().removeprefix("the ")
        else:
            # No alias: use place name with "the " stripped, then lowercased.
            query = place.lower().strip().removeprefix("the ")
        col_lower = self._gdf["nhood"].str.lower()
        # Exact match first: prevents "mission" matching "Outer Mission", "Mission Bay"
        exact = self._gdf[col_lower == query]
        if not exact.empty:
            return exact
        # Substring fallback: handles "richmond" → "Inner Richmond" + "Outer Richmond"
        return self._gdf[col_lower.str.contains(query, na=False, regex=False)]

    def get_polygon(self, place: str) -> BaseGeometry | None:
        candidates = self._match(place)
        return candidates.geometry.union_all() if not candidates.empty else None

    def get_centroid(self, place: str) -> Point | None:
        poly = self.get_polygon(place)
        return poly.centroid if poly else None

    def get_bbox(self, place: str) -> dict[str, float] | None:
        poly = self.get_polygon(place)
        if poly is None:
            return None
        minx, miny, maxx, maxy = poly.bounds
        return {"west": minx, "south": miny, "east": maxx, "north": maxy}
