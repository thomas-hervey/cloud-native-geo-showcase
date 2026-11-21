import pytest
import json
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_parse_valid_response():
    from llm_client import parse_bbox_response
    raw = json.dumps({
        "place": "The Richmond",
        "centroid_lat": 37.778,
        "centroid_lon": -122.476,
        "bbox_north": 37.785,
        "bbox_south": 37.770,
        "bbox_east": -122.450,
        "bbox_west": -122.510,
        "confidence": "high",
        "notes": ""
    })
    result = parse_bbox_response(raw)
    assert result is not None
    assert result["centroid_lat"] == pytest.approx(37.778)
    assert result["bbox_north"] > result["bbox_south"]


def test_parse_invalid_json_returns_none():
    from llm_client import parse_bbox_response
    assert parse_bbox_response("not json at all") is None


def test_parse_impossible_coordinates_returns_none():
    from llm_client import parse_bbox_response
    # bbox_north < bbox_south is impossible
    raw = json.dumps({
        "place": "Test", "centroid_lat": 37.7, "centroid_lon": -122.4,
        "bbox_north": 37.0,  # LESS than south — invalid
        "bbox_south": 37.8,
        "bbox_east": -122.3, "bbox_west": -122.5,
        "confidence": "low", "notes": ""
    })
    assert parse_bbox_response(raw) is None
