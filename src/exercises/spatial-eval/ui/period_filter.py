"""Sidebar control for choosing which evaluation period (run date) to view."""
from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from run_period import period_label


@dataclass(frozen=True)
class PeriodSelection:
    """The period shown everywhere, plus an optional earlier period to compare against."""

    current: str | None
    baseline: str | None


def render_period_filter(periods: list[str]) -> PeriodSelection:
    """Render the evaluation-period selectors and return the selection.

    Args:
        periods: Available period ids, oldest first.
    """
    st.sidebar.header("Evaluation Period")
    if not periods:
        st.sidebar.caption("No dated LLM runs found.")
        return PeriodSelection(current=None, baseline=None)

    current = st.sidebar.selectbox(
        "Show results from",
        options=periods,
        index=len(periods) - 1,
        format_func=period_label,
        key="period_current",
    )
    others = [p for p in periods if p != current]
    if not others:
        st.sidebar.caption("Only one evaluation period recorded so far.")
        return PeriodSelection(current=current, baseline=None)

    baseline = st.sidebar.selectbox(
        "Compare against",
        options=[None, *others],
        index=1,
        format_func=lambda p: "— none —" if p is None else period_label(p),
        key="period_baseline",
        help="Adds a period-over-period table to the Leaderboard tab.",
    )
    return PeriodSelection(current=current, baseline=baseline)
