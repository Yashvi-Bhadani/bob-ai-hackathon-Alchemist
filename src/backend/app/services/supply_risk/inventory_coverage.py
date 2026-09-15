"""
Inventory Coverage Calculation
================================

Formula
-------
    inventory_coverage_days = current_inventory_units / daily_consumption_units

Division-by-zero guard: if daily_consumption_units == 0, return None
(no consumption tracked — treat as "infinite", but flag explicitly).

Risk tiers vs. safety stock
----------------------------
A material is "below safety stock" when:
    inventory_coverage_days < safety_stock_days

Additional severity tiers based purely on days remaining:
    coverage_days < 7      → CRITICAL
    7 ≤ coverage_days < 14 → HIGH
    14 ≤ coverage_days < 30 → MEDIUM
    coverage_days ≥ 30      → LOW

Example
-------
    current_inventory = 500 units
    daily_consumption = 100 units/day
    safety_stock      = 10 days

    coverage = 500 / 100 = 5 days
    tier     = CRITICAL (< 7)
    below_safety_stock = True (5 < 10)
"""

from __future__ import annotations

from typing import Optional


def compute_coverage_days(
    current_inventory_units: float,
    daily_consumption_units: float,
) -> Optional[float]:
    """
    Calculate inventory coverage in days.

    Parameters
    ----------
    current_inventory_units:
        Units currently in stock.
    daily_consumption_units:
        Expected consumption per day.

    Returns
    -------
    float | None
        Days of coverage, rounded to 2 decimal places.
        Returns None when daily_consumption_units == 0 (no consumption tracked).
    """
    if daily_consumption_units == 0:
        return None
    return round(current_inventory_units / daily_consumption_units, 2)


def coverage_risk_tier(coverage_days: Optional[float]) -> str:
    """
    Map coverage days to a risk severity tier.

    Parameters
    ----------
    coverage_days:
        Output of ``compute_coverage_days``.  If None (zero consumption),
        returns "LOW" as no active depletion is occurring.

    Returns
    -------
    str
        "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    """
    if coverage_days is None:
        return "LOW"
    if coverage_days < 7:
        return "CRITICAL"
    if coverage_days < 14:
        return "HIGH"
    if coverage_days < 30:
        return "MEDIUM"
    return "LOW"


def is_below_safety_stock(
    coverage_days: Optional[float],
    safety_stock_days: float,
) -> bool:
    """
    Return True when current coverage is less than the configured safety stock.

    Parameters
    ----------
    coverage_days:
        Output of ``compute_coverage_days``.  None is treated as infinite.
    safety_stock_days:
        Configured safety stock threshold in days.
    """
    if coverage_days is None:
        return False
    return coverage_days < safety_stock_days


def coverage_normalised(coverage_days: Optional[float], safety_stock_days: float = 30.0) -> float:
    """
    Normalise coverage risk to [0, 1] for use in composite scoring.

    Logic
    -----
    * coverage_days is None (zero consumption) → 0.0 (no risk)
    * coverage_days >= safety_stock_days       → 0.0 (adequate)
    * coverage_days == 0                       → 1.0 (empty)
    * Linear interpolation between 0 and safety_stock_days

    Parameters
    ----------
    coverage_days:
        Output of ``compute_coverage_days``.
    safety_stock_days:
        The target baseline.  Defaults to 30 days when not material-specific.
    """
    if coverage_days is None:
        return 0.0
    if coverage_days <= 0:
        return 1.0
    if coverage_days >= safety_stock_days:
        return 0.0
    return round(1.0 - (coverage_days / safety_stock_days), 4)
