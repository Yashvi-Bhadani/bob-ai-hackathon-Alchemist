"""
Database connection pool management using asyncpg.
Reads DATABASE_URL from environment; falls back to an in-memory demo mode
so the app can still serve deterministic results without a live database.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

try:
    import asyncpg
    _ASYNCPG_AVAILABLE = True
except ImportError:
    _ASYNCPG_AVAILABLE = False

logger = logging.getLogger(__name__)

_pool: Optional[object] = None  # asyncpg.Pool when live


async def init_db() -> None:
    """Create the connection pool if DATABASE_URL is configured."""
    global _pool
    url = os.getenv("DATABASE_URL")
    if not url:
        logger.warning("DATABASE_URL not set — running in demo/offline mode.")
        return
    if not _ASYNCPG_AVAILABLE:
        logger.warning("asyncpg not installed — running in demo/offline mode.")
        return
    try:
        _pool = await asyncpg.create_pool(url, min_size=2, max_size=10)
        logger.info("asyncpg pool created.")
    except Exception as exc:
        logger.error("Failed to connect to database: %s — demo mode active.", exc)
        _pool = None


def get_pool():
    """Return the live pool, or None if in demo/offline mode."""
    return _pool


async def fetch_rows(query: str, *args) -> list[dict]:
    """Execute a SELECT and return rows as dicts.  Returns [] in demo mode."""
    if _pool is None:
        return []
    async with _pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]


async def fetch_one(query: str, *args) -> Optional[dict]:
    """Execute a SELECT and return first row as dict, or None."""
    if _pool is None:
        return None
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def execute(query: str, *args) -> str:
    """Execute an INSERT/UPDATE/DELETE.  No-op in demo mode."""
    if _pool is None:
        return "DEMO_NOOP"
    async with _pool.acquire() as conn:
        return await conn.execute(query, *args)
