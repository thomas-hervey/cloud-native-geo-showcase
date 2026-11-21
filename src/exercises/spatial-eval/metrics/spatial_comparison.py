"""Unified spatial comparison metrics for any two Shapely geometries.

compare_geometries(a, b) returns a ComparisonMetrics dataclass with:
  iou, overlap_pct_a, overlap_pct_b — area-based overlap
  de9im, de9im_label               — topological relationship
  hausdorff_m                      — max boundary deviation in metres (UTM)
  centroid_error_m                 — great-circle centroid distance in metres
  composite                        — 0-1 summary (70% IoU + 30% centroid score)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from pyproj import Geod, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

_WGS_TO_UTM10N = Transformer.from_crs("EPSG:4326", "EPSG:32610", always_xy=True).transform
_GEOD = Geod(ellps="WGS84")
_CENTROID_REF_M = 3000.0  # normalisation reference: ~large SF neighbourhood diameter


@dataclass
class ComparisonMetrics:
    iou: float
    overlap_pct_a: float    # intersection / area_a  (how much of A is covered)
    overlap_pct_b: float    # intersection / area_b  (how much of B is covered)
    de9im: str              # 9-char DE-9IM relation string from shapely.relate()
    de9im_label: str        # human-readable: "equals","disjoint","contains","within","overlaps",...
    hausdorff_m: float      # Hausdorff distance in metres (UTM Zone 10N projection)
    centroid_error_m: float # great-circle distance between centroids in metres
    composite: float        # 0-1 summary score


def _label(a: BaseGeometry, b: BaseGeometry) -> str:
    if a.equals(b):    return "equals"
    if a.disjoint(b):  return "disjoint"
    if a.contains(b):  return "contains"
    if b.contains(a):  return "within"
    if a.crosses(b):   return "crosses"
    if a.overlaps(b):  return "overlaps"
    if a.touches(b):   return "touches"
    return "intersects"


def _hausdorff_m(a: BaseGeometry, b: BaseGeometry) -> float:
    """Hausdorff distance in metres via UTM Zone 10N reprojection."""
    a_utm = transform(_WGS_TO_UTM10N, a)
    b_utm = transform(_WGS_TO_UTM10N, b)
    return a_utm.hausdorff_distance(b_utm)


def _centroid_m(a: BaseGeometry, b: BaseGeometry) -> float:
    ca, cb = a.centroid, b.centroid
    _, _, dist = _GEOD.inv(ca.x, ca.y, cb.x, cb.y)
    return abs(dist)


def compare_geometries(predicted: BaseGeometry, reference: BaseGeometry) -> ComparisonMetrics:
    """Compute full spatial comparison metrics between two geometries.

    Args:
        predicted: The geometry being evaluated (LLM bbox or alternative GT).
        reference: The reference geometry (designated ground truth).

    Returns:
        ComparisonMetrics with all spatial relationship metrics populated.
    """
    if predicted.is_empty or reference.is_empty:
        return ComparisonMetrics(
            iou=0.0, overlap_pct_a=0.0, overlap_pct_b=0.0,
            de9im="FFFFFFFFF", de9im_label="disjoint",
            hausdorff_m=float("inf"), centroid_error_m=float("inf"),
            composite=0.0,
        )

    intersection = predicted.intersection(reference).area
    union = predicted.union(reference).area

    iou = intersection / union if union > 0 else 0.0
    overlap_pct_a = intersection / predicted.area if predicted.area > 0 else 0.0
    overlap_pct_b = intersection / reference.area if reference.area > 0 else 0.0
    centroid_err = _centroid_m(predicted, reference)
    composite = 0.7 * iou + 0.3 * math.exp(-centroid_err / _CENTROID_REF_M)

    return ComparisonMetrics(
        iou=iou,
        overlap_pct_a=overlap_pct_a,
        overlap_pct_b=overlap_pct_b,
        de9im=predicted.relate(reference),
        de9im_label=_label(predicted, reference),
        hausdorff_m=_hausdorff_m(predicted, reference),
        centroid_error_m=centroid_err,
        composite=composite,
    )
