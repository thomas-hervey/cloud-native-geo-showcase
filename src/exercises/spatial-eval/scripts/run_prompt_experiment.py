"""Run admin prompt-variant experiments from the CLI.

Usage:
  uv run python run_prompt_experiment.py \
    --places "The Mission" "The Richmond" \
    --models anthropic/claude-3-5-haiku-latest \
    --variants baseline_v2 boundary_strict \
    --reference-gt sf_planning \
    --runs 1 \
    --db duckdb
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from shapely.geometry import box
from prompt_variants import DEFAULT_PROMPT_VARIANTS, build_variant_user_prompt
from model_registry import default_models
from metrics.spatial_comparison import compare_geometries
from llm_client import query_model
from geometry_source import load_gt_source, list_gt_sources
from db_factory import get_db
from models import comparison_record_from_metrics
from corpus import load_corpus


def _alias_lookup() -> dict[str, list[str]]:
    corpus = load_corpus(include_inactive=True)
    return {
        entry["name"]: entry.get("aliases", [])
        for entry in corpus
        if entry.get("name")
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run prompt variant experiments and persist results")
    parser.add_argument("--places", nargs="+", required=True)
    parser.add_argument("--models", nargs="+", default=default_models())
    parser.add_argument("--variants", nargs="+", default=["baseline_v2"])
    parser.add_argument(
        "--reference-gt", default="sf_planning", choices=list_gt_sources())
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--no-cache", action="store_true",
                        help="Ignore cache and force fresh model calls")
    parser.add_argument(
        "--db", required=True, choices=["sqlite", "duckdb"],
        help="Database backend: 'duckdb' (current) or 'sqlite' (legacy)"
    )
    args = parser.parse_args()

    variant_ids = {variant.variant_id for variant in DEFAULT_PROMPT_VARIANTS}
    unknown_variants = [v for v in args.variants if v not in variant_ids]
    if unknown_variants:
        raise ValueError(f"Unknown prompt variants: {unknown_variants}")

    corpus = load_corpus()
    tier_lookup = {entry["name"]: entry.get("tier") for entry in corpus}
    aliases = _alias_lookup()

    missing_places = [
        place for place in args.places if place not in tier_lookup]
    if missing_places:
        raise ValueError(
            f"Place(s) not found in active corpus: {missing_places}")

    db = get_db(args.db)
    reference_source = load_gt_source(args.reference_gt)
    exp_id = datetime.now(timezone.utc).strftime("exp-%Y%m%d-%H%M%S")

    total = len(args.places) * len(args.models) * \
        len(args.variants) * args.runs
    done = 0

    for place in args.places:
        ref_polygon = reference_source.get_polygon(place)
        for model in args.models:
            for variant_id in args.variants:
                for run in range(1, args.runs + 1):
                    prompt_text = build_variant_user_prompt(
                        place, aliases.get(place, []), variant_id)

                    result = query_model(
                        place,
                        model,
                        run=run,
                        use_cache=not args.no_cache,
                        prompt_variant_id=variant_id,
                        user_prompt_override=prompt_text,
                    )

                    parsed = result if isinstance(result, dict) else None
                    valid_result = bool(parsed and parsed.get("_valid"))
                    comparison = None
                    pred_poly = None
                    if valid_result and ref_polygon is not None:
                        assert parsed is not None
                        if parsed.get("polygon_wkt"):
                            from shapely import wkt
                            pred_poly = wkt.loads(str(parsed["polygon_wkt"]))
                        else:
                            pred_poly = box(
                                float(parsed["bbox_west"]),
                                float(parsed["bbox_south"]),
                                float(parsed["bbox_east"]),
                                float(parsed["bbox_north"]),
                            )
                        comparison = compare_geometries(pred_poly, ref_polygon)

                    record = comparison_record_from_metrics(
                        metrics=comparison,
                        run_id=exp_id,
                        place=place,
                        source_a=f"llm:{model}",
                        source_b=args.reference_gt,
                        variant_id=variant_id,
                        geom_a=parsed.get("polygon_wkt") if parsed else None,
                        model_id=model,
                        prompt_text=prompt_text,
                        raw_response=parsed.get("_raw") if parsed else None,
                        notes=parsed.get("_error") if parsed else "invalid_or_missing_geometry",
                        valid=bool(valid_result and comparison is not None),
                    )
                    db.insert_comparison(record)

                    done += 1
                    status = "ok" if valid_result and comparison is not None else "invalid"
                    print(
                        f"[{done}/{total}] {place} | {model} | {variant_id} | run{run}: {status}")

    print(f"\nStored prompt experiments under exp_id={exp_id}")
    db.close()


if __name__ == "__main__":
    main()
