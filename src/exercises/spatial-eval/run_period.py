"""Evaluation periods: group comparison rows by when the LLM answers were collected.

A period is either an explicit run tag (``run_batch_eval.py --run-tag 2026-11``
stores ``run_id = "2026-11:<model>-<gt>-run<n>"``) or, for untagged rows, the
``created_at`` month (``YYYY-MM``).

Shared by ``scripts/export_run_summary.py`` (Next.js dashboard) and the
Streamlit period selector so both agree on what "the March run" means.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd

LEGACY_PREFIX = "legacy-run-"
LLM_PREFIX = "llm:"


def period_of(
    run_id: str,
    created_at: datetime | pd.Timestamp | None,
    include_legacy: bool = False,
) -> str | None:
    """Return the evaluation period for a comparison row.

    Args:
        run_id: The comparisons.run_id value.
        created_at: Row insert timestamp, used for untagged rows.
        include_legacy: ``legacy-run-*`` rows are migrated duplicates of batch
            responses. Aggregates skip them (None) to avoid double counting;
            the UI keeps them under their created_at month so nothing it
            showed before disappears.
    """
    if run_id.startswith(LEGACY_PREFIX) and not include_legacy:
        return None
    if ":" in run_id:
        return run_id.split(":", 1)[0]
    if created_at is None or pd.isna(created_at):
        return None
    return pd.Timestamp(created_at).strftime("%Y-%m")


def period_label(period: str) -> str:
    """Human label for a period id: ``"2026-03"`` -> ``"March 2026"``; tags pass through."""
    try:
        return datetime.strptime(period, "%Y-%m").strftime("%B %Y")
    except ValueError:
        return period


def with_period(df: pd.DataFrame, include_legacy: bool = True) -> pd.DataFrame:
    """Return a copy of ``df`` with a ``period`` column (None where undeterminable)."""
    out = df.copy()
    out["period"] = [
        period_of(str(r), c, include_legacy=include_legacy)
        for r, c in zip(out["run_id"], out["created_at"])
    ]
    return out


def available_periods(df: pd.DataFrame) -> list[str]:
    """Distinct periods that contain LLM rows, oldest first."""
    llm = df[df["source_a"].str.startswith(LLM_PREFIX)]
    return sorted(p for p in llm["period"].dropna().unique())


def filter_to_period(df: pd.DataFrame, period: str | None) -> pd.DataFrame:
    """Keep LLM rows from ``period``; GT-vs-GT rows are period-independent and always kept."""
    if period is None:
        return df
    is_llm = df["source_a"].str.startswith(LLM_PREFIX)
    return df[~is_llm | (df["period"] == period)]


def compare_periods(
    df: pd.DataFrame,
    baseline: str,
    current: str,
    reference_gt: str,
    variants: list[str],
    successors: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Per-model median IoU and centroid error in two periods, on shared places only.

    Legacy-migrated rows are excluded, matching ``scripts/export_run_summary.py``.

    Args:
        df: Valid comparison rows with a ``period`` column.
        baseline: Earlier period id (e.g. "2026-03").
        current: Later period id (e.g. "2026-11").
        reference_gt: GT source both periods are scored against.
        variants: Prompt variants to include.
        successors: model_id -> retired model_id it replaces, so a successor in
            ``current`` is compared against its predecessor in ``baseline``.

    Returns:
        One row per model pair: model, baseline_model, places, n_baseline,
        n_current, iou_baseline, iou_current, iou_delta, err_baseline,
        err_current, err_delta. Empty if no model appears in both periods.
    """
    successors = successors or {}
    rows = df[
        df["source_a"].str.startswith(LLM_PREFIX)
        & (df["source_b"] == reference_gt)
        & df["variant_id"].isin(variants)
        & df["period"].isin([baseline, current])
        # legacy-run-* rows duplicate batch responses; counting them skews medians.
        & ~df["run_id"].astype(str).str.startswith(LEGACY_PREFIX)
    ].copy()
    rows["model"] = rows["source_a"].str.removeprefix(LLM_PREFIX)
    base = rows[rows["period"] == baseline]
    cur = rows[rows["period"] == current]
    base_models = set(base["model"])

    out = []
    for model, cur_rows in cur.groupby("model"):
        base_model = model if model in base_models else successors.get(model)
        if base_model not in base_models:
            continue
        base_rows = base[base["model"] == base_model]
        shared = set(cur_rows["place"]) & set(base_rows["place"])
        if not shared:
            continue
        b = base_rows[base_rows["place"].isin(shared)]
        c = cur_rows[cur_rows["place"].isin(shared)]
        iou_b, iou_c = b["iou"].median(), c["iou"].median()
        err_b, err_c = b["centroid_err_m"].median(), c["centroid_err_m"].median()
        out.append({
            "model": model,
            "baseline_model": base_model,
            "places": len(shared),
            "n_baseline": len(b),
            "n_current": len(c),
            "iou_baseline": iou_b,
            "iou_current": iou_c,
            "iou_delta": iou_c - iou_b,
            "err_baseline": err_b,
            "err_current": err_c,
            "err_delta": err_c - err_b,
        })
    columns = ["model", "baseline_model", "places", "n_baseline", "n_current",
               "iou_baseline", "iou_current", "iou_delta",
               "err_baseline", "err_current", "err_delta"]
    return pd.DataFrame(out, columns=columns).sort_values("iou_current", ascending=False,
                                                          ignore_index=True)
