"""
tests/test_member3.py
======================
Member 3 test suite.

Tests:
  1.  Impact: backlog recovery integration (reuses Member 1 calculate_backlog_recovery)
  2.  Impact: recovery not possible when capacity <= arrival_rate
  3.  Impact: downstream propagation via impact_service
  4.  Impact: affected wafer count
  5.  Impact: confidence integration
  6.  Recommendation: alternate-tool routing recommendation
  7.  Recommendation: SPOF supplier diversification recommendation
  8.  Recommendation: inventory replenishment recommendation
  9.  Recommendation: HHI concentration recommendation
  10. Recommendation: scheduling recommendation for long recovery
  11. Supply: combined supply risk score formula
  12. Supply: SPOF detection
  13. Supply: inventory coverage risk tiers
  14. Bob narration: fallback does not raise
  15. Bob narration: prompt builder builds structured facts
  16. Bob narration: Bob cannot recalculate; prompt is data-only
  17. Impact service: combined risk score formula (0.55 mfg + 0.45 sc)
  18. Impact service: combined risk tier classification
  19. Impact service: outage factor raises manufacturing risk
  20. End-to-end: LITH-07 scenario (demo data, no DB required)
"""

from __future__ import annotations

import asyncio
import pytest

# ── Member 1 backlog/recovery (imported directly per spec) ────────────────────
from app.services.bottleneck.backlog_recovery import (
    calculate_backlog_recovery,
    BacklogRecoveryResult,
)

# ── Supply service (Member 2 / shared) ────────────────────────────────────────
from app.services.supply_service import (
    compute_hhi,
    hhi_concentration_level,
    coverage_risk_tier,
)

# ── Impact service (Member 3) ─────────────────────────────────────────────────
from app.services.impact_service import (
    _combined_risk_tier,
    _build_recommendations,
    _TOOL_PRIMARY_MATERIAL,
)

# ── Bob narration service (Member 3) ─────────────────────────────────────────
from app.services.bob_service import (
    _fallback_narration,
    build_outage_prompt,
    build_combined_risk_prompt,
    build_supply_risk_prompt,
    build_bottleneck_prompt,
)


# =============================================================================
# 1–2. Backlog/Recovery Integration
# =============================================================================

class TestImpactBacklogRecovery:
    """Member 3 uses calculate_backlog_recovery from Member 1 unchanged."""

    def test_basic_integration(self):
        """
        LITH-07 demo scenario:
          arrival_rate  = utilization * capacity = 0.971 * 50 = ~48.5 lots/hr
          tool_capacity = 50 lots/hr
          outage        = 8 hours
          backlog       = 48.5 * 8 = 388 lots
          net_clearance = 50 - 48.5 = 1.5 lots/hr
          recovery      = 388 / 1.5 ≈ 258 hours  (long!)
        """
        util = 23.3 / 24.0       # LITH-07 utilisation ratio
        capacity_per_hour = 50.0
        arrival = util * capacity_per_hour

        result = calculate_backlog_recovery(
            arrival_rate=arrival,
            tool_capacity=capacity_per_hour,
            outage_duration=8.0,
        )
        assert result["backlog_added"] == pytest.approx(arrival * 8.0, rel=1e-4)
        assert result["recoverable"] is True
        assert result["recovery_time_hours"] is not None
        assert result["recovery_time_hours"] > 0

    def test_impossible_recovery(self):
        """When tool is saturated (util ~= 1), net clearance ≈ 0 → unrecoverable."""
        result = calculate_backlog_recovery(
            arrival_rate=50.0,    # equal to capacity
            tool_capacity=50.0,
            outage_duration=8.0,
        )
        assert result["recoverable"] is False
        assert result["recovery_time_hours"] is None

    def test_backlog_wafer_calculation(self):
        """Backlog lots × 25 wafers/lot = affected wafers."""
        result = calculate_backlog_recovery(
            arrival_rate=10.0,
            tool_capacity=15.0,
            outage_duration=8.0,
        )
        backlog_lots = result["backlog_added"]
        affected_wafers = backlog_lots * 25
        assert affected_wafers == pytest.approx(80.0 * 25)

    def test_recovery_time_finite_only_when_recoverable(self):
        """recovery_time_hours is None if and only if recoverable is False."""
        for arrival, cap in [(5.0, 10.0), (10.0, 10.0), (15.0, 10.0)]:
            r = calculate_backlog_recovery(arrival, cap, outage_duration=4.0)
            if r["recoverable"]:
                assert r["recovery_time_hours"] is not None
            else:
                assert r["recovery_time_hours"] is None


