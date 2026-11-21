import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_click_that_hood_registered():
    from geometry_source import load_gt_source
    src = load_gt_source("click_that_hood")
    assert src.name == "click_that_hood"
    assert src.source_type == "gt"


def test_click_that_hood_gets_richmond():
    from geometry_source import load_gt_source
    src = load_gt_source("click_that_hood")
    poly = src.get_polygon("The Richmond")
    assert poly is not None
    assert poly.geom_type in ("Polygon", "MultiPolygon")


def test_click_that_hood_returns_none_for_atlantis():
    from geometry_source import load_gt_source
    src = load_gt_source("click_that_hood")
    assert src.get_polygon("Atlantis") is None


def test_click_that_hood_centroid_and_bbox():
    from geometry_source import load_gt_source
    src = load_gt_source("click_that_hood")
    centroid = src.get_centroid("North Beach")
    bbox = src.get_bbox("North Beach")
    assert centroid is not None
    assert bbox is not None
    assert bbox["north"] > bbox["south"]
    assert bbox["east"] > bbox["west"]


def test_llm_source_is_geometry_source():
    from sources.llm import LLMSource
    from geometry_source import GeometrySource
    src = LLMSource("claude-haiku-4-5", run=1)
    assert isinstance(src, GeometrySource)
    assert src.source_type == "llm"
    assert src.name == "claude-haiku-4-5"
    # Verify the three required methods exist and are callable
    assert callable(src.get_polygon)
    assert callable(src.get_centroid)
    assert callable(src.get_bbox)


def test_osm_registered():
    from geometry_source import load_gt_source
    src = load_gt_source("osm")
    assert src.name == "osm"
    assert src.source_type == "gt"


def test_osm_cache_path_is_deterministic():
    """Cache path should be the same for the same place every time."""
    from sources.osm import OSMSource
    src = OSMSource()
    p1 = src._cache_path("The Mission")
    p2 = src._cache_path("The Mission")
    assert p1 == p2
    assert p1.suffix == ".json"


def test_sf_planning_registered():
    from geometry_source import load_gt_source
    src = load_gt_source("sf_planning")
    assert src.name == "sf_planning"
    assert src.source_type == "gt"


def test_sf_planning_returns_none_gracefully_when_file_missing(tmp_path, monkeypatch):
    """Should return None (not crash) when data file isn't downloaded yet."""
    from sources.sf_planning import SFPlanningSource
    import sources.sf_planning as mod
    monkeypatch.setattr(mod, "_DATA_PATH", tmp_path / "nonexistent.geojson")
    src = SFPlanningSource()
    assert src.get_polygon("The Richmond") is None


def test_zillow_registered():
    from geometry_source import load_gt_source
    src = load_gt_source("zillow")
    assert src.name == "zillow"
    assert src.source_type == "gt"


def test_zillow_returns_none_gracefully_when_file_missing(tmp_path, monkeypatch):
    from sources.zillow import ZillowSource
    import sources.zillow as mod
    monkeypatch.setattr(mod, "_DATA_PATH", tmp_path / "nonexistent.geojson")
    src = ZillowSource()
    assert src.get_polygon("The Mission") is None


def test_wikidata_registered():
    from geometry_source import load_gt_source
    src = load_gt_source("wikidata")
    assert src.name == "wikidata"
    assert src.source_type == "gt"


def test_wikidata_cache_path_deterministic():
    from sources.wikidata import WikidataSource
    src = WikidataSource()
    p1 = src._cache_path("The Castro")
    p2 = src._cache_path("The Castro")
    assert p1 == p2
    assert p1.suffix == ".json"
