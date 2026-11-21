"""OSM Overpass API GT adapter — boundary relations for SF neighborhoods.

Unlike the Nominatim-based `osm` source which often returns Points for SF
neighborhoods, this source queries the Overpass API directly for relation
boundaries tagged as administrative areas or neighbourhoods.

Query strategy: union of two relation filters within the SF bounding box:
  1. boundary=administrative (city/district admin boundaries)
  2. place=neighbourhood    (OSM neighbourhood relations)

Geometry is assembled from outer-role member ways using shapely.ops.polygonize,
which correctly handles multi-way outer rings (where a single outer boundary is
split across several way segments).

Cache: data/reference/cache_osm_overpass/{safe_query}.json (raw Overpass JSON)

COVERAGE NOTE (2026-03-11):
Current polygon coverage is 5/25 SF neighborhoods. Most SF neighborhoods are
stored in OSM as point nodes (node type, not relation/way), so Overpass boundary
queries return no geometry for them. This is a fundamental OSM data gap, not a
naming issue.

TODO — improve neighborhood polygon coverage:
  1. Manual OSM edits: contribute boundary relations for missing neighborhoods
     (see https://www.openstreetmap.org for each neighborhood).
  2. Overture Foundation Maps: the `divisions` layer (formerly `places`) includes
     neighborhood polygons derived from multiple authoritative sources. Available
     as GeoParquet via AWS/Azure — see https://overturemaps.org/download/.
     This would likely give near-complete coverage and is the recommended next
     step for production use.
  3. SF OpenData: datasf.org has "SF Find Neighborhoods" as a polygon dataset
     (already partially in use via sf_planning.geojson). Could serve as a
     canonical local source for missing neighborhoods.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import polygonize, unary_union

from geometry_source import register_gt
from sources.name_utils import load_source_aliases

_CACHE_DIR = Path(__file__).parent.parent / "data" / "reference" / "cache_osm_overpass"
_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_HEADERS = {"User-Agent": "sf-spatial-eval/1.0 (academic research; github.com/thomas-hervey)"}

# SF bounding box: south, west, north, east (Overpass bbox order)
_SF_BBOX = "(37.70,-122.55,37.85,-122.35)"


@register_gt("osm_overpass")
class OsmOverpassSource:
    """SF neighborhood boundaries from OSM via Overpass API boundary relations.

    Queries name=* tag directly against OSM relation data within the SF
    bounding box. Returns Polygon/MultiPolygon assembled from outer-role
    member ways. Coverage is significantly better than Nominatim for SF
    neighborhoods that OSM stores as relations rather than named nodes.
    """

    name = "osm_overpass"
    source_type = "gt"

    def __init__(self) -> None:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._aliases: dict[str, str] = load_source_aliases("osm_overpass")

    def _cache_path(self, query: str) -> Path:
        safe = query.lower().replace(" ", "_").replace("/", "-").replace("'", "")
        return _CACHE_DIR / f"{safe}.json"

    def _build_overpass_query(self, name: str) -> str:
        escaped = name.replace('"', '\\"')
        return (
            f'[out:json][timeout:25];'
            f'('
            f'  relation["boundary"="administrative"]["name"="{escaped}"]{_SF_BBOX};'
            f'  relation["place"="neighbourhood"]["name"="{escaped}"]{_SF_BBOX};'
            f'  way["place"="neighbourhood"]["name"="{escaped}"]{_SF_BBOX};'
            f'  way["place"="quarter"]["name"="{escaped}"]{_SF_BBOX};'
            f');'
            f'out geom;'
        )

    def _fetch(self, place: str) -> list[dict[str, Any]] | None:
        """Return the Overpass elements list (cached), or None on failure."""
        query_name = self._aliases.get(place, place)
        cache = self._cache_path(query_name)

        if cache.exists():
            cached = json.loads(cache.read_text())
            return cached  # may be None (cached failure) or list

        query = self._build_overpass_query(query_name)
        try:
            time.sleep(1.0)  # be polite to the public Overpass instance
            r = requests.post(_OVERPASS_URL, data={"data": query},
                              headers=_HEADERS, timeout=30)
            r.raise_for_status()
            elements = r.json().get("elements", [])
            cache.write_text(json.dumps(elements))
            return elements
        except Exception as e:
            print(f"[osm_overpass] fetch failed for '{place}' "
                  f"(query name: '{query_name}'): {e}")
            cache.write_text(json.dumps(None))
            return None

    @staticmethod
    def _parse_relation(element: dict[str, Any]) -> BaseGeometry | None:
        """Assemble a Polygon/MultiPolygon from an Overpass relation element.

        Uses polygonize() on all outer-role member ways so that multi-segment
        outer rings (a common OSM pattern) are assembled correctly.
        """
        outer_ways = [
            m for m in element.get("members", [])
            if m.get("role") == "outer" and "geometry" in m
        ]
        if not outer_ways:
            return None

        lines = []
        for way in outer_ways:
            coords = [(p["lon"], p["lat"]) for p in way["geometry"]]
            if len(coords) >= 2:
                lines.append(LineString(coords))

        polys = list(polygonize(lines))
        if not polys:
            return None
        return unary_union(polys)

    @staticmethod
    def _parse_way(element: dict[str, Any]) -> BaseGeometry | None:
        """Build a Polygon from a closed Overpass way element.

        Overpass way geometry is a list of {lat, lon} dicts. A closed way
        (first == last node) forms a valid polygon ring.
        """
        coords_raw = element.get("geometry", [])
        if len(coords_raw) < 4:
            return None
        coords = [(p["lon"], p["lat"]) for p in coords_raw]
        if coords[0] != coords[-1]:
            coords.append(coords[0])  # close the ring
        try:
            poly = Polygon(coords)
            return poly if poly.is_valid else poly.buffer(0)
        except Exception:
            return None

    def _get_geom(self, place: str) -> BaseGeometry | None:
        elements = self._fetch(place)
        if not elements:
            return None
        geoms: list[BaseGeometry] = []
        for el in elements:
            if el.get("type") == "relation":
                g = self._parse_relation(el)
            elif el.get("type") == "way":
                g = self._parse_way(el)
            else:
                g = None
            if g is not None:
                geoms.append(g)
        if not geoms:
            return None
        return unary_union(geoms)

    def get_polygon(self, place: str) -> BaseGeometry | None:
        return self._get_geom(place)

    def get_centroid(self, place: str) -> Point | None:
        poly = self.get_polygon(place)
        return poly.centroid if poly else None

    def get_bbox(self, place: str) -> dict[str, float] | None:
        poly = self.get_polygon(place)
        if poly is None:
            return None
        minx, miny, maxx, maxy = poly.bounds
        return {"west": minx, "south": miny, "east": maxx, "north": maxy}
