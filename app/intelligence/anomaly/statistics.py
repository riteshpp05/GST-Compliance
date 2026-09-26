"""
app.intelligence.anomaly.statistics
===================================
Deterministic statistical algorithms for anomaly detection (Sprint 7).
Provides median, MAD, robust Z-score, and IQR outlier boundaries with safe handling for zero variance.
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple


def calculate_median(values: List[float]) -> float:
    """Calculate exact median of a numerical list."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 1:
        return float(sorted_vals[mid])
    return float((sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0)


def calculate_mad(values: List[float], median: Optional[float] = None) -> float:
    """
    Calculate Median Absolute Deviation (MAD):
    MAD = median(|x_i - median(X)|)
    """
    if not values or len(values) < 2:
        return 0.0
    med = median if median is not None else calculate_median(values)
    abs_deviations = [abs(x - med) for x in values]
    return calculate_median(abs_deviations)


def percentile(sorted_vals: List[float], p: float) -> float:
    """Calculate percentile (0.0 to 1.0) using standard linear interpolation."""
    if not sorted_vals:
        return 0.0
    n = len(sorted_vals)
    if n == 1:
        return float(sorted_vals[0])
    idx = p * (n - 1)
    low = int(math.floor(idx))
    high = int(math.ceil(idx))
    weight = idx - low
    return float((1.0 - weight) * sorted_vals[low] + weight * sorted_vals[high])


def calculate_iqr(values: List[float]) -> Tuple[float, float, float]:
    """
    Calculate Q1, Q3, and IQR (Q3 - Q1).
    Returns (q1, q3, iqr).
    """
    if not values:
        return 0.0, 0.0, 0.0
    sorted_vals = sorted(values)
    q1 = percentile(sorted_vals, 0.25)
    q3 = percentile(sorted_vals, 0.75)
    iqr = max(0.0, q3 - q1)
    return q1, q3, iqr


def robust_z_score(val: float, median: float, mad: float, values_fallback: Optional[List[float]] = None) -> float:
    """
    Compute Robust Z-Score:
    robust_z = 0.6745 * |val - median| / MAD
    Safely handles MAD == 0 without dividing by zero.
    """
    diff = abs(val - median)
    if diff == 0.0:
        return 0.0

    if mad > 0.0:
        return round((0.6745 * diff) / mad, 4)

    # Safe handling for MAD == 0 (identical or very tight baseline)
    if values_fallback and len(values_fallback) > 1:
        # Fallback to standard deviation
        mean_val = sum(values_fallback) / len(values_fallback)
        variance = sum((x - mean_val) ** 2 for x in values_fallback) / (len(values_fallback) - 1)
        std_dev = math.sqrt(variance)
        if std_dev > 0.0:
            return round(diff / std_dev, 4)

    # Relative deviation fallback when variance is zero
    ref = max(abs(median), 1000.0)
    relative_dev = diff / ref
    return round(relative_dev * 10.0, 4)


def iqr_outlier_check(
    val: float,
    q1: float,
    q3: float,
    iqr: float,
    multiplier: float = 1.5,
) -> Tuple[bool, float, float]:
    """
    Determine if a value falls outside the IQR boundary:
    lower = q1 - multiplier * IQR
    upper = q3 + multiplier * IQR
    Safely handles IQR == 0.
    Returns: (is_outlier, lower_boundary, upper_boundary)
    """
    if iqr > 0.0:
        lower = max(0.0, q1 - (multiplier * iqr))
        upper = q3 + (multiplier * iqr)
        is_outlier = (val < lower) or (val > upper)
        return is_outlier, round(lower, 2), round(upper, 2)

    # Safe handling for IQR == 0 (all or 75%+ observations have identical value)
    if val == q1:
        return False, q1, q3

    # Use a proportional 25% boundary around q1/q3
    lower = max(0.0, q1 * 0.75)
    upper = q3 * 1.25 if q3 > 0.0 else 1000.0
    is_outlier = (val < lower) or (val > upper)
    return is_outlier, round(lower, 2), round(upper, 2)
