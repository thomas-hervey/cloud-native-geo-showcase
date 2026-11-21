import json
from shapely.geometry import Polygon, box, Point
from ui.map_view import _extract_geojson_from_layers

def test_extract_geojson_from_layers():
    """Verify that folium layer dicts are correctly converted into a FeatureCollection."""
    
    # 1. Dummy Polygon
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    
    # 2. Dummy Bbox
    bbox = box(-1, -1, -0.5, -0.5)
    
    # 3. Dummy Centroids (one as shapely Point, one as lat/lon tuple)
    centroid_pt = Point(2, 2)
    centroid_xy = (3.0, 4.0) # lat, lon
    
    layers = [
        {"name": "Test Poly", "layer_type": "poly", "geom": poly},
        {"name": "Test BBox", "layer_type": "bbox", "geom": bbox},
        {"name": "Test Centroid Pt", "layer_type": "centroid", "centroid": centroid_pt},
        {"name": "Test Centroid XY", "layer_type": "centroid", "centroid_xy": centroid_xy},
        {"name": "Empty Layer", "layer_type": "unknown"} # Should be skipped since no geom
    ]
    
    geojson = _extract_geojson_from_layers(layers)
    
    assert geojson is not None
    assert geojson["type"] == "FeatureCollection"
    
    features = geojson["features"]
    assert len(features) == 4
    
    # Check Poly
    assert features[0]["properties"]["name"] == "Test Poly"
    assert features[0]["geometry"]["type"] == "Polygon"
    
    # Check BBox
    assert features[1]["properties"]["name"] == "Test BBox"
    assert features[1]["geometry"]["type"] == "Polygon"
    
    # Check Centroid Pt
    assert features[2]["properties"]["name"] == "Test Centroid Pt"
    assert features[2]["geometry"]["type"] == "Point"
    assert features[2]["geometry"]["coordinates"] == [2.0, 2.0]
    
    # Check Centroid XY (note: coordinates are lon, lat meaning y, x)
    assert features[3]["properties"]["name"] == "Test Centroid XY"
    assert features[3]["geometry"]["type"] == "Point"
    assert features[3]["geometry"]["coordinates"] == [4.0, 3.0] # lon, lat
