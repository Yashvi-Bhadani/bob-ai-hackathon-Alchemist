"""
Herfindahl-Hirschman Index (HHI) — supplier concentration
==========================================================

Formula
-------
    HHI = Σ (supply_share_pct_i²)

where supply_share_pct_i is each supplier's share of THIS FAB's sourcing
for a given material, expressed as a percentage (0–100).

Example
-------
    Supplier A = 70 %
    Supplier B = 20 %
    Supplier C = 10 %

    HHI = 70² + 20² + 10²
        = 4900 + 400 + 100
        = 5400   → HIGH concentration

Thresholds (application-internal; not a universal regulatory standard)
-----------------------------------------------------------------------
    HHI > 2500  → HIGH
    HHI > 1500  → MODERATE
    HHI ≤ 1500  → LOW
    HHI = 10000 → MONOPOLY (single 100 % supplier)
"""

from __future__ import annotations

from typing import Sequence

HHI_HIGH_THRESHOLD: int = 2500
HHI_MODERATE_THRESHOLD: int = 1500


def compute_hhi(shares: Sequence[float]) -> float:
    """
    Calculate HHI from a sequence of supply-share percentages.

    Parameters
    ----------
    shares:
        Each element is a supplier's share in **percent** (e.g. 70.0 for 70 %).
        An empty sequence returns 0.0.

    Returns
    -------
    float
        HHI on the 0–10 000 scale, rounded to 2 decimal places.

    Notes
    -----
    * Does **not** assume shares sum to 100.  Callers should validate that
      constraint before storing data, but the formula is agnostic.
    * Pure function — no I/O, no side effects.
    """
    if not shares:
        return 0.0
    return round(sum(s * s for s in shares), 2)


def hhi_concentration_level(hhi: float) -> str:
    """
    Map an HHI value to a human-readable concentration label.

    Returns
    -------
    str
        One of "MONOPOLY" | "HIGH" | "MODERATE" | "LOW".

    Notes
    -----
    Thresholds are application-internal thresholds for this fab risk tool.
    They are NOT intended as regulatory or antitrust conclusions.
    """
    if hhi >= 10_000:
        return "MONOPOLY"
    if hhi > HHI_HIGH_THRESHOLD:
        return "HIGH"
    if hhi > HHI_MODERATE_THRESHOLD:
        return "MODERATE"
    return "LOW"
