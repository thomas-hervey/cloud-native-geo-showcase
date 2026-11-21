"""Centroid distance error in meters using pyproj geodesic calculation."""
from shapely.geometry import Point
from pyproj import Geod

_GEOD = Geod(ellps="WGS84")


def compute_centroid_error_m(predicted: Point, reference: Point) -> float:
    """Great-circle distance between two centroids in meters."""
    _, _, dist = _GEOD.inv(
        predicted.x, predicted.y,
        reference.x, reference.y,
    )
    return abs(dist)
