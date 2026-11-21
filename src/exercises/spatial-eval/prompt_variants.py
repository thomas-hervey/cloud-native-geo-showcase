"""Curated prompt variants for admin-controlled prompt experiments."""
from __future__ import annotations

from dataclasses import dataclass

from prompt_config import build_bbox_user_prompt, build_geojson_user_prompt, build_neighbor_user_prompt


@dataclass(frozen=True)
class PromptVariant:
    variant_id: str
    label: str
    description: str
    guidance_suffix: str = ""


DEFAULT_PROMPT_VARIANTS: list[PromptVariant] = [
    PromptVariant(
        variant_id="baseline_v2",
        label="Baseline v2",
        description="Current production prompt behavior.",
        guidance_suffix="",
    ),
    PromptVariant(
        variant_id="boundary_strict",
        label="Boundary Strict",
        description="Prioritize neighborhood boundary extents over broad district spillover.",
        guidance_suffix=(
            "Bias toward conservative neighborhood boundaries. "
            "Avoid including adjacent neighborhoods unless strongly implied by local usage."
        ),
    ),
    PromptVariant(
        variant_id="alias_explicit",
        label="Alias Explicit",
        description="Force explicit alias reconciliation before choosing bbox.",
        guidance_suffix=(
            "Explicitly reconcile the canonical place name with provided aliases before returning coordinates. "
            "If aliases disagree, explain the chosen interpretation briefly in notes."
        ),
    ),
    PromptVariant(
        variant_id="geojson_polygon",
        label="GeoJSON Polygon",
        description="Ask the LLM for a detailed GeoJSON Polygon of the neighborhood instead of a bounding box.",
        guidance_suffix="Ensure the geometry is a valid GeoJSON Polygon that closely matches the neighborhood's true complex shape.",
    ),
    PromptVariant(
        variant_id="l2_neighbors",
        label="L2: Neighbor Adjacency",
        description="Ask the LLM which neighborhoods share a border with the target place.",
        guidance_suffix="",
    ),
]


def variant_by_id(variant_id: str) -> PromptVariant | None:
    for variant in DEFAULT_PROMPT_VARIANTS:
        if variant.variant_id == variant_id:
            return variant
    return None


def build_variant_user_prompt(place: str, aliases: list[str], variant_id: str) -> str:
    """Build the full user prompt for a selected variant."""
    variant = variant_by_id(variant_id)
    if variant_id == "geojson_polygon":
        base_prompt = build_geojson_user_prompt(place, aliases)
    elif variant_id == "l2_neighbors":
        base_prompt = build_neighbor_user_prompt(place, aliases)
    else:
        base_prompt = build_bbox_user_prompt(place, aliases)

    if variant is None or not variant.guidance_suffix:
        return base_prompt
    return f"{base_prompt}\n\nAdditional guidance for this experiment variant:\n{variant.guidance_suffix}"
