"""
app/services/bottleneck/confidence.py
======================================
Estimates confidence in a bottleneck score based on historical snapshot data.

Rules
-----
- Fewer than 3 snapshots → low_confidence = True, wider uncertainty band.
- 3 or more snapshots    → compute variance/stability; confidence is higher
                           when WIP trend is stable, lower when volatile.

The confidence value (0–1) and trend direction are used by the API to annotate
bottleneck results so consumers understand how reliable the score is.

Transparency note
-----------------
This is a heuristic, not a statistically rigorous confidence interval.
The sample sizes involved (3–20 snapshots) are too small for formal inference.
The module documents this explicitly and returns low_confidence=True whenever
the sample is small.
"""

from __future__ import annotations

import math
from typing import TypedDict

MIN_SNAPSHOTS_FOR_CONFIDENCE: int = 3

# When variance is low (stable WIP), confidence is HIGH_CONF.
# When variance is high (volatile WIP), confidence degrades toward LOW_CONF.
HIGH_CONF: float = 0.90
LOW_CONF_SMALL_SAMPLE: float = 0.50   # fewer than MIN_SNAPSHOTS_FOR_CONFIDENCE
LOW_CONF_VOLATILE: float = 0.60       # high variance even with enough samples

# CoV (coefficient of variation) threshold above which stability is "poor"
COV_VOLATILE_THRESHOLD: float = 0.30  # 30 % CV = high relative variability


class ConfidenceResult(TypedDict):
    confidence: float          # 0–1
    low_confidence: bool       # True when estimate is unreliable
    snapshot_count: int
    wip_trend: str             # "RISING" | "STABLE" | "FALLING" | "UNKNOWN"
    cov: float | None          # coefficient of variation of WIP values; None if <2 snapshots


def compute_confidence(wip_history: list[float]) -> ConfidenceResult:
    """
    Estimate confidence from a list of historical WIP values (ordered oldest→newest).

    Parameters
    ----------
    wip_history : list[float]
        WIP unit counts from successive fab_snapshots, oldest first.
        Must contain at least 1 value.

    Returns
    -------
    ConfidenceResult
        confidence      : float in [0, 1]
        low_confidence  : bool
        snapshot_count  : int
        wip_trend       : str
        cov             : float | None

    Examples
    --------
    >>> compute_confidence([80, 85, 90, 95, 100])   # clearly rising
    {'confidence': 0.75, 'low_confidence': False, 'snapshot_count': 5,
     'wip_trend': 'RISING', 'cov': ...}

    >>> compute_confidence([80])                    # single snapshot
    {'confidence': 0.5, 'low_confidence': True, 'snapshot_count': 1,
     'wip_trend': 'UNKNOWN', 'cov': None}
    """
    n = len(wip_history)

    # ── Fewer than minimum snapshots ──────────────────────────────────────────
    if n < MIN_SNAPSHOTS_FOR_CONFIDENCE:
        return ConfidenceResult(
            confidence=LOW_CONF_SMALL_SAMPLE,
            low_confidence=True,
            snapshot_count=n,
            wip_trend="UNKNOWN" if n < 2 else _trend(wip_history),
            cov=None,
        )

    # ── Coefficient of Variation (relative dispersion) ────────────────────────
    mean_wip = sum(wip_history) / n
    if mean_wip <= 0:
        # All-zero WIP — no meaningful pressure, treat as stable but low signal
        return ConfidenceResult(
            confidence=HIGH_CONF,
            low_confidence=False,
            snapshot_count=n,
            wip_trend="STABLE",
            cov=0.0,
        )

    variance = sum((x - mean_wip) ** 2 for x in wip_history) / n
    std_dev = math.sqrt(variance)
    cov = std_dev / mean_wip

    # ── Trend detection ───────────────────────────────────────────────────────
    trend = _trend(wip_history)

    # ── Confidence mapping ────────────────────────────────────────────────────
    if cov > COV_VOLATILE_THRESHOLD:
        # High variability → score is less reliable
        confidence = LOW_CONF_VOLATILE
    else:
        # Stable — confidence scales inversely with CoV up to HIGH_CONF
        # cov = 0   → confidence = HIGH_CONF (0.90)
        # cov = 0.30 → confidence = LOW_CONF_VOLATILE (0.60)
        confidence = HIGH_CONF - (cov / COV_VOLATILE_THRESHOLD) * (HIGH_CONF - LOW_CONF_VOLATILE)
        confidence = round(max(LOW_CONF_VOLATILE, min(HIGH_CONF, confidence)), 4)

    return ConfidenceResult(
        confidence=confidence,
        low_confidence=False,
        snapshot_count=n,
        wip_trend=trend,
        cov=round(cov, 4),
    )


def _trend(values: list[float]) -> str:
    """Detect simple monotonic trend in a sequence of values."""
    if len(values) < 2:
        return "UNKNOWN"
    deltas = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    pos = sum(1 for d in deltas if d > 0)
    neg = sum(1 for d in deltas if d < 0)
    total = len(deltas)
    if pos / total >= 0.67:
        return "RISING"
    if neg / total >= 0.67:
        return "FALLING"
    return "STABLE"
