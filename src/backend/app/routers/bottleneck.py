"""
app/routers/bottleneck.py
==========================
Mounts the Member-1 bottleneck API sub-routers under the prefix that
main.py already registers at /api/v1/bottleneck.

Final URL layout (registered in main.py as prefix="/api/v1/bottleneck"):
  GET /api/v1/bottleneck/tools
  GET /api/v1/bottleneck/processes
  GET /api/v1/bottleneck/wip
  GET /api/v1/bottleneck/bottlenecks
  GET /api/v1/bottleneck/bottlenecks/{tool_id}

Member 3 integration note:
  Import the calculate_backlog_recovery function directly from:
      app.services.bottleneck.backlog_recovery
  Import the full assessment dict via the HTTP endpoint above, or call:
      app.api.bottlenecks._full_assessment(tool, snapshots)  (internal use only)

DO NOT modify main.py — this router is already registered there.
"""

from fastapi import APIRouter

from app.api.tools       import router as tools_router
from app.api.wip         import router as wip_router
from app.api.bottlenecks import router as bottlenecks_router

router = APIRouter()
router.include_router(tools_router)
router.include_router(wip_router)
router.include_router(bottlenecks_router)
