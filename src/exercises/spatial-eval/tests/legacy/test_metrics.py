import pytest
from shapely.geometry import box, Point
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_iou_perfect_overlap():
    from metrics.boundary_iou import compute_iou
    geom = box(-122.5, 37.7, -122.4, 37.8)
    assert compute_iou(geom, geom) == pytest.approx(1.0)


def test_iou_no_overlap():
    from metrics.boundary_iou import compute_iou
    a = box(-122.5, 37.7, -122.4, 37.8)
    b = box(-122.0, 37.0, -121.9, 37.1)
    assert compute_iou(a, b) == pytest.approx(0.0)


def test_iou_partial_overlap():
    from metrics.boundary_iou import compute_iou
    a = box(0, 0, 2, 2)   # area = 4
    b = box(1, 1, 3, 3)   # area = 4, overlap = 1
    # IoU = 1 / (4 + 4 - 1) = 1/7
    assert compute_iou(a, b) == pytest.approx(1/7, abs=1e-6)


def test_centroid_error_zero():
    from metrics.centroid_error import compute_centroid_error_m
    p = Point(-122.47, 37.78)
    assert compute_centroid_error_m(p, p) == pytest.approx(0.0, abs=1.0)


def test_centroid_error_nonzero():
    from metrics.centroid_error import compute_centroid_error_m
    p1 = Point(-122.47, 37.78)
    p2 = Point(-122.47, 37.79)  # ~1.1 km north
    err = compute_centroid_error_m(p1, p2)
    assert 1000 < err < 1500  # roughly 1.1 km


def test_composite_score_perfect():
    from metrics.composite_score import compute_composite
    assert compute_composite(iou=1.0, centroid_error_m=0.0) == pytest.approx(1.0, abs=0.01)


def test_composite_score_worst():
    from metrics.composite_score import compute_composite
    score = compute_composite(iou=0.0, centroid_error_m=5000.0)
    assert score < 0.2