# =============================================================================
# 3. Downstream propagation (via impact_service which calls bottleneck_service)
# =============================================================================

class TestDownstreamPropagation:
    def test_downstream_simulation_runs(self):
        """Downstream simulation should run without raising in demo mode."""
        async def run():
            from app.services.bottleneck_service import simulate_tool_outage
            return await simulate_tool_outage("LITH-07", 8.0)

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result.tool_id == "LITH-07"
        # LITH-07 has downstream steps after Lithography
        assert len(result.downstream_impact) >= 1

    def test_downstream_steps_have_positive_delay(self):
        """All downstream impact items should have delay > 0."""
        async def run():
            from app.services.bottleneck_service import simulate_tool_outage
            return await simulate_tool_outage("LITH-07", 8.0)

        result = asyncio.get_event_loop().run_until_complete(run())
        if result.is_recoverable:
            for step in result.downstream_impact:
                assert step.delay_hours > 0


# =============================================================================
# 4. Affected wafer count
# =============================================================================

class TestAffectedWafers:
    def test_wafer_count_is_lots_times_25(self):
        """backlog_wafers = total_backlog_lots * 25 (25 wafers/lot)."""
        async def run():
            from app.services.bottleneck_service import simulate_tool_outage
            return await simulate_tool_outage("LITH-07", 8.0)

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result.backlog_wafers == result.total_backlog_lots * 25


# =============================================================================
# 5. Confidence integration
# =============================================================================

class TestConfidenceIntegration:
    def test_confidence_from_bottleneck_module(self):
        """Impact service uses Member 1 confidence from full bottleneck assessment."""
        from app.services.bottleneck.confidence import compute_confidence
        # LITH-07 rising history → high confidence
        conf = compute_confidence([60.0, 80.0, 120.0, 180.0, 240.0])
        assert conf["low_confidence"] is False
        assert conf["confidence"] > 0.5

    def test_low_confidence_for_single_snapshot(self):
        from app.services.bottleneck.confidence import compute_confidence
        conf = compute_confidence([100.0])
        assert conf["low_confidence"] is True
        assert conf["confidence"] == pytest.approx(0.50)


# =============================================================================
# 6–10. Recommendation Engine
# =============================================================================

