"""Export per-period, per-model and per-tier medians for the Next.js dashboard.

Groups LLM-vs-GT comparisons into evaluation periods so a re-run (e.g. the
November 2026 run, tagged with ``run_batch_eval.py --run-tag 2026-11``) can be
shown side by side with the original baseline.

Period rules:
  - run_id ``"<tag>:<model>-<gt>-run<n>"``  -> period ``<tag>``
  - untagged batch run_id                   -> period = created_at month (YYYY-MM)
  - ``legacy-run-*`` rows are skipped (migrated duplicates of the same responses)

Usage:
    uv run python scripts/export_run_summary.py --db duckdb
    uv run python scripts/export_run_summary.py --db duckdb --out path/to/run-summary.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from corpus import load_corpus
from db_factory import get_db
from model_registry import load_models
from run_period import period_label, period_of

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUT = REPO_ROOT / "src" / "content" / "spatial-eval" / "run-summary.json"
def _round(value: float | None, digits: int) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _stats(group: pd.DataFrame) -> dict:
    valid = group[group["valid"]]
    return {
        "n": int(len(group)),
        "nValid": int(len(valid)),
        "medianIou": _round(valid["iou"].median(), 3),
        "medianCentroidErrM": _round(valid["centroid_err_m"].median(), 0),
    }


def summarize(
    df: pd.DataFrame,
    tiers: dict[str, int],
    registry: list[dict],
    reference_source: str,
    variant_id: str,
) -> dict:
    """Build the run-summary payload from a comparisons DataFrame.

    Args:
        df: Columns run_id, place, source_a, source_b, variant_id, model_id,
            iou, centroid_err_m, valid, created_at.
        tiers: Place name -> tier (1-4) for active corpus places.
        registry: Entries from data/models.json.
        reference_source: GT source to score against (e.g. "sf_planning").
        variant_id: Prompt variant to include (e.g. "baseline_v2").
    """
    meta = {m["model_id"]: m for m in registry}
    rows = df[
        df["source_a"].str.startswith("llm:")
        & (df["source_b"] == reference_source)
        & (df["variant_id"] == variant_id)
        & df["place"].isin(tiers.keys())
    ].copy()
    rows["model_id"] = rows["source_a"].str.removeprefix("llm:")
    rows["period"] = [period_of(r, c) for r, c in zip(rows["run_id"], rows["created_at"])]
    rows = rows[rows["period"].notna()]
    rows["tier"] = rows["place"].map(tiers)

    periods = []
    for period, p_rows in sorted(rows.groupby("period"), key=lambda kv: kv[0]):
        models = []
        for model_id, m_rows in p_rows.groupby("model_id"):
            entry = meta.get(model_id, {})
            models.append({
                "modelId": model_id,
                "displayName": entry.get("display_name", model_id),
                "provider": entry.get("provider"),
                "successorOf": entry.get("successor_of"),
                **_stats(m_rows),
                "places": int(m_rows["place"].nunique()),
                "tiers": [
                    {"tier": int(tier), **_stats(t_rows)}
                    for tier, t_rows in sorted(m_rows.groupby("tier"), key=lambda kv: kv[0])
                ],
            })
        models.sort(key=lambda m: (m["medianIou"] is None, -(m["medianIou"] or 0)))
        created = pd.to_datetime(p_rows["created_at"])
        periods.append({
            "id": period,
            "label": period_label(period),
            "firstRunAt": created.min().date().isoformat(),
            "lastRunAt": created.max().date().isoformat(),
            "models": models,
        })

    return {
        "generatedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "referenceSource": reference_source,
        "variantId": variant_id,
        "placeCount": len(tiers),
        "periods": periods,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", required=True, choices=["sqlite", "duckdb"])
    parser.add_argument("--gt-source", default="sf_planning")
    parser.add_argument("--variant", default="baseline_v2")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    db = get_db(args.db)
    records = [r.model_dump() for r in db.fetch_comparisons(source_b=args.gt_source)]
    db.close()

    tiers = {p["name"]: int(p["tier"]) for p in load_corpus()}
    payload = summarize(pd.DataFrame(records), tiers, load_models(), args.gt_source, args.variant)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {args.out} ({len(payload['periods'])} period(s))")


if __name__ == "__main__":
    main()
