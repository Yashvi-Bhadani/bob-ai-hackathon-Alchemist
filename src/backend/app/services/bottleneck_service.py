"""
Bottleneck Detection & Outage Simulation Service
=================================================
All calculations use deterministic engineering formulas — no ML models.

Formulas used
-------------
WIP Pressure       = queued_lots / (max_capacity_wph * shift_hours / avg_lot_cycle_time)
Capacity Pressure  = max(0, (utilization_pct - 85) / 15)   # normalised above 85 % threshold
Bottleneck Score   = 0.50 * (util/100) + 0.30 * wip_pressure + 0.20 * capacity_pressure

Outage Backlog     = arrival_rate * outage_hours   (lots arriving while tool is down)
Recovery Time      = (existing_backlog + outage_backlog) / (effective_rate - arrival_rate)
                   = impossible if effective_rate <= arrival_rate

Effective rate accounts for remaining capacity after downtime is resolved (tool back at 100 %).
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np

from app import database as db
from app.models import (
    BottleneckResult,
    OutageSimulationResult,
    DownstreamImpactItem,
)

# ── Constants ──────────────────────────────────────────────────────────────────
SHIFT_HOURS = 8.0                  # standard shift length for WIP pressure calc
AVG_LOT_CYCLE_TIME_HRS = 2.5       # typical lithography cycle time per lot
BOTTLENECK_UTIL_THRESHOLD = 85.0   # utilisation % above which pressure is measured
WIP_CRITICAL_THRESHOLD = 0.8       # WIP pressure score considered critical
CRITICAL_BOTTLENECK_SCORE = 0.60   # composite score for CRITICAL classification

# Downstream step sequence (step_order values from process_steps table)
DOWNSTREAM_STEP_ORDER = {
    "Lithography":            4,
    "Etch":                   5,
    "Deposition (CVD)":       6,
    "CMP Planarization":      7,
    "Metal Fill (PVD)":       8,
    "Final Inspection & Test":9,
}

# ── Demo / fallback data ───────────────────────────────────────────────────────
_DEMO_TOOLS: list[dict] = [
    {"tool_id": "LITH-07", "tool_name": "EUV Scanner Unit 7",       "process_step": "Lithography",
     "max_capacity_wph": 120.0, "mttr_hours": 8.0,
     "utilization_pct": 94.5, "wip_lots": 38, "downtime_hrs": 0.5, "throughput_wph": 113.4},
    {"tool_id": "LITH-08", "tool_name": "EUV Scanner Unit 8",       "process_step": "Lithography",
     "max_capacity_wph": 120.0, "mttr_hours": 8.0,
     "utilization_pct": 71.2, "wip_lots": 18, "downtime_hrs": 0.0, "throughput_wph": 85.4},
    {"tool_id": "ETCH-03", "tool_name": "Plasma Etch Chamber 3",    "process_step": "Etch",
     "max_capacity_wph": 180.0, "mttr_hours": 3.0,
     "utilization_pct": 62.0, "wip_lots": 14, "downtime_hrs": 0.0, "throughput_wph": 111.6},
    {"tool_id": "ETCH-04", "tool_name": "Plasma Etch Chamber 4",    "process_step": "Etch",
     "max_capacity_wph": 180.0, "mttr_hours": 3.0,
     "utilization_pct": 58.5, "wip_lots": 11, "downtime_hrs": 1.0, "throughput_wph": 105.3},
    {"tool_id": "CVD-11",  "tool_name": "LPCVD Furnace 11",         "process_step": "Deposition (CVD)",
     "max_capacity_wph": 150.0, "mttr_hours": 4.0,
     "utilization_pct": 45.0, "wip_lots":  9, "downtime_hrs": 0.0, "throughput_wph": 67.5},
    {"tool_id": "CMP-02",  "tool_name": "CMP Polisher 2",           "process_step": "CMP Planarization",
     "max_capacity_wph": 200.0, "mttr_hours": 2.5,
     "utilization_pct": 55.0, "wip_lots": 13, "downtime_hrs": 0.0, "throughput_wph": 110.0},
    {"tool_id": "IMP-05",  "tool_name": "Ion Implanter 5",          "process_step": "Well Implant",
     "max_capacity_wph": 100.0, "mttr_hours": 5.0,
     "utilization_pct": 70.0, "wip_lots": 20, "downtime_hrs": 2.0, "throughput_wph": 70.0},
    {"tool_id": "PVD-06",  "tool_name": "PVD Sputter Tool 6",       "process_step": "Metal Fill (PVD)",
     "max_capacity_wph": 160.0, "mttr_hours": 3.0,
     "utilization_pct": 48.0, "wip_lots":  9, "downtime_hrs": 0.0, "throughput_wph": 76.8},
    {"tool_id": "TEST-01", "tool_name": "Electrical Test Station 1","process_step": "Final Inspection & Test",
     "max_capacity_wph": 250.0, "mttr_hours": 1.5,
     "utilization_pct": 30.0, "wip_lots":  5, "downtime_hrs": 0.0, "throughput_wph": 75.0},
]


async def _get_tool_data() -> list[dict]:
    """Fetch live data; fall back to demo constants if DB unavailable."""
    rows = await db.fetch_rows(
        """
        SELECT ft.tool_id, ft.tool_name, ft.process_step,
               ft.max_capacity_wph, ft.mttr_hours,
               tu.utilization_pct, tu.wip_lots, tu.downtime_hrs, tu.throughput_wph
        FROM fab_tools ft
        LEFT JOIN LATERAL (
            SELECT utilization_pct, wip_lots, downtime_hrs, throughput_wph
            FROM tool_utilization
            WHERE tool_id = ft.tool_id
            ORDER BY snapshot_time DESC
            LIMIT 1
        ) tu ON TRUE
        WHERE ft.is_active = TRUE
        ORDER BY ft.tool_id
        """
    )
    if rows:
        return rows
    return _DEMO_TOOLS


def compute_wip_pressure(wip_lots: int, max_capacity_wph: float) -> float:
    """
    WIP Pressure = actual_queue / theoretical_capacity_in_one_shift.
    Clamped to [0, 1] — values > 1 would mean impossible queue depth.
    """
    shift_capacity_lots = (max_capacity_wph * SHIFT_HOURS) / AVG_LOT_CYCLE_TIME_HRS
    if shift_capacity_lots <= 0:
        return 1.0
    raw = wip_lots / shift_capacity_lots
    return float(np.clip(raw, 0.0, 1.0))


def compute_capacity_pressure(utilization_pct: float) -> float:
    """
    Capacity Pressure is zero up to 85 % and rises linearly to 1.0 at 100 %.
    Represents the urgency once the tool is approaching saturation.
    """
    excess = utilization_pct - BOTTLENECK_UTIL_THRESHOLD
    if excess <= 0:
        return 0.0
    return float(np.clip(excess / (100.0 - BOTTLENECK_UTIL_THRESHOLD), 0.0, 1.0))


def compute_bottleneck_score(
    utilization_pct: float,
    wip_pressure: float,
    capacity_pressure: float,
) -> float:
    """
    Composite Bottleneck Score (0–1).
    Weighted: 50 % utilisation, 30 % WIP pressure, 20 % capacity pressure.
    """
    score = (
        0.50 * (utilization_pct / 100.0)
        + 0.30 * wip_pressure
        + 0.20 * capacity_pressure
    )
    return round(float(np.clip(score, 0.0, 1.0)), 4)


def compute_outage_backlog_and_recovery(
    *,
    outage_hours: float,
    current_wip_lots: int,
    utilization_pct: float,
    max_capacity_wph: float,
    avg_cycle_time_hrs: float = AVG_LOT_CYCLE_TIME_HRS,
) -> dict:
    """
    Simulate an outage and calculate:
      - Additional backlog accrued during downtime
      - Total backlog (existing + outage)
      - Recovery time after tool returns to service
      - Whether recovery is achievable within a 24-hour window

    Arrival rate = current throughput rate expressed as lots/hr
    Effective processing rate = max_capacity_wph / avg_cycle_time_hrs (lots/hr)

    Division-by-zero and impossible-recovery conditions are handled explicitly.
    """
    # Arrival rate: how many lots arrive per hour at this tool
    # Approximated from utilization: lots in queue / (utilization * shift)
    arrival_rate_lots_per_hr: float = (utilization_pct / 100.0) * (
        max_capacity_wph / avg_cycle_time_hrs
    )

    # Lots accumulating during outage (tool processes zero)
    outage_backlog = math.ceil(arrival_rate_lots_per_hr * outage_hours)

    # Total backlog to clear after tool comes back online
    total_backlog = current_wip_lots + outage_backlog

    # Tool's maximum processing rate in lots/hr
    max_rate_lots_per_hr = max_capacity_wph / avg_cycle_time_hrs

    # Net clearance rate = how much faster the tool processes than lots arrive
    net_clearance_rate = max_rate_lots_per_hr - arrival_rate_lots_per_hr

    if net_clearance_rate <= 0:
        # Tool cannot clear backlog; demand equals or exceeds capacity
        return {
            "outage_backlog_lots": outage_backlog,
            "total_backlog_lots": total_backlog,
            "recovery_hours": None,
            "is_recoverable": False,
            "backlog_wafers": total_backlog * 25,  # assume 25 wfr/lot
            "note": "Recovery impossible: arrival rate ≥ max processing rate.",
        }

    recovery_hours = round(total_backlog / net_clearance_rate, 2)
    return {
        "outage_backlog_lots": outage_backlog,
        "total_backlog_lots": total_backlog,
        "recovery_hours": recovery_hours,
        "is_recoverable": recovery_hours <= 24.0,
        "backlog_wafers": total_backlog * 25,
        "note": None,
    }


async def get_all_tool_scores() -> list[BottleneckResult]:
    """Compute bottleneck scores for all active tools."""
    tools = await _get_tool_data()
    results: list[BottleneckResult] = []
    for t in tools:
        util = float(t.get("utilization_pct") or 0)
        wip  = int(t.get("wip_lots") or 0)
        cap  = float(t.get("max_capacity_wph") or 1)

        wip_p = compute_wip_pressure(wip, cap)
        cap_p = compute_capacity_pressure(util)
        score = compute_bottleneck_score(util, wip_p, cap_p)

        results.append(BottleneckResult(
            tool_id=t["tool_id"],
            tool_name=t["tool_name"],
            process_step=t["process_step"],
            utilization_pct=util,
            wip_lots=wip,
            downtime_hrs=float(t.get("downtime_hrs") or 0),
            wip_pressure=round(wip_p, 4),
            capacity_pressure=round(cap_p, 4),
            bottleneck_score=score,
            is_critical=score >= CRITICAL_BOTTLENECK_SCORE,
        ))

    # Sort: critical first, then by score descending
    results.sort(key=lambda r: r.bottleneck_score, reverse=True)
    return results


async def simulate_tool_outage(
    tool_id: str,
    outage_hours: float,
) -> OutageSimulationResult:
    """
    Simulate an outage on the specified tool and compute backlog + recovery.
    Also identifies downstream steps that will be delayed.
    """
    tools = await _get_tool_data()
    tool = next((t for t in tools if t["tool_id"] == tool_id), None)
    if tool is None:
        raise ValueError(f"Tool '{tool_id}' not found.")

    outage_result = compute_outage_backlog_and_recovery(
        outage_hours=outage_hours,
        current_wip_lots=int(tool.get("wip_lots") or 0),
        utilization_pct=float(tool.get("utilization_pct") or 0),
        max_capacity_wph=float(tool.get("max_capacity_wph") or 1),
    )

    # Downstream impact: all steps after this one in process order
    affected_step_order = DOWNSTREAM_STEP_ORDER.get(tool["process_step"])
    downstream: list[DownstreamImpactItem] = []
    if affected_step_order is not None and outage_result["recovery_hours"] is not None:
        for step, order in sorted(DOWNSTREAM_STEP_ORDER.items(), key=lambda x: x[1]):
            if order > affected_step_order:
                delay_factor = 1.0 + (order - affected_step_order) * 0.15
                delay_hrs = round(outage_result["recovery_hours"] * delay_factor, 2)
                severity = "LOW"
                if delay_hrs > 8:
                    severity = "MEDIUM"
                if delay_hrs > 16:
                    severity = "HIGH"
                if delay_hrs > 24:
                    severity = "CRITICAL"
                downstream.append(DownstreamImpactItem(
                    affected_step=step,
                    delay_hours=delay_hrs,
                    affected_lots=outage_result["total_backlog_lots"],
                    impact_severity=severity,
                ))

    return OutageSimulationResult(
        tool_id=tool_id,
        tool_name=tool["tool_name"],
        process_step=tool["process_step"],
        outage_hours=outage_hours,
        outage_backlog_lots=outage_result["outage_backlog_lots"],
        total_backlog_lots=outage_result["total_backlog_lots"],
        backlog_wafers=outage_result["backlog_wafers"],
        recovery_hours=outage_result["recovery_hours"],
        is_recoverable=outage_result["is_recoverable"],
        downstream_impact=downstream,
        simulation_note=outage_result["note"],
    )
