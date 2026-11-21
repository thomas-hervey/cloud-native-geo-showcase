"""Centralized prompt configuration for spatial-eval LLM calls."""
from __future__ import annotations

PROMPT_VERSION = "v2-neighborhood-disambiguation"

SPATIAL_SYSTEM_PROMPT = """\
You are a careful geospatial analyst.

Your task is to identify the approximate neighborhood- or district-level geographic extent
of a named place in San Francisco, California.

Interpret the target as a San Francisco neighborhood, district, or locally recognized area.
Do not return a building, business, park feature, block, or single point of interest unless the
place itself is widely recognized as a neighborhood-scale area.

If the name is ambiguous, resolve it to the San Francisco neighborhood-level interpretation.
Use any provided alias hints to disambiguate. If the alias hints conflict, prefer the canonical
San Francisco neighborhood interpretation.

Return only valid JSON matching the requested schema.
"""

_BBOX_JSON_SCHEMA = """\
{{
  "place": "{place}",
  "resolved_place": "<the neighborhood or district name you actually used>",
  "centroid_lat": <decimal degrees>,
  "centroid_lon": <decimal degrees>,
  "bbox_north": <decimal degrees>,
  "bbox_south": <decimal degrees>,
  "bbox_east": <decimal degrees>,
  "bbox_west": <decimal degrees>,
  "confidence": "high" | "medium" | "low",
  "notes": "<brief disambiguation note if needed>"
}}
"""


def format_alias_hint(place: str, aliases: list[str]) -> str:
    """Return a compact alias hint line for the prompt."""
    clean_aliases = [alias.strip() for alias in aliases if alias and alias.strip() and alias.strip() != place]
    if not clean_aliases:
        return "No additional alias hints are available."
    return "Known aliases or nearby canonical references: " + ", ".join(clean_aliases) + "."


def build_bbox_user_prompt(place: str, aliases: list[str] | None = None) -> str:
    """Build the user prompt for neighborhood bbox extraction."""
    alias_hint = format_alias_hint(place, aliases or [])
    return """\
What are the approximate geographic bounding box coordinates of "{place}" in San Francisco, California?

Treat "{place}" as a neighborhood or district name in San Francisco.
{alias_hint}

Return the approximate neighborhood-level bounding box, not a landmark inside it.

Respond ONLY with a JSON object in this exact format:
{schema}

No explanation outside the JSON.
""".format(place=place, alias_hint=alias_hint, schema=_BBOX_JSON_SCHEMA.format(place=place))


_GEOJSON_JSON_SCHEMA = """\
{{
  "place": "{place}",
  "resolved_place": "<the neighborhood or district name you actually used>",
  "geometry": {{
    "type": "Polygon",
    "coordinates": [
      [
        [<lon>, <lat>],
        [<lon>, <lat>],
        [<lon>, <lat>],
        [<lon>, <lat>]
      ]
    ]
  }},
  "confidence": "high" | "medium" | "low",
  "notes": "<brief disambiguation note if needed>"
}}
"""


def build_geojson_user_prompt(place: str, aliases: list[str] | None = None) -> str:
    """Build the user prompt for neighborhood GeoJSON polygon extraction."""
    alias_hint = format_alias_hint(place, aliases or [])
    return """\
What is the approximate geographic shape of "{place}" in San Francisco, California?

Treat "{place}" as a neighborhood or district name in San Francisco.
{alias_hint}

Return the approximate neighborhood-level shape as a valid GeoJSON Polygon, not just a bounding box or a single point.
The Polygon coordinates must form a closed loop (the first and last coordinate pair must be identical).

Respond ONLY with a JSON object in this exact format:
{schema}

No explanation outside the JSON.
""".format(place=place, alias_hint=alias_hint, schema=_GEOJSON_JSON_SCHEMA.format(place=place))


_NEIGHBOR_JSON_SCHEMA = """\
{{
  "place": "{place}",
  "resolved_place": "<the neighborhood or district name you actually used>",
  "neighbors": [
    "<adjacent neighborhood name>",
    "<adjacent neighborhood name>"
  ],
  "confidence": "high" | "medium" | "low",
  "notes": "<brief note if needed>"
}}
"""


def build_neighbor_user_prompt(place: str, aliases: list[str] | None = None) -> str:
    """Build the user prompt for L2 neighbor adjacency experiments."""
    alias_hint = format_alias_hint(place, aliases or [])
    return """\
Which San Francisco neighborhoods share a direct border with "{place}"?

Treat "{place}" as a neighborhood or district name in San Francisco.
{alias_hint}

List only neighborhoods that physically touch the boundary of "{place}" — not
neighborhoods that are merely nearby or accessible by a short walk.

Respond ONLY with a JSON object in this exact format:
{schema}

No explanation outside the JSON.
""".format(place=place, alias_hint=alias_hint, schema=_NEIGHBOR_JSON_SCHEMA.format(place=place))