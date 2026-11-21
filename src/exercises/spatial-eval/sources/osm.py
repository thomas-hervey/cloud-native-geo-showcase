"""OSM GT adapter — SF neighborhood boundaries via Nominatim + polygon_geojson."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests
from shapely.geometry import shape, Point
from shapely.geometry.base import BaseGeometry

from geometry_source import register_gt
from sources.name_utils import load_source_aliases

_CACHE_DIR = Path(__file__).parent.parent / "data" / "reference" / "cache_osm"
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_HEADERS = {"User-Agent": "sf-spatial-eval/1.0 (academic research; github.com/thomas-hervey)"}


@register_gt("osm")
class OSMSource:
    """SF neighborhood boundaries from OpenStreetMap via Nominatim search.

    Query strings are resolved via data/source_aliases.json so that corpus
    names like "The Mission" map to the OSM-indexed name "Mission District".
    Cache keys are based on the resolved query (not the raw corpus name) so
    updating an alias automatically triggers a fresh fetch.

    TODO: store the resolved OSM relation/way ID in cache metadata and surface
    it in the Source Config UI for one-click verification against osm.org.
    """

    name = "osm"
    source_type = "gt"

    def __init__(self) -> None:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._aliases: dict[str, str] = load_source_aliases("osm")

    def _cache_path(self, query: str) -> Path:
        safe = query.lower().replace(" ", "_").replace("/", "-")
        return _CACHE_DIR / f"{safe}.json"

    def _fetch(self, place: str) -> dict[str, Any] | None:
        query = self._aliases.get(place, place)
        cache = self._cache_path(query)
        if cache.exists():
            return json.loads(cache.read_text())

        params = {
            "q": f"{query}, San Francisco, California",
            "format": "geojson",
            "polygon_geojson": 1,
            "limit": 1,
        }
        try:
            time.sleep(1.1)  # Nominatim rate limit: max 1 req/sec
            r = requests.get(_NOMINATIM_URL, params=params,
                             headers=_HEADERS, timeout=20)
            r.raise_for_status()
            features = r.json().get("features", [])
            result = features[0] if features else None
            cache.write_text(json.dumps(result))
            return result
        except Exception as e:
            print(f"[osm] fetch failed for '{place}' (query: '{query}'): {e}")
            cache.write_text(json.dumps(None))
            return None

    def _get_geom(self, place: str) -> BaseGeometry | None:
        feature = self._fetch(place)
        if not feature:
            return None
        geom = feature.get("geometry")
        if not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
            return None
        return shape(geom)

    def get_polygon(self, place: str) -> BaseGeometry | None:
        return self._get_geom(place)

    def get_centroid(self, place: str) -> Point | None:
        poly = self.get_polygon(place)
        if poly:
            return poly.centroid

        feature = self._fetch(place)
        if not feature:
            return None

        geom = feature.get("geometry")
        if not geom:
            return None
        if geom.get("type") == "Point":
            coords = geom.get("coordinates", [])
            if len(coords) == 2:
                return Point(coords[0], coords[1])
        return None

    def get_bbox(self, place: str) -> dict[str, float] | None:
        poly = self.get_polygon(place)
        if poly is None:
            return None
        minx, miny, maxx, maxy = poly.bounds
        return {"west": minx, "south": miny, "east": maxx, "north": maxy}