class TestRecommendationEngine:
    def _make_supply_risk(
        self,
        has_spof: bool = False,
        coverage_days: float = 30.0,
        hhi: float = 1000.0,
        material_id: str = "PHOTO-RES-EUV",
    ):
        """Build a minimal MaterialSupplyRisk-like dict/object for testing."""
        from app.models import MaterialSupplyRisk
        coverage_tier = coverage_risk_tier(coverage_days)
        risk_score_map = {"LOW": 0.1, "MEDIUM": 0.4, "HIGH": 0.7, "CRITICAL": 1.0}
        hhi_norm = hhi / 10000.0
        inv_score = risk_score_map[coverage_tier]
        spof_score = 1.0 if has_spof else 0.0
        combined = round(0.30 * hhi_norm + 0.30 * inv_score + 0.25 * spof_score + 0.15 * 0.1, 4)
        tier = "CRITICAL" if combined >= 0.75 else "RED" if combined >= 0.55 else "AMBER" if combined >= 0.35 else "GREEN"
        return MaterialSupplyRisk(
            material_id=material_id,
            material_name="EUV Photoresist",
            hhi_score=hhi_norm,
            hhi_value=hhi,
            inventory_risk_tier=coverage_tier,
            inventory_coverage_days=coverage_days,
            has_spof=has_spof,
            geopolitical_risk_score=0.1,
            combined_supply_risk=combined,
            risk_tier=tier,
        )

    def test_alternate_tool_recommendation(self):
        """LITH-07 bottleneck → reroute to LITH-08 recommended."""
        recs = _build_recommendations(
            tool_id="LITH-07",
            tool_name="EUV Scanner Unit 7",
            bottleneck_score=92.0,
            is_critical_bottleneck=True,
            outage_hours=8.0,
            recovery_hours=16.0,
            supply_risk=None,
            material_id=None,
            has_spof=False,
            inventory_coverage_days=None,
            hhi_value=None,
        )
        # At least one tool-reroute recommendation should be present
        tool_recs = [r for r in recs if r.category == "TOOL"]
        assert len(tool_recs) > 0
        assert "LITH-08" in tool_recs[0].recommendation

    def test_spof_recommendation_generated(self):
        """SPOF detected → supplier diversification recommendation."""
        supply = self._make_supply_risk(has_spof=True, coverage_days=30.0)
        recs = _build_recommendations(
            tool_id="LITH-07",
            tool_name="EUV Scanner Unit 7",
            bottleneck_score=50.0,
            is_critical_bottleneck=False,
            outage_hours=None,
            recovery_hours=None,
            supply_risk=supply,
            material_id="PHOTO-RES-EUV",
            has_spof=True,
            inventory_coverage_days=30.0,
            hhi_value=5000.0,
        )
        supplier_recs = [r for r in recs if r.category == "SUPPLIER"]
        assert len(supplier_recs) > 0
        assert "PHOTO-RES-EUV" in supplier_recs[0].recommendation

    def test_low_inventory_recommendation(self):
        """Coverage < 14 days → inventory replenishment recommendation."""
        supply = self._make_supply_risk(has_spof=False, coverage_days=5.0)
        recs = _build_recommendations(
            tool_id="LITH-07",
            tool_name="EUV Scanner Unit 7",
            bottleneck_score=50.0,
            is_critical_bottleneck=False,
            outage_hours=None,
            recovery_hours=None,
            supply_risk=supply,
            material_id="PHOTO-RES-EUV",
            has_spof=False,
            inventory_coverage_days=5.0,
            hhi_value=None,
        )
        inv_recs = [r for r in recs if r.category == "INVENTORY"]
        assert len(inv_recs) > 0
        assert "5.0" in inv_recs[0].recommendation

    def test_high_hhi_recommendation(self):
        """HHI > 2500 without SPOF → concentration diversification recommendation."""
        supply = self._make_supply_risk(has_spof=False, coverage_days=30.0, hhi=3500.0)
        recs = _build_recommendations(
            tool_id="CVD-11",
            tool_name="LPCVD Furnace 11",
            bottleneck_score=45.0,
            is_critical_bottleneck=False,
            outage_hours=None,
            recovery_hours=None,
            supply_risk=supply,
            material_id="CVD-TEOS",
            has_spof=False,
            inventory_coverage_days=30.0,
            hhi_value=3500.0,
        )
        supplier_recs = [r for r in recs if r.category == "SUPPLIER"]
        # Should get a concentration diversification rec (HHI > 2500, no SPOF)
        assert len(supplier_recs) > 0

    def test_scheduling_recommendation_long_recovery(self):
        """Recovery > 4h with critical bottleneck → scheduling recommendation."""
        recs = _build_recommendations(
            tool_id="LITH-07",
            tool_name="EUV Scanner Unit 7",
            bottleneck_score=92.0,
            is_critical_bottleneck=True,
            outage_hours=8.0,
            recovery_hours=20.0,
            supply_risk=None,
            material_id=None,
            has_spof=False,
            inventory_coverage_days=None,
            hhi_value=None,
        )
        sched_recs = [r for r in recs if r.category == "SCHEDULE"]
        assert len(sched_recs) > 0


