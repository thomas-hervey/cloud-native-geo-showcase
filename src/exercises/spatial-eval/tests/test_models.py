"""Tests for models.py — ComparisonRecord, GroundTruthRecord, converter."""
from __future__ import annotations

import pytest
from metrics.spatial_comparison import ComparisonMetrics
from models import ComparisonRecord, GroundTruthRecord, comparison_record_from_metrics

# The exact set of columns in the DuckDB INSERT (excludes server-computed fields)
_DB_INSERT_COLUMNS = {
    "run_id", "place", "source_a", "source_b", "variant_id", "question_type",
    "iou", "overlap_a", "overlap_b", "hausdorff_m", "centroid_err_m",
    "composite_score", "de9im_string", "de9im_label", "geom_a", "geom_b",
    "neighbor_list_a", "neighbor_list_b", "neighbor_iou",
    "model_id", "prompt_text", "raw_response", "confidence", "notes", "valid",
}

_FAKE_METRICS = ComparisonMetrics(
    iou=0.72,
    overlap_pct_a=0.85,
    overlap_pct_b=0.61,
    de9im="212101212",
    de9im_label="overlaps",
    hausdorff_m=123.4,
    centroid_error_m=56.7,
    composite=0.81,
)


def test_comparison_record_from_metrics_maps_all_fields() -> None:
    record = comparison_record_from_metrics(
        metrics=_FAKE_METRICS,
        run_id="run-001",
        place="The Mission",
        source_a="llm:gpt-4o",
        source_b="sf_planning",
    )
    # Verify every ComparisonMetrics field lands on the right ComparisonRecord field
    assert record.iou == pytest.approx(0.72)
    assert record.overlap_a == pytest.approx(0.85)        # overlap_pct_a → overlap_a
    assert record.overlap_b == pytest.approx(0.61)        # overlap_pct_b → overlap_b
    assert record.de9im_string == "212101212"              # de9im → de9im_string
    assert record.de9im_label == "overlaps"
    assert record.hausdorff_m == pytest.approx(123.4)
    assert record.centroid_err_m == pytest.approx(56.7)   # centroid_error_m → centroid_err_m
    assert record.composite_score == pytest.approx(0.81)  # composite → composite_score


def test_comparison_record_from_metrics_none_metrics() -> None:
    record = comparison_record_from_metrics(
        metrics=None,
        run_id="run-fail",
        place="The Mission",
        source_a="llm:gpt-4o",
        source_b="sf_planning",
        valid=False,
        notes="parse_failure",
    )
    assert record.valid is False
    assert record.notes == "parse_failure"
    # Identity fields are populated
    assert record.run_id == "run-fail"
    assert record.place == "The Mission"
    # All metric fields are None
    assert record.iou is None
    assert record.overlap_a is None
    assert record.composite_score is None
    assert record.de9im_string is None


def test_comparison_record_none_metrics_is_insertable() -> None:
    """A None-metrics record must pass Pydantic validation (no required metric fields)."""
    record = comparison_record_from_metrics(
        metrics=None,
        run_id="run-fail",
        place="The Mission",
        source_a="llm:gpt-4o",
        source_b="sf_planning",
        valid=False,
    )
    # Re-validate — must not raise
    ComparisonRecord.model_validate(record.model_dump())


def test_model_dump_keys_exactly_match_insert_columns() -> None:
    """Bidirectional check: model_dump() keys must exactly equal the INSERT column set.

    Catches both:
    - fields in the model not in the DB schema (would cause INSERT errors)
    - DB columns missing from the model (would cause silent data loss)
    """
    record = ComparisonRecord(run_id="x", place="y", source_a="z", source_b="w")
    actual = set(record.model_dump(exclude={"cognitive_level", "created_at"}).keys())
    assert actual == _DB_INSERT_COLUMNS, (
        f"Mismatch:\n"
        f"  Extra in model (not in DB): {actual - _DB_INSERT_COLUMNS}\n"
        f"  Missing from model (in DB):  {_DB_INSERT_COLUMNS - actual}"
    )


def test_ground_truth_record_fields() -> None:
    record = GroundTruthRecord(
        place="The Mission",
        source="sf_planning",
        geom_wkt="POLYGON((0 0,1 0,1 1,0 1,0 0))",
    )
    assert record.place == "The Mission"
    assert record.source == "sf_planning"
    assert record.created_at is None
