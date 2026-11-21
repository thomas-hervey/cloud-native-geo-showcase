"""Tests for DuckDB-backed EvalDB — typed interface."""
from __future__ import annotations

import unittest.mock
from pathlib import Path

import pytest

from db_duckdb import EvalDB
from db_protocol import EvalDBProtocol
from models import ComparisonRecord, GroundTruthRecord


@pytest.fixture
def db(tmp_path: Path) -> EvalDB:
    return EvalDB(tmp_path / "test.duckdb")


def test_schema_creates_tables(db: EvalDB) -> None:
    tables = db.table_names()
    assert "comparisons" in tables
    assert "ground_truths" in tables


def test_valid_column_present_on_fresh_db(db: EvalDB) -> None:
    """valid must be in the DDL, not just added via ALTER TABLE."""
    with db._lock:
        cols = db._conn.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'comparisons'"
        ).fetchall()
    col_names = {c[0] for c in cols}
    assert "valid" in col_names


def test_insert_and_fetch_comparison(db: EvalDB) -> None:
    record = ComparisonRecord(
        run_id="run-001",
        place="Golden Gate Park",
        source_a="llm:claude-sonnet-4-6",
        source_b="sf_planning",
        variant_id="baseline_v2",
        question_type="bbox_identification",
        iou=0.72,
        composite_score=0.81,
        geom_a="POLYGON((0 0,1 0,1 1,0 1,0 0))",
        model_id="claude-sonnet-4-6",
    )
    db.insert_comparison(record)
    results = db.fetch_comparisons(place="Golden Gate Park")
    assert len(results) == 1
    assert results[0].iou == pytest.approx(0.72)
    assert results[0].source_a == "llm:claude-sonnet-4-6"


def test_fetch_returns_comparison_record_instances(db: EvalDB) -> None:
    db.insert_comparison(ComparisonRecord(
        run_id="run-001", place="The Mission",
        source_a="llm:gpt-4o", source_b="sf_planning",
    ))
    results = db.fetch_comparisons(place="The Mission")
    assert len(results) == 1
    assert isinstance(results[0], ComparisonRecord)


def test_cognitive_level_generated_column(db: EvalDB) -> None:
    db.insert_comparison(ComparisonRecord(
        run_id="run-002", place="Mission",
        source_a="llm:gpt-4o", source_b="sf_planning",
        question_type="topology_relation",
        model_id="gpt-4o",
    ))
    results = db.fetch_comparisons(place="Mission")
    assert results[0].cognitive_level == "L2"


def test_bbox_identification_maps_to_l1(db: EvalDB) -> None:
    db.insert_comparison(ComparisonRecord(
        run_id="run-003", place="Noe Valley",
        source_a="llm:gpt-4o", source_b="sf_planning",
        question_type="bbox_identification",
    ))
    results = db.fetch_comparisons(place="Noe Valley")
    assert results[0].cognitive_level == "L1"


def test_duplicate_insert_skipped_with_warning(db: EvalDB) -> None:
    record = ComparisonRecord(
        run_id="run-dupe", place="SoMa",
        source_a="llm:gpt-4o", source_b="sf_planning",
        variant_id="baseline_v2",
    )
    db.insert_comparison(record)
    import db_duckdb as db_module
    with unittest.mock.patch.object(db_module.logger, "warning") as mock_warn:
        db.insert_comparison(record)  # duplicate — must not raise
        mock_warn.assert_called_once()
        assert "Skipping duplicate" in mock_warn.call_args[0][0]
    # only one record stored
    results = db.fetch_comparisons(place="SoMa")
    assert len(results) == 1


def test_fetch_filter_by_variant_id(db: EvalDB) -> None:
    for variant in ("baseline_v2", "boundary_strict"):
        db.insert_comparison(ComparisonRecord(
            run_id=f"run-{variant}", place="Haight",
            source_a="llm:gpt-4o", source_b="sf_planning",
            variant_id=variant,
        ))
    results = db.fetch_comparisons(variant_id="boundary_strict")
    assert len(results) == 1
    assert results[0].variant_id == "boundary_strict"


def test_fetch_filter_by_variant_ids(db: EvalDB) -> None:
    for variant in ("baseline_v2", "boundary_strict", "l2_neighbors"):
        db.insert_comparison(ComparisonRecord(
            run_id=f"run-{variant}", place="Haight",
            source_a="llm:gpt-4o", source_b="sf_planning",
            variant_id=variant,
        ))
    results = db.fetch_comparisons(variant_ids=["baseline_v2", "l2_neighbors"])
    assert len(results) == 2


def test_fetch_filter_by_run_id(db: EvalDB) -> None:
    db.insert_comparison(ComparisonRecord(
        run_id="run-a", place="The Mission",
        source_a="llm:gpt-4o", source_b="sf_planning",
    ))
    db.insert_comparison(ComparisonRecord(
        run_id="run-b", place="The Richmond",
        source_a="llm:gpt-4o", source_b="sf_planning",
    ))
    results = db.fetch_comparisons(run_id="run-a")
    assert len(results) == 1
    assert results[0].run_id == "run-a"


def test_fetch_filter_by_cognitive_level(db: EvalDB) -> None:
    db.insert_comparison(ComparisonRecord(
        run_id="run-l1", place="The Mission",
        source_a="llm:gpt-4o", source_b="sf_planning",
        question_type="bbox_identification",
    ))
    db.insert_comparison(ComparisonRecord(
        run_id="run-l2", place="The Richmond",
        source_a="llm:gpt-4o", source_b="sf_planning",
        question_type="topology_relation",
    ))
    results = db.fetch_comparisons(cognitive_level="L2")
    assert len(results) == 1
    assert results[0].question_type == "topology_relation"


def test_get_experiment_coverage(db: EvalDB) -> None:
    for i, q_type in enumerate(("bbox_identification", "bbox_identification", "topology_relation")):
        db.insert_comparison(ComparisonRecord(
            run_id=f"run-cov-{i}", place="Mission",
            source_a="llm:gpt-4o", source_b="sf_planning",
            question_type=q_type,
        ))
    coverage = db.get_experiment_coverage()
    assert coverage.get("L1") == 2
    assert coverage.get("L2") == 1


def test_insert_and_fetch_ground_truth(db: EvalDB) -> None:
    record = GroundTruthRecord(
        place="Castro", source="sf_planning",
        geom_wkt="POLYGON((0 0,1 0,1 1,0 1,0 0))",
    )
    db.insert_ground_truth(record)
    results = db.fetch_ground_truths(place="Castro")
    assert len(results) == 1
    assert isinstance(results[0], GroundTruthRecord)
    assert results[0].source == "sf_planning"


def test_duckdb_satisfies_protocol(tmp_path: Path) -> None:
    db = EvalDB(tmp_path / "proto.duckdb")
    assert isinstance(db, EvalDBProtocol)
    db.close()
