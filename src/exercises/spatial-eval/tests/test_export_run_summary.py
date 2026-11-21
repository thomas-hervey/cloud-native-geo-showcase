"""Tests for the per-period run summary exported to the Next.js dashboard."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from scripts.export_run_summary import period_of, summarize

MARCH = datetime(2026, 3, 21, 12)
NOV = datetime(2026, 11, 11, 12)
TIERS = {"Chinatown": 1, "The Mission": 2}
REGISTRY = [
    {"model_id": "gpt-4o", "display_name": "GPT-4o", "provider": "openai"},
    {"model_id": "new-model", "display_name": "New", "provider": "openai", "successor_of": "old-model"},
]


def _row(run_id: str, place: str, model: str, iou: float, err: float, created: datetime,
         valid: bool = True, source_b: str = "sf_planning", variant: str = "baseline_v2") -> dict:
    return {
        "run_id": run_id, "place": place, "source_a": f"llm:{model}", "source_b": source_b,
        "variant_id": variant, "iou": iou, "centroid_err_m": err, "valid": valid,
        "created_at": created,
    }


def test_should_derive_period_from_tag_or_month() -> None:
    assert period_of("2026-11:gpt-4o-sf_planning-run1", MARCH) == "2026-11"
    assert period_of("gpt-4o-sf_planning-run1", MARCH) == "2026-03"
    assert period_of("legacy-run-0-abc", MARCH) is None


def test_should_split_periods_and_compute_medians() -> None:
    df = pd.DataFrame([
        _row("gpt-4o-sf_planning-run1", "Chinatown", "gpt-4o", 0.6, 100, MARCH),
        _row("gpt-4o-sf_planning-run2", "Chinatown", "gpt-4o", 0.4, 300, MARCH),
        _row("gpt-4o-sf_planning-run1", "The Mission", "gpt-4o", 0.2, 500, MARCH),
        _row("2026-11:gpt-4o-sf_planning-run1", "Chinatown", "gpt-4o", 0.8, 50, NOV),
        _row("legacy-run-0-x", "Chinatown", "gpt-4o", 0.0, 9999, MARCH),
        _row("gpt-4o-osm-run1", "Chinatown", "gpt-4o", 0.0, 9999, MARCH, source_b="osm"),
        _row("gpt-4o-sf_planning-run1", "Chinatown", "gpt-4o", 0.0, 9999, MARCH, variant="alias_explicit"),
    ])
    out = summarize(df, TIERS, REGISTRY, "sf_planning", "baseline_v2")

    assert [p["id"] for p in out["periods"]] == ["2026-03", "2026-11"]
    march = out["periods"][0]["models"][0]
    assert march["n"] == 3
    assert march["medianIou"] == 0.4
    assert march["medianCentroidErrM"] == 300
    assert [(t["tier"], t["n"], t["medianIou"]) for t in march["tiers"]] == [(1, 2, 0.5), (2, 1, 0.2)]
    assert out["periods"][1]["models"][0]["medianIou"] == 0.8
    assert out["periods"][1]["label"] == "November 2026"


def test_should_exclude_invalid_rows_from_medians_but_count_them() -> None:
    df = pd.DataFrame([
        _row("gpt-4o-sf_planning-run1", "Chinatown", "gpt-4o", 0.5, 100, MARCH),
        _row("gpt-4o-sf_planning-run2", "Chinatown", "gpt-4o", None, None, MARCH, valid=False),
    ])
    model = summarize(df, TIERS, REGISTRY, "sf_planning", "baseline_v2")["periods"][0]["models"][0]
    assert (model["n"], model["nValid"], model["medianIou"]) == (2, 1, 0.5)


def test_should_pass_through_successor_label() -> None:
    df = pd.DataFrame([_row("2026-11:new-model-sf_planning-run1", "Chinatown", "new-model", 0.5, 1, NOV)])
    model = summarize(df, TIERS, REGISTRY, "sf_planning", "baseline_v2")["periods"][0]["models"][0]
    assert model["successorOf"] == "old-model"
    assert model["displayName"] == "New"
