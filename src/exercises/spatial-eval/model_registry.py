"""LLM model registry — load and query data/models.json.

Provides a single source of truth for which models are benchmarked and their
display metadata. Used by run_batch_eval.py (default model list) and app.py
(display names and provider grouping in the leaderboard).
"""
from __future__ import annotations

import json
from pathlib import Path

_DEFAULT_REGISTRY = Path(__file__).parent / "data" / "models.json"


def load_models(path: Path = _DEFAULT_REGISTRY) -> list[dict]:
    """Load and validate the model registry JSON.

    Args:
        path: Path to models.json. Defaults to data/models.json.

    Returns:
        List of model entry dicts, each with keys:
        model_id, display_name, provider, tier, default, and optionally
        successor_of (the model_id of a retired model this one replaces in
        period-over-period comparisons).

    Raises:
        FileNotFoundError: if path does not exist.
        ValueError: if JSON is malformed or missing 'models' key.
    """
    if not path.exists():
        raise FileNotFoundError(f"Model registry not found: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in model registry {path}: {e}") from e
    if "models" not in data:
        raise ValueError(f"Model registry {path} must have a top-level 'models' key")
    return data["models"]


def default_models(path: Path = _DEFAULT_REGISTRY) -> list[str]:
    """Return model_ids for all entries with default=True, in registry order.

    Args:
        path: Path to models.json. Defaults to data/models.json.

    Returns:
        List of LiteLLM model ID strings for default-enabled models.
    """
    return [m["model_id"] for m in load_models(path) if m.get("default")]


def display_name(model_id: str, path: Path = _DEFAULT_REGISTRY) -> str:
    """Return human-friendly display name for a model_id, or model_id if unknown.

    Args:
        model_id: LiteLLM model ID string (e.g. "gemini/gemini-1.5-pro").
        path: Path to models.json.

    Returns:
        display_name from registry, or model_id unchanged if not found.
    """
    bare_id = model_id.removeprefix("llm:")
    for m in load_models(path):
        if m["model_id"] == bare_id:
            return m["display_name"]
    return model_id
