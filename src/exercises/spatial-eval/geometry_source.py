"""Unified GeometrySource protocol and GT source registry.

Any geometry source — GT dataset or LLM output — implements GeometrySource.
GT adapters are registered with @register_gt("name") and discovered via
load_gt_source("name") which lazy-imports the sources/ package.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable
from shapely.geometry import Point
from shapely.geometry.base import BaseGeometry


@runtime_checkable
class GeometrySource(Protocol):
    """Unified interface for any geometry source: GT dataset or LLM output."""

    name: str         # "click_that_hood", "osm", "claude-haiku-4-5", etc.
    source_type: str  # "gt" | "llm"

    def get_polygon(self, place: str) -> BaseGeometry | None: ...
    def get_centroid(self, place: str) -> Point | None: ...
    def get_bbox(self, place: str) -> dict[str, float] | None: ...


# Module-level registry — populated by @register_gt decorators at import time
GT_REGISTRY: dict[str, type[GeometrySource]] = {}


def _try_import_sources() -> None:
    try:
        import sources  # noqa: F401
    except ModuleNotFoundError:
        pass


def register_gt(name: str):
    """Decorator to register a GT source class under the given name."""
    def decorator(cls):
        GT_REGISTRY[name] = cls
        return cls
    return decorator


def load_gt_source(name: str) -> GeometrySource:
    """Instantiate a registered GT source by name.

    Lazy-imports the sources/ package on first call to trigger all
    @register_gt() decorators without circular imports.
    """
    _try_import_sources()
    if name not in GT_REGISTRY:
        available = sorted(k for k in GT_REGISTRY if not k.startswith("_"))
        raise KeyError(f"Unknown GT source: '{name}'. Available: {available}")
    return GT_REGISTRY[name]()


def list_gt_sources() -> list[str]:
    """Return sorted names of all registered GT sources."""
    _try_import_sources()
    return sorted(k for k in GT_REGISTRY if not k.startswith("_"))
