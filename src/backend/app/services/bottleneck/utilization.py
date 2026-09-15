"""
app/services/bottleneck/utilization.py
=======================================
Computes tool utilization from raw time measurements.

Formula
-------
    utilization = busy_time / available_time        (returns 0–1 ratio)

Edge cases handled
------------------
- available_time == 0  → returns 0.0 (tool has no scheduled time; not a bottleneck)
- busy_time > available_time  → clamped to 1.0 (cannot exceed 100 %)
- negative inputs     → treated as 0.0

The result is a ratio in [0, 1].  The API layer can multiply by 100 for display
as a percentage.  Internally the score formula always works with the ratio form.
"""

from __future__ import annotations


def compute_utilization(busy_time: float, available_time: float) -> float:
    """
    Return utilization as a ratio in [0.0, 1.0].

    Parameters
    ----------
    busy_time : float
        Hours (or any consistent time unit) the tool was actively processing.
    available_time : float
        Hours the tool was scheduled / available (excludes planned maintenance).

    Returns
    -------
    float
        Utilization ratio in [0.0, 1.0].  Multiply by 100 for percentage.

    Examples
    --------
    >>> compute_utilization(23.3, 24.0)
    0.9708...
    >>> compute_utilization(0, 0)   # no available time
    0.0
    >>> compute_utilization(25.0, 24.0)  # clamped: cannot exceed 1
    1.0
    """
    if available_time <= 0:
        return 0.0
    busy_time = max(0.0, float(busy_time))
    raw = busy_time / float(available_time)
    return min(raw, 1.0)
