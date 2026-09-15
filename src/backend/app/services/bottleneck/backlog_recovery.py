"""
app/services/bottleneck/backlog_recovery.py
============================================
Reusable outage backlog and recovery calculation.

This module is intentionally standalone — Member 3 can import
``calculate_backlog_recovery`` directly without pulling in the rest of
the bottleneck package.

Formula
-------
    backlog_added       = arrival_rate × outage_duration
    net_clearance_rate  = tool_capacity − arrival_rate

    If tool_capacity > arrival_rate:
        recovery_time = backlog_added / net_clearance_rate
        recoverable   = True

    If tool_capacity ≤ arrival_rate:
        recovery is NOT achievable at current capacity.
        recovery_time = None
        recoverable   = False

Little's Law (reference only)
------------------------------
Little's Law W = L / λ gives a baseline CYCLE-TIME ESTIMATE, not a recovery
time.  It is documented here for reference only and is NOT used in the
backlog/recovery calculation.

    W = average time a lot spends in the system (hours)
    L = average WIP (lots)
    λ = arrival / throughput rate (lots/hour)

Units
-----
All time values are in hours.  Arrival rate and capacity must use the same
unit (e.g. lots/hour or wafers/hour — caller's responsibility to be consistent).
"""

from __future__ import annotations

from typing import TypedDict


class BacklogRecoveryResult(TypedDict):
    """Structured result from calculate_backlog_recovery."""
    backlog_added: float           # lots / units added during outage
    net_clearance_rate: float      # tool_capacity - arrival_rate (lots/hr)
    recovery_time_hours: float | None  # None if not recoverable
    recoverable: bool


def calculate_backlog_recovery(
    arrival_rate: float,
    tool_capacity: float,
    outage_duration: float,
) -> BacklogRecoveryResult:
    """
    Calculate the backlog that accumulates during an outage and the time
    required to clear it after the tool returns to service.

    Parameters
    ----------
    arrival_rate : float
        Rate at which lots arrive at the tool while it is down (lots/hour).
        Must be ≥ 0.
    tool_capacity : float
        Maximum processing rate of the tool when fully operational (lots/hour).
        Must be > 0.
    outage_duration : float
        Duration of the outage (hours).  Must be > 0.

    Returns
    -------
    BacklogRecoveryResult
        Dictionary with keys:
          - backlog_added       (float) — lots accumulated during outage
          - net_clearance_rate  (float) — lots/hr available for backlog clearance
          - recovery_time_hours (float | None) — None if not recoverable
          - recoverable         (bool)

    Raises
    ------
    ValueError
        If tool_capacity ≤ 0 or outage_duration ≤ 0.

    Examples
    --------
    >>> calculate_backlog_recovery(
    ...     arrival_rate=10.0,
    ...     tool_capacity=15.0,
    ...     outage_duration=8.0,
    ... )
    {'backlog_added': 80.0, 'net_clearance_rate': 5.0,
     'recovery_time_hours': 16.0, 'recoverable': True}

    >>> calculate_backlog_recovery(
    ...     arrival_rate=15.0,
    ...     tool_capacity=15.0,
    ...     outage_duration=4.0,
    ... )
    {'backlog_added': 60.0, 'net_clearance_rate': 0.0,
     'recovery_time_hours': None, 'recoverable': False}
    """
    if tool_capacity <= 0:
        raise ValueError(f"tool_capacity must be > 0, got {tool_capacity}")
    if outage_duration <= 0:
        raise ValueError(f"outage_duration must be > 0, got {outage_duration}")

    arrival_rate = max(0.0, float(arrival_rate))
    tool_capacity = float(tool_capacity)
    outage_duration = float(outage_duration)

    backlog_added: float = arrival_rate * outage_duration
    net_clearance_rate: float = tool_capacity - arrival_rate

    if net_clearance_rate <= 0:
        return BacklogRecoveryResult(
            backlog_added=backlog_added,
            net_clearance_rate=net_clearance_rate,
            recovery_time_hours=None,
            recoverable=False,
        )

    recovery_time_hours: float = round(backlog_added / net_clearance_rate, 4)
    return BacklogRecoveryResult(
        backlog_added=backlog_added,
        net_clearance_rate=net_clearance_rate,
        recovery_time_hours=recovery_time_hours,
        recoverable=True,
    )


def estimate_cycle_time_littles_law(avg_wip: float, throughput_rate: float) -> float | None:
    """
    Baseline cycle-time estimate using Little's Law: W = L / λ.

    This is a REFERENCE ESTIMATE ONLY — not used for outage or recovery time.

    Parameters
    ----------
    avg_wip : float
        Average WIP (lots) in the system.
    throughput_rate : float
        Average throughput / arrival rate (lots/hour).

    Returns
    -------
    float | None
        Estimated average time in system (hours), or None if throughput is 0.
    """
    if throughput_rate <= 0:
        return None
    return round(float(avg_wip) / float(throughput_rate), 4)
