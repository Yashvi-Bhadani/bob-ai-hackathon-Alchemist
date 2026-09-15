"""
Supply Risk API endpoints
==========================

GET /api/supply-risks
GET /api/supply-risks/{material_id}
GET /api/spofs

Member 2 owns this file.  Do not modify from other members.

Scoring engine (all weights documented in services/supply_risk/score.py):
    HHI concentration : 30 %
    SPOF              : 30 %
    Inventory coverage: 20 %
    Geopolitical risk : 20 %

Severity labels:
    0 – 39   LOW
    40 – 69  MEDIUM
    70 – 84  HIGH
    85 – 100 CRITICAL
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app import database as db
from app.services.supply_risk.demo_data import (
    DEMO_MATERIALS,
    DEMO_MATERIAL_SUPPLIERS,
    DEMO_INVENTORY,
)
from app.services.supply_risk.geo_risk import (
    DEMO_RISK_FACTORS,
    aggregate_geo_risk_score,
    GEO_RISK_LEVEL_SCORE,
)
from app.services.supply_risk.hhi import compute_hhi, hhi_concentration_level
from app.services.supply_risk.spof import is_spof, qualified_supplier_count
from app.services.supply_risk.inventory_coverage import (
    compute_coverage_days,
    coverage_risk_tier,
    is_below_safety_stock,
    coverage_normalised,
)
from app.services.supply_risk.score import compute_composite_score, severity_label

router = APIRouter()


# ── Internal helpers ───────────────────────────────────────────────────────

async def _load_all() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """
    Load (materials, material_suppliers, inventory, risk_factors) from DB
    or fall back to demo data.
    """
    mat_rows = await db.fetch_rows(
        "SELECT material_id, material_name, material_category, criticality "
        "FROM materials ORDER BY material_id"
    )
    sup_rows = await db.fetch_rows(
        """
        SELECT ms.material_id, ms.supplier_id, s.supplier_name,
               ms.supply_share_pct, ms.qualified, ms.lead_time_days,
               s.country, s.region
        FROM material_suppliers ms
        JOIN suppliers s ON s.supplier_id = ms.supplier_id
        ORDER BY ms.material_id, ms.supply_share_pct DESC
        """
    )
    inv_rows = await db.fetch_rows(
        "SELECT material_id, current_inventory_units, daily_consumption_units, "
        "       safety_stock_days "
        "FROM material_inventory"
    )
    risk_rows = await db.fetch_rows(
        "SELECT material_id, risk_type, risk_level, reason, source, "
        "       source_date::text AS source_date, affected_region "
        "FROM risk_factors ORDER BY risk_factor_id"
    )

    if not mat_rows:
        mat_rows = DEMO_MATERIALS
    if not sup_rows:
        sup_rows = DEMO_MATERIAL_SUPPLIERS
    if not inv_rows:
        inv_rows = DEMO_INVENTORY
    if not risk_rows:
        risk_rows = DEMO_RISK_FACTORS

    return mat_rows, sup_rows, inv_rows, risk_rows


def _assess_material(
    material: dict,
    supplier_rows: list[dict],
    inventory_row: dict | None,
    risk_rows: list[dict],
    detailed: bool = False,
) -> dict:
    """
    Compute the full supply risk assessment for one material.

    Parameters
    ----------
    material      : single material dict
    supplier_rows : all material_supplier rows for this material
    inventory_row : inventory row for this material (or None)
    risk_rows     : ALL risk factor rows (filtered internally)
    detailed      : if True, include per-supplier detail and geo factor list
    """
    mid = material["material_id"]

    # ── HHI ──────────────────────────────────────────────────────────────────
    shares = [float(r["supply_share_pct"]) for r in supplier_rows]
    hhi = compute_hhi(shares)
    hhi_level = hhi_concentration_level(hhi)
    hhi_interpretation = (
        "HIGH concentration (HHI > 2500 — application-internal threshold)"
        if hhi > 2500
        else f"{hhi_level} concentration"
    )

    # ── SPOF ──────────────────────────────────────────────────────────────────
    spof = is_spof(supplier_rows)
    qual_count = qualified_supplier_count(supplier_rows)

    # ── Inventory ─────────────────────────────────────────────────────────────
    if inventory_row:
        cov_days = compute_coverage_days(
            float(inventory_row.get("current_inventory_units", 0)),
            float(inventory_row.get("daily_consumption_units", 0)),
        )
        safety_days = float(inventory_row.get("safety_stock_days", 14))
    else:
        cov_days = None
        safety_days = 14.0

    inv_tier = coverage_risk_tier(cov_days)
    below_safety = is_below_safety_stock(cov_days, safety_days)

    # ── Geopolitical ──────────────────────────────────────────────────────────
    geo_score = aggregate_geo_risk_score(risk_rows, mid)

    # ── Composite score ───────────────────────────────────────────────────────
    inv_norm = coverage_normalised(cov_days, safety_stock_days=safety_days)
    composite = compute_composite_score(hhi, spof, inv_norm, geo_score)
    severity = severity_label(composite)

    result: dict = {
        "material_id": mid,
        "material_name": material["material_name"],
        "criticality": material["criticality"],
        "hhi": round(hhi, 2),
        "hhi_interpretation": hhi_interpretation,
        "qualified_supplier_count": qual_count,
        "spof": spof,
        "inventory_coverage_days": cov_days,
        "safety_stock_days": safety_days,
        "inventory_risk_tier": inv_tier,
        "below_safety_stock": below_safety,
        "geopolitical_risk_score": geo_score,
        "composite_score": composite,
        "severity": severity,
    }

    if detailed:
        result["suppliers"] = [
            {
                "supplier_id": r["supplier_id"],
                "supplier_name": r.get("supplier_name", r["supplier_id"]),
                "supply_share_pct": float(r["supply_share_pct"]),
                "qualified": bool(r.get("qualified", True)),
                "lead_time_days": int(r.get("lead_time_days", 30)),
                "country": r.get("country", "Unknown"),
                "region": r.get("region", "Unknown"),
            }
            for r in supplier_rows
        ]
        result["geopolitical_factors"] = [
            {
                "risk_type": r.get("risk_type"),
                "risk_level": r.get("risk_level"),
                "reason": r.get("reason"),
                "source": r.get("source"),
                "source_date": str(r.get("source_date", "")),
                "affected_region": r.get("affected_region"),
            }
            for r in risk_rows
            if r.get("material_id") is None or r.get("material_id") == mid
        ]

    return result


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get(
    "/supply-risks",
    summary="Return all material risk assessments ranked by composite score",
    tags=["Supply Risk"],
    response_description="Array of risk assessments, highest score first",
)
async def get_all_supply_risks():
    """
    Compute and return supply risk assessments for all tracked materials.

    Results are sorted by **composite_score** descending so the riskiest
    materials appear first.  Each entry includes HHI, SPOF flag, inventory
    coverage, geopolitical risk, composite score, and severity label.
    """
    mat_rows, sup_rows, inv_rows, risk_rows = await _load_all()

    suppliers_by_mat: dict[str, list[dict]] = {}
    for r in sup_rows:
        suppliers_by_mat.setdefault(r["material_id"], []).append(r)

    inventory_by_mat: dict[str, dict] = {r["material_id"]: r for r in inv_rows}

    results = [
        _assess_material(
            mat,
            suppliers_by_mat.get(mat["material_id"], []),
            inventory_by_mat.get(mat["material_id"]),
            risk_rows,
            detailed=False,
        )
        for mat in mat_rows
    ]
    results.sort(key=lambda r: r["composite_score"], reverse=True)
    return results


@router.get(
    "/supply-risks/{material_id}",
    summary="Get detailed supply risk assessment for a specific material",
    tags=["Supply Risk"],
    response_description="Detailed risk record including suppliers and geo factors",
)
async def get_supply_risk_by_material(material_id: str):
    """
    Return a full risk breakdown for **material_id**, including:

    - Per-supplier shares, qualification status, lead time
    - HHI value and interpretation
    - Qualified supplier count and SPOF flag
    - Inventory coverage vs. safety stock
    - Geopolitical risk factors (source/date-aware)
    - Composite score (0–100) and severity label
    """
    mat_rows, sup_rows, inv_rows, risk_rows = await _load_all()

    mid_upper = material_id.upper()
    material = next((m for m in mat_rows if m["material_id"].upper() == mid_upper), None)
    if material is None:
        raise HTTPException(status_code=404, detail=f"Material '{material_id}' not found.")

    suppliers_for_mat = [r for r in sup_rows if r["material_id"].upper() == mid_upper]
    inv_row = next((r for r in inv_rows if r["material_id"].upper() == mid_upper), None)

    return _assess_material(material, suppliers_for_mat, inv_row, risk_rows, detailed=True)


@router.get(
    "/spofs",
    summary="Return materials with a Single Point of Failure (SPOF = true)",
    tags=["Supply Risk"],
    response_description="Array of materials where exactly one qualified supplier exists",
)
async def get_spofs():
    """
    Return all materials where **exactly one qualified supplier** exists.

    A high HHI alone does **not** constitute a SPOF — a material is only
    flagged here when a single qualified supplier is the sole viable source.
    """
    mat_rows, sup_rows, inv_rows, risk_rows = await _load_all()

    suppliers_by_mat: dict[str, list[dict]] = {}
    for r in sup_rows:
        suppliers_by_mat.setdefault(r["material_id"], []).append(r)

    inventory_by_mat: dict[str, dict] = {r["material_id"]: r for r in inv_rows}

    spof_results = []
    for mat in mat_rows:
        mid = mat["material_id"]
        sups = suppliers_by_mat.get(mid, [])
        if is_spof(sups):
            assessment = _assess_material(mat, sups, inventory_by_mat.get(mid), risk_rows, detailed=True)
            spof_results.append(assessment)

    spof_results.sort(key=lambda r: r["composite_score"], reverse=True)
    return spof_results
