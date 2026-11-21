"""LLMSource adapter — wraps an LLM model as a GeometrySource."""
from __future__ import annotations

import json
import config
from typing import Any
from shapely.geometry import box, Point
from shapely.geometry.base import BaseGeometry

from llm_client import query_model, responses_dir_for


class LLMSource:
    """Wraps an LLM model query as a GeometrySource for uniform comparison.

    Not registered in GT_REGISTRY — instantiated directly with model name.
    """

    source_type = "llm"

    def __init__(
        self,
        model: str,
        run: int = 1,
        use_cache: bool = True,
        variant_id: str = "baseline_v2",
        run_tag: str | None = None,
    ) -> None:
        """
        Args:
            run_tag: Optional evaluation period tag (e.g. "2026-11"). Tagged
                sources read and write their own cache subdirectory and never
                fall back to the untagged baseline cache.
        """
        self.name = model
        self._model = model
        self._run = run
        self._use_cache = use_cache
        self._variant_id = variant_id
        self._run_tag = run_tag
        self._responses_dir = responses_dir_for(run_tag)
        self._cache: dict[str, dict | None] = {}

    def _result(self, place: str) -> "dict[str, Any] | None":
        if place not in self._cache:
            if self._use_cache:
                # 1. Look for explicit variant match
                safe_place = place.lower().replace(" ", "_").replace("/", "-")
                safe_model = self._model.replace("/", "-").replace(":", "-")
                variant_path = self._responses_dir / f"{safe_place}__{safe_model}__run{self._run}__variant-{self._variant_id}.json"
                if variant_path.exists():
                    try:
                        self._cache[place] = json.loads(variant_path.read_text())
                        self._cache[place]["_cached"] = True
                        return self._cache[place]
                    except Exception:
                        pass
                
                # 2. Look for legacy baseline fallback if variant is baseline_v2
                if self._variant_id == "baseline_v2" and self._run_tag is None:
                    legacy_path = config.LLM_RESPONSES_DIR / f"{safe_place}__{safe_model}__run{self._run}.json"
                    if legacy_path.exists():
                        try:
                            self._cache[place] = json.loads(legacy_path.read_text())
                            self._cache[place]["_cached"] = True
                            return self._cache[place]
                        except Exception:
                            pass
            
            # 3. Fallback to API querying
            self._cache[place] = query_model(
                place,
                self._model,
                run=self._run,
                use_cache=self._use_cache,
                prompt_variant_id=self._variant_id,
                responses_dir=self._responses_dir,
            )
        return self._cache[place]

    def get_polygon(self, place: str) -> BaseGeometry | None:
        r = self._result(place)
        if r is None or not r.get("_valid"):
            return None
        if "polygon_wkt" in r:
            from shapely import wkt
            return wkt.loads(r["polygon_wkt"])
        return box(r["bbox_west"], r["bbox_south"], r["bbox_east"], r["bbox_north"])

    def get_centroid(self, place: str) -> Point | None:
        r = self._result(place)
        if r is None or not r.get("_valid"):
            return None
        return Point(r["centroid_lon"], r["centroid_lat"])

    def get_bbox(self, place: str) -> dict[str, float] | None:
        r = self._result(place)
        if r is None or not r.get("_valid"):
            return None
        return {"west": r["bbox_west"], "south": r["bbox_south"],
                "east": r["bbox_east"], "north": r["bbox_north"]}

    def was_cached(self, place: str) -> bool:
        r = self._result(place)
        if r is None:
            return False
        return r.get("_cached", False)
