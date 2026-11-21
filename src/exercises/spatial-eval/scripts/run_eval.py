"""Foundation CLI for the SF spatial reasoning eval.

Usage:
    uv run python run_eval.py --place "The Richmond" --model claude-haiku-4-5 --db duckdb
    uv run python run_eval.py --place "The Mission" --model gpt-4o-mini --runs 3 --gt-source osm --db duckdb
    uv run python run_eval.py --query "boundary of the Richmond" --model claude-haiku-4-5 --db duckdb
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sources.llm import LLMSource
from metrics.spatial_comparison import compare_geometries
from geometry_source import load_gt_source, list_gt_sources
from db_factory import get_db
from models import comparison_record_from_metrics
from corpus import load_corpus


def _tier(place: str) -> int | None:
    corpus = load_corpus(include_inactive=True)
    for p in corpus:
        if p["name"].lower() == place.lower():
            return p["tier"]
    return None


def evaluate(place: str, model: str, gt_source_name: str,
             runs: int, use_cache: bool, variant_id: str, db_backend: str) -> None:
    gt = load_gt_source(gt_source_name)
    ref_polygon = gt.get_polygon(place)

    if ref_polygon is None:
        print(
            f"WARNING: '{gt_source_name}' has no polygon for '{place}'. Skipping.")
        return

    db = get_db(db_backend)

    for run in range(1, runs + 1):
        llm = LLMSource(model, run=run, use_cache=use_cache,
                        variant_id=variant_id)
        pred_polygon = llm.get_polygon(place)

        if pred_polygon is None:
            print(f"  Run {run}: PARSE FAILURE", file=sys.stderr)
            db.insert_comparison(comparison_record_from_metrics(
                metrics=None,
                run_id=f"{model}-{gt_source_name}-run{run}",
                place=place,
                source_a=f"llm:{model}",
                source_b=gt_source_name,
                variant_id=variant_id,
                model_id=model,
                valid=False,
                notes="parse_failure",
            ))
            continue

        m = compare_geometries(pred_polygon, ref_polygon)

        db.insert_comparison(comparison_record_from_metrics(
            metrics=m,
            run_id=f"{model}-{gt_source_name}-run{run}",
            place=place,
            source_a=f"llm:{model}",
            source_b=gt_source_name,
            variant_id=variant_id,
            geom_a=pred_polygon.wkt,
            model_id=model,
        ))
        print(f"\n=== {place} | {model} vs {gt_source_name} | run {run} ===")
        print(f"  IoU:            {m.iou:.3f}")
        print(
            f"  Overlap A/B:    {m.overlap_pct_a:.1%} / {m.overlap_pct_b:.1%}")
        print(f"  DE-9IM:         {m.de9im_label} ({m.de9im})")
        print(f"  Hausdorff:      {m.hausdorff_m:.0f} m")
        print(f"  Centroid error: {m.centroid_error_m:.0f} m")
        print(f"  Composite:      {m.composite:.3f}")

    db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SF spatial reasoning eval (single model)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--place", help="Exact place name")
    group.add_argument("--query", help="Free-text query (used as place name)")
    parser.add_argument("--model", default="claude-haiku-4-5")
    parser.add_argument("--gt-source", default="sf_planning",
                        choices=list_gt_sources(),
                        help="Ground truth source to compare against")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--variant", default="baseline_v2",
                        help="Prompt variant id to query/store (default: baseline_v2)")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument(
        "--db", required=True, choices=["sqlite", "duckdb"],
        help="Database backend: 'duckdb' (current) or 'sqlite' (legacy)"
    )
    args = parser.parse_args()

    place = args.place or args.query
    evaluate(
        place,
        args.model,
        args.gt_source,
        args.runs,
        use_cache=not args.no_cache,
        variant_id=args.variant,
        db_backend=args.db,
    )


if __name__ == "__main__":
    main()