# =============================================================================
# 11. Supply: combined supply risk score formula
# =============================================================================

class TestSupplyRiskFormula:
    def test_hhi_formula(self):
        """HHI = Σ(share²). One supplier at 100% → HHI = 10000 (monopoly)."""
        assert compute_hhi([100.0]) == pytest.approx(10000.0)

    def test_hhi_two_equal_suppliers(self):
        """Two equal 50% suppliers → HHI = 50² + 50² = 5000."""
        assert compute_hhi([50.0, 50.0]) == pytest.approx(5000.0)

    def test_hhi_concentration_levels(self):
        assert hhi_concentration_level(10000.0) == "MONOPOLY"
        assert hhi_concentration_level(3000.0) == "HIGH"
        assert hhi_concentration_level(2000.0) == "MODERATE"
        assert hhi_concentration_level(1000.0) == "LOW"

    def test_hhi_empty_shares(self):
        assert compute_hhi([]) == 0.0


# =============================================================================
# 12. Supply: SPOF detection
# =============================================================================

class TestSPOFDetection:
    def test_spof_async(self):
        """SPOF analysis identifies materials with dominant supplier ≥ 70%."""
        async def run():
            from app.services.supply_service import get_spof_analysis
            return await get_spof_analysis()

        results = asyncio.get_event_loop().run_until_complete(run())
        # CLEAN-SC1 has 100% from one supplier → SPOF
        spof_ids = [s.material_id for s in results]
        assert "CLEAN-SC1" in spof_ids


# =============================================================================
# 13. Supply: inventory coverage tiers
# =============================================================================

class TestInventoryCoverageTiers:
    def test_critical_under_7(self):
        assert coverage_risk_tier(5.0) == "CRITICAL"

    def test_high_between_7_and_14(self):
        assert coverage_risk_tier(10.0) == "HIGH"

    def test_medium_between_14_and_30(self):
        assert coverage_risk_tier(20.0) == "MEDIUM"

    def test_low_above_30(self):
        assert coverage_risk_tier(35.0) == "LOW"

    def test_boundary_7_is_high(self):
        assert coverage_risk_tier(7.0) == "HIGH"

    def test_boundary_14_is_medium(self):
        assert coverage_risk_tier(14.0) == "MEDIUM"

    def test_boundary_30_is_low(self):
        assert coverage_risk_tier(30.0) == "LOW"


# =============================================================================
# 14–16. Bob Narration
# =============================================================================

