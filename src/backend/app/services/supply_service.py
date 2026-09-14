"""
Supply Chain Risk Service
=========================
Implements:
  - Herfindahl-Hirschman Index (HHI) for supplier concentration
  - Single Point of Failure (SPOF) detection
  - Inventory coverage calculation
  - Geopolitical risk assessment
  - Material-level combined supply risk score

All calculations are deterministic formulas — no ML models.

HHI formula:
  HHI = Σ(market_share_i²)   where market_share is in 0-100 range
  HHI < 1500  → Low concentration
  1500–2500   → Moderate
  > 2500      → High
  10000       → Monopoly (single supplier, 100 %)

SPOF: any supplier with share ≥ 70 % AND no qualified alternative is a SPOF.

Inventory Coverage (days):
  coverage_days = quantity_on_hand / daily_consumption
  Risk tier:
    < 7 days   → CRITICAL
    7-14 days  → HIGH
    14-30 days → MEDIUM
    ≥ 30 days  → LOW
"""

from __future__ import annotations

from typing import Optional
import numpy as np

from app import database as db
from app.models import (
    HHIResult,
    SPOFResult,
    InventoryCoverageResult,
    GeopoliticalRiskItem,
    MaterialSupplyRisk,
)

# ── Demo / fallback data ───────────────────────────────────────────────────────
_DEMO_SUPPLIER_MATERIALS: list[dict] = [
    {"material_id": "PHOTO-RES-EUV", "material_name": "EUV Photoresist",        "critical_flag": True,
     "supplier_id": "SUP-ALPHA-JP", "supplier_name": "Alpha Chem Industries (Demo)", "supply_share_pct": 70.0,
     "country": "Japan", "region": "Asia-Pacific", "qualified": True, "lead_time_days": 35},
    {"material_id": "PHOTO-RES-EUV", "material_name": "EUV Photoresist",        "critical_flag": True,
     "supplier_id": "SUP-BETA-KR",  "supplier_name": "Beta Materials Corp (Demo)",   "supply_share_pct": 30.0,
     "country": "South Korea", "region": "Asia-Pacific", "qualified": True, "lead_time_days": 28},
    {"material_id": "PHOTO-RES-ARF", "material_name": "ArF Immersion Photoresist", "critical_flag": True,
     "supplier_id": "SUP-GAMMA-DE", "supplier_name": "Gamma Precision GmbH (Demo)", "supply_share_pct": 50.0,
     "country": "Germany", "region": "Europe", "qualified": True, "lead_time_days": 45},
    {"material_id": "PHOTO-RES-ARF", "material_name": "ArF Immersion Photoresist", "critical_flag": True,
     "supplier_id": "SUP-DELTA-US", "supplier_name": "Delta Supply Co (Demo)",       "supply_share_pct": 50.0,
     "country": "United States", "region": "North America", "qualified": True, "lead_time_days": 21},
    {"material_id": "SPUTT-TGT-W",  "material_name": "Tungsten Sputter Target", "critical_flag": True,
     "supplier_id": "SUP-DELTA-US", "supplier_name": "Delta Supply Co (Demo)",       "supply_share_pct": 60.0,
     "country": "United States", "region": "North America", "qualified": True, "lead_time_days": 21},
    {"material_id": "SPUTT-TGT-W",  "material_name": "Tungsten Sputter Target", "critical_flag": True,
     "supplier_id": "SUP-EPSILON-TW","supplier_name":"Epsilon Tech Ltd (Demo)",      "supply_share_pct": 40.0,
     "country": "Taiwan", "region": "Asia-Pacific", "qualified": True, "lead_time_days": 30},
    {"material_id": "IMP-BF3",      "material_name": "BF3 Dopant Gas",           "critical_flag": True,
     "supplier_id": "SUP-ALPHA-JP", "supplier_name": "Alpha Chem Industries (Demo)", "supply_share_pct": 80.0,
     "country": "Japan", "region": "Asia-Pacific", "qualified": True, "lead_time_days": 35},
    {"material_id": "IMP-BF3",      "material_name": "BF3 Dopant Gas",           "critical_flag": True,
     "supplier_id": "SUP-DELTA-US", "supplier_name": "Delta Supply Co (Demo)",       "supply_share_pct": 20.0,
     "country": "United States", "region": "North America", "qualified": True, "lead_time_days": 21},
    {"material_id": "CVD-TEOS",     "material_name": "TEOS Precursor Gas",       "critical_flag": False,
     "supplier_id": "SUP-ETA-CN",   "supplier_name": "Eta Chemical Group (Demo)",    "supply_share_pct": 55.0,
     "country": "China", "region": "Asia-Pacific", "qualified": True, "lead_time_days": 25},
    {"material_id": "CVD-TEOS",     "material_name": "TEOS Precursor Gas",       "critical_flag": False,
     "supplier_id": "SUP-DELTA-US", "supplier_name": "Delta Supply Co (Demo)",       "supply_share_pct": 45.0,
     "country": "United States", "region": "North America", "qualified": True, "lead_time_days": 21},
    {"material_id": "CLEAN-SC1",    "material_name": "SC-1 Clean Chemical",      "critical_flag": False,
     "supplier_id": "SUP-DELTA-US", "supplier_name": "Delta Supply Co (Demo)",       "supply_share_pct": 100.0,
     "country": "United States", "region": "North America", "qualified": True, "lead_time_days": 21},
]

