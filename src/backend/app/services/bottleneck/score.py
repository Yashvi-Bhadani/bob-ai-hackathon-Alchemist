"""
app/services/bottleneck/score.py
=================================
Composite Bottleneck Score and severity classification.

Score Formula (0–100)
---------------------
    score = 100 × (
        0.30 × utilization              [ratio 0–1]
      + 0.30 × capacity_pressure_norm  [ratio 0–1, clamped]
      + 0.25 × normalized_wip_pressure [ratio 0–1, via normalize_wip_pressure]
      + 0.15 × downtime_pct            [ratio 0–1]
    )

All four inputs MUST be in [0, 1] before being passed here.
  - utilization:             from utilization.compute_utilization()
  - capacity_pressure_norm:  from capacity_pressure.compute_capacity_pressure()  (already clamped)
  - normalized_wip_pressure: from wip_pressure.normalize_wip_pressure()
  - downtime_pct:            downtime_hours / total_hours  (clamped to [0,1])

Weights sum to 1.0:  0.30 + 0.30 + 0.25 + 0.15 = 1.00
Final score is in [0.0, 100.0] (two decimal places).

Severity Bands
--------------
    0 –  39.99  →  LOW
   40 –  69.99  →  MEDIUM
   70 –  84.99  →  HIGH
   85 – 100     →  CRITICAL

Thresholds are defined as module-level constants so they are easy to adjust.
"""

from __future__ import annotations

# ── Weight constants ───────────────────────────────────────────────────────────
W_UTILIZATION:        float = 0.30
W_CAPACITY_PRESSURE:  float = 0.30
W_WIP_PRESSURE:       float = 0.25
W_DOWNTIME:           float = 0.15

# ── Severity thresholds (lower bound, inclusive) ───────────────────────────────
SEVERITY_CRITICAL: float = 85.0
SEVERITY_HIGH:     float = 70.0
SEVERITY_MEDIUM:   float = 40.0
# Below SEVERITY_MEDIUM → LOW


def compute_downtime_pct(downtime_hours: float, total_hours: float) -> float:
    """
    Return downtime as a ratio in [0.0, 1.0].

    Parameters
    ----------
    downtime_hours : float
        Hours of unplanned downtime in the period.
    total_hours : float
        Total hours in the period (available + downtime).
    """
    if total_hours <= 0:
        return 0.0
    raw = max(0.0, float(downtime_hours)) / float(total_hours)
    return min(raw, 1.0)


def compute_bottleneck_score(
    utilization: float,
    capacity_pressure: float,
    normalized_wip_pressure: float,
    downtime_pct: float,
) -> float:
    """
    Compute the composite Bottleneck Score on a 0–100 scale.

    All parameters must already be normalized to [0.0, 1.0].

    Parameters
    ----------
    utilization : float
        Tool utilization ratio [0, 1].
    capacity_pressure : float
        Capacity pressure ratio [0, 1] (already clamped).
    normalized_wip_pressure : float
        WIP pressure normalized to [0, 1] via normalize_wip_pressure().
    downtime_pct : float
        Downtime fraction of total period [0, 1].

    Returns
    -------
    float
        Score in [0.0, 100.0], rounded to 2 decimal places.

    Examples
    --------
    >>> compute_bottleneck_score(0.97, 0.97, 0.80, 0.10)  # LITH-07-like
    90.35
    >>> compute_bottleneck_score(0.0, 0.0, 0.0, 0.0)
    0.0
    >>> compute_bottleneck_score(1.0, 1.0, 1.0, 1.0)
    100.0
    """
    raw = (
        W_UTILIZATION       * float(utilization)
        + W_CAPACITY_PRESSURE * float(capacity_pressure)
        + W_WIP_PRESSURE      * float(normalized_wip_pressure)
        + W_DOWNTIME          * float(downtime_pct)
    )
    # Clamp then scale to 0–100
    return round(min(max(raw, 0.0), 1.0) * 100.0, 2)


def classify_severity(score: float) -> str:
    """
    Map a Bottleneck Score (0–100) to a severity label.

    Parameters
    ----------
    score : float
        Score from compute_bottleneck_score().

    Returns
    -------
    str
        One of: 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'.
    """
    if score >= SEVERITY_CRITICAL:
        return "CRITICAL"
    if score >= SEVERITY_HIGH:
        return "HIGH"
    if score >= SEVERITY_MEDIUM:
        return "MEDIUM"
    return "LOW"
