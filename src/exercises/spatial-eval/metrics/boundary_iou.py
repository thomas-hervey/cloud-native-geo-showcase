"""Intersection over Union between two Shapely geometries."""
from shapely.geometry.base import BaseGeometry


def compute_iou(predicted: BaseGeometry, reference: BaseGeometry) -> float:
    """Compute IoU between two geometries. Returns float in [0, 1]."""
    if predicted.is_empty or reference.is_empty:
        return 0.0
    intersection = predicted.intersection(reference).area
    union = predicted.union(reference).area
    if union == 0:
        return 0.0
    return intersection / union
