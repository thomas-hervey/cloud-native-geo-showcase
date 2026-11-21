"""Protocol conformance tests — both backends must satisfy EvalDBProtocol."""
from __future__ import annotations

from pathlib import Path

from db import ResultsDB
from db_duckdb import EvalDB
from db_protocol import EvalDBProtocol
from models import ComparisonRecord


def test_duckdb_satisfies_protocol(tmp_path: Path) -> None:
    db = EvalDB(tmp_path / "test.duckdb")
    assert isinstance(db, EvalDBProtocol)
    db.close()


def test_sqlite_satisfies_protocol(tmp_path: Path) -> None:
    db = ResultsDB(tmp_path / "test.db")
    assert isinstance(db, EvalDBProtocol)
    db.close()


def test_sqlite_fetch_applies_run_id_filter(tmp_path: Path) -> None:
    """Structural typing doesn't verify filter semantics — test explicitly."""
    db = ResultsDB(tmp_path / "test.db")
    db.insert_comparison(ComparisonRecord(
        run_id="run-a", place="The Mission",
        source_a="llm:gpt-4o", source_b="sf_planning",
    ))
    db.insert_comparison(ComparisonRecord(
        run_id="run-b", place="The Richmond",
        source_a="llm:gpt-4o", source_b="sf_planning",
    ))
    results = db.fetch_comparisons(run_id="run-a")
    assert len(results) == 1 and results[0].run_id == "run-a"
    db.close()


def test_sqlite_fetch_applies_cognitive_level_filter(tmp_path: Path) -> None:
    db = ResultsDB(tmp_path / "test.db")
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
    db.close()
