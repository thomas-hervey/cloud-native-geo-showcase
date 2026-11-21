"""Tagged re-runs must stay separate from the baseline run (ids and cache)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import config
import llm_client
import sources.llm as llm_source_module
from llm_client import _cache_path, responses_dir_for, tagged_run_id, validate_run_tag
from sources.llm import LLMSource


@pytest.fixture
def responses_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(llm_client, "RESPONSES_DIR", tmp_path)
    monkeypatch.setattr(config, "LLM_RESPONSES_DIR", tmp_path)
    return tmp_path


def _write_cached(path: Path, centroid_lat: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "_valid": True, "centroid_lat": centroid_lat, "centroid_lon": -122.42,
        "bbox_north": 37.77, "bbox_south": 37.75, "bbox_east": -122.40, "bbox_west": -122.43,
    }))


@pytest.mark.parametrize("tag", ["2026-11", "nov.2026", "run_2"])
def test_should_accept_safe_run_tags(tag: str) -> None:
    assert validate_run_tag(tag) == tag


@pytest.mark.parametrize("tag", ["", "../april", "a/b", "x" * 40, "-lead"])
def test_should_reject_unsafe_run_tags(tag: str) -> None:
    with pytest.raises(ValueError):
        validate_run_tag(tag)


def test_should_keep_untagged_run_id_format_unchanged() -> None:
    assert tagged_run_id("gpt-4o", "sf_planning", 2) == "gpt-4o-sf_planning-run2"


def test_should_prefix_tagged_run_id() -> None:
    assert tagged_run_id("gemini/x", "sf_planning", 1, "2026-11") == "2026-11:gemini/x-sf_planning-run1"


def test_should_use_tag_subdirectory_for_cache(responses_dir: Path) -> None:
    assert responses_dir_for(None) == responses_dir
    assert responses_dir_for("2026-11") == responses_dir / "2026-11"
    path = _cache_path("The Mission", "gpt-4o", 1, "baseline_v2", responses_dir_for("2026-11"))
    assert path.parent == responses_dir / "2026-11"


def test_untagged_source_should_read_baseline_cache(responses_dir: Path) -> None:
    _write_cached(responses_dir / "the_mission__gpt-4o__run1__variant-baseline_v2.json", 37.76)
    src = LLMSource("gpt-4o", run=1)
    assert src.get_centroid("The Mission").y == pytest.approx(37.76)


def test_tagged_source_should_not_read_baseline_cache(
    responses_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_cached(responses_dir / "the_mission__gpt-4o__run1__variant-baseline_v2.json", 37.76)
    _write_cached(responses_dir / "the_mission__gpt-4o__run1.json", 37.76)
    calls: list[Path | None] = []

    def fake_query(place, model, **kwargs):  # noqa: ANN001, ANN003
        calls.append(kwargs.get("responses_dir"))
        return None

    monkeypatch.setattr(llm_source_module, "query_model", fake_query)
    src = LLMSource("gpt-4o", run=1, run_tag="2026-11")
    assert src.get_polygon("The Mission") is None
    assert calls == [responses_dir / "2026-11"]


def test_tagged_source_should_read_its_own_cache(responses_dir: Path) -> None:
    _write_cached(responses_dir / "the_mission__gpt-4o__run1__variant-baseline_v2.json", 37.76)
    _write_cached(responses_dir / "2026-11" / "the_mission__gpt-4o__run1__variant-baseline_v2.json", 37.70)
    src = LLMSource("gpt-4o", run=1, run_tag="2026-11")
    assert src.get_centroid("The Mission").y == pytest.approx(37.70)