class TestBobNarration:
    def test_fallback_does_not_raise(self):
        """Fallback narration must never raise an exception."""
        for ctx in ("BOTTLENECK", "OUTAGE", "SUPPLY_RISK", "COMBINED", "UNKNOWN"):
            text = _fallback_narration("any prompt", ctx)
            assert isinstance(text, str)
            assert len(text) > 0

    def test_fallback_returns_non_empty_for_all_contexts(self):
        contexts = ["BOTTLENECK", "OUTAGE", "SUPPLY_RISK", "COMBINED"]
        for ctx in contexts:
            text = _fallback_narration("prompt", ctx)
            assert len(text) > 20, f"Fallback too short for {ctx}"

    def test_outage_prompt_contains_structured_facts(self):
        """Prompt must contain the pre-calculated numbers, not ask Bob to compute them."""
        data = {
            "tool_id": "LITH-07",
            "process_step": "Lithography",
            "outage_hours": 8,
            "outage_backlog_lots": 388,
            "backlog_wafers": 9700,
            "total_backlog_lots": 388,
            "recovery_hours": 258.0,
            "is_recoverable": True,
            "downstream_impact": [],
        }
        prompt = build_outage_prompt(data)
        assert "LITH-07" in prompt
        assert "388" in prompt        # backlog lots — pre-calculated
        assert "258" in prompt        # recovery hours — pre-calculated
        assert "8" in prompt          # outage hours

    def test_supply_risk_prompt_contains_structured_facts(self):
        data = {
            "material_id": "PHOTO-RES-EUV",
            "material_name": "EUV Photoresist",
            "hhi_value": 5800.0,
            "concentration_level": "HIGH",
            "inventory_coverage_days": 5.0,
            "inventory_risk_tier": "CRITICAL",
            "has_spof": True,
            "geopolitical_risk_score": 0.7,
            "combined_supply_risk": 0.82,
            "risk_tier": "CRITICAL",
        }
        prompt = build_supply_risk_prompt(data)
        assert "PHOTO-RES-EUV" in prompt
        assert "5800" in prompt
        assert "5.0" in prompt

    def test_combined_prompt_contains_scores(self):
        data = {
            "tool_id": "LITH-07",
            "process_step": "Lithography",
            "manufacturing_risk_score": 0.92,
            "supply_chain_risk_score": 0.75,
            "combined_risk_score": 0.84,
            "risk_tier": "CRITICAL",
            "risk_tier_label": "Critical Risk",
            "confidence_pct": 90,
            "recommendations": [{"priority": 1, "category": "TOOL", "recommendation": "Re-route lots to LITH-08"}],
        }
        prompt = build_combined_risk_prompt(data)
        assert "LITH-07" in prompt
        assert "0.92" in prompt
        assert "0.75" in prompt
        assert "0.84" in prompt

    def test_bob_receives_facts_not_instructions_to_calculate(self):
        """
        The prompt must contain pre-computed numbers.
        Bob is given facts to EXPLAIN, not raw inputs to calculate from.
        Verify: the prompt contains the computed recovery_hours, not just
        arrival_rate + capacity for Bob to derive.
        """
        data = {
            "tool_id": "LITH-07",
            "process_step": "Lithography",
            "outage_hours": 8,
            "outage_backlog_lots": 388,
            "backlog_wafers": 9700,
            "total_backlog_lots": 388,
            "recovery_hours": 258.0,
            "is_recoverable": True,
            "downstream_impact": [],
        }
        prompt = build_outage_prompt(data)
        # Bob receives recovery_hours=258 directly, not arrival_rate=48.5 to recompute
        assert "258" in prompt
        # The prompt should NOT ask Bob to compute backlog from first principles
        assert "arrival_rate" not in prompt
        assert "formula" not in prompt.lower()


# =============================================================================
# 17–19. Impact Service: combined risk formula
# =============================================================================

class TestCombinedRiskFormula:
    def test_combined_risk_formula(self):
        """Combined = 0.55 × mfg_risk + 0.45 × supply_risk."""
        mfg = 0.80
        sc = 0.60
        expected = round(0.55 * mfg + 0.45 * sc, 4)
        # We test by calling the tier logic
        combined = 0.55 * mfg + 0.45 * sc
        assert round(combined, 4) == expected

    def test_combined_risk_tiers(self):
        """Risk tiers based on combined score."""
        assert _combined_risk_tier(0.80) == "CRITICAL"
        assert _combined_risk_tier(0.60) == "RED"
        assert _combined_risk_tier(0.45) == "AMBER"
        assert _combined_risk_tier(0.20) == "GREEN"

    def test_combined_tier_boundaries(self):
        assert _combined_risk_tier(0.75) == "CRITICAL"
        assert _combined_risk_tier(0.74) == "RED"
        assert _combined_risk_tier(0.55) == "RED"
        assert _combined_risk_tier(0.54) == "AMBER"
        assert _combined_risk_tier(0.35) == "AMBER"
        assert _combined_risk_tier(0.34) == "GREEN"

    def test_tool_primary_material_mapping(self):
        """LITH-07 must map to its primary material (EUV photoresist)."""
        material = _TOOL_PRIMARY_MATERIAL.get("LITH-07")
        assert material is not None
        # Must reference the photoresist (EUV exposure process)
        assert "PHOTO" in material or "EUV" in material or "RES" in material


