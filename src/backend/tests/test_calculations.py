"""
Tests for bottleneck detection calculations.
These tests validate all core deterministic formulas independently of the database.
"""

import pytest
from app.services.bottleneck_service import (
    compute_wip_pressure,
    compute_capacity_pressure,
    compute_bottleneck_score,
    compute_outage_backlog_and_recovery,
    SHIFT_HOURS,
    AVG_LOT_CYCLE_TIME_HRS,
    CRITICAL_BOTTLENECK_SCORE,
)


class TestWIPPressure:
    def test_zero_wip(self):
        assert compute_wip_pressure(0, 120.0) == 0.0

    def test_normal_wip(self):
        # 38 lots, capacity = 120 wph * 8h / 2.5 = 384 lots/shift → 38/384 ≈ 0.099
        result = compute_wip_pressure(38, 120.0)
        expected = 38 / ((120.0 * SHIFT_HOURS) / AVG_LOT_CYCLE_TIME_HRS)
        assert abs(result - expected) < 0.001

    def test_clamped_at_one(self):
        # Extremely high WIP should clamp to 1.0
        result = compute_wip_pressure(10000, 1.0)
        assert result == 1.0

    def test_zero_capacity_returns_one(self):
        # Division by zero guard
        result = compute_wip_pressure(10, 0.0)
        assert result == 1.0


class TestCapacityPressure:
    def test_below_threshold_zero(self):
        """Below 85% utilisation → no capacity pressure."""
        assert compute_capacity_pressure(80.0) == 0.0
        assert compute_capacity_pressure(85.0) == 0.0

    def test_at_100_pct_is_one(self):
        result = compute_capacity_pressure(100.0)
        assert abs(result - 1.0) < 0.001

    def test_midpoint(self):
        # 92.5% = midpoint between 85 and 100 → should be ~0.5
        result = compute_capacity_pressure(92.5)
        assert abs(result - 0.5) < 0.01

    def test_above_100_clamped(self):
        result = compute_capacity_pressure(105.0)
        assert result <= 1.0


class TestBottleneckScore:
    def test_lith07_is_critical(self):
        """LITH-07 demo values should produce a CRITICAL bottleneck score (>= 0.60).
        
        With 38 lots on a 384-lot/shift capacity tool, WIP pressure = 0.099.
        Capacity pressure = (94.5 - 85) / 15 = 0.633.
        Score = 0.5*(94.5/100) + 0.3*0.099 + 0.2*0.633 ≈ 0.63 — exceeds 0.60 threshold.
        """
        util = 94.5
        wip_p = compute_wip_pressure(38, 120.0)
        cap_p = compute_capacity_pressure(util)
        score = compute_bottleneck_score(util, wip_p, cap_p)
        assert score >= CRITICAL_BOTTLENECK_SCORE, (
            f"LITH-07 should be CRITICAL; got score={score:.4f}"
        )

    def test_low_util_not_critical(self):
        """Low utilisation tool should not be critical."""
        score = compute_bottleneck_score(30.0, 0.02, 0.0)
        assert score < CRITICAL_BOTTLENECK_SCORE

    def test_score_bounds(self):
        """Score must always be in [0, 1]."""
        for util in [0, 50, 85, 100]:
            for wip in [0.0, 0.5, 1.0]:
                for cap in [0.0, 0.5, 1.0]:
                    score = compute_bottleneck_score(util, wip, cap)
                    assert 0.0 <= score <= 1.0

    def test_weights_sum(self):
        """With all inputs at 1.0, score must be 1.0 (weights sum to 1)."""
        score = compute_bottleneck_score(100.0, 1.0, 1.0)
        assert abs(score - 1.0) < 0.001


class TestOutageSimulation:
    def test_basic_recovery(self):
        result = compute_outage_backlog_and_recovery(
            outage_hours=8.0,
            current_wip_lots=38,
            utilization_pct=94.5,
            max_capacity_wph=120.0,
        )
        assert result["outage_backlog_lots"] > 0
        assert result["total_backlog_lots"] >= result["outage_backlog_lots"]
        assert result["backlog_wafers"] == result["total_backlog_lots"] * 25

    def test_recovery_hours_positive(self):
        result = compute_outage_backlog_and_recovery(
            outage_hours=8.0,
            current_wip_lots=10,
            utilization_pct=50.0,
            max_capacity_wph=120.0,
        )
        if result["is_recoverable"]:
            assert result["recovery_hours"] > 0

    def test_impossible_recovery_at_full_utilization(self):
        """At 100% utilisation, arrival rate equals max capacity → unrecoverable."""
        result = compute_outage_backlog_and_recovery(
            outage_hours=4.0,
            current_wip_lots=100,
            utilization_pct=100.0,
            max_capacity_wph=120.0,
        )
        assert result["is_recoverable"] is False
        assert result["recovery_hours"] is None

    def test_zero_wip_outage(self):
        """Outage on empty tool only adds arriving lots."""
        result = compute_outage_backlog_and_recovery(
            outage_hours=2.0,
            current_wip_lots=0,
            utilization_pct=60.0,
            max_capacity_wph=120.0,
        )
        assert result["outage_backlog_lots"] >= 0
        # With some utilisation, lots will arrive during the outage
        assert result["total_backlog_lots"] >= 0

    def test_outage_hours_must_be_positive(self):
        """Zero outage hours should produce zero backlog."""
        result = compute_outage_backlog_and_recovery(
            outage_hours=0.0,
            current_wip_lots=10,
            utilization_pct=80.0,
            max_capacity_wph=120.0,
        )
        assert result["outage_backlog_lots"] == 0


class TestHHICalculation:
    """Import and test HHI from supply service without DB."""

    def test_monopoly(self):
        from app.services.supply_service import compute_hhi, hhi_concentration_level
        hhi = compute_hhi([100.0])
        assert hhi == 10000.0
        assert hhi_concentration_level(hhi) == "MONOPOLY"

    def test_duopoly_high(self):
        from app.services.supply_service import compute_hhi, hhi_concentration_level
        hhi = compute_hhi([70.0, 30.0])
        assert hhi == pytest.approx(70**2 + 30**2)
        assert hhi_concentration_level(hhi) == "HIGH"

    def test_balanced_four_suppliers(self):
        """4 equal suppliers at 25% each → HHI = 2500 (MODERATE boundary).
        HHI > 2500 = HIGH, HHI > 1500 = MODERATE, else LOW.
        HHI exactly 2500 is NOT > 2500, so it falls into MODERATE.
        """
        from app.services.supply_service import compute_hhi, hhi_concentration_level
        hhi = compute_hhi([25.0, 25.0, 25.0, 25.0])
        assert hhi == pytest.approx(2500.0)
        # 2500 is exactly the MODERATE threshold (> 1500, not > 2500)
        assert hhi_concentration_level(hhi) == "MODERATE"

    def test_empty_list(self):
        from app.services.supply_service import compute_hhi
        assert compute_hhi([]) == 0.0


class TestInventoryCoverage:
    def test_critical_coverage(self):
        from app.services.supply_service import coverage_risk_tier
        assert coverage_risk_tier(3.0) == "CRITICAL"

    def test_high_coverage(self):
        from app.services.supply_service import coverage_risk_tier
        assert coverage_risk_tier(10.0) == "HIGH"

    def test_medium_coverage(self):
        from app.services.supply_service import coverage_risk_tier
        assert coverage_risk_tier(20.0) == "MEDIUM"

    def test_low_risk_coverage(self):
        from app.services.supply_service import coverage_risk_tier
        assert coverage_risk_tier(45.0) == "LOW"
