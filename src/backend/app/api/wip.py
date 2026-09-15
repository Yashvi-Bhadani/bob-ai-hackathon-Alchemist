"""
app/api/wip.py
==============
GET /api/wip  — WIP lots grouped by tool, process, and product

Member 1 — feature/bottleneck
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query

from app.services.bottleneck.queries import get_wip_lots

router = APIRouter()


@router.get("/wip", summary="Return WIP lots with optional filters")
async def get_wip(
    tool_id:    Optional[str] = Query(None, description="Filter by tool_id, e.g. LITH-07"),
    process_id: Optional[int] = Query(None, description="Filter by process_id"),
    product_id: Optional[str] = Query(None, description="Filter by product_id"),
):
    """
    Returns active WIP lots.

    Optional filters:
    - tool_id    : restrict to a specific tool
    - process_id : restrict to a specific process step
    - product_id : restrict to a specific product

    Response includes priority (1=HOT, 2=NORMAL, 3=LOW), status, and arrival_time
    so the caller can order lots by priority for scheduling.
    """
    lots = await get_wip_lots(
        tool_id=tool_id,
        process_id=process_id,
        product_id=product_id,
    )

    # Summarise counts by tool for convenience
    by_tool: dict[str, int] = {}
    for lot in lots:
        tid = lot.get("tool_id") or "unassigned"
        by_tool[tid] = by_tool.get(tid, 0) + 1

    return {
        "lots": [
            {
                "lot_id":      lot["lot_id"],
                "product_id":  lot["product_id"],
                "process_id":  lot["process_id"],
                "tool_id":     lot.get("tool_id"),
                "quantity":    lot.get("quantity", 25),
                "arrival_time": lot["arrival_time"].isoformat()
                                if hasattr(lot["arrival_time"], "isoformat")
                                else str(lot["arrival_time"]),
                "priority":    lot.get("priority", 2),
                "priority_label": {1: "HOT", 2: "NORMAL", 3: "LOW"}.get(
                    lot.get("priority", 2), "NORMAL"
                ),
                "status":      lot.get("status", "QUEUED"),
            }
            for lot in lots
        ],
        "total_lots":    len(lots),
        "lots_by_tool":  by_tool,
    }
