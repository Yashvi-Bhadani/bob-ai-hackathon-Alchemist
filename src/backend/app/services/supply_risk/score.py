"""
Composite Supply Risk Score
============================

Deterministic 0–100 risk score combining four components:

    Component               Weight   Input source
    ───────────────────────────────────────────────────
    Supplier concentration  30 %     HHI (normalised 0–10000 → 0–1)
    SPOF                    30 %     Binary 0 or 1
    Inventory coverage      20 %     coverage_normalised() → 0–1
    Geopolitical risk       20 %     aggregate_geo_risk_score() → 0–1

    composite_score = 100 × (
        0.30 × hhi_norm
      + 0.30 × spof_norm
      + 0.20 × inv_norm
      + 0.20 × geo_norm
    )

Weights sum to 1.0.  Final score is clamped to [0, 100].

Severity labels
---------------
    0 – 39   → LOW
    40 – 69  → MEDIUM
    70 – 84  → HIGH
    85 – 100 → CRITICAL
"""

from __future__ import annotations

# Component weights — must sum to 1.0
_W_HHI = 0.30
_W_SPOF = 0.30
_W_INV = 0.20
_W_GEO = 0.20

assert abs(_W_HHI + _W_SPOF + _W_INV + _W_GEO - 1.0) < 1e-9, "Weights must sum to 1.0"

# HHI normalisation ceiling (max possible HHI = 10 000)
_HHI_MAX = 10_000.0

# Severity thresholds
_THRESHOLDS = [
    (85, "CRITICAL"),
    (70, "HIGH"),
    (40, "MEDIUM"),
    (0,  "LOW"),
]


def _normalise_hhi(hhi: float) -> float:
    """Map HHI (0–10 000) to [0, 1]."""
    return min(max(hhi / _HHI_MAX, 0.0), 1.0)


def _normalise_spof(spof: bool) -> float:
    """Binary: 1.0 if SPOF, else 0.0."""
    return 1.0 if spof else 0.0


def compute_composite_score(
    hhi: float,
    spof: bool,
    inv_norm: float,
    geo_norm: float,
) -> float:
    """
    Compute the composite supply risk score (0–100).

    Parameters
    ----------
    hhi:
        Raw HHI value (0–10 000).
    spof:
        True when exactly one qualified supplier exists.
    inv_norm:
        Inventory risk normalised to [0, 1] from ``coverage_normalised()``.
    geo_norm:
        Geopolitical risk normalised to [0, 1] from ``aggregate_geo_risk_score()``.

    Returns
    -------
    float
        Score in [0.0, 100.0], rounded to 2 decimal places.
    """
    hhi_n = _normalise_hhi(hhi)
    spof_n = _normalise_spof(spof)

    # Clamp inputs to [0, 1] defensively
    inv_n = min(max(float(inv_norm), 0.0), 1.0)
    geo_n = min(max(float(geo_norm), 0.0), 1.0)

    raw = (
        _W_HHI  * hhi_n
        + _W_SPOF * spof_n
        + _W_INV  * inv_n
        + _W_GEO  * geo_n
    )

    # Scale to 0–100 and clamp
    score = round(min(max(raw * 100.0, 0.0), 100.0), 2)
    return score


def severity_label(score: float) -> str:
    """
    Map a 0–100 composite score to a severity label.

    Thresholds
    ----------
    0 – 39   → LOW
    40 – 69  → MEDIUM
    70 – 84  → HIGH
    85 – 100 → CRITICAL
    """
    for threshold, label in _THRESHOLDS:
        if score >= threshold:
            return label
    return "LOW"
