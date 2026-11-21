"""Bradley-Terry pairwise ranking for LLM spatial-eval models.

Pure Python module — no Streamlit dependency. Called by ui/tabs/leaderboard.py.

The core algorithm:
  1. Average composite_score per (source_a, place) to collapse multiple runs.
  2. For each shared place, compare all model pairs: higher avg score wins.
  3. Ties (equal avg score) are dropped.
  4. Feed (winner_idx, loser_idx) pairs to choix.ilsr_pairwise.
  5. Return log-scale skill parameters sorted descending.
"""
from __future__ import annotations

import itertools
import logging

import pandas as pd

logger = logging.getLogger(__name__)

_EMPTY = pd.DataFrame(columns=["source_a", "bt_score"])


def rank_models(df: pd.DataFrame) -> pd.DataFrame:
    """Fit Bradley-Terry model from pairwise composite_score comparisons.

    Expects a DataFrame already filtered to a single reference_gt and LLM
    sources only. Averages composite_score per (source_a, place) before
    constructing pairs to handle multiple runs per model per place correctly.

    Args:
        df: DataFrame with columns [source_a, place, composite_score].
            Must contain >=2 distinct source_a values with shared place coverage.

    Returns:
        DataFrame with columns [source_a, bt_score] sorted by bt_score descending.
        Returns empty DataFrame if insufficient data or fitting fails.
    """
    import choix

    models = df["source_a"].unique()
    if len(models) < 2:
        return _EMPTY.copy()

    # Step 1: Average composite_score per (model, place) to collapse multiple runs.
    avg = df.groupby(["source_a", "place"])["composite_score"].mean().reset_index()

    # Step 2: Map model names to integer indices required by choix.
    model_list = sorted(models)
    model_idx = {m: i for i, m in enumerate(model_list)}

    # Step 3: Build pairwise (winner, loser) tuples from shared places.
    pairs: list[tuple[int, int]] = []
    for place, place_rows in avg.groupby("place"):
        if len(place_rows) < 2:
            continue  # place not shared by >=2 models
        scores = dict(zip(place_rows["source_a"], place_rows["composite_score"]))
        for ma, mb in itertools.combinations(place_rows["source_a"].tolist(), 2):
            sa, sb = scores[ma], scores[mb]
            if sa > sb:
                pairs.append((model_idx[ma], model_idx[mb]))
            elif sb > sa:
                pairs.append((model_idx[mb], model_idx[ma]))
            # equal scores: tie dropped

    if not pairs:
        return _EMPTY.copy()

    # Step 4: Fit BT model. alpha=0.01 regularization prevents failures from
    # disconnected comparison graphs or non-convergence on sparse data.
    # Catch any remaining exception (singular matrix, etc.).
    try:
        params = choix.ilsr_pairwise(len(model_list), pairs, alpha=0.01)
    except Exception as exc:
        logger.warning("Bradley-Terry fitting failed: %s", exc)
        return _EMPTY.copy()

    # Step 5: Return sorted result.
    return (
        pd.DataFrame({"source_a": model_list, "bt_score": params})
        .sort_values("bt_score", ascending=False)
        .reset_index(drop=True)
    )
