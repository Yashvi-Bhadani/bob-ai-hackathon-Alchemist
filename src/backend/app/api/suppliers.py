"""
GET /api/suppliers
==================
Returns all known suppliers.  Reads from the ``suppliers`` table in the live
database; falls back to demo data when no database is configured.

Member 2 owns this file.  Do not modify from other members.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app import database as db
from app.services.supply_risk.demo_data import DEMO_SUPPLIERS

router = APIRouter()


# ── Response shape ─────────────────────────────────────────────────────────

def _format_supplier(row: dict) -> dict:
    return {
        "supplier_id": row["supplier_id"],
        "supplier_name": row["supplier_name"],
        "country": row["country"],
        "region": row["region"],
        "qualification_status": row.get("qualification_status", "QUALIFIED"),
        "created_at": str(row["created_at"]) if row.get("created_at") else None,
    }


# ── Endpoint ───────────────────────────────────────────────────────────────

@router.get(
    "/suppliers",
    summary="List all suppliers",
    tags=["Supply Risk"],
    response_description="Array of supplier records",
)
async def get_suppliers(
    region: Optional[str] = Query(None, description="Filter by region (case-insensitive)"),
    qualification_status: Optional[str] = Query(
        None, description="Filter by status: QUALIFIED | PENDING | DISQUALIFIED"
    ),
):
    """
    Return information on every tracked supplier.

    Optional filters:
    - **region**: e.g. `Asia-Pacific`, `Europe`, `North America`
    - **qualification_status**: `QUALIFIED` | `PENDING` | `DISQUALIFIED`
    """
    rows = await db.fetch_rows(
        """
        SELECT supplier_id, supplier_name, country, region,
               qualification_status, created_at
        FROM suppliers
        ORDER BY region, country, supplier_name
        """
    )
    if not rows:
        rows = DEMO_SUPPLIERS

    # Apply optional filters
    if region:
        rows = [r for r in rows if r.get("region", "").lower() == region.lower()]
    if qualification_status:
        rows = [
            r for r in rows
            if r.get("qualification_status", "QUALIFIED").upper() == qualification_status.upper()
        ]

    return [_format_supplier(r) for r in rows]
