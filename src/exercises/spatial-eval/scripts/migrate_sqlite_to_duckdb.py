"""One-time migration: copy SQLite results.db → DuckDB eval.duckdb.

Reads both 'comparisons' and 'prompt_experiments' from the old SQLite DB
and writes them into the unified 'comparisons' table in DuckDB.

This script is idempotent: rows that already exist (same UNIQUE key) are
skipped — insert failures are caught and silently ignored in the loop.

Usage:
    uv run python scripts/migrate_sqlite_to_duckdb.py
    uv run python scripts/migrate_sqlite_to_duckdb.py --dry-run
    uv run python scripts/migrate_sqlite_to_duckdb.py --source data/results.db --target data/eval.duckdb
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from db_duckdb import EvalDB


def _safe_col(row: sqlite3.Row, col: str) -> str | None:
    """Read a column by name from a sqlite3.Row; return None if missing."""
    try:
        return row[col]
    except IndexError:
        return None


def migrate(source_db: Path, target_db: Path, *, dry_run: bool = False) -> None:
    if not source_db.exists():
        print(f"Source DB not found: {source_db}")
        sys.exit(1)

    print(f"Source: {source_db}")
    print(f"Target: {target_db}")
    if dry_run:
        print("DRY RUN — no writes")

    src = sqlite3.connect(str(source_db))
    src.row_factory = sqlite3.Row

    dst = EvalDB(target_db) if not dry_run else None

    # ── comparisons table ───────────────────────────────────────────────────
    comp_rows = src.execute("SELECT * FROM comparisons").fetchall()
    print(f"comparisons rows to migrate: {len(comp_rows)}")

    inserted_comp = 0
    for row in comp_rows:
        kwargs: dict = dict(
            place=row["place"],
            source_a=row["source_a"],
            source_b=row["source_b"] or "",
            run_id=f"legacy-run-{row['run']}-{uuid.uuid4().hex[:8]}",
            variant_id=row["variant_id"] or "baseline_v2",
            question_type="bbox_identification",
            iou=row["iou"],
            overlap_a=row["overlap_pct_a"],
            overlap_b=row["overlap_pct_b"],
            hausdorff_m=row["hausdorff_m"],
            centroid_err_m=row["centroid_error_m"],
            composite_score=row["composite"],
            de9im_string=row["de9im"],
            de9im_label=row["de9im_label"],
            geom_a=_safe_col(row, "polygon_wkt_a"),
            geom_b=_safe_col(row, "polygon_wkt_b"),
            model_id=row["source_a"],
            prompt_text=_safe_col(row, "prompt_text"),
            raw_response=_safe_col(row, "raw_response"),
        )
        if not dry_run:
            try:
                dst.insert_comparison(**kwargs)
                inserted_comp += 1
            except Exception:
                pass  # duplicate — skip

    # ── prompt_experiments table ────────────────────────────────────────────
    try:
        exp_rows = src.execute("SELECT * FROM prompt_experiments").fetchall()
    except sqlite3.OperationalError:
        exp_rows = []

    print(f"prompt_experiments rows to migrate: {len(exp_rows)}")

    inserted_exp = 0
    for row in exp_rows:
        kwargs = dict(
            place=row["place"],
            source_a=f"llm:{row['model']}",
            source_b=row["reference_gt"] or "",
            run_id=row["exp_id"] or f"exp-{uuid.uuid4().hex[:8]}",
            variant_id=row["variant_id"] or "baseline_v2",
            question_type="bbox_identification",
            iou=row["iou"],
            overlap_a=_safe_col(row, "overlap_pct_a"),
            overlap_b=_safe_col(row, "overlap_pct_b"),
            hausdorff_m=row["hausdorff_m"],
            centroid_err_m=row["centroid_error_m"],
            composite_score=row["composite"],
            de9im_string=_safe_col(row, "de9im"),
            de9im_label=_safe_col(row, "de9im_label"),
            geom_a=_safe_col(row, "polygon_wkt_a"),
            geom_b=None,  # prompt_experiments has no polygon_wkt_b column
            model_id=row["model"],
            prompt_text=_safe_col(row, "prompt_text"),
            raw_response=_safe_col(row, "raw_response"),
            notes=_safe_col(row, "error"),
        )
        if not dry_run:
            try:
                dst.insert_comparison(**kwargs)
                inserted_exp += 1
            except Exception:
                pass

    src.close()

    if not dry_run:
        print(f"Inserted from comparisons: {inserted_comp}")
        print(f"Inserted from prompt_experiments: {inserted_exp}")
    else:
        print(f"Would migrate: {len(comp_rows)} comparison rows, {len(exp_rows)} experiment rows")
    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate SQLite → DuckDB eval DB")
    parser.add_argument("--source", type=Path, default=config.RESULTS_DB_PATH)
    parser.add_argument("--target", type=Path, default=config.DUCKDB_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    migrate(args.source, args.target, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
