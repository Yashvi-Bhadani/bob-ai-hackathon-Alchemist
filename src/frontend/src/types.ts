// ─── API Response Types ────────────────────────────────────────────────────────
// Mirror Python Pydantic models exactly.

export interface BottleneckResult {
  tool_id: string
  tool_name: string
  process_step: string
  utilization_pct: number
  wip_lots: number
  downtime_hrs: number
  wip_pressure: number
  capacity_pressure: number
  bottleneck_score: number
  is_critical: boolean
}

export interface BottleneckListResponse {
  tools: BottleneckResult[]
  critical_count: number
  most_critical_tool_id: string | null
}

export interface DownstreamImpactItem {
  affected_step: string
  delay_hours: number
  affected_lots: number
  impact_severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
}

export interface OutageSimulationResult {
  tool_id: string
  tool_name: string
  process_step: string
  outage_hours: number
  outage_backlog_lots: number
  total_backlog_lots: number
  backlog_wafers: number
  recovery_hours: number | null
  is_recoverable: boolean
  downstream_impact: DownstreamImpactItem[]
  simulation_note: string | null
}

export interface HHIResult {
  material_id: string
  material_name: string
  critical_flag: boolean
  hhi_value: number
  concentration_level: 'LOW' | 'MODERATE' | 'HIGH' | 'MONOPOLY'
  supplier_count: number
  suppliers: Array<{ supplier_id: string; supplier_name: string; share_pct: number; country: string }>
}

export interface SPOFResult {
  material_id: string
  material_name: string
  critical_flag: boolean
  dominant_supplier_id: string
  dominant_supplier_name: string
  dominant_share_pct: number
  qualified_supplier_count: number
  spof_reason: string
}

export interface InventoryCoverageResult {
  material_id: string
  material_name: string
  critical_flag: boolean
  quantity_on_hand: number
  daily_consumption: number
  coverage_days: number
  reorder_point: number
  safety_stock: number
  below_reorder_point: boolean
  below_safety_stock: boolean
  risk_tier: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
}

export interface GeopoliticalRiskItem {
  risk_id: string
  affected_region: string
  affected_material_id: string | null
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  risk_reason: string
  source: string
  source_date: string
}

export interface MaterialSupplyRisk {
  material_id: string
  material_name: string
  hhi_score: number
  hhi_value: number | null
  inventory_risk_tier: string
  inventory_coverage_days: number | null
  has_spof: boolean
  geopolitical_risk_score: number
  combined_supply_risk: number
  risk_tier: 'GREEN' | 'AMBER' | 'RED' | 'CRITICAL'
}

export interface MitigationRecommendation {
  priority: number
  category: 'TOOL' | 'SCHEDULE' | 'INVENTORY' | 'SUPPLIER' | 'OTHER'
  recommendation: string
  expected_impact: string | null
  feasibility: 'HIGH' | 'MEDIUM' | 'LOW'
}

export interface CombinedRiskResult {
  tool_id: string
  tool_name: string
  process_step: string
  manufacturing_risk_score: number
  supply_chain_risk_score: number
  combined_risk_score: number
  risk_tier: 'GREEN' | 'AMBER' | 'RED' | 'CRITICAL'
  risk_tier_label: string
  confidence_pct: number
  primary_material_id: string | null
  outage_simulation: OutageSimulationResult | null
  supply_risk: MaterialSupplyRisk | null
  recommendations: MitigationRecommendation[]
}

export interface NarrationResponse {
  context_type: string
  narration_text: string
  is_fallback: boolean
  model_used: string
  prompt_hash: string
}
