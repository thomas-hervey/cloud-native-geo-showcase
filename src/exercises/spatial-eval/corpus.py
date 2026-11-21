"""Shared helpers for loading the evaluation corpus."""
from __future__ import annotations

import json

import config

PLACES_JSON = config.PLACES_JSON_PATH


def load_corpus(include_inactive: bool = False) -> list[dict]:
    """Load corpus place entries from places.json.

    Entries default to active unless `active: false` is explicitly set.
    """
    payload = json.loads(PLACES_JSON.read_text())
    places = payload.get("places", [])
    if include_inactive:
        return places
    return [place for place in places if place.get("active", True)]


def load_place_names(include_inactive: bool = False) -> list[str]:
    """Return corpus place names in file order."""
    return [place["name"] for place in load_corpus(include_inactive=include_inactive)]


def place_alias_lookup() -> dict[str, list[str]]:
    """Return a mapping of corpus place names to their aliases."""
    if not PLACES_JSON.exists():
        return {}
    payload = json.loads(PLACES_JSON.read_text())
    return {
        entry["name"]: entry.get("aliases", [])
        for entry in payload.get("places", [])
        if entry.get("name")
    }