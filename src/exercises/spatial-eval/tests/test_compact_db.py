"""compact_database must restore the canonical schema, not just copy rows."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from db_duckdb import EvalDB, compact_database
from models import ComparisonRecord


def _degraded_db(path: Path) -> None:
    """Mimic the old CREATE TABLE AS compaction: no constraints, no defaults."""
    con = duckdb.connect(str(path))
    con.execute("""
        CREATE TABLE comparisons AS SELECT * FROM (VALUES
            ('2026-11:m-sf_planning-run1', 'Chinatown', 'llm:m', 'sf_planning', 'baseline_v2',
             'bbox_identification', 'L1', 0.5, NULL::TIMESTAMP, true),
            ('2026-11:m-sf_planning-run1', 'Chinatown', 'llm:m', 'sf_planning', 'baseline_v2',
             'bbox_identification', 'L1', 0.5, NULL::TIMESTAMP, true),
            ('m-sf_planning-run1', 'Chinatown', 'llm:m', 'sf_planning', NULL,
             NULL, NULL, 0.4, TIMESTAMP '2026-03-21 12:00', true)
        ) t(run_id, place, source_a, source_b, variant_id, question_type, cognitive_level,
            iou, created_at, valid)
    """)
    con.execute("CREATE TABLE ground_truths (place TEXT, source TEXT, geom_wkt TEXT, created_at TIMESTAMP)")
    con.execute("INSERT INTO ground_truths VALUES ('Chinatown', 'osm', 'POINT (0 0)', NULL)")
    con.close()


@pytest.fixture
def compacted(tmp_path: Path) -> tuple[Path, tuple[int, int]]:
    path = tmp_path / "eval.duckdb"
    _degraded_db(path)
    return path, compact_database(path)


def test_should_dedupe_and_backfill_degraded_rows(compacted) -> None:
    path, counts = compacted
    assert counts == (3, 2)
    con = duckdb.connect(str(path), read_only=True)
    rows = con.execute(
        "SELECT run_id, place, source_a, source_b, variant_id, cognitive_level, iou, "
        "created_at IS NOT NULL FROM comparisons ORDER BY run_id"
    ).fetchall()
    assert rows == [
        ("2026-11:m-sf_planning-run1", "Chinatown", "llm:m", "sf_planning", "baseline_v2", "L1",
         pytest.approx(0.5), True),
        ("m-sf_planning-run1", "Chinatown", "llm:m", "sf_planning", "baseline_v2", "L1",
         pytest.approx(0.4), True),
    ]
    assert con.execute("SELECT COUNT(*) FROM ground_truths").fetchone()[0] == 1
    con.close()


def test_should_restore_unique_key_and_created_at_default(compacted) -> None:
    path, _ = compacted
    db = EvalDB(path)
    record = ComparisonRecord(run_id="x-sf_planning-run1", place="Chinatown",
                              source_a="llm:x", source_b="sf_planning", iou=0.1)
    db.insert_comparison(record)
    db.insert_comparison(record)  # duplicate is skipped, not stored
    rows = [r for r in db.fetch_comparisons() if r.run_id == "x-sf_planning-run1"]
    db.close()
    assert len(rows) == 1
    assert rows[0].created_at is not None


def test_should_not_reset_invalid_rows_when_reopening(tmp_path: Path) -> None:
    path = tmp_path / "eval.duckdb"
    db = EvalDB(path)
    db.insert_comparison(ComparisonRecord(run_id="r1", place="Chinatown", source_a="llm:x",
                                          source_b="sf_planning", valid=False,
                                          notes="parse_failure"))
    db.close()
    reopened = EvalDB(path)
    rows = reopened.fetch_comparisons()
    reopened.close()
    assert [r.valid for r in rows] == [False]
