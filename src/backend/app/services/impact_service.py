"""
Impact & Combined Risk Service
================================
Computes a full combined risk assessment that fuses:
  - Manufacturing bottleneck score (from bottleneck_service)
  - Supply chain risk score for the critical material (from supply_service)

Combined Risk Score = 0.55 * manufacturing_risk + 0.45 * supply_chain_risk

Generates prioritised mitigation recommendations based on all risk signals.
"""

from __future__ import annotations

from app.models import (
    CombinedRiskResult,
    MitigationRecommendation,
)
from app.services import bottleneck_service, supply_service

# Tool → primary critical material mapping (fallback for when DB unavailable)
_TOOL_PRIMARY_MATERIAL = {
    "LITH-07": "PHOTO-RES-EUV",
    "LITH-08": "PHOTO-RES-EUV",
    "ETCH-03": "CLEAN-SC1",
    "ETCH-04": "CLEAN-SC1",
    "CVD-11":  "CVD-TEOS",
    "CVD-12":  "CVD-TEOS",
    "CMP-02":  "CMP-SLUR-STI",
    "IMP-05":  "IMP-BF3",
    "PVD-06":  "SPUTT-TGT-W",
    "TEST-01": "CLEAN-SC1",
}

# Alternate qualified tools (same process step, can absorb load)
_ALTERNATE_TOOLS = {
    "LITH-07": [{"tool_id": "LITH-08", "tool_name": "EUV Scanner Unit 8", "available_capacity_pct": 28.8}],
    "LITH-08": [{"tool_id": "LITH-07", "tool_name": "EUV Scanner Unit 7", "available_capacity_pct": 5.5}],
    "ETCH-03": [{"tool_id": "ETCH-04", "tool_name": "Plasma Etch Chamber 4", "available_capacity_pct": 41.5}],
    "ETCH-04": [{"tool_id": "ETCH-03", "tool_name": "Plasma Etch Chamber 3", "available_capacity_pct": 38.0}],
    "CVD-11":  [{"tool_id": "CVD-12",  "tool_name": "LPCVD Furnace 12",     "available_capacity_pct": 57.0}],
    "CVD-12":  [{"tool_id": "CVD-11",  "tool_name": "LPCVD Furnace 11",     "available_capacity_pct": 55.0}],
}

_RISK_TIER_LABEL = {
    "GREEN":    "Low Risk",
    "AMBER":    "Elevated Risk",
    "RED":      "High Risk",
    "CRITICAL": "Critical Risk",
}


def _combined_risk_tier(score: float) -> str:
    if score >= 0.75:
        return "CRITICAL"
    if score >= 0.55:
        return "RED"
    if score >= 0.35:
        return "AMBER"
    return "GREEN"


def _build_recommendations(
    tool_id: str,
    tool_name: str,
    bottleneck_score: float,
    is_critical_bottleneck: bool,
    outage_hours: float | None,
    recovery_hours: float | None,
    supply_risk: "MaterialSupplyRisk | None",
    material_id: str | None,
    has_spof: bool,
    inventory_coverage_days: float | None,
    hhi_value: float | None,
) -> list[MitigationRecommendation]:
    """
    Generate ordered mitigation recommendations based on risk signals.
    Rules are deterministic business logic — no ML.
    """
    recs: list[MitigationRecommendation] = []
    priority = 1

    # ── Alternate tool recommendation ──────────────────────────────────────────
    alternates = _ALTERNATE_TOOLS.get(tool_id, [])
    if alternates and (is_critical_bottleneck or outage_hours):
        alt = alternates[0]
        if alt["available_capacity_pct"] > 5:
            recs.append(MitigationRecommendation(
                priority=priority,
                category="TOOL",
                recommendation=(
                    f"Re-route {min(30, int(alt['available_capacity_pct']))}% of "
                    f"lots from {tool_id} to alternate qualified tool "
                    f"{alt['tool_id']} ({alt['tool_name']}). "
                    f"Available spare capacity: {alt['available_capacity_pct']:.1f}%."
                ),
                expected_impact=(
                    f"Reduces {tool_id} queue depth by ~"
                    f"{min(30, int(alt['available_capacity_pct']))}%, "
                    f"lowering backlog pressure."
                ),
                feasibility="HIGH" if alt["available_capacity_pct"] > 20 else "MEDIUM",
            ))
            priority += 1

    # ── Scheduling recommendation ──────────────────────────────────────────────
    if is_critical_bottleneck or (recovery_hours and recovery_hours > 4):
        recs.append(MitigationRecommendation(
            priority=priority,
            category="SCHEDULE",
            recommendation=(
                f"Promote HOT-priority lots ahead of NORMAL lots in the {tool_id} queue "
                f"and defer low-priority lots to the next shift to reduce effective WIP "
                f"by an estimated 15–20%."
            ),
            expected_impact=(
                "Reduces cycle time for critical lots by prioritising throughput. "
                f"{'Shortens estimated recovery time.' if recovery_hours else ''}"
            ),
            feasibility="HIGH",
        ))
        priority += 1

    # ── Inventory action ───────────────────────────────────────────────────────
    if inventory_coverage_days is not None and inventory_coverage_days < 14:
        tier_word = "CRITICAL" if inventory_coverage_days < 7 else "LOW"
        recs.append(MitigationRecommendation(
            priority=priority,
            category="INVENTORY",
            recommendation=(
                f"Immediately place emergency replenishment order for {material_id}. "
                f"Current coverage is {inventory_coverage_days:.1f} days — below the "
                f"14-day risk threshold. Target: restore to ≥ 30 days on-hand."
            ),
            expected_impact=f"Eliminates {tier_word} inventory risk within supplier lead time.",
            feasibility="HIGH",
        ))
        priority += 1

    # ── SPOF / supplier diversification ───────────────────────────────────────
    if has_spof and material_id:
        recs.append(MitigationRecommendation(
            priority=priority,
            category="SUPPLIER",
            recommendation=(
                f"Initiate qualification of a second source supplier for {material_id} "
                f"to eliminate the identified Single Point of Failure. "
                f"Target: reduce dominant-supplier share to ≤ 50%."
            ),
            expected_impact=(
                "Reduces SPOF exposure and HHI concentration. "
                "Estimated qualification lead time: 6–12 months."
            ),
            feasibility="MEDIUM",
        ))
        priority += 1

    # ── High HHI diversification ───────────────────────────────────────────────
    if hhi_value and hhi_value > 2500 and not has_spof and material_id:
        recs.append(MitigationRecommendation(
            priority=priority,
            category="SUPPLIER",
            recommendation=(
                f"Supply concentration for {material_id} is HIGH (HHI={hhi_value:.0f}). "
                f"Negotiate spot-purchase agreements with secondary qualified suppliers "
                f"to rebalance allocation toward target HHI < 2500."
            ),
            expected_impact="Reduces supply concentration risk and improves resilience to single-supplier disruptions.",
            feasibility="MEDIUM",
        ))
        priority += 1

    # ── Long recovery time ─────────────────────────────────────────────────────
    if recovery_hours and recovery_hours > 16:
        recs.append(MitigationRecommendation(
            priority=priority,
            category="SCHEDULE",
            recommendation=(
                f"Recovery time of {recovery_hours:.1f} hours exceeds one shift. "
                f"Authorise overtime / second-shift staffing for {tool_id} to "
                f"sustain maximum processing rate through recovery."
            ),
            expected_impact="Compresses recovery window by extending available tool-hours.",
            feasibility="MEDIUM",
        ))
        priority += 1

    # ── General fallback ───────────────────────────────────────────────────────
    if not recs:
        recs.append(MitigationRecommendation(
            priority=1,
            category="OTHER",
            recommendation=(
                f"Current risk level for {tool_id} is within acceptable bounds. "
                f"Continue monitoring utilisation and WIP queue. "
                f"Escalate if bottleneck score exceeds 0.75."
            ),
            expected_impact="Maintains situational awareness without disruptive intervention.",
            feasibility="HIGH",
        ))

    return recs


