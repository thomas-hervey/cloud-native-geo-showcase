"""Shared coverage-status logic for GT sources.

Used by audit_gt_coverage.py (CLI) and app.py (Streamlit coverage matrix).
"""
from __future__ import annotations

from geometry_source import load_gt_source

# API-based sources that support point-only detection.
# Local GeoJSON sources always return None from get_centroid when polygon is
# absent, so the pin symbol is only meaningful for these three.
_DEFAULT_API_SOURCES: frozenset[str] = frozenset({"osm", "osm_overpass", "wikidata"})


def get_gt_coverage(source_name: str, place: str) -> dict[str, bool]:
    """Return dict of availability for poly, bbox, and point."""
    try:
        src = load_gt_source(source_name)
        return {
            "poly": src.get_polygon(place) is not None,
            "bbox": src.get_bbox(place) is not None,
            "point": src.get_centroid(place) is not None
        }
    except Exception:
        return {"poly": False, "bbox": False, "point": False}


def coverage_symbol(
    source_name: str,
    place: str,
) -> str:
    """Return a string of icons representing available geometries."""
    status = get_gt_coverage(source_name, place)
    icons = []
    if status["poly"]: icons.append("⬠")
    if status["bbox"]: icons.append("⬚")
    if status["point"]: icons.append("•")
    return " ".join(icons) if icons else "—"
