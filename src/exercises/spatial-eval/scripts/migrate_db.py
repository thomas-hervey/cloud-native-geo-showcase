"""Migrate results.db to a variant-aware unified comparisons schema.

This script preserves existing data while promoting prompt variant to a
first-class column in `comparisons`.

Default behavior writes to a new DB file to avoid destructive changes.
Use --in-place to replace the original DB after creating a backup.

Examples:
    uv run python scripts/migrate_db.py
    uv run python scripts/migrate_db.py --in-place
    uv run python scripts/migrate_db.py --reference-gt sf_planning
"""
import argparse
import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from metrics.spatial_comparison import compare_geometries
from geometry_source import load_gt_source
from db import ResultsDB
from corpus import load_corpus
import config

import argparse
import json
import re
import shutil
import sqlite3
from pathlib import Path
import sys

from shapely.geometry import box
from shapely.geometry.base import BaseGeometry

sys.path.insert(0, str(Path(__file__).parent.parent))


CACHE_RE = re.compile(
    r"^(?P<place>.+?)__(?P<model>.+?)__run(?P<run>\d+)(?:__variant-(?P<variant>.+?))?\.json$"
)


def _normalize_variant(raw_variant: str | None) -> str:
    # Legacy no-suffix cache files are treated as baseline_v2.
    if not raw_variant:
        return "baseline_v2"
    return raw_variant


def _cache_records(cache_dir: Path) -> list[tuple[str, str, int, str, Path]]:
    records: list[tuple[str, str, int, str, Path]] = []
    for p in cache_dir.glob("*.json"):
        match = CACHE_RE.match(p.name)
        if not match:
            continue
        place, model, run_s, raw_variant = (
            match.group("place"),
            match.group("model"),
            match.group("run"),
            match.group("variant"),
        )
        records.append((place, model, int(run_s),
                       _normalize_variant(raw_variant), p))
    return records


def _prediction_polygon(payload: dict) -> BaseGeometry | None:
    if "polygon_wkt" in payload and payload["polygon_wkt"]:
        from shapely import wkt

        try:
            return wkt.loads(str(payload["polygon_wkt"]))
        except Exception:
            return None

    bbox_keys = ["bbox_west", "bbox_south", "bbox_east", "bbox_north"]
    if all(payload.get(k) is not None for k in bbox_keys):
        try:
            return box(
                float(payload["bbox_west"]),
                float(payload["bbox_south"]),
                float(payload["bbox_east"]),
                float(payload["bbox_north"]),
            )
        except Exception:
            return None

    return None


def _load_prompt_experiment_lookup(conn: sqlite3.Connection) -> dict[tuple[str, str, str, int, str], dict]:
    lookup: dict[tuple[str, str, str, int, str], dict] = {}
    try:
        rows = conn.execute(
            """
            SELECT place, model, reference_gt, run, variant_id, prompt_text, raw_response
            FROM prompt_experiments
            """
        ).fetchall()
    except sqlite3.OperationalError:
        return lookup

    for row in rows:
        key = (
            row["place"],
            row["model"],
            row["reference_gt"],
            int(row["run"]),
            row["variant_id"] or "baseline_v2",
        )
        lookup[key] = {
            "prompt_text": row["prompt_text"],
            "raw_response": row["raw_response"],
        }
    return lookup


