"""
Pydantic response models for the Fab Risk Advisor API.
All fields use snake_case per Python convention.
"""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


# ── Bottleneck (Member 1) ──────────────────────────────────────────────────────

class HistoryPoint(BaseModel):
    """Single snapshot data point in the bottleneck history trend."""
    snapshot_time: str
    wip_units: Optional[int] = None
    utilization: Optional[float] = None


class BottleneckAssessment(BaseModel):
    """
    Full bottleneck assessment for a single tool.
    Returned by GET /api/v1/bottleneck/bottlenecks/{tool_id}.
    Member 3 should use this as the primary integration payload.
    """
    tool_id: str
    tool_name: str
    process_id: int
    process_name: str
    tool_type: str
    status: str
    compatible_products: List[str] = []

    # Score inputs
    utilization: float = Field(..., ge=0, le=1, description="Ratio 0–1")
    utilization_pct: float = Field(..., ge=0, le=100)
    wip_units: int = Field(..., ge=0)
    normal_wip: float = Field(..., ge=0)
    wip_pressure_raw: float = Field(..., ge=0, description="Raw ratio; can exceed 1")
    wip_pressure_normalized: float = Field(..., ge=0, le=1)
    capacity_pressure: float = Field(..., ge=0, le=1)
    downtime_hours: float = Field(..., ge=0)
    downtime_pct: float = Field(..., ge=0, le=1)

    # Score outputs
    bottleneck_score: float = Field(..., ge=0, le=100, description="Composite score 0–100")
    severity: str = Field(..., description="LOW | MEDIUM | HIGH | CRITICAL")
    is_bottleneck: bool

    # Confidence
    confidence: float = Field(..., ge=0, le=1)
    low_confidence: bool
    snapshot_count: int
    wip_trend: str = Field(..., description="RISING | STABLE | FALLING | UNKNOWN")
    wip_cov: Optional[float] = None

    # Little's Law reference only
    cycle_time_estimate_hrs: Optional[float] = None
    cycle_time_note: str = ""

    # History
    history: List[HistoryPoint] = []


class BottleneckListResponse(BaseModel):
    bottlenecks: List[dict]       # dict form (BottleneckAssessment without history)
    count: int
    critical_count: int
    most_critical_tool_id: Optional[str] = None


class BacklogRecoveryResult(BaseModel):
    """Structured result from the backlog/recovery calculation (Member 3 integration)."""
    backlog_added: float
    net_clearance_rate: float
    recovery_time_hours: Optional[float] = None
    recoverable: bool


# ── Downstream Impact (Member 3 owned, kept here for shared use) ───────────────

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

# Legacy alias kept so Member 2/3 code that references BottleneckResult still imports
BottleneckResult = BottleneckAssessment


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
