"""Export the headline findings shown on /spatial-eval ("What the data says").

Reads the LLM-vs-sf_planning L1 comparisons (same row rules as
export_run_summary.py: ``legacy-run-*`` duplicates are skipped) and the
reference-vs-reference comparisons, and writes small, reproducible aggregates.

Usage:
    uv run --with duckdb --with shapely --with pyproj python scripts/export_story_findings.py
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb
from pyproj import Geod
from shapely import wkt

HERE = Path(__file__).resolve().parent.parent
REPO_ROOT = Path(__file__).resolve().parents[4]
DB_PATH = HERE / "data" / "eval.duckdb"
PLACES_PATH = HERE / "data" / "places.json"
DEFAULT_OUT = REPO_ROOT / "src" / "content" / "spatial-eval" / "story-findings.json"

GEOD = Geod(ellps="WGS84")
LLM_WHERE = (
    "source_a LIKE 'llm:%' AND source_b = 'sf_planning' AND cognitive_level = 'L1'"
    " AND run_id NOT LIKE 'legacy-run-%'"
)
# OSM/Nominatim lookups score 0.0 IoU against every other source for most places,
# which points at an alias/matching problem rather than real disagreement. They are
# excluded from the reference-agreement numbers until the aliases are reviewed.
REFERENCE_SOURCES = ("sf_planning", "click_that_hood", "zillow")


def med(values: list[float], digits: int = 3) -> float:
    return round(st.median(values), digits)


def spearman(xs: list[float], ys: list[float]) -> float:
    def ranks(values: list[float]) -> list[float]:
        ordered = sorted(values)
        return [ordered.index(v) + (ordered.count(v) + 1) / 2 for v in values]

    rx, ry = ranks(xs), ranks(ys)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    return num / (sum((a - mx) ** 2 for a in rx) ** 0.5 * sum((b - my) ** 2 for b in ry) ** 0.5)


def area_m2(geom) -> float:
    return abs(GEOD.geometry_area_perimeter(geom)[0])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    tiers = {p["name"]: p["tier"] for p in json.loads(PLACES_PATH.read_text())["places"]}
    con = duckdb.connect(str(DB_PATH), read_only=True)

    rows = con.sql(
        f"SELECT place, iou, centroid_err_m, valid, raw_response, geom_a, geom_b, run_id "
        f"FROM comparisons WHERE {LLM_WHERE}"
    ).fetchall()

    # Non-legacy rows keep only the LLM box (geom_a); the official polygon is the same
    # for every row of a place, so take it from any row that stored it.
    ref_geom = {
        place: wkt.loads(g)
        for place, g in con.sql(
            "SELECT place, any_value(geom_b) FROM comparisons WHERE source_a LIKE 'llm:%' "
            "AND source_b = 'sf_planning' AND geom_b IS NOT NULL GROUP BY place"
        ).fetchall()
    }

    by_place: dict[str, list[tuple]] = defaultdict(list)
    no_polygon: set[str] = set()
    for place, iou, err, valid, raw, ga, gb, run_id in rows:
        if valid and iou is not None:
            by_place[place].append((iou, err))
        else:
            no_polygon.add(place)
    no_polygon -= set(by_place)

    places = sorted(
        (
            {
                "place": p,
                "tier": tiers.get(p),
                "n": len(v),
                "medianIou": med([x[0] for x in v]),
                "medianCentroidErrM": round(st.median(x[1] for x in v if x[1] is not None)),
            }
            for p, v in by_place.items()
        ),
        key=lambda r: -r["medianIou"],
    )
    all_iou = [x[0] for v in by_place.values() for x in v]

    # Size and displacement (only rows that stored geometry).
    ratios: list[float] = []
    offsets: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for place, iou, err, valid, raw, ga, gb, run_id in rows:
        b = ref_geom.get(place)
        if not (valid and ga and b is not None):
            continue
        a = wkt.loads(ga)
        ratios.append(area_m2(a) / area_m2(b))
        offsets[place].append(((a.centroid.y - b.centroid.y) * 111_000, (a.centroid.x - b.centroid.x) * 88_000))
    displaced = [
        {
            "place": p,
            "n": len(v),
            "medianEastM": round(st.median(x[1] for x in v)),
            "medianNorthM": round(st.median(x[0] for x in v)),
            "medianAreaRatio": None,
        }
        for p, v in offsets.items()
        if p in ("The Richmond", "The Sunset")
    ]
    for d in displaced:
        d["medianAreaRatio"] = med(
            [
                area_m2(wkt.loads(ga)) / area_m2(ref_geom[place])
                for place, iou, err, valid, raw, ga, gb, run_id in rows
                if place == d["place"] and valid and ga and place in ref_geom
            ],
            1,
        )

    # Self-reported confidence vs accuracy. Raw responses are only kept on the
    # migrated March (legacy-run-*) rows, so this uses those stored responses.
    conf: dict[str, list[float]] = defaultdict(list)
    stored = con.sql(
        "SELECT iou, raw_response FROM comparisons WHERE source_a LIKE 'llm:%' AND source_b = 'sf_planning' "
        "AND cognitive_level = 'L1' AND valid AND iou IS NOT NULL AND raw_response IS NOT NULL"
    ).fetchall()
    for iou, raw in stored:
        try:
            level = json.loads(raw[raw.index("{") : raw.rindex("}") + 1]).get("confidence")
        except (ValueError, json.JSONDecodeError):
            continue
        if level in ("high", "medium", "low"):
            conf[level].append(iou)
    conf_total = sum(len(v) for v in conf.values())

    # Run-to-run repeatability (same model, place and period, 3 runs).
    cells: dict[tuple, list[float]] = defaultdict(list)
    model_of = {r[0]: r[1] for r in con.sql("SELECT DISTINCT run_id, model_id FROM comparisons").fetchall()}
    for place, iou, err, valid, raw, ga, gb, run_id in rows:
        if valid and iou is not None:
            period = run_id.split(":")[0] if ":" in run_id else "baseline"
            cells[(model_of.get(run_id), place, period)].append(iou)
    ranges = [max(v) - min(v) for v in cells.values() if len(v) == 3]

    # Reference sources vs each other (excluding OSM, see REFERENCE_SOURCES note).
    placeholders = ",".join(f"'{s}'" for s in REFERENCE_SOURCES)
    ref = con.sql(
        f"SELECT place, source_a, source_b, iou FROM comparisons WHERE source_a IN ({placeholders}) "
        f"AND source_b IN ({placeholders}) AND source_a < source_b AND iou IS NOT NULL"
    ).fetchall()
    ref_by_place: dict[str, list[float]] = defaultdict(list)
    for place, _, _, iou in ref:
        ref_by_place[place].append(iou)
    ref_places = sorted(
        (
            {"place": p, "n": len(v), "lowestIou": round(min(v), 2), "highestIou": round(max(v), 2)}
            for p, v in ref_by_place.items()
        ),
        key=lambda r: r["lowestIou"],
    )

    # Do models do best where the human reference sources agree? Spearman rank
    # correlation between a place's median LLM IoU and its lowest reference-pair IoU,
    # over places with all three reference pairs.
    llm_iou = {r["place"]: r["medianIou"] for r in places}
    paired = [(llm_iou[r["place"]], r["lowestIou"]) for r in ref_places if r["n"] >= 3 and r["place"] in llm_iou]
    agreement_rho = spearman([a for a, _ in paired], [b for _, b in paired])

    out = {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "referenceSource": "sf_planning",
        "answers": {
            "n": len(all_iou),
            "medianIou": med(all_iou),
            "shareAtLeast05": round(sum(i >= 0.5 for i in all_iou) / len(all_iou), 2),
        },
        "places": places,
        "noOfficialPolygon": sorted(no_polygon),
        "size": {
            "n": len(ratios),
            "medianAreaRatio": med(ratios, 2),
            "shareLargerThanOfficial": round(sum(r > 1 for r in ratios) / len(ratios), 2),
        },
        "displaced": displaced,
        "confidence": {
            "n": conf_total,
            "levels": {k: {"n": len(v), "share": round(len(v) / conf_total, 2), "medianIou": med(v)} for k, v in conf.items()},
        },
        "repeatability": {
            "cells": len(ranges),
            "medianRange": med(ranges),
            "shareOver02": round(sum(r > 0.2 for r in ranges) / len(ranges), 2),
        },
        "referenceAgreement": {
            "sources": list(REFERENCE_SOURCES),
            "places": ref_places,
            "rankCorrelation": round(agreement_rho, 2),
            "correlationPlaces": len(paired),
        },
    }
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
