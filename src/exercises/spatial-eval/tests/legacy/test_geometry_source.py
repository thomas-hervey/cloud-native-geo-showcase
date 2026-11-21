import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_registry_registers_and_loads():
    from geometry_source import GT_REGISTRY, register_gt, load_gt_source, GeometrySource

    @register_gt("_test_source")
    class _TestSource:
        name = "_test_source"
        source_type = "gt"
        def get_polygon(self, place): return None
        def get_centroid(self, place): return None
        def get_bbox(self, place): return None

    try:
        assert "_test_source" in GT_REGISTRY
        src = load_gt_source("_test_source")
        assert isinstance(src, GeometrySource)
    finally:
        GT_REGISTRY.pop("_test_source", None)


def test_load_unknown_source_raises():
    from geometry_source import load_gt_source
    with pytest.raises(KeyError, match="Unknown GT source"):
        load_gt_source("nonexistent_xyz")


def test_list_gt_sources_returns_sorted_list():
    from geometry_source import list_gt_sources
    sources = list_gt_sources()
    assert isinstance(sources, list)
    assert sources == sorted(sources)
    assert all(not s.startswith("_") for s in sources)
