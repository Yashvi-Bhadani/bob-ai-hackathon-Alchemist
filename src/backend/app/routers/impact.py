"""
Impact & Combined Risk Router
Member 3 — feature/dashboard
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.services import impact_service
from app.models import CombinedRiskResult

router = APIRouter()


@router.get("/{tool_id}", response_model=CombinedRiskResult,
            summary="Get combined manufacturing + supply chain risk for a tool")
async def get_combined_risk(
    tool_id: str,
    outage_hours: Optional[float] = Query(
        None, gt=0, le=168,
        description="If provided, includes an outage simulation in the assessment"
    ),
):
    """
    Returns a full combined risk assessment for the given tool, combining:
    - Manufacturing bottleneck score
    - Supply chain risk for the tool's primary material
    - Outage simulation (if outage_hours supplied)
    - Prioritised mitigation recommendations

    This is the main endpoint for the dashboard full-risk view.
    """
    try:
        result = await impact_service.get_combined_risk(tool_id.upper(), outage_hours)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result
