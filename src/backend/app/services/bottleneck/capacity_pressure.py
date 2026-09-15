"""
app/services/bottleneck/capacity_pressure.py
=============================================
Computes capacity pressure for a fab tool.

Formula
-------
    capacity_pressure = required_capacity / available_capacity

Where:
    required_capacity  = arrival rate × average lot cycle time
                        OR simply the current throughput demand the tool faces
    available_capacity = capacity_units_per_hour × available_hours_in_period

This is a ratio that can exceed 1.0 (demand exceeds supply).

Edge cases
----------
- available_capacity == 0  → returns 1.0  (tool has no capacity; maximum pressure)
- required_capacity <= 0   → returns 0.0

Normalization
-------------
Raw capacity_pressure is clamped to [0, 1] for the score formula:
    normalized = min(capacity_pressure, 1.0)

A value > 1.0 in the raw ratio already indicates the tool cannot serve demand.
Clamping at 1.0 prevents the score from being inflated beyond maximum weight.
"""

from __future__ import annotations


def compute_capacity_pressure(
    required_capacity: float,
    available_capacity: float,
) -> float:
    """
    Return capacity pressure as a ratio clamped to [0.0, 1.0].

    Parameters
    ----------
    required_capacity : float
        Capacity units demanded in the period (e.g. wafers to process).
    available_capacity : float
        Maximum capacity units the tool can supply in the same period.

    Returns
    -------
    float
        Ratio in [0.0, 1.0].  1.0 means the tool is at or beyond capacity.

    Examples
    --------
    >>> compute_capacity_pressure(95, 100)    # 95 % loaded
    0.95
    >>> compute_capacity_pressure(120, 100)   # over capacity — clamped
    1.0
    >>> compute_capacity_pressure(0, 100)
    0.0
    >>> compute_capacity_pressure(50, 0)      # no capacity — maximum pressure
    1.0
    """
    if available_capacity <= 0:
        return 1.0
    if required_capacity <= 0:
        return 0.0
    raw = float(required_capacity) / float(available_capacity)
    return min(raw, 1.0)