_DEMO_INVENTORY: list[dict] = [
    {"material_id": "PHOTO-RES-EUV", "material_name": "EUV Photoresist",         "critical_flag": True,  "quantity_on_hand": 62.5,  "daily_consumption": 12.5, "reorder_point": 37.5, "safety_stock": 25.0},
    {"material_id": "PHOTO-RES-ARF", "material_name": "ArF Immersion Photoresist","critical_flag": True,  "quantity_on_hand": 300.0, "daily_consumption":  8.0, "reorder_point": 40.0, "safety_stock": 24.0},
    {"material_id": "SPUTT-TGT-W",  "material_name": "Tungsten Sputter Target",  "critical_flag": True,  "quantity_on_hand":  18.0, "daily_consumption":  0.9, "reorder_point":  5.4, "safety_stock":  2.7},
    {"material_id": "SPUTT-TGT-CU", "material_name": "Copper Sputter Target",    "critical_flag": False, "quantity_on_hand":  55.0, "daily_consumption":  1.2, "reorder_point":  7.2, "safety_stock":  3.6},
    {"material_id": "CVD-TEOS",      "material_name": "TEOS Precursor Gas",       "critical_flag": False, "quantity_on_hand": 420.0, "daily_consumption": 15.0, "reorder_point": 90.0, "safety_stock": 45.0},
    {"material_id": "CMP-SLUR-STI",  "material_name": "STI CMP Slurry",           "critical_flag": False, "quantity_on_hand": 900.0, "daily_consumption": 20.0, "reorder_point": 80.0, "safety_stock": 40.0},
    {"material_id": "IMP-BF3",       "material_name": "BF3 Dopant Gas",           "critical_flag": True,  "quantity_on_hand":   8.0, "daily_consumption":  1.6, "reorder_point":  9.6, "safety_stock":  4.8},
    {"material_id": "CLEAN-SC1",     "material_name": "SC-1 Clean Chemical",      "critical_flag": False, "quantity_on_hand":1200.0, "daily_consumption": 25.0, "reorder_point": 75.0, "safety_stock": 37.5},
]

_DEMO_GEO_RISKS: list[dict] = [
    {"risk_id": "GEO-001", "affected_region": "Asia-Pacific",   "affected_material_id": "PHOTO-RES-EUV", "risk_level": "HIGH",
     "risk_reason": "[DEMO SCENARIO] Hypothetical export licensing delays for specialty photochemical precursors.", "source": "Demo/Synthetic Scenario", "source_date": "2025-01-01"},
    {"risk_id": "GEO-002", "affected_region": "Asia-Pacific",   "affected_material_id": "IMP-BF3",       "risk_level": "HIGH",
     "risk_reason": "[DEMO SCENARIO] Simulated regional logistics disruption causing lead-time extension for dopant gases.", "source": "Demo/Synthetic Scenario", "source_date": "2025-01-01"},
    {"risk_id": "GEO-003", "affected_region": "Europe",         "affected_material_id": "SPUTT-TGT-W",  "risk_level": "MEDIUM",
     "risk_reason": "[DEMO SCENARIO] Hypothetical energy-cost surcharge increasing unit cost of refractory metal targets.", "source": "Demo/Synthetic Scenario", "source_date": "2025-01-01"},
    {"risk_id": "GEO-004", "affected_region": "Asia-Pacific",   "affected_material_id": None,            "risk_level": "MEDIUM",
     "risk_reason": "[DEMO SCENARIO] Simulated shipping lane congestion increasing transit time by 7-14 days.", "source": "Demo/Synthetic Scenario", "source_date": "2025-01-01"},
]


# ── HHI ───────────────────────────────────────────────────────────────────────

def compute_hhi(shares: list[float]) -> float:
    """
    Herfindahl-Hirschman Index.
    shares: list of market share percentages (e.g. [70.0, 30.0]).
    Returns HHI on 0–10 000 scale.
    """
    if not shares:
        return 0.0
    return round(float(np.sum(np.array(shares) ** 2)), 2)


