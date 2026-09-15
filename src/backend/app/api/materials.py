"""
GET /api/materials
==================
Returns all tracked materials with criticality, active supplier count,
inventory coverage days, and current risk status.

Member 2 owns this file.  Do not modify from other members.
"""

from __future__ import annotations

from fastapi import APIRouter

from app import database as db
from app.services.supply_risk.demo_data import (
    DEMO_MATERIALS,
    DEMO_MATERIAL_SUPPLIERS,
    DEMO_INVENTORY,
)
from app.services.supply_risk.inventory_coverage import (
    compute_coverage_days,
    coverage_risk_tier,
)
from app.services.supply_risk.spof import qualified_supplier_count

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────────────

def _build_material_response(
    material: dict,
    supplier_rows: list[dict],
    inventory_row: dict | None,
) -> dict:
    """Assemble the per-material response dict."""
    qual_count = qualified_supplier_count(supplier_rows)
    total_count = len(supplier_rows)

    inv_coverage: float | None = None
    risk_status = "UNKNOWN"
    if inventory_row:
        inv_coverage = compute_coverage_days(
            float(inventory_row.get("current_inventory_units", 0)),
            float(inventory_row.get("daily_consumption_units", 0)),
        )
        risk_status = coverage_risk_tier(inv_coverage)

    return {
        "material_id": material["material_id"],
        "material_name": material["material_name"],
        "material_category": material["material_category"],
        "criticality": material["criticality"],
        "supplier_count": total_count,
        "qualified_supplier_count": qual_count,
        "inventory_coverage_days": inv_coverage,
        "risk_status": risk_status,
        "created_at": str(material["created_at"]) if material.get("created_at") else None,
    }


# ── Endpoint ───────────────────────────────────────────────────────────────

@router.get(
    "/materials",
    summary="List all materials with criticality, supplier count, and inventory coverage",
    tags=["Supply Risk"],
    response_description="Array of material summary records",
)
async def get_materials():
    """
    Return all tracked materials enriched with:
    - **criticality** (LOW / MEDIUM / HIGH / CRITICAL)
    - **supplier_count** — total number of supplier rows
    - **qualified_supplier_count** — suppliers with `qualified = true`
    - **inventory_coverage_days** — current days on hand (null if no consumption)
    - **risk_status** — inventory risk tier (CRITICAL / HIGH / MEDIUM / LOW)
    """
    mat_rows = await db.fetch_rows(
        "SELECT material_id, material_name, material_category, criticality, created_at "
        "FROM materials ORDER BY criticality DESC, material_name"
    )
    sup_rows = await db.fetch_rows(
        "SELECT material_id, supplier_id, qualified FROM material_suppliers"
    )
    inv_rows = await db.fetch_rows(
        "SELECT material_id, current_inventory_units, daily_consumption_units "
        "FROM material_inventory"
    )

    # Fall back to demo data when database is unavailable
    if not mat_rows:
        mat_rows = DEMO_MATERIALS
    if not sup_rows:
        sup_rows = DEMO_MATERIAL_SUPPLIERS
    if not inv_rows:
        inv_rows = DEMO_INVENTORY

    # Index by material_id
    suppliers_by_mat: dict[str, list[dict]] = {}
    for r in sup_rows:
        suppliers_by_mat.setdefault(r["material_id"], []).append(r)

    inventory_by_mat: dict[str, dict] = {r["material_id"]: r for r in inv_rows}

    return [
        _build_material_response(
            mat,
            suppliers_by_mat.get(mat["material_id"], []),
            inventory_by_mat.get(mat["material_id"]),
        )
        for mat in mat_rows
    ]
