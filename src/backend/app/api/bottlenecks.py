"""
app/api/bottlenecks.py
=======================
GET /api/bottlenecks           — ranked bottleneck list (highest score first)
GET /api/bottlenecks/{tool_id} — full detail for one tool

Member 1 — feature/bottleneck
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.bottleneck.queries import get_tools, get_tool, get_snapshots
from app.services.bottleneck.utilization import compute_utilization
from app.services.bottleneck.wip_pressure import compute_wip_pressure, normalize_wip_pressure
from app.services.bottleneck.capacity_pressure import compute_capacity_pressure
from app.services.bottleneck.score import (
    compute_bottleneck_score,
    classify_severity,
    compute_downtime_pct,
)
from app.services.bottleneck.confidence import compute_confidence
from app.services.bottleneck.backlog_recovery import (
    calculate_backlog_recovery,
    estimate_cycle_time_littles_law,
)

router = APIRouter()


def _full_assessment(tool: dict, snapshots: list[dict]) -> dict:
    """
    Compute the full bottleneck assessment dict for a single tool.
    This is the authoritative assessment object consumed by Member 3.
    """
    avail    = float(tool.get("available_hours") or 24.0)
    cap_rate = float(tool.get("capacity_units_per_hour") or 1.0)

    # Latest snapshot values (or tool-level fallback for demo)
    if snapshots:
        latest   = snapshots[-1]
        busy     = float(latest.get("busy_hours") or 0)
        downtime = float(latest.get("downtime_hours") or 0)
        total    = float(latest.get("available_hours") or avail)
        wip      = int(latest.get("wip_units") or tool.get("_wip_units") or 0)
        cap_units = float(latest.get("capacity_units") or cap_rate * avail)
    else:
        busy     = float(tool.get("_busy_hours") or 0)
        downtime = float(tool.get("_downtime_hours") or 0)
        total    = avail
        wip      = int(tool.get("_wip_units") or 0)
        cap_units = cap_rate * avail

    normal_wip  = float(tool.get("_normal_wip") or max(wip, 1))

    # ── Core calculations ──────────────────────────────────────────────────
    util         = compute_utilization(busy, total)
    raw_wip_p    = compute_wip_pressure(wip, normal_wip)
    norm_wip_p   = normalize_wip_pressure(raw_wip_p)
    cap_p        = compute_capacity_pressure(busy * cap_rate, cap_units)
    dt_pct       = compute_downtime_pct(downtime, total)
    score        = compute_bottleneck_score(util, cap_p, norm_wip_p, dt_pct)
    severity     = classify_severity(score)

    # ── Confidence and trend ───────────────────────────────────────────────
    wip_history  = [float(s.get("wip_units") or 0) for s in snapshots]
    conf         = compute_confidence(wip_history if wip_history else [float(wip)])

    # ── Historical trend data (last 5 snapshots) ───────────────────────────
    history = [
        {
            "snapshot_time": s["snapshot_time"].isoformat()
                             if hasattr(s.get("snapshot_time"), "isoformat")
                             else str(s.get("snapshot_time", "")),
            "wip_units":    s.get("wip_units"),
            "utilization":  round(
                compute_utilization(
                    float(s.get("busy_hours") or 0),
                    float(s.get("available_hours") or avail),
                ), 4
            ),
        }
        for s in snapshots[-5:]
    ]

    # ── Arrival rate for Little's Law estimate ─────────────────────────────
    arrival_rate   = util * cap_rate            # lots/hr derived from utilisation
    cycle_time_est = estimate_cycle_time_littles_law(wip, arrival_rate)

    return {
        # Identification
        "tool_id":                 tool["tool_id"],
        "tool_name":               tool["tool_name"],
        "process_id":              tool["process_id"],
        "process_name":            tool.get("process_name", ""),
        "tool_type":               tool.get("tool_type", ""),
        "status":                  tool.get("status", "ACTIVE"),
        "compatible_products":     tool.get("compatible_products", []),
        # Score inputs
        "utilization":             round(util, 4),
        "utilization_pct":         round(util * 100, 2),
        "wip_units":               wip,
        "normal_wip":              normal_wip,
        "wip_pressure_raw":        round(raw_wip_p, 4),
        "wip_pressure_normalized": round(norm_wip_p, 4),
        "capacity_pressure":       round(cap_p, 4),
        "downtime_hours":          downtime,
        "downtime_pct":            round(dt_pct, 4),
        # Score outputs
        "bottleneck_score":        score,
        "severity":                severity,
        "is_bottleneck":           severity in ("HIGH", "CRITICAL"),
        # Confidence
        "confidence":              conf["confidence"],
        "low_confidence":          conf["low_confidence"],
        "snapshot_count":          conf["snapshot_count"],
        "wip_trend":               conf["wip_trend"],
        "wip_cov":                 conf["cov"],
        # Little's Law cycle-time estimate (reference only)
        "cycle_time_estimate_hrs": cycle_time_est,
        "cycle_time_note":         "Little's Law baseline estimate only; not used for recovery calculations.",
        # Trend history
        "history":                 history,
    }


@router.get("/bottlenecks", summary="Ranked list of all tool bottleneck assessments")
async def list_bottlenecks():
    """
    Returns all tools ranked by bottleneck_score descending.
    Critical tools appear first.

    Response shape mirrors GET /api/bottlenecks/{tool_id} but without
    the full history array (use the detail endpoint for that).
    """
    tools = await get_tools()
    results = []
    for t in tools:
        snaps  = await get_snapshots(t["tool_id"])
        detail = _full_assessment(t, snaps)
        # Drop verbose history for the list view
        detail.pop("history", None)
        results.append(detail)

    results.sort(key=lambda r: r["bottleneck_score"], reverse=True)
    critical = [r for r in results if r["severity"] == "CRITICAL"]
    return {
        "bottlenecks":            results,
        "count":                  len(results),
        "critical_count":         len(critical),
        "most_critical_tool_id":  results[0]["tool_id"] if results else None,
    }


@router.get("/bottlenecks/{tool_id}", summary="Full bottleneck detail for a single tool")
async def get_bottleneck(tool_id: str):
    """
    Returns the complete bottleneck assessment for the given tool including:
    - Utilization ratio and percentage
    - Raw and normalized WIP pressure
    - Capacity pressure
    - Downtime percentage
    - Composite bottleneck score (0–100)
    - Severity classification
    - Confidence and trend (from historical snapshots)
    - Little's Law cycle-time estimate (reference only)
    - Last 5 snapshot history points

    Intended as the primary integration endpoint for Member 3.
    """
    tool = await get_tool(tool_id.upper())
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found.")

    snaps = await get_snapshots(tool["tool_id"])
    return _full_assessment(tool, snaps)
