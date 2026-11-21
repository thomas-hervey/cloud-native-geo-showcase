"""Shared name-resolution utilities for GT sources.

Sources (OSM, Wikidata) index SF neighborhoods under different names than the
evaluation corpus uses (e.g. "The Mission" vs "Mission District"). This module
provides a single place to load and apply those per-source query overrides so
no source file hardcodes its own alias dict.

Config file: data/source_aliases.json
  Keys are corpus place names; values are dicts with source-keyed query strings.
  All 25 corpus places are listed explicitly so the file doubles as a review
  checklist. Use the Source Config tab in the Streamlit app to inspect and edit.

Usage:
    from sources.name_utils import load_source_aliases, clear_null_caches

    aliases = load_source_aliases("osm")        # {corpus_name: query_string}
    query   = aliases.get("The Mission", "The Mission")  # "Mission District"

    # After editing source_aliases.json, clear stale None caches:
    from pathlib import Path
    n = clear_null_caches([
        Path("data/reference/cache_osm"),
        Path("data/reference/cache_wikidata"),
    ])
    print(f"Cleared {n} stale cache files")
"""
from __future__ import annotations

import json
from pathlib import Path

_ALIASES_PATH = Path(__file__).parent.parent / "data" / "source_aliases.json"

# Module-level cache so the file is only read once per process.
_cache: dict[str, dict[str, str]] | None = None


def _load_raw() -> dict[str, dict[str, str]]:
    global _cache
    if _cache is None:
        raw = json.loads(_ALIASES_PATH.read_text())
        # Strip internal metadata keys that start with "_"
        _cache = {k: v for k, v in raw.items() if not k.startswith("_")}
    return _cache


def load_source_aliases(source: str) -> dict[str, str]:
    """Return a mapping of corpus_name → query_string for the given source.

    Args:
        source: Source key, e.g. "osm" or "wikidata".

    Returns:
        Dict where each value is the query string to use for that source.
        Places not listed in source_aliases.json are absent from the dict;
        callers should fall back to the raw corpus name via .get(place, place).
    """
    raw = _load_raw()
    return {
        place: overrides[source]
        for place, overrides in raw.items()
        if source in overrides and overrides[source] is not None
    }


def clear_null_caches(cache_dirs: list[Path]) -> int:
    """Delete cache files whose content is JSON null (failed lookups).

    Call this after editing source_aliases.json so that places that previously
    returned None are re-fetched with the corrected query string.

    Args:
        cache_dirs: List of cache directories to scan (e.g. cache_osm/, cache_wikidata/).

    Returns:
        Number of files deleted.
    """
    deleted = 0
    for cache_dir in cache_dirs:
        if not cache_dir.exists():
            continue
        for f in cache_dir.glob("*.json"):
            try:
                if json.loads(f.read_text()) is None:
                    f.unlink()
                    deleted += 1
                    print(f"[name_utils] cleared null cache: {f.name}")
            except (json.JSONDecodeError, OSError):
                pass
    return deleted
