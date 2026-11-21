"""Canonical data models for the spatial eval pipeline.

ComparisonRecord is the single source of truth for field names used by:
  - Both DB backends (DuckDB and SQLite)
  - All batch scripts
  - The Streamlit UI DataFrame

comparison_record_from_metrics() is the ONLY place where ComparisonMetrics
field names are translated to ComparisonRecord field names.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from metrics.spatial_comparison import ComparisonMetrics


class ComparisonRecord(BaseModel):
    """One row in the comparisons table. Field names match DuckDB column names."""

    # Identity
    run_id: str
    place: str
    source_a: str          # "llm:claude-sonnet-4-6" or "sf_planning"
    source_b: str = ""
    variant_id: str = "baseline_v2"
    question_type: str = "bbox_identification"

    # Populated by DuckDB GENERATED column on read; excluded from INSERT
    cognitive_level: str | None = None

    # Spatial metrics — field names match DuckDB schema exactly
    iou: float | None = None
    overlap_a: float | None = None        # intersection / area_a
    overlap_b: float | None = None        # intersection / area_b
    hausdorff_m: float | None = None
    centroid_err_m: float | None = None
    composite_score: float | None = None
    de9im_string: str | None = None
    de9im_label: str | None = None

    # Geometry (WKT strings)
    geom_a: str | None = None
    geom_b: str | None = None

    # L2 neighbor metrics
    neighbor_list_a: str | None = None    # JSON array string
    neighbor_list_b: str | None = None    # JSON array string
    neighbor_iou: float | None = None

    # Provenance
    model_id: str | None = None
    prompt_text: str | None = None
    raw_response: str | None = None
    confidence: str | None = None
    notes: str | None = None
    valid: bool = True
    created_at: datetime | None = None


class GroundTruthRecord(BaseModel):
    """One row in the ground_truths table."""

    place: str
    source: str
    geom_wkt: str
    created_at: datetime | None = None


def comparison_record_from_metrics(
    *,
    metrics: ComparisonMetrics | None,
    run_id: str,
    place: str,
    source_a: str,
    source_b: str,
    variant_id: str = "baseline_v2",
    question_type: str = "bbox_identification",
    geom_a: str | None = None,
    model_id: str | None = None,
    prompt_text: str | None = None,
    raw_response: str | None = None,
    notes: str | None = None,
    valid: bool = True,
) -> ComparisonRecord:
    """Build a ComparisonRecord from a ComparisonMetrics result.

    This is the ONLY place where ComparisonMetrics field names are translated
    to ComparisonRecord field names. When metrics is None (failed parse),
    all metric fields are None and valid should be False.

    Args:
        metrics: Output of compare_geometries(), or None for failed runs.
        run_id: Unique experiment identifier (UUID or timestamp string).
        place: Place name from corpus.
        source_a: LLM source ("llm:model-id") or GT source name.
        source_b: Reference GT source name.
        variant_id: Prompt variant identifier.
        question_type: Cognitive taxonomy question type.
        geom_a: WKT string of predicted geometry, or None.
        model_id: Model identifier string, or None.
        prompt_text: Full prompt text, or None.
        raw_response: Raw LLM response string, or None.
        notes: Error message or notes, or None.
        valid: Whether this result is valid for analysis.

    Returns:
        ComparisonRecord ready for insertion into either DB backend.
    """
    return ComparisonRecord(
        run_id=run_id,
        place=place,
        source_a=source_a,
        source_b=source_b,
        variant_id=variant_id,
        question_type=question_type,
        iou=metrics.iou if metrics else None,
        overlap_a=metrics.overlap_pct_a if metrics else None,
        overlap_b=metrics.overlap_pct_b if metrics else None,
        hausdorff_m=metrics.hausdorff_m if metrics else None,
        centroid_err_m=metrics.centroid_error_m if metrics else None,
        composite_score=metrics.composite if metrics else None,
        de9im_string=metrics.de9im if metrics else None,
        de9im_label=metrics.de9im_label if metrics else None,
        geom_a=geom_a,
        model_id=model_id,
        prompt_text=prompt_text,
        raw_response=raw_response,
        notes=notes,
        valid=valid,
    )
