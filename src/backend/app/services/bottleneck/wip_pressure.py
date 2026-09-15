"""
app/services/bottleneck/wip_pressure.py
========================================
Computes WIP (Work-in-Progress) pressure for a fab tool.

Formula — raw WIP pressure
--------------------------
    wip_pressure = current_wip / normal_wip

This is a *raw ratio* that can exceed 1.0.  For example:
    current_wip = 240 lots,  normal_wip = 100 lots  →  wip_pressure = 2.4

Edge cases
----------
- normal_wip == 0  → returns 0.0 (no baseline defined; treated as no pressure)
- current_wip <= 0 → returns 0.0

Normalization for the score formula
-------------------------------------
The bottleneck score uses a 0–1 weighted sum, so raw wip_pressure (which can be
>>1) must be normalized before inclusion.  The chosen normalization is:

    normalized_wip_pressure = min(wip_pressure / WIP_NORM_DIVISOR, 1.0)

WIP_NORM_DIVISOR = 3.0 by default.  Rationale:
  - A 3× queue (240 lots when normal is 80) is an extreme, unambiguous bottleneck.
  - Values above 3× saturate the score component at 1.0 — they do not inflate
    the score beyond physical meaning.
  - The divisor is a module-level constant so it can be adjusted without touching
    the score formula.

This normalization is documented here so Member 3 can reference the decision.
"""

from __future__ import annotations

# Divisor used to normalise raw WIP pressure into [0, 1].
# A tool whose WIP is 3× the normal level scores the maximum 1.0 on this component.
WIP_NORM_DIVISOR: float = 3.0


def compute_wip_pressure(current_wip: float, normal_wip: float) -> float:
    """
    Return raw WIP pressure ratio (can exceed 1.0).

    Parameters
    ----------
    current_wip : float
        Current number of WIP lots queued at the tool.
    normal_wip : float
        Baseline / expected WIP under normal operating conditions.

    Returns
    -------
    float
        Raw ratio ≥ 0.  Values > 1.0 indicate queue exceeds normal level.

    Examples
    --------
    >>> compute_wip_pressure(240, 100)
    2.4
    >>> compute_wip_pressure(0, 100)
    0.0
    >>> compute_wip_pressure(50, 0)   # no baseline defined
    0.0
    """
    if normal_wip <= 0:
        return 0.0
    if current_wip <= 0:
        return 0.0
    return float(current_wip) / float(normal_wip)


def normalize_wip_pressure(
    wip_pressure: float,
    divisor: float = WIP_NORM_DIVISOR,
) -> float:
    """
    Normalize raw WIP pressure into [0.0, 1.0] for use in the score formula.

    Parameters
    ----------
    wip_pressure : float
        Raw ratio from ``compute_wip_pressure``.
    divisor : float
        Saturation point (default 3.0 — see module docstring).

    Returns
    -------
    float
        Clamped value in [0.0, 1.0].

    Examples
    --------
    >>> normalize_wip_pressure(2.4)   # 2.4 / 3.0 = 0.8
    0.8
    >>> normalize_wip_pressure(4.5)   # clamped to 1.0
    1.0
    >>> normalize_wip_pressure(0.5)   # 0.5 / 3.0 ≈ 0.167
    0.1667
    """
    if divisor <= 0:
        return 1.0 if wip_pressure > 0 else 0.0
    return min(float(wip_pressure) / divisor, 1.0)
