import pytest
from pathlib import Path
import json
import sys

EVAL_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(EVAL_DIR))


def test_datasf_file_exists():
    p = EVAL_DIR / "data" / "reference" / "datasf_neighborhoods.geojson"
    assert p.exists(), "Run: download DataSF GeoJSON"


def test_ground_truth_loads_richmond():
    from ground_truth import GroundTruth
    gt = GroundTruth()
    geom = gt.get_polygon("The Richmond")
    assert geom is not None
    assert geom.geom_type in ("Polygon", "MultiPolygon")


def test_ground_truth_returns_none_for_unknown():
    from ground_truth import GroundTruth
    gt = GroundTruth()
    assert gt.get_polygon("Atlantis") is None
