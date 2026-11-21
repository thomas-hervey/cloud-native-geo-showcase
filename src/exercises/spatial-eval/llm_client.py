"""LLM client for spatial bbox queries.

Uses LiteLLM so any provider (Anthropic, OpenAI, Gemini, Mistral, Groq)
works with the same interface. Responses are cached to disk to avoid
re-querying APIs on every analysis run.

Environment variables required (set whichever providers you use):
  ANTHROPIC_API_KEY
  OPENAI_API_KEY
  GEMINI_API_KEY
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from litellm import completion
from dotenv import load_dotenv

from config import LLM_RESPONSES_DIR, PLACES_JSON_PATH
from corpus import place_alias_lookup
from prompt_config import PROMPT_VERSION, SPATIAL_SYSTEM_PROMPT, build_bbox_user_prompt


def _find_and_load_env() -> None:
    """Walk up from this file looking for .env.local. Also checks the main
    repo root when running in a git worktree."""
    candidates: list[Path] = []

    # Walk up the tree
    current = Path(__file__).resolve().parent
    for _ in range(8):
        candidates.append(current / ".env.local")
        current = current.parent

    # If this is a git worktree, the .git file contains a pointer to the
    # common gitdir; the main repo root is two levels above it.
    worktree_root = Path(__file__).resolve().parent
    while worktree_root != worktree_root.parent:
        git_path = worktree_root / ".git"
        if git_path.exists():
            if git_path.is_file():
                # We're in a worktree — parse the gitdir line
                gitdir_line = git_path.read_text().strip()
                if gitdir_line.startswith("gitdir:"):
                    gitdir = Path(gitdir_line[len("gitdir:"):].strip())
                    # gitdir is like <main_repo>/.git/worktrees/<name>
                    # main repo root is .parent.parent.parent
                    main_repo_root = gitdir.parent.parent.parent
                    candidates.append(main_repo_root / ".env.local")
            break
        worktree_root = worktree_root.parent

    for candidate in candidates:
        if candidate.exists():
            load_dotenv(candidate, override=True)
            return


_find_and_load_env()


# SF bounding box for sanity check: no coordinate should be outside this
SF_BOUNDS = {"lat_min": 37.6, "lat_max": 37.95, "lon_min": -123.2, "lon_max": -122.2}

RESPONSES_DIR = LLM_RESPONSES_DIR
RESPONSES_DIR.mkdir(parents=True, exist_ok=True)

PLACES_JSON = PLACES_JSON_PATH

# Approximate token counts for cost estimation (shared with run_batch_eval)
_EST_INPUT_TOKENS = 300
_EST_OUTPUT_TOKENS_BBOX = 200
_EST_OUTPUT_TOKENS_POLY = 2000


def estimate_cost(models: list[str], n_calls_per_model: int, is_polygon: bool = False) -> list[tuple[str, float]]:
    """Return (model_id, estimated_usd) for each model.

    Shared utility used by run_batch_eval.py and the Streamlit experiments UI.
    Token estimates vary by experiment type (Polygon vs BBox).
    """
    from model_registry import load_models
    registry = {m["model_id"]: m for m in load_models()}
    rows = []
    out_est = _EST_OUTPUT_TOKENS_POLY if is_polygon else _EST_OUTPUT_TOKENS_BBOX
    for model_id in models:
        meta = registry.get(model_id, {})
        in_cost = float(meta.get("input_cost_per_1m", 0) or 0)
        out_cost = float(meta.get("output_cost_per_1m", 0) or 0)
        cost = n_calls_per_model * (
            _EST_INPUT_TOKENS / 1_000_000 * in_cost
            + out_est / 1_000_000 * out_cost
        )
        rows.append((model_id, cost))
    return rows


def parse_bbox_response(raw: str) -> dict[str, Any] | None:
    """Parse and validate an LLM bbox response string.

    Returns the parsed dict if valid, None if unparseable or impossible.
    """
    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    required = {"centroid_lat", "centroid_lon", "bbox_north", "bbox_south", "bbox_east", "bbox_west"}
    if not required.issubset(data.keys()):
        return None

    # Validate coordinate relationships
    if data["bbox_north"] <= data["bbox_south"]:
        return None
    if data["bbox_east"] <= data["bbox_west"]:
        return None

    # Validate within SF bounds
    b = SF_BOUNDS
    for lat_key in ("centroid_lat", "bbox_north", "bbox_south"):
        if not (b["lat_min"] <= data[lat_key] <= b["lat_max"]):
            return None
    for lon_key in ("centroid_lon", "bbox_east", "bbox_west"):
        if not (b["lon_min"] <= data[lon_key] <= b["lon_max"]):
            return None

    return data


def parse_geojson_polygon_response(raw: str) -> dict[str, Any] | None:
    """Parse and validate an LLM GeoJSON Polygon response string.

    Returns the parsed dict if valid, None if unparseable or impossible.
    """
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if "place" not in data or "geometry" not in data:
        return None

    geom = data["geometry"]
    if geom.get("type") != "Polygon" or "coordinates" not in geom:
        return None

    from shapely.geometry import shape
    try:
        poly = shape(geom)
    except Exception:
        return None

    if not poly.is_valid or poly.is_empty:
        return None

    bounds = poly.bounds
    return {
        "place": data["place"],
        "resolved_place": data.get("resolved_place", data["place"]),
        "confidence": data.get("confidence", "unknown"),
        "notes": data.get("notes", ""),
        "centroid_lat": poly.centroid.y,
        "centroid_lon": poly.centroid.x,
        "bbox_west": bounds[0],
        "bbox_south": bounds[1],
        "bbox_east": bounds[2],
        "bbox_north": bounds[3],
        "polygon_wkt": poly.wkt,
    }


_RUN_TAG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,31}$")


def validate_run_tag(run_tag: str) -> str:
    """Return run_tag unchanged if it is safe to use in run ids and paths.

    Raises:
        ValueError: if the tag is empty, too long, or contains path separators.
    """
    if not _RUN_TAG_PATTERN.match(run_tag):
        raise ValueError(
            f"Invalid run tag {run_tag!r}: use 1-32 letters, digits, '.', '_' or '-' (e.g. '2026-11')"
        )
    return run_tag


def responses_dir_for(run_tag: str | None = None) -> Path:
    """Return the LLM response cache directory for a run tag.

    Untagged runs use the shared cache (the original baseline). Tagged runs get
    their own subdirectory, so a re-run never reads or overwrites baseline
    responses.
    """
    if run_tag is None:
        return RESPONSES_DIR
    return RESPONSES_DIR / validate_run_tag(run_tag)


def tagged_run_id(model: str, gt_source: str, run: int, run_tag: str | None = None) -> str:
    """Build the comparisons.run_id for one model x GT source x run.

    Untagged ids keep the original format (``{model}-{gt}-run{n}``); tagged ids
    are prefixed (``{tag}:{model}-{gt}-run{n}``) so periods stay distinguishable.
    """
    base = f"{model}-{gt_source}-run{run}"
    return base if run_tag is None else f"{validate_run_tag(run_tag)}:{base}"


def _cache_path(
    place: str,
    model: str,
    run: int,
    prompt_variant_id: str | None = None,
    responses_dir: Path | None = None,
) -> Path:
    safe_place = place.lower().replace(" ", "_").replace("/", "-")
    safe_model = model.replace("/", "-").replace(":", "-")
    safe_variant = ""
    if prompt_variant_id:
        safe_variant = f"__variant-{prompt_variant_id.replace('/', '-').replace(':', '-')}"
    directory = responses_dir if responses_dir is not None else RESPONSES_DIR
    return directory / f"{safe_place}__{safe_model}__run{run}{safe_variant}.json"


def _extract_response_text(response: Any) -> str:
    """Extract text from LiteLLM responses across typed variants."""
    # Common object shape: response.choices[0].message.content
    choices = getattr(response, "choices", None)
    if choices:
        first = choices[0]
        message = getattr(first, "message", None)
        if message is not None:
            content = getattr(message, "content", "")
            return content if isinstance(content, str) else str(content)

    # Dict-like fallback (provider/SDK differences)
    if isinstance(response, dict):
        raw_choices = response.get("choices")
        if isinstance(raw_choices, list) and raw_choices:
            first = raw_choices[0]
            if isinstance(first, dict):
                msg = first.get("message")
                if isinstance(msg, dict):
                    content = msg.get("content", "")
                    return content if isinstance(content, str) else str(content)

    return ""


def query_model(
    place: str,
    model: str,
    run: int = 1,
    use_cache: bool = True,
    retry_count: int = 3,
    prompt_variant_id: str = "baseline_v2",
    user_prompt_override: str | None = None,
    system_prompt_override: str | None = None,
    responses_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Query an LLM for the bbox of a place, with disk caching.

    Args:
        place: Place name (e.g. "The Richmond").
        model: LiteLLM model string (e.g. "claude-haiku-4-5", "gpt-4o-mini").
        run: Run number (1-3) for repeated sampling.
        use_cache: Return cached result if it exists.
        retry_count: Number of retries if parse fails.
        responses_dir: Cache directory; defaults to the shared baseline cache.
            Use ``responses_dir_for(run_tag)`` for a tagged re-run.

    Returns:
        Parsed bbox dict, or None if all retries failed.
    """
    cache_file = _cache_path(
        place, model, run, prompt_variant_id=prompt_variant_id, responses_dir=responses_dir
    )
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    if use_cache and cache_file.exists():
        cached = json.loads(cache_file.read_text())
        cached["_cached"] = True
        return cached

    place_aliases = place_alias_lookup().get(place, [])
    prompt = user_prompt_override if user_prompt_override is not None else build_bbox_user_prompt(place, place_aliases)
    system_prompt = system_prompt_override if system_prompt_override is not None else SPATIAL_SYSTEM_PROMPT

    for attempt in range(retry_count):
        try:
            max_tokens = 16384 if prompt_variant_id == "geojson_polygon" else 8192
            response = completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=max_tokens,
            )
            raw = _extract_response_text(response)
            
            # Detect truncation
            finish_reason = None
            choices = getattr(response, "choices", None)
            if choices:
                finish_reason = getattr(choices[0], "finish_reason", None)
            
            if prompt_variant_id == "geojson_polygon":
                parsed = parse_geojson_polygon_response(raw)
                error_prefix = "GeoJSON Polygon"
            else:
                parsed = parse_bbox_response(raw)
                error_prefix = "bounding box"

            result = {
                "_model": model,
                "_place": place,
                "_run": run,
                "_raw": raw,
                "_valid": parsed is not None,
                "_attempt": attempt + 1,
                "_prompt_variant_id": prompt_variant_id,
                "_place_aliases": place_aliases,
                "_cached": False,
            }
            if parsed:
                result.update(parsed)
            else:
                if finish_reason == "length":
                    result["_error"] = f"Response truncated due to token limit ({max_tokens})"
                else:
                    result["_error"] = f"Failed to parse {error_prefix} from raw response"

            cache_file.write_text(json.dumps(result, indent=2))
            return result

        except Exception as e:
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)  # exponential backoff
            else:
                result = {"_valid": False, "_error": f"{type(e).__name__} - {e}", "_cached": False}
                cache_file.write_text(json.dumps(result))
                return result

    return None