async def get_combined_risk(
    tool_id: str,
    outage_hours: float | None = None,
) -> CombinedRiskResult:
    """
    Full combined risk assessment for a given tool.
    Optionally incorporates an outage scenario.

    Uses the new Member-1 bottleneck API (score is now 0–100).
    Manufacturing risk is normalised to 0–1 by dividing by 100.
    """
    from app.services.bottleneck.queries import get_tool, get_snapshots
    from app.api.bottlenecks import _full_assessment

    # 1. Manufacturing risk via new bottleneck service
    tool_data = await get_tool(tool_id)
    if tool_data is None:
        raise ValueError(f"Tool '{tool_id}' not found.")
    snaps = await get_snapshots(tool_id)
    assessment = _full_assessment(tool_data, snaps)

    # Normalise 0–100 score → 0–1 ratio for combined formula
    mfg_risk = round(assessment["bottleneck_score"] / 100.0, 4)
    is_critical = assessment["severity"] == "CRITICAL"

    # 2. Outage simulation (if requested) — still use the standalone function
    outage_result = None
    recovery_hours: float | None = None
    if outage_hours and outage_hours > 0:
        outage_result = await bottleneck_service.simulate_tool_outage(tool_id, outage_hours)
        recovery_hours = outage_result.recovery_hours
        # Outage increases manufacturing risk proportionally to recovery time
        if recovery_hours:
            outage_factor = min(1.0, recovery_hours / 24.0)
            mfg_risk = min(1.0, mfg_risk + 0.2 * outage_factor)

    # 3. Supply chain risk for primary material
    material_id = _TOOL_PRIMARY_MATERIAL.get(tool_id)
    supply_risk_obj = None
    sc_risk = 0.5  # neutral fallback
    if material_id:
        try:
            supply_risk_obj = await supply_service.get_material_supply_risk(material_id)
            sc_risk = supply_risk_obj.combined_supply_risk
        except Exception:
            pass

    # 4. Combined score
    combined = round(0.55 * mfg_risk + 0.45 * sc_risk, 4)
    risk_tier = _combined_risk_tier(combined)

    # 5. Recommendations
    recommendations = _build_recommendations(
        tool_id=tool_id,
        tool_name=assessment["tool_name"],
        bottleneck_score=assessment["bottleneck_score"],
        is_critical_bottleneck=is_critical,
        outage_hours=outage_hours,
        recovery_hours=recovery_hours,
        supply_risk=supply_risk_obj,
        material_id=material_id,
        has_spof=supply_risk_obj.has_spof if supply_risk_obj else False,
        inventory_coverage_days=supply_risk_obj.inventory_coverage_days if supply_risk_obj else None,
        hhi_value=supply_risk_obj.hhi_value if supply_risk_obj else None,
    )

    return CombinedRiskResult(
        tool_id=tool_id,
        tool_name=assessment["tool_name"],
        process_step=assessment.get("process_name", ""),
        manufacturing_risk_score=round(mfg_risk, 4),
        supply_chain_risk_score=round(sc_risk, 4),
        combined_risk_score=combined,
        risk_tier=risk_tier,
        risk_tier_label=_RISK_TIER_LABEL[risk_tier],
        confidence_pct=round(assessment.get("confidence", 0.80) * 100),
        primary_material_id=material_id,
        outage_simulation=outage_result,
        supply_risk=supply_risk_obj,
        recommendations=recommendations,
    )
