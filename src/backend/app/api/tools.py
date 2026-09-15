"""
app/api/tools.py
=================
GET /api/tools      — tool list with live utilization and bottleneck indicator
GET /api/processes  — ordered process sequence with next-step dependencies

Member 1 — feature/bottleneck
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.bottleneck.queries import get_tools, get_processes, get_snapshots
from app.services.bottleneck.utilization import compute_utilization
from app.services.bottleneck.wip_pressure import compute_wip_pressure, normalize_wip_pressure
from app.services.bottleneck.capacity_pressure import compute_capacity_pressure
from app.services.bottleneck.score import compute_bottleneck_score, classify_severity, compute_downtime_pct
from app.services.bottleneck.confidence import compute_confidence

router = APIRouter()


def _score_tool(tool: dict, snapshots: list[dict]) -> dict:
    """Compute all scores for a single tool dict and return an annotated copy."""
    avail = float(tool.get("available_hours") or 24.0)
    cap_rate = float(tool.get("capacity_units_per_hour") or 1.0)

    # Use the latest snapshot values if available; fall back to tool-level fields
    if snapshots:
        latest = snapshots[-1]
        busy    = float(latest.get("busy_hours") or 0)
        downtime = float(latest.get("downtime_hours") or 0)
        total   = float(latest.get("available_hours") or avail)
        wip     = int(latest.get("wip_units") or tool.get("_wip_units") or 0)
        cap_units = float(latest.get("capacity_units") or cap_rate * avail)
    else:
        busy     = float(tool.get("_busy_hours") or 0)
        downtime = float(tool.get("_downtime_hours") or 0)
        total    = avail
        wip      = int(tool.get("_wip_units") or 0)
        cap_units = cap_rate * avail

    normal_wip = float(tool.get("_normal_wip") or max(wip, 1))

    util         = compute_utilization(busy, total)
    raw_wip_p    = compute_wip_pressure(wip, normal_wip)
    norm_wip_p   = normalize_wip_pressure(raw_wip_p)
    cap_p        = compute_capacity_pressure(busy * cap_rate, cap_units)
    dt_pct       = compute_downtime_pct(downtime, total)
    score        = compute_bottleneck_score(util, cap_p, norm_wip_p, dt_pct)
    severity     = classify_severity(score)

    wip_history  = [float(s.get("wip_units") or 0) for s in snapshots]
    conf_result  = compute_confidence(wip_history) if wip_history else compute_confidence([wip])

    return {
        "tool_id":                tool["tool_id"],
        "tool_name":              tool["tool_name"],
        "process_id":             tool["process_id"],
        "process_name":           tool.get("process_name", ""),
        "tool_type":              tool.get("tool_type", ""),
        "status":                 tool.get("status", "ACTIVE"),
        "available_hours":        avail,
        "capacity_units_per_hour": cap_rate,
        "compatible_products":    tool.get("compatible_products", []),
        "utilization":            round(util, 4),
        "utilization_pct":        round(util * 100, 2),
        "wip_units":              wip,
        "wip_pressure_raw":       round(raw_wip_p, 4),
        "capacity_pressure":      round(cap_p, 4),
        "downtime_pct":           round(dt_pct, 4),
        "bottleneck_score":       score,
        "severity":               severity,
        "is_bottleneck":          severity in ("HIGH", "CRITICAL"),
        "confidence":             conf_result["confidence"],
        "low_confidence":         conf_result["low_confidence"],
        "wip_trend":              conf_result["wip_trend"],
    }


@router.get("/tools", summary="List all fab tools with utilization and bottleneck indicator")
async def list_tools():
    """
    Returns all active fab tools enriched with live utilization, WIP, scores,
    and bottleneck indicator.

    Fields of interest for Member 3 (alternate-tool check):
      - compatible_products : list of product IDs the tool can process
      - is_bottleneck        : True when severity is HIGH or CRITICAL
      - utilization_pct      : current utilisation as a percentage
    """
    tools = await get_tools()
    result = []
    for t in tools:
        snaps = await get_snapshots(t["tool_id"])
        result.append(_score_tool(t, snaps))
    result.sort(key=lambda r: r["bottleneck_score"], reverse=True)
    return {"tools": result, "count": len(result)}


@router.get("/processes", summary="Return ordered process sequence with next-step links")
async def list_processes():
    """
    Returns all fab processes in production order with their next_process_id
    linked field, enabling Member 3 to traverse the downstream impact chain.
    """
    processes = await get_processes()
    return {"processes": processes, "count": len(processes)}
