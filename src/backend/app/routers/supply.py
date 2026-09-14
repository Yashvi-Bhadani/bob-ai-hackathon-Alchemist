"""
Supply Chain Risk Router
Member 2 — feature/supply-risk
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services import supply_service
from app.models import (
    HHIResult,
    SPOFResult,
    InventoryCoverageResult,
    GeopoliticalRiskItem,
    MaterialSupplyRisk,
)
from typing import List

router = APIRouter()


@router.get("/hhi", response_model=List[HHIResult],
            summary="Get HHI supplier concentration scores for all materials")
async def get_hhi():
    """
    Computes the Herfindahl-Hirschman Index (HHI) for each material.
    HHI > 2500 = High concentration. HHI = 10000 = monopoly.
    """
    return await supply_service.get_hhi_for_all_materials()


@router.get("/spof", response_model=List[SPOFResult],
            summary="Identify single points of failure in the supply chain")
async def get_spof():
    """
    Returns materials with a Single Point of Failure (SPOF):
    - A supplier holding ≥ 70% share, OR
    - Only one qualified supplier exists for the material.
    """
    return await supply_service.get_spof_analysis()


@router.get("/inventory", response_model=List[InventoryCoverageResult],
            summary="Get inventory coverage in days for all materials")
async def get_inventory():
    """
    Returns current inventory coverage (days on-hand) for all tracked materials.
    Risk tiers: CRITICAL (<7 days), HIGH (7-14), MEDIUM (14-30), LOW (≥30).
    """
    return await supply_service.get_inventory_coverage()


@router.get("/geopolitical", response_model=List[GeopoliticalRiskItem],
            summary="Get active geopolitical and export-control risk entries")
async def get_geopolitical():
    """
    Returns active geopolitical risk entries.
    ⚠️ All entries are synthetic demo/scenario data. Not real-world claims.
    """
    return await supply_service.get_geopolitical_risks()


@router.get("/material/{material_id}", response_model=MaterialSupplyRisk,
            summary="Get combined supply risk score for a specific material")
async def get_material_risk(material_id: str):
    """
    Returns a combined supply risk score for the given material.
    Combines HHI, inventory coverage, SPOF, and geopolitical risk.
    """
    try:
        return await supply_service.get_material_supply_risk(material_id.upper())
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))