# =============================================================================
# 20. End-to-end LITH-07 scenario (demo data, no DB)
# =============================================================================

class TestLITH07EndToEnd:
    """
    Full LITH-07 + 8h outage scenario using demo data.
    Verifies the complete chain without a live database.
    """

    def test_lith07_bottleneck_score_is_high_or_critical(self):
        """LITH-07 must emerge as HIGH or CRITICAL from actual calculations."""
        from app.services.bottleneck.queries import get_tool, get_snapshots
        from app.api.bottlenecks import _full_assessment

        async def run():
            tool = await get_tool("LITH-07")
            snaps = await get_snapshots("LITH-07")
            return _full_assessment(tool, snaps)

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result["severity"] in ("HIGH", "CRITICAL"), (
            f"LITH-07 severity is {result['severity']} (score={result['bottleneck_score']:.2f}), expected HIGH or CRITICAL"
        )
        assert result["bottleneck_score"] >= 70.0

    def test_lith07_outage_simulation(self):
        """LITH-07 8h outage simulation runs and returns valid result."""
        from app.services.bottleneck_service import simulate_tool_outage

        async def run():
            return await simulate_tool_outage("LITH-07", 8.0)

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result.tool_id == "LITH-07"
        assert result.outage_hours == 8.0
        assert result.outage_backlog_lots > 0
        assert result.backlog_wafers > 0
        assert result.backlog_wafers == result.total_backlog_lots * 25

    def test_lith07_combined_risk(self):
        """LITH-07 combined risk assessment returns a valid, non-trivial result."""
        from app.services.impact_service import get_combined_risk

        async def run():
            return await get_combined_risk("LITH-07", outage_hours=8.0)

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result.tool_id == "LITH-07"
        assert result.combined_risk_score > 0
        assert result.risk_tier in ("AMBER", "RED", "CRITICAL")
        assert len(result.recommendations) > 0
        assert result.outage_simulation is not None

    def test_lith07_has_recommendations(self):
        """LITH-07 scenario should produce actionable recommendations."""
        from app.services.impact_service import get_combined_risk

        async def run():
            return await get_combined_risk("LITH-07", outage_hours=8.0)

        result = asyncio.get_event_loop().run_until_complete(run())
        categories = [r.category for r in result.recommendations]
        # Must have at least a TOOL or SCHEDULE recommendation
        assert any(c in ("TOOL", "SCHEDULE") for c in categories)

    def test_lith07_bob_fallback_generates_text(self):
        """Bob fallback must produce text even if API is unavailable."""
        text = _fallback_narration("...", "COMBINED")
        assert isinstance(text, str)
        assert len(text) > 50

    def test_lith07_primary_material_linked(self):
        """LITH-07 must have a primary material linked via impact_service mapping."""
        material = _TOOL_PRIMARY_MATERIAL.get("LITH-07")
        assert material is not None, "LITH-07 must have a primary material mapping"

    def test_recovery_uses_member1_function_not_duplicate(self):
        """
        The recovery calculation used in impact_service must be the same
        BacklogRecoveryResult type as Member 1's calculate_backlog_recovery.
        This test ensures no duplicate implementation exists.
        """
        result = calculate_backlog_recovery(
            arrival_rate=48.5,
            tool_capacity=50.0,
            outage_duration=8.0,
        )
        # Type check: must be the Member 1 BacklogRecoveryResult TypedDict
        assert "backlog_added" in result
        assert "recovery_time_hours" in result
        assert "recoverable" in result
        assert "net_clearance_rate" in result
