"""Print comparison matrix grouped by tier and place.

Usage:
    uv run python run_analysis.py --db duckdb
    uv run python run_analysis.py --metric composite_score --gt-source click_that_hood --db duckdb
    uv run python run_analysis.py --source-type gt --db duckdb
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from db_factory import get_db


def print_matrix(rows: list[dict], metric: str = "iou") -> None:
    """Print a place × source_a pivot table averaged across runs."""
    if not rows:
        print("No data.")
        return

    df = pd.DataFrame([r for r in rows if r["valid"] and r[metric] is not None])
    if df.empty:
        print("No valid rows with metric data.")
        return

    pivot = (
        df.groupby(["place", "source_a"])[metric]
        .mean()
        .unstack()
        .round(3)
    )

    print(f"\n=== {metric} matrix (rows=place, cols=source_a) ===")
    print(pivot.to_string())
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Analysis matrix for eval results")
    parser.add_argument("--metric", default="iou",
                        choices=["iou", "centroid_err_m", "composite_score",
                                 "overlap_a", "overlap_b", "hausdorff_m"])
    parser.add_argument("--gt-source", default=None,
                        help="Filter to comparisons against this GT source")
    parser.add_argument("--source-type", default="llm",
                        choices=["llm", "gt", "all"],
                        help="Show LLM-vs-GT rows, GT-vs-GT rows, or all")
    parser.add_argument(
        "--db", required=True, choices=["sqlite", "duckdb"],
        help="Database backend: 'duckdb' (current) or 'sqlite' (legacy)"
    )
    args = parser.parse_args()

    db = get_db(args.db)
    records = db.fetch_comparisons(source_b=args.gt_source)
    rows = [r.model_dump() for r in records]
    db.close()

    if args.source_type == "llm":
        rows = [r for r in rows if r["source_a"].startswith("llm:")]
    elif args.source_type == "gt":
        rows = [r for r in rows if not r["source_a"].startswith("llm:")]

    print_matrix(rows, args.metric)


if __name__ == "__main__":
    main()
