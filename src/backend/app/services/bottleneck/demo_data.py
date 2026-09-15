"""
app/services/bottleneck/demo_data.py
=====================================
In-memory synthetic demo dataset.

⚠ ALL DATA IS FABRICATED FOR DEMO PURPOSES ONLY.
  No real fab, tool, or product data is represented.

Used when DATABASE_URL is not configured (demo / offline mode).
Member 3 / supply module can import DEMO_TOOLS for alternate-tool checks.

LITH-07 is deliberately the obvious CRITICAL bottleneck:
  - utilization ≈ 97 %
  - WIP pressure = 240/100 = 2.4  (raw)
  - high capacity pressure
  - recent downtime
  - 5 snapshots showing a clearly rising WIP trend
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

_NOW = datetime.now(timezone.utc)
_H = lambda h: _NOW - timedelta(hours=h)  # noqa: E731


# ---------------------------------------------------------------------------
# Processes (mirrors fab_processes table)
# ---------------------------------------------------------------------------
DEMO_PROCESSES: list[dict] = [
    {"process_id": 1, "process_name": "Lithography",         "process_sequence": 1, "next_process_id": 2},
    {"process_id": 2, "process_name": "Etch",                "process_sequence": 2, "next_process_id": 3},
    {"process_id": 3, "process_name": "CVD",                 "process_sequence": 3, "next_process_id": 4},
    {"process_id": 4, "process_name": "Inspection",          "process_sequence": 4, "next_process_id": 5},
    {"process_id": 5, "process_name": "Packaging",           "process_sequence": 5, "next_process_id": None},
]

# ---------------------------------------------------------------------------
# Tools (mirrors fab_tools table)
# ---------------------------------------------------------------------------
DEMO_TOOLS: list[dict] = [
    # ── Lithography ──────────────────────────────────────────────────────────
    {
        "tool_id":               "LITH-07",
        "tool_name":             "EUV Scanner Unit 7",
        "process_id":            1,
        "process_name":          "Lithography",
        "tool_type":             "EUV Scanner",
        "available_hours":       24.0,
        "capacity_units_per_hour": 50.0,       # max 50 lots/hr
        "compatible_products":   ["PROD-7NM-CPU", "PROD-7NM-GPU", "PROD-7NM-SYS"],
        "status":                "ACTIVE",
        # snapshot-derived fields used by score engine
        "_busy_hours":           23.3,         # 23.3/24 = 97.1 % utilization
        "_wip_units":            240,           # current WIP
        "_normal_wip":           100,           # normal WIP baseline
        "_downtime_hours":       1.2,           # recent unplanned downtime
        "_total_hours":          24.0,
    },
    {
        "tool_id":               "LITH-08",
        "tool_name":             "EUV Scanner Unit 8",
        "process_id":            1,
        "process_name":          "Lithography",
        "tool_type":             "EUV Scanner",
        "available_hours":       24.0,
        "capacity_units_per_hour": 50.0,
        "compatible_products":   ["PROD-7NM-CPU", "PROD-7NM-GPU"],  # shares products with LITH-07
        "status":                "ACTIVE",
        "_busy_hours":           14.4,          # 60 % utilization — has spare capacity
        "_wip_units":            52,
        "_normal_wip":           100,
        "_downtime_hours":       0.0,
        "_total_hours":          24.0,
    },
    # ── Etch ─────────────────────────────────────────────────────────────────
    {
        "tool_id":               "ETCH-03",
        "tool_name":             "Plasma Etch Chamber 3",
        "process_id":            2,
        "process_name":          "Etch",
        "tool_type":             "Plasma Etcher",
        "available_hours":       24.0,
        "capacity_units_per_hour": 75.0,
        "compatible_products":   ["PROD-7NM-CPU", "PROD-7NM-GPU", "PROD-7NM-SYS"],
        "status":                "ACTIVE",
        "_busy_hours":           14.9,
        "_wip_units":            110,
        "_normal_wip":           120,
        "_downtime_hours":       0.0,
        "_total_hours":          24.0,
    },
    {
        "tool_id":               "ETCH-04",
        "tool_name":             "Plasma Etch Chamber 4",
        "process_id":            2,
        "process_name":          "Etch",
        "tool_type":             "Plasma Etcher",
        "available_hours":       24.0,
        "capacity_units_per_hour": 75.0,
        "compatible_products":   ["PROD-7NM-CPU", "PROD-7NM-SYS"],
        "status":                "ACTIVE",
        "_busy_hours":           13.2,
        "_wip_units":            95,
        "_normal_wip":           120,
        "_downtime_hours":       1.0,
        "_total_hours":          24.0,
    },
    # ── CVD ──────────────────────────────────────────────────────────────────
    {
        "tool_id":               "CVD-11",
        "tool_name":             "LPCVD Furnace 11",
        "process_id":            3,
        "process_name":          "CVD",
        "tool_type":             "LPCVD Furnace",
        "available_hours":       24.0,
        "capacity_units_per_hour": 60.0,
        "compatible_products":   ["PROD-7NM-CPU", "PROD-7NM-GPU", "PROD-7NM-SYS"],
        "status":                "ACTIVE",
        "_busy_hours":           10.8,
        "_wip_units":            70,
        "_normal_wip":           100,
        "_downtime_hours":       0.0,
        "_total_hours":          24.0,
    },
    # ── Inspection ───────────────────────────────────────────────────────────
    {
        "tool_id":               "INSP-01",
        "tool_name":             "Optical Inspection Unit 1",
        "process_id":            4,
        "process_name":          "Inspection",
        "tool_type":             "Optical Inspector",
        "available_hours":       24.0,
        "capacity_units_per_hour": 120.0,
        "compatible_products":   ["PROD-7NM-CPU", "PROD-7NM-GPU", "PROD-7NM-SYS"],
        "status":                "ACTIVE",
        "_busy_hours":           7.2,
        "_wip_units":            40,
        "_normal_wip":           80,
        "_downtime_hours":       0.0,
        "_total_hours":          24.0,
    },
    # ── Packaging ────────────────────────────────────────────────────────────
    {
        "tool_id":               "PKG-02",
        "tool_name":             "Die Attach & Wire Bond Station 2",
        "process_id":            5,
        "process_name":          "Packaging",
        "tool_type":             "Packaging Station",
        "available_hours":       24.0,
        "capacity_units_per_hour": 200.0,
        "compatible_products":   ["PROD-7NM-CPU", "PROD-7NM-GPU"],
        "status":                "ACTIVE",
        "_busy_hours":           6.0,
        "_wip_units":            30,
        "_normal_wip":           60,
        "_downtime_hours":       0.0,
        "_total_hours":          24.0,
    },
]

# ---------------------------------------------------------------------------
# Historical snapshots (mirrors fab_snapshots table)
# LITH-07 shows a clear rising WIP trend (60 → 80 → 120 → 180 → 240).
# LITH-08 is stable (~50 lots).
# ---------------------------------------------------------------------------
DEMO_SNAPSHOTS: dict[str, list[dict]] = {
    "LITH-07": [
        {"snapshot_time": _H(96), "wip_units": 60,  "busy_hours": 14.0, "available_hours": 24.0, "capacity_units": 1200.0, "downtime_hours": 0.0},
        {"snapshot_time": _H(72), "wip_units": 80,  "busy_hours": 17.0, "available_hours": 24.0, "capacity_units": 1200.0, "downtime_hours": 0.3},
        {"snapshot_time": _H(48), "wip_units": 120, "busy_hours": 20.5, "available_hours": 24.0, "capacity_units": 1200.0, "downtime_hours": 0.5},
        {"snapshot_time": _H(24), "wip_units": 180, "busy_hours": 22.0, "available_hours": 24.0, "capacity_units": 1200.0, "downtime_hours": 0.8},
        {"snapshot_time": _H(0),  "wip_units": 240, "busy_hours": 23.3, "available_hours": 24.0, "capacity_units": 1200.0, "downtime_hours": 1.2},
    ],
    "LITH-08": [
        {"snapshot_time": _H(96), "wip_units": 48,  "busy_hours": 12.0, "available_hours": 24.0, "capacity_units": 1200.0, "downtime_hours": 0.0},
        {"snapshot_time": _H(72), "wip_units": 55,  "busy_hours": 14.0, "available_hours": 24.0, "capacity_units": 1200.0, "downtime_hours": 0.0},
        {"snapshot_time": _H(48), "wip_units": 50,  "busy_hours": 13.5, "available_hours": 24.0, "capacity_units": 1200.0, "downtime_hours": 0.0},
        {"snapshot_time": _H(24), "wip_units": 53,  "busy_hours": 14.2, "available_hours": 24.0, "capacity_units": 1200.0, "downtime_hours": 0.0},
        {"snapshot_time": _H(0),  "wip_units": 52,  "busy_hours": 14.4, "available_hours": 24.0, "capacity_units": 1200.0, "downtime_hours": 0.0},
    ],
    "ETCH-03": [
        {"snapshot_time": _H(48), "wip_units": 105, "busy_hours": 14.0, "available_hours": 24.0, "capacity_units": 1800.0, "downtime_hours": 0.0},
        {"snapshot_time": _H(24), "wip_units": 108, "busy_hours": 14.5, "available_hours": 24.0, "capacity_units": 1800.0, "downtime_hours": 0.0},
        {"snapshot_time": _H(0),  "wip_units": 110, "busy_hours": 14.9, "available_hours": 24.0, "capacity_units": 1800.0, "downtime_hours": 0.0},
    ],
    "ETCH-04": [
        {"snapshot_time": _H(48), "wip_units": 98,  "busy_hours": 13.0, "available_hours": 24.0, "capacity_units": 1800.0, "downtime_hours": 0.5},
        {"snapshot_time": _H(24), "wip_units": 96,  "busy_hours": 13.1, "available_hours": 24.0, "capacity_units": 1800.0, "downtime_hours": 0.8},
        {"snapshot_time": _H(0),  "wip_units": 95,  "busy_hours": 13.2, "available_hours": 24.0, "capacity_units": 1800.0, "downtime_hours": 1.0},
    ],
    "CVD-11":  [{"snapshot_time": _H(0), "wip_units": 70, "busy_hours": 10.8, "available_hours": 24.0, "capacity_units": 1440.0, "downtime_hours": 0.0}],
    "INSP-01": [{"snapshot_time": _H(0), "wip_units": 40, "busy_hours":  7.2, "available_hours": 24.0, "capacity_units": 2880.0, "downtime_hours": 0.0}],
    "PKG-02":  [{"snapshot_time": _H(0), "wip_units": 30, "busy_hours":  6.0, "available_hours": 24.0, "capacity_units": 4800.0, "downtime_hours": 0.0}],
}

# ---------------------------------------------------------------------------
# WIP lots at each tool (mirrors wip_lots table)
# ---------------------------------------------------------------------------
DEMO_WIP_LOTS: list[dict] = [
    # LITH-07 — 8 queued lots (demonstrating deep queue)
    {"lot_id": "LOT-L7-001", "product_id": "PROD-7NM-CPU", "process_id": 1, "tool_id": "LITH-07", "quantity": 25, "arrival_time": _H(6),  "priority": 1, "status": "RUNNING"},
    {"lot_id": "LOT-L7-002", "product_id": "PROD-7NM-GPU", "process_id": 1, "tool_id": "LITH-07", "quantity": 25, "arrival_time": _H(5),  "priority": 2, "status": "QUEUED"},
    {"lot_id": "LOT-L7-003", "product_id": "PROD-7NM-CPU", "process_id": 1, "tool_id": "LITH-07", "quantity": 25, "arrival_time": _H(4),  "priority": 1, "status": "QUEUED"},
    {"lot_id": "LOT-L7-004", "product_id": "PROD-7NM-SYS", "process_id": 1, "tool_id": "LITH-07", "quantity": 25, "arrival_time": _H(4),  "priority": 2, "status": "QUEUED"},
    {"lot_id": "LOT-L7-005", "product_id": "PROD-7NM-CPU", "process_id": 1, "tool_id": "LITH-07", "quantity": 25, "arrival_time": _H(3),  "priority": 2, "status": "QUEUED"},
    {"lot_id": "LOT-L7-006", "product_id": "PROD-7NM-GPU", "process_id": 1, "tool_id": "LITH-07", "quantity": 25, "arrival_time": _H(3),  "priority": 3, "status": "QUEUED"},
    {"lot_id": "LOT-L7-007", "product_id": "PROD-7NM-CPU", "process_id": 1, "tool_id": "LITH-07", "quantity": 25, "arrival_time": _H(2),  "priority": 1, "status": "QUEUED"},
    {"lot_id": "LOT-L7-008", "product_id": "PROD-7NM-SYS", "process_id": 1, "tool_id": "LITH-07", "quantity": 25, "arrival_time": _H(1),  "priority": 2, "status": "QUEUED"},
    # LITH-08 — 2 lots (light load, available capacity)
    {"lot_id": "LOT-L8-001", "product_id": "PROD-7NM-CPU", "process_id": 1, "tool_id": "LITH-08", "quantity": 25, "arrival_time": _H(3),  "priority": 2, "status": "RUNNING"},
    {"lot_id": "LOT-L8-002", "product_id": "PROD-7NM-GPU", "process_id": 1, "tool_id": "LITH-08", "quantity": 25, "arrival_time": _H(2),  "priority": 2, "status": "QUEUED"},
    # Etch tools
    {"lot_id": "LOT-E3-001", "product_id": "PROD-7NM-CPU", "process_id": 2, "tool_id": "ETCH-03", "quantity": 25, "arrival_time": _H(2),  "priority": 2, "status": "RUNNING"},
    {"lot_id": "LOT-E4-001", "product_id": "PROD-7NM-SYS", "process_id": 2, "tool_id": "ETCH-04", "quantity": 25, "arrival_time": _H(2),  "priority": 2, "status": "RUNNING"},
]