def migrate(
    source_db: Path,
    output_db: Path,
    reference_gt: str,
) -> None:
    if not source_db.exists():
        raise FileNotFoundError(f"Source DB not found: {source_db}")

    source_conn = sqlite3.connect(str(source_db))
    source_conn.row_factory = sqlite3.Row

    old_rows = source_conn.execute("SELECT * FROM comparisons").fetchall()
    prompt_lookup = _load_prompt_experiment_lookup(source_conn)

    if output_db.exists():
        output_db.unlink()

    target_db = ResultsDB(path=output_db, read_only=False)

    corpus = load_corpus(include_inactive=True)
    tier_lookup = {entry["name"].lower(): entry.get("tier")
                   for entry in corpus if entry.get("name")}

    # 1) Preserve GT-vs-GT rows (run=0) exactly, adding baseline variant metadata.
    preserved_gt_rows = 0
    for row in old_rows:
        if int(row["run"]) != 0:
            continue

        target_db.insert_comparison(
            place=row["place"],
            source_a=row["source_a"],
            source_b=row["source_b"],
            run=int(row["run"]),
            tier=row["tier"],
            centroid_lat_a=row["centroid_lat_a"],
            centroid_lon_a=row["centroid_lon_a"],
            bbox_north_a=row["bbox_north_a"],
            bbox_south_a=row["bbox_south_a"],
            bbox_east_a=row["bbox_east_a"],
            bbox_west_a=row["bbox_west_a"],
            iou=row["iou"],
            overlap_pct_a=row["overlap_pct_a"],
            overlap_pct_b=row["overlap_pct_b"],
            de9im=row["de9im"],
            de9im_label=row["de9im_label"],
            hausdorff_m=row["hausdorff_m"],
            centroid_error_m=row["centroid_error_m"],
            composite=row["composite"],
            variant_id="baseline_v2",
            polygon_wkt_a=row["polygon_wkt_a"],
            polygon_wkt_b=row["polygon_wkt_b"],
            raw_response=row["raw_response"] if "raw_response" in row.keys(
            ) else None,
            prompt_text=row["prompt_text"] if "prompt_text" in row.keys(
            ) else None,
            valid=bool(row["valid"]),
        )
        preserved_gt_rows += 1

    # 2) Rebuild LLM rows from cache directory against selected reference GT.
    ref_source = load_gt_source(reference_gt)
    cache_rows = 0
    cache_failures = 0
    inserted_keys: set[tuple[str, str, str, int, str]] = set()

    for place_key, model, run, variant_id, cache_path in _cache_records(config.LLM_RESPONSES_DIR):
        place = place_key.replace("_", " ").title()
        try:
            payload = json.loads(cache_path.read_text())
        except (json.JSONDecodeError, OSError):
            cache_failures += 1
            continue

        place_name = payload.get("_place") or payload.get("place") or place
        if not isinstance(place_name, str):
            place_name = place

        key = (place_name, model, reference_gt, run, variant_id)
        inserted_keys.add(key)

        prompt_meta = prompt_lookup.get(key, {})
        prompt_text = prompt_meta.get("prompt_text")
        raw_response = payload.get("_raw") or prompt_meta.get("raw_response")

        ref_polygon = ref_source.get_polygon(place_name)
        pred_polygon = _prediction_polygon(
            payload) if payload.get("_valid") else None

        comparison = None
        is_valid = False
        if ref_polygon is not None and pred_polygon is not None:
            comparison = compare_geometries(pred_polygon, ref_polygon)
            is_valid = True

        bbox = {
            "north": payload.get("bbox_north"),
            "south": payload.get("bbox_south"),
            "east": payload.get("bbox_east"),
            "west": payload.get("bbox_west"),
        }
        if pred_polygon is not None and any(v is None for v in bbox.values()):
            b = pred_polygon.bounds
            bbox = {"west": b[0], "south": b[1], "east": b[2], "north": b[3]}

        centroid_lat = payload.get("centroid_lat")
        centroid_lon = payload.get("centroid_lon")
        if pred_polygon is not None and (centroid_lat is None or centroid_lon is None):
            centroid_lat = pred_polygon.centroid.y
            centroid_lon = pred_polygon.centroid.x

        target_db.insert_comparison(
            place=place_name,
            source_a=model,
            source_b=reference_gt,
            run=run,
            tier=tier_lookup.get(place_name.lower()),
            centroid_lat_a=float(
                centroid_lat) if centroid_lat is not None else 0,
            centroid_lon_a=float(
                centroid_lon) if centroid_lon is not None else 0,
            bbox_north_a=float(
                bbox["north"]) if bbox["north"] is not None else 0,
            bbox_south_a=float(
                bbox["south"]) if bbox["south"] is not None else 0,
            bbox_east_a=float(bbox["east"]) if bbox["east"] is not None else 0,
            bbox_west_a=float(bbox["west"]) if bbox["west"] is not None else 0,
            iou=comparison.iou if comparison else None,
            overlap_pct_a=comparison.overlap_pct_a if comparison else None,
            overlap_pct_b=comparison.overlap_pct_b if comparison else None,
            de9im=comparison.de9im if comparison else None,
            de9im_label=comparison.de9im_label if comparison else None,
            hausdorff_m=comparison.hausdorff_m if comparison else None,
            centroid_error_m=comparison.centroid_error_m if comparison else None,
            composite=comparison.composite if comparison else None,
            variant_id=variant_id,
            polygon_wkt_a=pred_polygon.wkt if pred_polygon is not None else None,
            polygon_wkt_b=ref_polygon.wkt if ref_polygon is not None else None,
            raw_response=raw_response,
            prompt_text=prompt_text,
            valid=is_valid,
        )
        cache_rows += 1

    # 3) Preserve any old LLM rows not represented by cache-derived keys.
    preserved_llm_rows = 0
    for row in old_rows:
        if int(row["run"]) == 0:
            continue

        row_variant = row["variant_id"] if "variant_id" in row.keys(
        ) and row["variant_id"] else "baseline_v2"
        key = (row["place"], row["source_a"],
               row["source_b"], int(row["run"]), row_variant)
        if key in inserted_keys:
            continue

        target_db.insert_comparison(
            place=row["place"],
            source_a=row["source_a"],
            source_b=row["source_b"],
            run=int(row["run"]),
            tier=row["tier"],
            centroid_lat_a=row["centroid_lat_a"],
            centroid_lon_a=row["centroid_lon_a"],
            bbox_north_a=row["bbox_north_a"],
            bbox_south_a=row["bbox_south_a"],
            bbox_east_a=row["bbox_east_a"],
            bbox_west_a=row["bbox_west_a"],
            iou=row["iou"],
            overlap_pct_a=row["overlap_pct_a"],
            overlap_pct_b=row["overlap_pct_b"],
            de9im=row["de9im"],
            de9im_label=row["de9im_label"],
            hausdorff_m=row["hausdorff_m"],
            centroid_error_m=row["centroid_error_m"],
            composite=row["composite"],
            variant_id=row_variant,
            polygon_wkt_a=row["polygon_wkt_a"],
            polygon_wkt_b=row["polygon_wkt_b"],
            raw_response=row["raw_response"] if "raw_response" in row.keys(
            ) else None,
            prompt_text=row["prompt_text"] if "prompt_text" in row.keys(
            ) else None,
            valid=bool(row["valid"]),
        )
        preserved_llm_rows += 1

    source_conn.close()

    print("Migration complete")
    print(f"  Source DB: {source_db}")
    print(f"  Output DB: {output_db}")
    print(f"  Preserved GT rows: {preserved_gt_rows}")
    print(f"  Rebuilt cache-derived LLM rows: {cache_rows}")
    print(f"  Cache parse failures: {cache_failures}")
    print(f"  Preserved non-cache LLM rows: {preserved_llm_rows}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate spatial-eval DB to variant-aware comparisons schema")
    parser.add_argument("--db", type=Path,
                        default=config.RESULTS_DB_PATH, help="Source DB path")
    parser.add_argument(
        "--output",
        type=Path,
        default=config.DATA_DIR / "results.migrated.db",
        help="Output migrated DB path",
    )
    parser.add_argument(
        "--reference-gt",
        default="sf_planning",
        help="Reference GT used to compute metrics from cache-derived LLM geometries",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Replace source DB with migrated output (creates .bak backup first)",
    )
    args = parser.parse_args()

    source_db = args.db
    output_db = args.output

    migrate(source_db=source_db, output_db=output_db,
            reference_gt=args.reference_gt)

    if args.in_place:
        backup_path = source_db.with_suffix(source_db.suffix + ".bak")
        shutil.copy2(source_db, backup_path)
        shutil.copy2(output_db, source_db)
        print(f"In-place replace complete. Backup: {backup_path}")


if __name__ == "__main__":
    main()
