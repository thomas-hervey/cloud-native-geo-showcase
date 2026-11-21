"""Batch evaluation: all models × all places × all GT sources × N runs.

Usage:
    uv run python run_batch_eval.py --db duckdb
    uv run python run_batch_eval.py --models claude-haiku-4-5 gpt-4o-mini --db duckdb
    uv run python run_batch_eval.py --gt-sources click_that_hood osm --db duckdb
    uv run python run_batch_eval.py --places "The Richmond" --runs 3 --db duckdb
    uv run python run_batch_eval.py --yes --db duckdb  # skip cost confirmation
    uv run python run_batch_eval.py --run-tag 2026-11 --db duckdb  # new period, separate cache
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

from model_registry import default_models as _default_models
from sources.llm import LLMSource
from metrics.spatial_comparison import compare_geometries
from geometry_source import load_gt_source, list_gt_sources
from db_factory import get_db
from db_protocol import EvalDBProtocol
from models import comparison_record_from_metrics
from llm_client import estimate_cost, tagged_run_id, validate_run_tag
from corpus import load_corpus


DEFAULT_MODELS = _default_models()

DEFAULT_GT_SOURCES = ["sf_planning"]


def _confirm_run(models: list[str], n_places: int, gt_sources: list[str], runs: int, variants: list[str]) -> bool:
    """Print cost estimate and prompt for confirmation. Returns True if user confirms."""
    n_calls_per_model = n_places * len(gt_sources) * runs * len(variants)
    total_calls = len(models) * n_calls_per_model

    estimates = estimate_cost(models, n_calls_per_model)
    total_cost = sum(c for _, c in estimates)

    print("\n── Batch eval cost estimate ─────────────────────────────────────")
    print(
        f"  Places  : {n_places}  ×  GT sources: {len(gt_sources)}  × "
        f"Variants: {len(variants)}  ×  Runs: {runs}"
    )
    print(f"  Models  : {len(models)}  →  {total_calls} total LLM calls\n")
    print(f"  {'Model':<30}  {'Calls':>6}  {'Est. cost':>10}")
    print(f"  {'-'*30}  {'------':>6}  {'----------':>10}")
    for model_id, cost in estimates:
        print(f"  {model_id:<30}  {n_calls_per_model:>6}  ${cost:>9.4f}")
    print(f"  {'-'*30}  {'------':>6}  {'----------':>10}")
    print(f"  {'TOTAL':<30}  {total_calls:>6}  ${total_cost:>9.4f}")
    print("─────────────────────────────────────────────────────────────────")
    print("  (Estimates assume ~300 input / ~800 output tokens per call.)")
    print("  Pass --yes to skip this prompt.\n")

    answer = input("Proceed? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def evaluate_one(place: str, tier: int, model: str, gt_source_name: str, variant_id: str,
                 run: int, db: EvalDBProtocol, use_cache: bool,
                 run_tag: str | None = None) -> dict:
    gt = load_gt_source(gt_source_name)
    ref_polygon = gt.get_polygon(place)
    llm = LLMSource(model, run=run, use_cache=use_cache, variant_id=variant_id, run_tag=run_tag)
    run_id = tagged_run_id(model, gt_source_name, run, run_tag)
    pred_polygon = llm.get_polygon(place)
    was_cached = llm.was_cached(place)

    if pred_polygon is None or ref_polygon is None:
        db.insert_comparison(comparison_record_from_metrics(
            metrics=None,
            run_id=run_id,
            place=place,
            source_a=f"llm:{model}",
            source_b=gt_source_name,
            variant_id=variant_id,
            model_id=model,
            valid=False,
            notes="parse_failure",
        ))
        return {
            "place": place,
            "model": model,
            "gt": gt_source_name,
            "run": run,
            "variant_id": variant_id,
            "valid": False,
            "cached": was_cached,
        }

    m = compare_geometries(pred_polygon, ref_polygon)

    db.insert_comparison(comparison_record_from_metrics(
        metrics=m,
        run_id=run_id,
        place=place,
        source_a=f"llm:{model}",
        source_b=gt_source_name,
        variant_id=variant_id,
        geom_a=pred_polygon.wkt,
        model_id=model,
    ))
    return {"place": place, "model": model, "gt": gt_source_name, "variant_id": variant_id,
            "run": run, "iou": m.iou, "valid": True, "cached": was_cached}


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch spatial eval")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--gt-sources", nargs="+", default=DEFAULT_GT_SOURCES,
                        choices=list_gt_sources())
    parser.add_argument("--places", nargs="+", default=None)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument(
        "--variants",
        nargs="+",
        default=["baseline_v2"],
        help="Prompt variants to evaluate (default: baseline_v2)",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Skip cost confirmation prompt")
    parser.add_argument("--no-cache", action="store_true",
                        help="Force re-running LLM queries even if cached")
    parser.add_argument(
        "--run-tag", default=None, type=validate_run_tag,
        help=(
            "Evaluation period tag, e.g. 2026-11. Prefixes run_id and uses a separate "
            "response cache (data/llm_responses/<tag>/) so earlier runs are never "
            "read or overwritten."
        ),
    )
    parser.add_argument(
        "--db", required=True, choices=["sqlite", "duckdb"],
        help="Database backend: 'duckdb' (current) or 'sqlite' (legacy)"
    )
    args = parser.parse_args()

    corpus = load_corpus()
    if args.places:
        corpus = [p for p in corpus if p["name"] in args.places]

    if not args.yes:
        confirmed = _confirm_run(args.models, len(
            corpus), args.gt_sources, args.runs, args.variants)
        if not confirmed:
            print("Aborted.")
            sys.exit(0)

    db = get_db(args.db)
    tasks = [
        (p["name"], p["tier"], m, gt, v, r)
        for p in corpus
        for m in args.models
        for gt in args.gt_sources
        for v in args.variants
        for r in range(1, args.runs + 1)
    ]

    total, done = len(tasks), 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(evaluate_one, place, tier, model, gt, variant, run, db,
                            not args.no_cache, args.run_tag): None
            for place, tier, model, gt, variant, run in tasks
        }
        for future in as_completed(futures):
            done += 1
            r = future.result()
            status = f"IoU={r.get('iou', 0):.2f}" if r["valid"] else "FAILED"
            cache_tag = " [cached]" if r.get("cached") else ""
            print(
                f"[{done}/{total}] {r['place']} | {r['model']} vs {r['gt']} "
                f"variant={r['variant_id']} run{r['run']}: {status}{cache_tag}"
            )

    print(f"\nDone. {total} comparisons stored.")
    db.close()


if __name__ == "__main__":
    main()
