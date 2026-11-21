"""Tests for evaluation-period grouping used by the Streamlit period selector."""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from run_period import (
    available_periods,
    compare_periods,
    filter_to_period,
    period_label,
    period_of,
    with_period,
)

MARCH = datetime(2026, 3, 21, 12)
NOV = datetime(2026, 11, 12, 9)


def _row(run_id: str, model: str, place: str, iou: float, err: float, created: datetime,
         source_b: str = "sf_planning", variant: str = "baseline_v2") -> dict:
    return {"run_id": run_id, "source_a": f"llm:{model}", "source_b": source_b, "place": place,
            "variant_id": variant, "iou": iou, "centroid_err_m": err, "created_at": created,
            "valid": True}


def _gt_row(created: datetime) -> dict:
    return {"run_id": "gt-compare", "source_a": "osm", "source_b": "sf_planning",
            "place": "Chinatown", "variant_id": "baseline_v2", "iou": 0.9,
            "centroid_err_m": 10, "created_at": created, "valid": True}


def test_should_keep_legacy_rows_under_created_month_only_when_asked() -> None:
    assert period_of("legacy-run-1-abc", MARCH) is None
    assert period_of("legacy-run-1-abc", MARCH, include_legacy=True) == "2026-03"


def test_should_prefer_tag_over_created_at() -> None:
    assert period_of("2026-11:gpt-4o-sf_planning-run1", MARCH) == "2026-11"
    assert period_of("gpt-4o-sf_planning-run1", pd.NaT) is None


@pytest.mark.parametrize(("period", "label"), [("2026-03", "March 2026"), ("pilot", "pilot")])
def test_should_label_month_periods_and_pass_through_tags(period: str, label: str) -> None:
    assert period_label(period) == label


def test_should_list_llm_periods_and_keep_gt_rows_in_every_period() -> None:
    df = with_period(pd.DataFrame([
        _row("gpt-4o-sf_planning-run1", "gpt-4o", "Chinatown", 0.4, 300, MARCH),
        _row("2026-11:gpt-4o-sf_planning-run1", "gpt-4o", "Chinatown", 0.6, 100, NOV),
        _gt_row(datetime(2026, 1, 5)),
    ]))
    assert available_periods(df) == ["2026-03", "2026-11"]

    nov = filter_to_period(df, "2026-11")
    assert sorted(nov["run_id"]) == ["2026-11:gpt-4o-sf_planning-run1", "gt-compare"]
    assert len(filter_to_period(df, None)) == 3


def test_should_compare_medians_on_shared_places_only() -> None:
    df = with_period(pd.DataFrame([
        _row("gpt-4o-sf_planning-run1", "gpt-4o", "Chinatown", 0.4, 300, MARCH),
        _row("gpt-4o-sf_planning-run2", "gpt-4o", "Chinatown", 0.2, 500, MARCH),
        _row("gpt-4o-sf_planning-run1", "gpt-4o", "The Mission", 0.0, 9999, MARCH),
        _row("legacy-run-1-abc", "gpt-4o", "Chinatown", 0.0, 9999, MARCH),
        _row("2026-11:gpt-4o-sf_planning-run1", "gpt-4o", "Chinatown", 0.5, 200, NOV),
        _row("2026-11:gpt-4o-osm-run1", "gpt-4o", "Chinatown", 0.0, 9999, NOV, source_b="osm"),
        _row("2026-11:gpt-4o-sf_planning-run1", "gpt-4o", "Chinatown", 0.0, 9999, NOV,
             variant="alias_explicit"),
    ]))
    out = compare_periods(df, "2026-03", "2026-11", "sf_planning", ["baseline_v2"])

    assert len(out) == 1
    row = out.iloc[0]
    assert (row["places"], row["n_baseline"], row["n_current"]) == (1, 2, 1)
    assert row["iou_baseline"] == pytest.approx(0.3)
    assert row["iou_delta"] == pytest.approx(0.2)
    assert row["err_delta"] == pytest.approx(-200)


def test_should_pair_successor_with_retired_model() -> None:
    df = with_period(pd.DataFrame([
        _row("old-model-sf_planning-run1", "old-model", "Chinatown", 0.3, 400, MARCH),
        _row("2026-11:new-model-sf_planning-run1", "new-model", "Chinatown", 0.5, 200, NOV),
        _row("2026-11:orphan-sf_planning-run1", "orphan", "Chinatown", 0.9, 10, NOV),
    ]))
    out = compare_periods(df, "2026-03", "2026-11", "sf_planning", ["baseline_v2"],
                          successors={"new-model": "old-model"})

    assert out[["model", "baseline_model"]].values.tolist() == [["new-model", "old-model"]]


def test_should_return_empty_frame_when_no_overlap() -> None:
    df = with_period(pd.DataFrame([
        _row("gpt-4o-sf_planning-run1", "gpt-4o", "Chinatown", 0.4, 300, MARCH),
    ]))
    out = compare_periods(df, "2026-03", "2026-11", "sf_planning", ["baseline_v2"])
    assert out.empty
    assert "iou_delta" in out.columns
