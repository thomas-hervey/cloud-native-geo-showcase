import pytest
from shapely.geometry import box, Point
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_compare_identical_geometries():
    from metrics.spatial_comparison import compare_geometries
    geom = box(-122.5, 37.7, -122.4, 37.8)
    m = compare_geometries(geom, geom)
    assert m.iou == pytest.approx(1.0)
    assert m.overlap_pct_a == pytest.approx(1.0)
    assert m.overlap_pct_b == pytest.approx(1.0)
    assert m.de9im_label == "equals"
    assert m.hausdorff_m == pytest.approx(0.0, abs=1.0)
    assert m.centroid_error_m == pytest.approx(0.0, abs=1.0)
    assert m.composite == pytest.approx(1.0, abs=0.01)


def test_compare_disjoint_geometries():
    from metrics.spatial_comparison import compare_geometries
    a = box(-122.5, 37.7, -122.4, 37.8)
    b = box(-121.0, 36.0, -120.9, 36.1)
    m = compare_geometries(a, b)
    assert m.iou == pytest.approx(0.0)
    assert m.de9im_label == "disjoint"
    assert m.composite < 0.1


def test_compare_partial_overlap():
    from metrics.spatial_comparison import compare_geometries
    a = box(0, 0, 2, 2)
    b = box(1, 1, 3, 3)
    m = compare_geometries(a, b)
    assert m.iou == pytest.approx(1/7, abs=1e-6)
    assert m.overlap_pct_a == pytest.approx(0.25, abs=1e-6)
    assert m.overlap_pct_b == pytest.approx(0.25, abs=1e-6)
    assert m.de9im_label == "overlaps"


def test_compare_contains():
    from metrics.spatial_comparison import compare_geometries
    outer = box(-122.5, 37.7, -122.4, 37.8)
    inner = box(-122.48, 37.72, -122.42, 37.78)
    m = compare_geometries(outer, inner)
    assert m.de9im_label == "contains"
    assert m.overlap_pct_b == pytest.approx(1.0)


def test_hausdorff_in_metres_is_reasonable():
    from metrics.spatial_comparison import compare_geometries
    a = box(-122.47, 37.77, -122.45, 37.79)
    b = box(-122.46, 37.78, -122.44, 37.80)
    m = compare_geometries(a, b)
    assert 100 < m.hausdorff_m < 5000


def test_de9im_string_is_9_chars():
    from metrics.spatial_comparison import compare_geometries
    a = box(-122.5, 37.7, -122.4, 37.8)
    b = box(-122.45, 37.75, -122.35, 37.85)
    m = compare_geometries(a, b)
    assert len(m.de9im) == 9
