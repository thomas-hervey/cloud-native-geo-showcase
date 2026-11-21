"""Print ranked leaderboard from eval results."""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from db_factory import get_db


def main() -> None:
    parser = __import__("argparse").ArgumentParser()
    parser.add_argument("--gt-source", default=None,
                        help="Filter to comparisons against this GT source")
    parser.add_argument(
        "--db", required=True, choices=["sqlite", "duckdb"],
        help="Database backend: 'duckdb' (current) or 'sqlite' (legacy)"
    )
    args = parser.parse_args()

    db = get_db(args.db)
    records = db.fetch_comparisons(source_b=args.gt_source)
    rows = [r.model_dump() for r in records]
    db.close()

    # LLM runs only
    df = pd.DataFrame([r for r in rows if r["valid"] and r["source_a"].startswith("llm:")])
    if df.empty:
        print("No results. Run run_batch_eval.py first.")
        return

    summary = (
        df.groupby("source_a")
        .agg(
            avg_iou=("iou", "mean"),
            avg_centroid_err=("centroid_err_m", "mean"),
            avg_composite=("composite_score", "mean"),
            avg_hausdorff=("hausdorff_m", "mean"),
            n_places=("place", "nunique"),
            n_runs=("run_id", "count"),
        )
        .round(3)
        .sort_values("avg_composite", ascending=False)
        .reset_index()
    )
    summary.index += 1

    # DE-9IM label distribution per model
    de9im_dist = (
        df.groupby(["source_a", "de9im_label"])
        .size()
        .unstack(fill_value=0)
    )

    print("\n=== SF Spatial Reasoning Leaderboard ===")
    gt_filter = f" (vs {args.gt_source})" if args.gt_source else " (all GT sources)"
    print(f"Reference Ground Truth{gt_filter}\n")
    print(summary.to_string())
    print("\n=== DE-9IM Label Distribution ===")
    print(de9im_dist.to_string())
    print()


if __name__ == "__main__":
    main()
