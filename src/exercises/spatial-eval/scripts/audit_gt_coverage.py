"""Audit GT coverage: 25 x N matrix of polygon availability per place x source.

Run before run_batch_eval.py to catch name-matching issues early.

Usage:
    uv run python audit_gt_coverage.py
    uv run python audit_gt_coverage.py --gt-sources sf_planning click_that_hood
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus import load_corpus
from geometry_source import list_gt_sources
from sources.coverage_utils import coverage_symbol


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit GT polygon coverage")
    parser.add_argument("--gt-sources", nargs="+", default=list_gt_sources(),
                        help="GT sources to audit (default: all registered)")
    args = parser.parse_args()

    corpus = load_corpus()
    sources = args.gt_sources

    # Header
    col_w = 22
    src_w = 18
    header = f"{'Place':<{col_w}}" + "".join(f"{s:<{src_w}}" for s in sources)
    print(header)
    print("-" * len(header))

    totals = {s: 0 for s in sources}
    for entry in corpus:
        place = entry["name"]
        row = f"{place:<{col_w}}"
        for src_name in sources:
            try:
                sym = coverage_symbol(src_name, place)
            except Exception as e:
                sym = f"⚠️"
            if sym == "✅":
                totals[src_name] += 1
            row += f"{sym:<{src_w}}"
        print(row)

    print("-" * len(header))
    summary = f"{'Polygon total':<{col_w}}" + "".join(f"{totals[s]}/{len(corpus):<{src_w - 2}}" for s in sources)
    print(summary)
    print("\nLegend: ✅ polygon  📍 point only  ❌ missing  ⚠️ error")


if __name__ == "__main__":
    main()
