"""Ground truth polygon loader for SF neighborhood evaluation.

Loads the official DataSF neighborhood boundaries and provides fuzzy name
matching so LLM-style names ("The Richmond") map to official names ("Inner Richmond").
"""
from __future__ import annotations

import json
from pathlib import Path
import geopandas as gpd
from shapely.geometry import shape, box
from shapely.geometry.base import BaseGeometry


DATA_DIR = Path(__file__).parent / "data" / "reference"
DATASF_PATH = DATA_DIR / "datasf_neighborhoods.geojson"


class GroundTruth:
    """Loads DataSF neighborhood polygons and resolves informal place names."""

    def __init__(self, datasf_path: Path = DATASF_PATH) -> None:
        self._gdf = gpd.read_file(datasf_path)
        # Normalize column names to lowercase
        self._gdf.columns = [c.lower() for c in self._gdf.columns]

    def get_polygon(self, place_name: str) -> BaseGeometry | None:
        """Return the official polygon for a place, or None if not found.

        Does case-insensitive substring matching against the 'nhood' column
        so informal names like 'The Richmond' match 'Inner Richmond'.
        """
        query = place_name.lower().strip()
        # Strip leading "the " for matching
        query = query.removeprefix("the ")

        col_lower = self._gdf["nhood"].str.lower()
        # Exact match first: prevents "mission" matching "Outer Mission", "Mission Bay"
        candidates = self._gdf[col_lower == query]
        if candidates.empty:
            # Substring fallback: handles "richmond" → "Inner Richmond" + "Outer Richmond"
            candidates = self._gdf[col_lower.str.contains(query, na=False, regex=False)]
        if candidates.empty:
            return None
        # Return union if multiple matches (e.g. Inner + Outer Richmond)
        return candidates.geometry.union_all()

    def get_bbox(self, place_name: str) -> dict[str, float] | None:
        """Return {north, south, east, west} bbox for a place, or None."""
        geom = self.get_polygon(place_name)
        if geom is None:
            return None
        minx, miny, maxx, maxy = geom.bounds
        return {"west": minx, "south": miny, "east": maxx, "north": maxy}

    def list_neighborhoods(self) -> list[str]:
        """Return all official neighborhood names."""
        return sorted(self._gdf["nhood"].tolist())
