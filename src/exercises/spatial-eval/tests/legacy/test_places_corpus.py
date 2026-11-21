import json
from pathlib import Path


def test_places_json_loads():
    p = Path(__file__).parent.parent.parent / "data" / "places.json"
    data = json.loads(p.read_text())
    assert "places" in data
    assert len(data["places"]) >= 20
    for place in data["places"]:
        assert "name" in place
        assert "tier" in place
        assert place["tier"] in (1, 2, 3, 4)