def hhi_concentration_level(hhi: float) -> str:
    """Classify HHI into standard concentration tiers."""
    if hhi >= 10000:
        return "MONOPOLY"
    if hhi > 2500:
        return "HIGH"
    if hhi > 1500:
        return "MODERATE"
    return "LOW"


async def _get_supplier_materials() -> list[dict]:
    rows = await db.fetch_rows(
        """
        SELECT sm.material_id, m.material_name, m.critical_flag,
               sm.supplier_id, s.supplier_name, sm.supply_share_pct,
               s.country, s.region, s.qualified, s.lead_time_days
        FROM supplier_materials sm
        JOIN materials m ON m.material_id = sm.material_id
        JOIN suppliers  s ON s.supplier_id = sm.supplier_id
        ORDER BY sm.material_id, sm.supply_share_pct DESC
        """
    )
    return rows if rows else _DEMO_SUPPLIER_MATERIALS


async def get_hhi_for_all_materials() -> list[HHIResult]:
    """Compute HHI for every material in the supply chain."""
    rows = await _get_supplier_materials()

    # Group by material
    material_map: dict[str, list[dict]] = {}
    for row in rows:
        mid = row["material_id"]
        material_map.setdefault(mid, []).append(row)

    results: list[HHIResult] = []
    for mid, suppliers in material_map.items():
        shares = [float(s["supply_share_pct"]) for s in suppliers]
        hhi = compute_hhi(shares)
        level = hhi_concentration_level(hhi)
        results.append(HHIResult(
            material_id=mid,
            material_name=suppliers[0]["material_name"],
            critical_flag=bool(suppliers[0]["critical_flag"]),
            hhi_value=hhi,
            concentration_level=level,
            supplier_count=len(suppliers),
            suppliers=[{"supplier_id": s["supplier_id"],
                        "supplier_name": s["supplier_name"],
                        "share_pct": s["supply_share_pct"],
                        "country": s["country"]} for s in suppliers],
        ))
    results.sort(key=lambda r: r.hhi_value, reverse=True)
    return results


# ── SPOF ──────────────────────────────────────────────────────────────────────
SPOF_SHARE_THRESHOLD = 70.0  # % share that makes a supplier a SPOF candidate


async def get_spof_analysis() -> list[SPOFResult]:
    """
    Identify single points of failure:
      - Supplier holds ≥ 70 % share of a critical material, OR
      - Only one qualified supplier exists for a material.
    """
    rows = await _get_supplier_materials()

    material_map: dict[str, list[dict]] = {}
    for row in rows:
        material_map.setdefault(row["material_id"], []).append(row)

    spofs: list[SPOFResult] = []
    for mid, suppliers in material_map.items():
        qualified_suppliers = [s for s in suppliers if s["qualified"]]
        dominant = max(suppliers, key=lambda s: float(s["supply_share_pct"]))
        dominant_share = float(dominant["supply_share_pct"])

        is_spof = (
            dominant_share >= SPOF_SHARE_THRESHOLD
            or len(qualified_suppliers) == 1
        )
        if is_spof:
            spofs.append(SPOFResult(
                material_id=mid,
                material_name=suppliers[0]["material_name"],
                critical_flag=bool(suppliers[0]["critical_flag"]),
                dominant_supplier_id=dominant["supplier_id"],
                dominant_supplier_name=dominant["supplier_name"],
                dominant_share_pct=dominant_share,
                qualified_supplier_count=len(qualified_suppliers),
                spof_reason=(
                    f"Single qualified supplier" if len(qualified_suppliers) == 1
                    else f"Dominant supplier holds {dominant_share:.0f}% share"
                ),
            ))

    return sorted(spofs, key=lambda r: r.dominant_share_pct, reverse=True)


# ── Inventory Coverage ─────────────────────────────────────────────────────────

def coverage_risk_tier(days: float) -> str:
    if days < 7:
        return "CRITICAL"
    if days < 14:
        return "HIGH"
    if days < 30:
        return "MEDIUM"
    return "LOW"


async def _get_inventory_data() -> list[dict]:
    rows = await db.fetch_rows(
        """
        SELECT i.material_id, m.material_name, m.critical_flag,
               i.quantity_on_hand, i.daily_consumption, i.reorder_point, i.safety_stock
        FROM inventory_snapshots i
        JOIN materials m ON m.material_id = i.material_id
        WHERE i.snapshot_date = (
            SELECT MAX(snapshot_date) FROM inventory_snapshots ii WHERE ii.material_id = i.material_id
        )
        ORDER BY i.material_id
        """
    )
    return rows if rows else _DEMO_INVENTORY


