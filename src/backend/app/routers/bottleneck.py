"""
Bottleneck Detection & Outage Simulation Router
Member 1 — feature/bottleneck
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services import bottleneck_service
from app.models import BottleneckListResponse, OutageSimulationResult

router = APIRouter()


@router.get("/", response_model=BottleneckListResponse, summary="Get all tool bottleneck scores")
async def get_bottleneck_scores():
    """
    Returns bottleneck scores for all active fab tools, sorted by severity.
    Scores are computed using utilisation, WIP pressure, and capacity pressure.
    """
    results = await bottleneck_service.get_all_tool_scores()
    critical = [r for r in results if r.is_critical]
    return BottleneckListResponse(
        tools=results,
        critical_count=len(critical),
        most_critical_tool_id=results[0].tool_id if results else None,
    )


@router.get("/{tool_id}", summary="Get bottleneck score for a specific tool")
async def get_tool_bottleneck(tool_id: str):
    """Returns bottleneck details for a single tool by its tool_id."""
    results = await bottleneck_service.get_all_tool_scores()
    tool = next((r for r in results if r.tool_id == tool_id.upper()), None)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found.")
    return tool


@router.post("/simulate-outage", response_model=OutageSimulationResult,
             summary="Simulate a tool outage and calculate backlog/recovery")
async def simulate_outage(
    tool_id: str = Query(..., description="Tool identifier, e.g. LITH-07"),
    outage_hours: float = Query(..., gt=0, le=168, description="Duration of simulated outage in hours"),
):
    """
    Simulates an outage of the specified tool for the given number of hours.
    Calculates:
    - Backlog accumulated during downtime
    - Total backlog to recover
    - Recovery time after tool is restored
    - Downstream process steps affected and their delay estimates
    """
    try:
        result = await bottleneck_service.simulate_tool_outage(tool_id.upper(), outage_hours)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result
