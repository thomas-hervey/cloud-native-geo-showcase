"""Unit tests for model_registry.py."""
from __future__ import annotations

import json
from pathlib import Path
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_registry(tmp_path: Path, entries: list[dict]) -> Path:
    p = tmp_path / "models.json"
    p.write_text(json.dumps({"models": entries}))
    return p


_VALID_ENTRY = {
    "model_id": "claude-haiku-4-5",
    "display_name": "Claude Haiku 4.5",
    "provider": "anthropic",
    "tier": 1,
    "default": True,
}


# ---------------------------------------------------------------------------
# Tests: load_models
# ---------------------------------------------------------------------------

def test_load_models_returns_list_of_dicts(tmp_path):
    """load_models returns one dict per entry in the registry."""
    reg_path = _write_registry(tmp_path, [_VALID_ENTRY])
    from model_registry import load_models
    models = load_models(reg_path)
    assert len(models) == 1
    assert models[0]["model_id"] == "claude-haiku-4-5"


def test_load_models_all_entries_have_required_keys(tmp_path):
    """Every entry has model_id, display_name, provider, tier, default."""
    entries = [
        _VALID_ENTRY,
        {**_VALID_ENTRY, "model_id": "gpt-4o-mini", "display_name": "GPT-4o Mini",
         "provider": "openai", "tier": 1, "default": True},
    ]
    reg_path = _write_registry(tmp_path, entries)
    from model_registry import load_models
    required = {"model_id", "display_name", "provider", "tier", "default"}
    for m in load_models(reg_path):
        assert required.issubset(m.keys()), f"Missing keys in {m}"


def test_load_models_missing_file_raises_file_not_found(tmp_path):
    """load_models raises FileNotFoundError for a missing path."""
    from model_registry import load_models
    with pytest.raises(FileNotFoundError):
        load_models(tmp_path / "nonexistent.json")


def test_load_models_invalid_json_raises_value_error(tmp_path):
    """load_models raises ValueError if JSON is malformed."""
    bad = tmp_path / "models.json"
    bad.write_text("not json")
    from model_registry import load_models
    with pytest.raises(ValueError):
        load_models(bad)


def test_load_models_missing_models_key_raises_value_error(tmp_path):
    """load_models raises ValueError if top-level 'models' key is absent."""
    p = tmp_path / "models.json"
    p.write_text(json.dumps({"wrong_key": []}))
    from model_registry import load_models
    with pytest.raises(ValueError, match="'models'"):
        load_models(p)


# ---------------------------------------------------------------------------
# Tests: default_models
# ---------------------------------------------------------------------------

def test_default_models_returns_only_default_true_ids(tmp_path):
    """default_models returns model_ids for entries with default=True."""
    entries = [
        _VALID_ENTRY,
        {**_VALID_ENTRY, "model_id": "non-default", "default": False},
    ]
    reg_path = _write_registry(tmp_path, entries)
    from model_registry import default_models
    result = default_models(reg_path)
    assert result == ["claude-haiku-4-5"]


def test_default_models_preserves_order(tmp_path):
    """default_models returns model_ids in registry file order."""
    entries = [
        {**_VALID_ENTRY, "model_id": "model-b", "default": True},
        {**_VALID_ENTRY, "model_id": "model-a", "default": True},
    ]
    reg_path = _write_registry(tmp_path, entries)
    from model_registry import default_models
    result = default_models(reg_path)
    assert result == ["model-b", "model-a"]
