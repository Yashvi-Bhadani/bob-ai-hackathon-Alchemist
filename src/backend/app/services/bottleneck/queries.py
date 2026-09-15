"""
app/services/bottleneck/queries.py
====================================
Database query helpers for the bottleneck module.
Falls back to DEMO_DATA when the database pool is unavailable.

These functions are called exclusively by the api/ routers.
They do NOT perform any calculations — that is handled by the
services/bottleneck/* modules.
"""

from __future__ import annotations

from app import database as db
from app.services.bottleneck.demo_data import (
    DEMO_TOOLS,
    DEMO_PROCESSES,
    DEMO_SNAPSHOTS,
    DEMO_WIP_LOTS,
)


async def get_tools() -> list[dict]:
    rows = await db.fetch_rows(
        """
        SELECT t.tool_id, t.tool_name, t.process_id, p.process_name,
               t.tool_type, t.available_hours, t.capacity_units_per_hour,
               t.compatible_products, t.status
        FROM fab_tools t
        JOIN fab_processes p ON p.process_id = t.process_id
        ORDER BY p.process_sequence, t.tool_id
        """
    )
    return rows if rows else DEMO_TOOLS


async def get_tool(tool_id: str) -> dict | None:
    row = await db.fetch_one(
        """
        SELECT t.tool_id, t.tool_name, t.process_id, p.process_name,
               t.tool_type, t.available_hours, t.capacity_units_per_hour,
               t.compatible_products, t.status
        FROM fab_tools t
        JOIN fab_processes p ON p.process_id = t.process_id
        WHERE t.tool_id = $1
        """,
        tool_id,
    )
    if row:
        return row
    return next((t for t in DEMO_TOOLS if t["tool_id"] == tool_id), None)


async def get_processes() -> list[dict]:
    rows = await db.fetch_rows(
        """
        SELECT process_id, process_name, process_sequence, next_process_id
        FROM fab_processes
        ORDER BY process_sequence
        """
    )
    return rows if rows else DEMO_PROCESSES


async def get_snapshots(tool_id: str, limit: int = 10) -> list[dict]:
    """Return up to `limit` most-recent snapshots for a tool (oldest first)."""
    rows = await db.fetch_rows(
        """
        SELECT snapshot_time, wip_units, busy_hours, available_hours,
               capacity_units, downtime_hours
        FROM fab_snapshots
        WHERE tool_id = $1
        ORDER BY snapshot_time ASC
        LIMIT $2
        """,
        tool_id,
        limit,
    )
    if rows:
        return rows
    snaps = DEMO_SNAPSHOTS.get(tool_id, [])
    # Already ordered oldest-first in demo data; return last `limit`
    return snaps[-limit:] if len(snaps) > limit else snaps


async def get_wip_lots(
    tool_id: str | None = None,
    process_id: int | None = None,
    product_id: str | None = None,
) -> list[dict]:
    """Flexible WIP lot query with optional filters."""
    if db.get_pool() is not None:
        clauses = ["status != 'COMPLETE'"]
        params: list = []
        idx = 1
        if tool_id:
            clauses.append(f"tool_id = ${idx}")
            params.append(tool_id)
            idx += 1
        if process_id:
            clauses.append(f"process_id = ${idx}")
            params.append(process_id)
            idx += 1
        if product_id:
            clauses.append(f"product_id = ${idx}")
            params.append(product_id)
            idx += 1
        where = " AND ".join(clauses)
        rows = await db.fetch_rows(
            f"SELECT * FROM wip_lots WHERE {where} ORDER BY priority, arrival_time",
            *params,
        )
        return rows

    # Demo fallback with same filtering logic
    lots = [l for l in DEMO_WIP_LOTS if l["status"] != "COMPLETE"]
    if tool_id:
        lots = [l for l in lots if l.get("tool_id") == tool_id]
    if process_id:
        lots = [l for l in lots if l.get("process_id") == process_id]
    if product_id:
        lots = [l for l in lots if l.get("product_id") == product_id]
    return lots
