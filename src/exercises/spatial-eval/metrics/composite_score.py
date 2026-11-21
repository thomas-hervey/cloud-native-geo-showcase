"""Composite accuracy score combining IoU and centroid error.

Score is 0.0 (worst) to 1.0 (perfect). IoU is weighted 70%, normalized
centroid error 30%. Centroid error is normalized against a 3 km reference
(roughly the diameter of a large SF neighborhood).
"""
import math


_CENTROID_REF_M = 3000.0  # normalization reference: 3 km


def compute_composite(iou: float, centroid_error_m: float) -> float:
    """Combine IoU and centroid error into a single 0-1 score."""
    centroid_score = math.exp(-centroid_error_m / _CENTROID_REF_M)
    return 0.7 * iou + 0.3 * centroid_score
