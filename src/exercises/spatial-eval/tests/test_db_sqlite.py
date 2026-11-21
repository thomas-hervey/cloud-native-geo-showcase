"""Tests for SQLite-backed ResultsDB — typed interface (mirrors test_db_duckdb.py)."""
from __future__ import annotations

from pathlib import Path

import pytest

from db import ResultsDB
from db_protocol import EvalDBProtocol
from models import ComparisonRecord, GroundTruthRecord


@pytest.fixture
def db(tmp_path: Path) -> ResultsDB:
    return ResultsDB(tmp_path / "test.db")


def test_schema_creates_tables(db: ResultsDB) -> None:
    with db._lock:
        tables = {row[0] for row in db._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert "comparisons" in tables
    assert "ground_truths" in tables


def test_insert_and_fetch_comparison(db: ResultsDB) -> None:
    record = ComparisonRecord(
        run_id="run-001",
        place="Golden Gate Park",
        source_a="llm:gpt-4o",
        source_b="sf_planning",
        iou=0.72,
        composite_score=0.81,
    )
    db.insert_comparison(record)
    results = db.fetch_comparisons(place="Golden Gate Park")
    assert len(results) == 1
    assert results[0].iou == pytest.approx(0.72)
    assert results[0].source_a == "llm:gpt-4o"


def test_fetch_returns_comparison_record_instances(db: ResultsDB) -> None:
    db.insert_comparison(ComparisonRecord(
        run_id="run-001", place="The Mission",
        source_a="llm:gpt-4o", source_b="sf_planning",
    ))
    results = db.fetch_comparisons(place="The Mission")
    assert isinstance(results[0], ComparisonRecord)


def test_run_id_stored_on_insert(db: ResultsDB) -> None:
    db.insert_comparison(ComparisonRecord(
        run_id="exp-20260320", place="The Mission",
        source_a="llm:gpt-4o", source_b="sf_planning",
    ))
    results = db.fetch_comparisons(run_id="exp-20260320")
    assert len(results) == 1
    assert results[0].run_id == "exp-20260320"


def test_fetch_filter_by_run_id(db: ResultsDB) -> None:
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


def test_fetch_filter_by_variant_ids(db: ResultsDB) -> None:
    for variant in ("baseline_v2", "boundary_strict"):
        db.insert_comparison(ComparisonRecord(
            run_id=f"run-{variant}", place="Haight",
            source_a="llm:gpt-4o", source_b="sf_planning",
            variant_id=variant,
        ))
    results = db.fetch_comparisons(variant_ids=["baseline_v2"])
    assert len(results) == 1


def test_fetch_filter_by_cognitive_level(db: ResultsDB) -> None:
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


def test_get_experiment_coverage(db: ResultsDB) -> None:
    for i, q_type in enumerate(("bbox_identification", "bbox_identification", "topology_relation")):
        db.insert_comparison(ComparisonRecord(
            run_id=f"run-cov-{i}", place="Mission",
            source_a="llm:gpt-4o", source_b="sf_planning",
            question_type=q_type,
        ))
    coverage = db.get_experiment_coverage()
    assert coverage.get("L1") == 2
    assert coverage.get("L2") == 1


def test_insert_and_fetch_ground_truth(db: ResultsDB) -> None:
    record = GroundTruthRecord(
        place="Castro", source="sf_planning",
        geom_wkt="POLYGON((0 0,1 0,1 1,0 1,0 0))",
    )
    db.insert_ground_truth(record)
    results = db.fetch_ground_truths(place="Castro")
    assert len(results) == 1
    assert isinstance(results[0], GroundTruthRecord)


def test_sqlite_satisfies_protocol(tmp_path: Path) -> None:
    db = ResultsDB(tmp_path / "proto.db")
    assert isinstance(db, EvalDBProtocol)
    db.close()
