"""
Pydantic response models for the Fab Risk Advisor API.
All fields use snake_case per Python convention.
"""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


# ── Bottleneck ─────────────────────────────────────────────────────────────────

class BottleneckResult(BaseModel):
    tool_id: str
    tool_name: str
    process_step: str
    utilization_pct: float = Field(..., ge=0, le=100)
    wip_lots: int = Field(..., ge=0)
    downtime_hrs: float = Field(..., ge=0)
    wip_pressure: float = Field(..., ge=0, le=1)
    capacity_pressure: float = Field(..., ge=0, le=1)
    bottleneck_score: float = Field(..., ge=0, le=1)
    is_critical: bool


class BottleneckListResponse(BaseModel):
    tools: List[BottleneckResult]
    critical_count: int
    most_critical_tool_id: Optional[str] = None


# ── Outage Simulation ──────────────────────────────────────────────────────────

class DownstreamImpactItem(BaseModel):
    affected_step: str
    delay_hours: float
    affected_lots: int
    impact_severity: str  # LOW | MEDIUM | HIGH | CRITICAL


class OutageSimulationResult(BaseModel):
    tool_id: str
    tool_name: str
    process_step: str
    outage_hours: float
    outage_backlog_lots: int
    total_backlog_lots: int
    backlog_wafers: int
    recovery_hours: Optional[float] = None
    is_recoverable: bool
    downstream_impact: List[DownstreamImpactItem] = []
    simulation_note: Optional[str] = None


# ── Supply Chain ───────────────────────────────────────────────────────────────

class HHIResult(BaseModel):
    material_id: str
    material_name: str
    critical_flag: bool
    hhi_value: float
    concentration_level: str  # LOW | MODERATE | HIGH | MONOPOLY
    supplier_count: int
    suppliers: List[dict] = []


class SPOFResult(BaseModel):
    material_id: str
    material_name: str
    critical_flag: bool
    dominant_supplier_id: str
    dominant_supplier_name: str
    dominant_share_pct: float
    qualified_supplier_count: int
    spof_reason: str


class InventoryCoverageResult(BaseModel):
    material_id: str
    material_name: str
    critical_flag: bool
    quantity_on_hand: float
    daily_consumption: float
    coverage_days: float
    reorder_point: float
    safety_stock: float
    below_reorder_point: bool
    below_safety_stock: bool
    risk_tier: str  # CRITICAL | HIGH | MEDIUM | LOW


class GeopoliticalRiskItem(BaseModel):
    risk_id: str
    affected_region: str
    affected_material_id: Optional[str] = None
    risk_level: str  # LOW | MEDIUM | HIGH | CRITICAL
    risk_reason: str
    source: str
    source_date: str


class MaterialSupplyRisk(BaseModel):
    material_id: str
    material_name: str
    hhi_score: float
    hhi_value: Optional[float] = None
    inventory_risk_tier: str
    inventory_coverage_days: Optional[float] = None
    has_spof: bool
    geopolitical_risk_score: float
    combined_supply_risk: float
    risk_tier: str  # GREEN | AMBER | RED | CRITICAL


# ── Impact & Combined Risk ─────────────────────────────────────────────────────

class MitigationRecommendation(BaseModel):
    priority: int
    category: str  # TOOL | SCHEDULE | INVENTORY | SUPPLIER | OTHER
    recommendation: str
    expected_impact: Optional[str] = None
    feasibility: str  # HIGH | MEDIUM | LOW


class CombinedRiskResult(BaseModel):
    tool_id: str
    tool_name: str
    process_step: str
    manufacturing_risk_score: float
    supply_chain_risk_score: float
    combined_risk_score: float
    risk_tier: str
    risk_tier_label: str
    confidence_pct: int
    primary_material_id: Optional[str] = None
    outage_simulation: Optional[OutageSimulationResult] = None
    supply_risk: Optional[MaterialSupplyRisk] = None
    recommendations: List[MitigationRecommendation] = []


# ── Bob Narration ──────────────────────────────────────────────────────────────

class NarrationRequest(BaseModel):
    context_type: str  # BOTTLENECK | OUTAGE | SUPPLY_RISK | COMBINED
    context_data: dict[str, Any]


class NarrationResponse(BaseModel):
    context_type: str
    narration_text: str
    is_fallback: bool
    model_used: str
    prompt_hash: str
