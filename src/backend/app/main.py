"""
Fab Bottleneck & Supply Chain Risk Advisor — FastAPI Application
================================================================
Entry point for the backend API.  Member 3 owns this file for integration.

Architecture:
  /api/v1/bottleneck  — bottleneck detection & outage simulation  (Member 1)
  /api/v1/supply      — supply-chain risk, HHI, SPOF, inventory  (Member 2)
  /api/v1/impact      — combined risk, downstream, mitigation     (Member 3)
  /api/v1/narration   — IBM Bob AI narration layer                (Member 3)
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import bottleneck, supply, impact, narration
from app.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database connection pool on startup."""
    await init_db()
    logger.info("Database pool initialised.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Fab Bottleneck & Supply Chain Risk Advisor",
    description=(
        "Intelligence and decision-support system for semiconductor fab "
        "bottleneck detection, outage simulation, and supply-chain risk assessment. "
        "IBM Bob provides natural-language explanation of all deterministic results."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────────────────────────
# This is a public read-only demo API — no cookies or auth headers are used.
# allow_origins=["*"] with allow_credentials=False is the correct, simplest
# configuration and avoids every browser CORS edge case for public APIs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────────────
app.include_router(bottleneck.router, prefix="/api/v1/bottleneck", tags=["Bottleneck"])
app.include_router(supply.router,     prefix="/api/v1/supply",     tags=["Supply Risk"])
app.include_router(impact.router,     prefix="/api/v1/impact",     tags=["Impact & Combined Risk"])
app.include_router(narration.router,  prefix="/api/v1/narration",  tags=["Bob Narration"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok", "service": "fab-risk-advisor"}
