"""Compute pairwise GT-vs-GT comparisons for all registered sources.

Run this once to populate the comparisons table with GT agreement metrics.
No LLMs involved — just compares every GT source against every other.

Usage:
    uv run python run_gt_comparison.py --db duckdb
    uv run python run_gt_comparison.py --gt-sources click_that_hood osm sf_planning --db duckdb
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from itertools import combinations

sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus import load_corpus
from db_factory import get_db
from models import comparison_record_from_metrics
from geometry_source import load_gt_source, list_gt_sources
from metrics.spatial_comparison import compare_geometries

# Wikidata excluded: P3896 geoshape is unset for all 25 SF corpus neighborhoods
# (March 2026 audit — 0/25 coverage). Keep the source class for future use but
# don't run it by default since it only produces null comparisons.
#
# OSM caveat: some OSM polygons have near-zero IoU vs. reliable sources
# (sf_planning, click_that_hood). This indicates Nominatim matched a wrong
# feature (e.g. a small mission building instead of the Mission neighborhood).
# Use --gt-sources osm to include it, but treat low-IoU OSM results with
# skepticism. Long-term fix: replace Nominatim with Overpass API boundary
# queries (see docs/plans/2026-03-11-eval-framework-refactor.md).
DEFAULT_GT_SOURCES = ["sf_planning", "click_that_hood", "zillow", "osm", "osm_overpass"]


def main() -> None:
    parser = argparse.ArgumentParser(description="GT-vs-GT pairwise comparison")
    parser.add_argument("--gt-sources", nargs="+", default=DEFAULT_GT_SOURCES,
                        help="Subset of GT sources (default: all reliable sources excluding wikidata)")
    parser.add_argument(
        "--db", required=True, choices=["sqlite", "duckdb"],
        help="Database backend: 'duckdb' (current) or 'sqlite' (legacy)"
    )
    args = parser.parse_args()

    corpus = load_corpus()
    sources = args.gt_sources
    db = get_db(args.db)
    pairs = list(combinations(sources, 2))

    print(f"GT sources: {sources}")
    print(f"Comparing {len(pairs)} pairs × {len(corpus)} places...\n")

    for place_entry in corpus:
        place = place_entry["name"]
        for src_a_name, src_b_name in pairs:
            src_a = load_gt_source(src_a_name)
            src_b = load_gt_source(src_b_name)
            poly_a = src_a.get_polygon(place)
            poly_b = src_b.get_polygon(place)

            if poly_a is None or poly_b is None:
                missing = src_a_name if poly_a is None else src_b_name
                print(f"  SKIP {place} | {src_a_name} vs {src_b_name}: {missing} has no polygon")
                continue

            m = compare_geometries(poly_a, poly_b)

            db.insert_comparison(comparison_record_from_metrics(
                metrics=m,
                run_id=f"gt-{src_a_name}-vs-{src_b_name}",
                place=place,
                source_a=src_a_name,
                source_b=src_b_name,
            ))
            print(f"  {place} | {src_a_name} vs {src_b_name}: "
                  f"IoU={m.iou:.3f} | {m.de9im_label}")

    print("\nDone. GT comparisons stored.")
    db.close()


if __name__ == "__main__":
    main()
