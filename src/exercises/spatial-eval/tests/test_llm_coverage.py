import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from ui.tabs.source_config import _llm_coverage_summary


def test_llm_coverage_summary_reads_baseline_and_legacy_only(tmp_path):
    """Test that coverage summary only loads official legacy (.json) and baseline_v2 responses.

    It should explicitly ignore experimental variants like geojson_polygon to ensure the Map
    and Coverage Matrix stay perfectly in sync.
    """

    mock_config = MagicMock()
    mock_config.LLM_RESPONSES_DIR = tmp_path

    prefix = "test_place__test_model__run1"

    # Legacy Baseline: only has a centroid
    legacy_path = tmp_path / f"{prefix}.json"
    legacy_path.write_text(json.dumps({
        "_valid": True,
        "centroid_lat": 1.0,
        "centroid_lon": 1.0,
        "place": "Test Place"
    }))

    # Active Baseline Version 2: has a polygon/bbox
    v2_path = tmp_path / f"{prefix}__variant-baseline_v2.json"
    v2_path.write_text(json.dumps({
        "_valid": True,
        "polygon_wkt": "POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))",
        "place": "Test Place"
    }))

    # Experimental Variant: should be IGNORED
    random_path = tmp_path / f"{prefix}__variant-geojson_polygon.json"
    random_path.write_text(json.dumps({
        "_valid": True,
        "bbox_north": 1, "bbox_south": 0, "bbox_east": 1, "bbox_west": 0,
        "place": "Test Place"
    }))

    # Run the function
    with patch("ui.tabs.source_config.config", mock_config):
        status, icons, resolved = _llm_coverage_summary(
            "Test Place", "test_model", runs=1, variant_ids=["baseline_v2"]
        )

    assert "⬠" in icons   # Found polygon from baseline_v2
    assert "•" in icons   # Found centroid from legacy
    assert "⬚" not in icons  # Ignored the bbox hidden in the experimental variant
    assert resolved == "Test Place"
