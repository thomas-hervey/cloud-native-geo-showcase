"""Wikidata GT adapter — SF neighborhood boundaries via P3896 geoshape."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests
from shapely.geometry import shape, Point
from shapely.geometry.base import BaseGeometry
from shapely import wkt

from geometry_source import register_gt
from sources.name_utils import load_source_aliases

_CACHE_DIR = Path(__file__).parent.parent / "data" / "reference" / "cache_wikidata"
_SPARQL_URL = "https://query.wikidata.org/sparql"
_CACHE_SCHEMA_VERSION = 2
_HEADERS = {
    "User-Agent": "sf-spatial-eval/1.0 (academic research; github.com/thomas-hervey)",
    "Accept": "application/sparql-results+json",
}

# TODO: store Wikidata QIDs in source_aliases.json (e.g. "wikidata_qid": "Q7469")
# and query by QID directly: wd:Q7469 wdt:P3896 ?geoshape
# This is more reliable than label matching since labels can change.
# QIDs can be added via the Source Config tab in the Streamlit app once looked up.
_SPARQL_TEMPLATE = """
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?item ?geoshape ?coord WHERE {{
  ?item wdt:P31/wdt:P279* wd:Q123705 .
  ?item wdt:P131 wd:Q62 .
    ?item (rdfs:label|skos:altLabel) "{label}"@en .
    OPTIONAL {{ ?item wdt:P3896 ?geoshape . }}
    OPTIONAL {{ ?item wdt:P625 ?coord . }}
}} LIMIT 1
"""


@register_gt("wikidata")
class WikidataSource:
    """SF neighborhood polygons from Wikidata P3896 geoshape property.

    **Coverage note (March 2026):** P3896 geoshape is set for 0/25 SF corpus
    neighborhoods on Wikidata. Most neighborhood items (e.g. Mission District
    Q7469) only have a GeoNames ID and a P625 coordinate location (point), not
    an area polygon. This source is retained for completeness and future
    coverage improvement, but expect near-zero results for SF neighborhoods.

    Alternatives to explore:
    - P625 (coordinate location): centroid point only, no polygon
    - GeoNames API: use the GeoNames ID from Wikidata to fetch a bounding box
    - OSM Overpass API: better SF neighborhood polygon coverage than Nominatim

    Label strings are resolved via data/source_aliases.json so that corpus
    names like "The Mission" map to the Wikidata-indexed label "Mission District".
    Cache keys are based on the resolved label (not the raw corpus name) so
    updating an alias automatically triggers a fresh fetch.

    TODO: migrate to QID-based queries (see _SPARQL_TEMPLATE comment above)
    once QIDs are populated in source_aliases.json.
    """

    name = "wikidata"
    source_type = "gt"

    def __init__(self) -> None:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._aliases: dict[str, str] = load_source_aliases("wikidata")

    def _cache_path(self, label: str) -> Path:
        safe = label.lower().replace(" ", "_").replace("/", "-")
        return _CACHE_DIR / f"{safe}__v{_CACHE_SCHEMA_VERSION}.json"

    def _fetch(self, place: str) -> dict[str, Any] | None:
        label = self._aliases.get(place, place)
        cache = self._cache_path(label)
        if cache.exists():
            payload = json.loads(cache.read_text())
            if isinstance(payload, dict):
                return payload

        try:
            time.sleep(1.0)
            sparql = _SPARQL_TEMPLATE.format(label=label.replace('"', '\\"'))
            r = requests.get(_SPARQL_URL,
                             params={"query": sparql, "format": "json"},
                             headers=_HEADERS, timeout=20)
            r.raise_for_status()
            bindings = r.json().get("results", {}).get("bindings", [])

            if not bindings:
                payload = {"geoshape": None, "coord_wkt": None}
                cache.write_text(json.dumps(payload))
                return payload

            row = bindings[0]
            geoshape_payload: dict[str, Any] | None = None
            if "geoshape" in row:
                geoshape_url = row["geoshape"]["value"]
                time.sleep(0.5)
                gr = requests.get(geoshape_url, headers=_HEADERS, timeout=15)
                gr.raise_for_status()
                geoshape_payload = gr.json()

            coord_wkt = row.get("coord", {}).get("value")
            payload = {
                "geoshape": geoshape_payload,
                "coord_wkt": coord_wkt,
            }
            cache.write_text(json.dumps(payload))
            return payload

        except Exception as e:
            print(f"[wikidata] fetch failed for '{place}' (label: '{label}'): {e}")
            payload = {"geoshape": None, "coord_wkt": None}
            cache.write_text(json.dumps(payload))
            return payload

    @staticmethod
    def _coord_point(coord_wkt: str | None) -> Point | None:
        if not coord_wkt:
            return None
        try:
            geom = wkt.loads(coord_wkt)
            if isinstance(geom, Point):
                return geom
        except Exception:
            return None
        return None

    def _get_geom(self, place: str) -> BaseGeometry | None:
        data = self._fetch(place)
        if not data:
            return None
        geoshape = data.get("geoshape") if isinstance(data, dict) else None
        if isinstance(data, dict) and "features" in data:
            # Legacy cache compatibility with old geoshape-only payload.
            geoshape = data
        if not geoshape:
            return None
        features = geoshape.get("features", [])
        if not features:
            return None
        geom = features[0].get("geometry")
        if not geom or geom.get("type") not in ("Polygon", "MultiPolygon"):
            return None
        return shape(geom)

    def get_polygon(self, place: str) -> BaseGeometry | None:
        return self._get_geom(place)

    def get_centroid(self, place: str) -> Point | None:
        poly = self.get_polygon(place)
        if poly:
            return poly.centroid
        data = self._fetch(place)
        if not data:
            return None
        coord_wkt = data.get("coord_wkt") if isinstance(data, dict) else None
        return self._coord_point(coord_wkt)

    def get_bbox(self, place: str) -> dict[str, float] | None:
        poly = self.get_polygon(place)
        if poly is None:
            return None
        minx, miny, maxx, maxy = poly.bounds
        return {"west": minx, "south": miny, "east": maxx, "north": maxy}