async def get_inventory_coverage() -> list[InventoryCoverageResult]:
    """Calculate days of coverage for all tracked materials."""
    rows = await _get_inventory_data()
    results: list[InventoryCoverageResult] = []
    for row in rows:
        daily = float(row["daily_consumption"])
        on_hand = float(row["quantity_on_hand"])
        coverage_days = round(on_hand / daily, 1) if daily > 0 else 999.0
        below_reorder = on_hand <= float(row["reorder_point"])
        below_safety  = on_hand <= float(row["safety_stock"])
        results.append(InventoryCoverageResult(
            material_id=row["material_id"],
            material_name=row["material_name"],
            critical_flag=bool(row["critical_flag"]),
            quantity_on_hand=on_hand,
            daily_consumption=daily,
            coverage_days=coverage_days,
            reorder_point=float(row["reorder_point"]),
            safety_stock=float(row["safety_stock"]),
            below_reorder_point=below_reorder,
            below_safety_stock=below_safety,
            risk_tier=coverage_risk_tier(coverage_days),
        ))
    results.sort(key=lambda r: r.coverage_days)
    return results


# ── Geopolitical Risk ──────────────────────────────────────────────────────────

async def get_geopolitical_risks() -> list[GeopoliticalRiskItem]:
    rows = await db.fetch_rows(
        "SELECT * FROM geopolitical_risks WHERE is_active = TRUE ORDER BY risk_level DESC, risk_id"
    )
    if not rows:
        rows = _DEMO_GEO_RISKS
    return [
        GeopoliticalRiskItem(
            risk_id=r["risk_id"],
            affected_region=r["affected_region"],
            affected_material_id=r.get("affected_material_id"),
            risk_level=r["risk_level"],
            risk_reason=r["risk_reason"],
            source=r["source"],
            source_date=str(r.get("source_date", "2025-01-01")),
        )
        for r in rows
    ]


# ── Combined material supply risk score ───────────────────────────────────────
_RISK_LEVEL_SCORE = {"LOW": 0.1, "MEDIUM": 0.4, "HIGH": 0.7, "CRITICAL": 1.0}


async def get_material_supply_risk(material_id: str) -> MaterialSupplyRisk:
    """
    Compute a combined supply risk score for a single material.
    Combines: HHI score, inventory coverage, SPOF presence, geopolitical risk.
    Weights: 30 % HHI, 30 % inventory, 25 % SPOF, 15 % geopolitical.
    """
    hhi_list = await get_hhi_for_all_materials()
    inv_list = await get_inventory_coverage()
    spof_list = await get_spof_analysis()
    geo_list  = await get_geopolitical_risks()

    hhi_item = next((h for h in hhi_list if h.material_id == material_id), None)
    inv_item  = next((i for i in inv_list  if i.material_id == material_id), None)
    spof_item = next((s for s in spof_list if s.material_id == material_id), None)

    # HHI component: normalise 0-10000 → 0-1
    hhi_score = (hhi_item.hhi_value / 10000.0) if hhi_item else 0.5

    # Inventory component
    inv_tier = inv_item.risk_tier if inv_item else "MEDIUM"
    inv_score = _RISK_LEVEL_SCORE.get(inv_tier, 0.4)

    # SPOF component
    spof_score = 1.0 if spof_item else 0.0

    # Geopolitical component (max risk for this material)
    geo_score = 0.0
    for g in geo_list:
        if g.affected_material_id == material_id or g.affected_material_id is None:
            geo_score = max(geo_score, _RISK_LEVEL_SCORE.get(g.risk_level, 0.1))

    combined = (
        0.30 * hhi_score
        + 0.30 * inv_score
        + 0.25 * spof_score
        + 0.15 * geo_score
    )
    combined = round(float(np.clip(combined, 0.0, 1.0)), 4)

    tier = "GREEN"
    if combined >= 0.75:
        tier = "CRITICAL"
    elif combined >= 0.55:
        tier = "RED"
    elif combined >= 0.35:
        tier = "AMBER"

    return MaterialSupplyRisk(
        material_id=material_id,
        material_name=hhi_item.material_name if hhi_item else material_id,
        hhi_score=round(hhi_score, 4),
        hhi_value=hhi_item.hhi_value if hhi_item else None,
        inventory_risk_tier=inv_tier,
        inventory_coverage_days=inv_item.coverage_days if inv_item else None,
        has_spof=spof_item is not None,
        geopolitical_risk_score=round(geo_score, 4),
        combined_supply_risk=combined,
        risk_tier=tier,
    )
