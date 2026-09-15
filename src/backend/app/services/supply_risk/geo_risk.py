"""
Geopolitical Risk Assessment
=============================

Each risk factor record carries:
    - risk_level    : "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    - reason        : human-readable explanation
    - source        : provenance string (always "Demo/Synthetic Scenario" for demo)
    - source_date   : ISO date of the risk assessment
    - affected_region: geographic region
    - risk_type     : one of the allowed category strings

Supported risk_type categories
-------------------------------
    export_control
    geopolitical_instability
    trade_restriction
    transportation_risk
    regional_dependency

Normalised score mapping
------------------------
    LOW      → 0.10
    MEDIUM   → 0.40
    HIGH     → 0.70
    CRITICAL → 1.00

aggregate_geo_risk_score() returns the MAXIMUM normalised score across all
risk factors that are either material-specific or have no material filter
(region-wide).

⚠  All demo risk data is synthetic scenario data.
   Do NOT hard-code unsupported real-world geopolitical claims.
"""

from __future__ import annotations

from typing import Optional, Sequence

# Normalised risk scores (0–1) per level
GEO_RISK_LEVEL_SCORE: dict[str, float] = {
    "LOW":      0.10,
    "MEDIUM":   0.40,
    "HIGH":     0.70,
    "CRITICAL": 1.00,
}

# ── Demo / fallback risk factor data ─────────────────────────────────────────
# All entries are SYNTHETIC SCENARIO DATA for demonstration purposes only.
# ⚠  These do NOT constitute verified real-world geopolitical claims.

DEMO_RISK_FACTORS: list[dict] = [
    # ── Neon ─────────────────────────────────────────────────────────────────
    {
        "risk_factor_id": 1,
        "material_id": "NEON",
        "risk_type": "regional_dependency",
        "risk_level": "HIGH",
        "reason": (
            "[DEMO SCENARIO] Synthetic scenario: neon production is concentrated "
            "in a limited number of regions; a hypothetical supply disruption "
            "would immediately impact semiconductor fabs worldwide."
        ),
        "source": "Demo/Synthetic Scenario",
        "source_date": "2025-01-15",
        "affected_region": "Eastern Europe / Global",
    },
    {
        "risk_factor_id": 2,
        "material_id": "NEON",
        "risk_type": "export_control",
        "risk_level": "HIGH",
        "reason": (
            "[DEMO SCENARIO] Simulated export licensing restrictions on rare "
            "industrial gases create uncertain delivery timelines."
        ),
        "source": "Demo/Synthetic Scenario",
        "source_date": "2025-01-15",
        "affected_region": "Global",
    },
    # ── Gallium ──────────────────────────────────────────────────────────────
    {
        "risk_factor_id": 3,
        "material_id": "GALLIUM",
        "risk_type": "export_control",
        "risk_level": "HIGH",
        "reason": (
            "[DEMO SCENARIO] Hypothetical export-control scenario for gallium "
            "compounds; represents supply-concentration risk in a single region."
        ),
        "source": "Demo/Synthetic Scenario",
        "source_date": "2025-02-01",
        "affected_region": "Asia-Pacific",
    },
    {
        "risk_factor_id": 4,
        "material_id": "GALLIUM",
        "risk_type": "trade_restriction",
        "risk_level": "MEDIUM",
        "reason": (
            "[DEMO SCENARIO] Simulated tariff escalation scenario affecting "
            "gallium metal imports; 30 % cost increase modeled."
        ),
        "source": "Demo/Synthetic Scenario",
        "source_date": "2025-02-01",
        "affected_region": "Asia-Pacific",
    },
    # ── Germanium ─────────────────────────────────────────────────────────────
    {
        "risk_factor_id": 5,
        "material_id": "GERMANIUM",
        "risk_type": "export_control",
        "risk_level": "MEDIUM",
        "reason": (
            "[DEMO SCENARIO] Synthetic scenario: hypothetical export licensing "
            "requirements for germanium-based compounds."
        ),
        "source": "Demo/Synthetic Scenario",
        "source_date": "2025-02-15",
        "affected_region": "Asia-Pacific",
    },
    # ── Photoresist ────────────────────────────────────────────────────────
    {
        "risk_factor_id": 6,
        "material_id": "PHOTORESIST",
        "risk_type": "transportation_risk",
        "risk_level": "LOW",
        "reason": (
            "[DEMO SCENARIO] Minor shipping-lane congestion scenario adding "
            "3–5 days to photoresist delivery schedules."
        ),
        "source": "Demo/Synthetic Scenario",
        "source_date": "2025-03-01",
        "affected_region": "Asia-Pacific",
    },
    # ── Regional (applies to all materials) ─────────────────────────────────
    {
        "risk_factor_id": 7,
        "material_id": None,   # region-wide — no material filter
        "risk_type": "geopolitical_instability",
        "risk_level": "LOW",
        "reason": (
            "[DEMO SCENARIO] Background low-level geopolitical instability "
            "scenario applied to all Asia-Pacific sourced materials."
        ),
        "source": "Demo/Synthetic Scenario",
        "source_date": "2025-01-01",
        "affected_region": "Asia-Pacific",
    },
]


def aggregate_geo_risk_score(
    risk_factors: Sequence[dict],
    material_id: Optional[str] = None,
) -> float:
    """
    Compute the geopolitical risk score for a material.

    Takes the **maximum** normalised risk score across all risk factors that:
      (a) target the given material specifically, or
      (b) are region-wide (material_id is None).

    Parameters
    ----------
    risk_factors:
        Sequence of risk factor dicts, each containing at minimum
        ``"material_id"`` (str or None) and ``"risk_level"`` (str).
    material_id:
        The material to filter for.  Pass None to get the region-wide max.

    Returns
    -------
    float
        Normalised score in [0.0, 1.0].  Returns 0.0 if no factors apply.
    """
    score = 0.0
    for factor in risk_factors:
        fmat = factor.get("material_id")
        if fmat is None or fmat == material_id:
            level = factor.get("risk_level", "LOW")
            score = max(score, GEO_RISK_LEVEL_SCORE.get(level, 0.0))
    return round(score, 4)
