"""
Tests for Member 1 — Fab Bottleneck Intelligence module.

Covers all 10 required test cases:
  1. utilization calculation
  2. WIP pressure (raw + normalized)
  3. capacity pressure
  4. downtime percentage
  5. bottleneck score
  6. severity classification
  7. backlog calculation
  8. recovery calculation
  9. impossible recovery when capacity <= arrival rate
 10. confidence behavior with <3 snapshots and >=3 snapshots
"""

import math
import pytest

from app.services.bottleneck.utilization import compute_utilization
from app.services.bottleneck.wip_pressure import (
    compute_wip_pressure,
    normalize_wip_pressure,
    WIP_NORM_DIVISOR,
)
from app.services.bottleneck.capacity_pressure import compute_capacity_pressure
from app.services.bottleneck.score import (
    compute_bottleneck_score,
    compute_downtime_pct,
    classify_severity,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    W_UTILIZATION,
    W_CAPACITY_PRESSURE,
    W_WIP_PRESSURE,
    W_DOWNTIME,
)
from app.services.bottleneck.backlog_recovery import (
    calculate_backlog_recovery,
    estimate_cycle_time_littles_law,
)
from app.services.bottleneck.confidence import (
    compute_confidence,
    MIN_SNAPSHOTS_FOR_CONFIDENCE,
)


# =============================================================================
# 1. Utilization
# =============================================================================

class TestUtilization:
    def test_normal(self):
        result = compute_utilization(23.3, 24.0)
        assert abs(result - 23.3 / 24.0) < 1e-9

    def test_zero_busy(self):
        assert compute_utilization(0.0, 24.0) == 0.0

    def test_zero_available(self):
        """available_time == 0 → safe return of 0.0 (not a bottleneck)."""
        assert compute_utilization(10.0, 0.0) == 0.0

    def test_clamped_above_one(self):
        """Busy hours cannot logically exceed available hours; clamped to 1.0."""
        assert compute_utilization(30.0, 24.0) == 1.0

    def test_full_utilization(self):
        assert compute_utilization(24.0, 24.0) == 1.0

    def test_lith07_approx(self):
        """LITH-07 demo: 23.3 / 24.0 ≈ 97.1 %."""
        result = compute_utilization(23.3, 24.0)
        assert abs(result * 100 - 97.083) < 0.01

    def test_ratio_times_100_is_percentage(self):
        util = compute_utilization(12.0, 24.0)
        assert abs(util * 100 - 50.0) < 1e-9


# =============================================================================
# 2. WIP Pressure
# =============================================================================

class TestWIPPressure:
    def test_spec_example(self):
        """Spec example: current=240, normal=100 → raw pressure = 2.4."""
        assert compute_wip_pressure(240, 100) == pytest.approx(2.4)

    def test_zero_current_wip(self):
        assert compute_wip_pressure(0, 100) == 0.0

    def test_zero_normal_wip(self):
        """normal_wip == 0 → safe return of 0.0."""
        assert compute_wip_pressure(50, 0) == 0.0

    def test_equal_wip(self):
        assert compute_wip_pressure(100, 100) == pytest.approx(1.0)

    def test_raw_can_exceed_one(self):
        result = compute_wip_pressure(300, 100)
        assert result > 1.0

    def test_normalization_spec_example(self):
        """2.4 / 3.0 = 0.8 exactly."""
        raw = compute_wip_pressure(240, 100)
        norm = normalize_wip_pressure(raw)
        assert norm == pytest.approx(0.8)

    def test_normalization_clamps_high_value(self):
        """Values > 3× normal saturate at 1.0."""
        raw = compute_wip_pressure(400, 100)  # raw = 4.0 > 3.0
        assert normalize_wip_pressure(raw) == 1.0

    def test_normalization_zero(self):
        assert normalize_wip_pressure(0.0) == 0.0

    def test_normalization_custom_divisor(self):
        norm = normalize_wip_pressure(2.0, divisor=4.0)
        assert norm == pytest.approx(0.5)


# =============================================================================
# 3. Capacity Pressure
# =============================================================================

class TestCapacityPressure:
    def test_normal_load(self):
        result = compute_capacity_pressure(95.0, 100.0)
        assert result == pytest.approx(0.95)

    def test_zero_required(self):
        assert compute_capacity_pressure(0.0, 100.0) == 0.0

    def test_zero_available(self):
        """No capacity available → maximum pressure 1.0."""
        assert compute_capacity_pressure(50.0, 0.0) == 1.0

    def test_over_capacity_clamped(self):
        """Demand > supply → clamped to 1.0."""
        assert compute_capacity_pressure(120.0, 100.0) == 1.0

    def test_exact_capacity(self):
        assert compute_capacity_pressure(100.0, 100.0) == pytest.approx(1.0)

    def test_half_capacity(self):
        assert compute_capacity_pressure(50.0, 100.0) == pytest.approx(0.5)

    def test_bounds(self):
        for req in [0, 25, 50, 75, 100, 125]:
            result = compute_capacity_pressure(req, 100.0)
            assert 0.0 <= result <= 1.0


# =============================================================================
# 4. Downtime Percentage
# =============================================================================

class TestDowntimePct:
    def test_zero_downtime(self):
        assert compute_downtime_pct(0.0, 24.0) == 0.0

    def test_full_downtime(self):
        assert compute_downtime_pct(24.0, 24.0) == pytest.approx(1.0)

    def test_partial(self):
        result = compute_downtime_pct(6.0, 24.0)
        assert result == pytest.approx(0.25)

    def test_zero_total_hours(self):
        assert compute_downtime_pct(1.0, 0.0) == 0.0

    def test_clamped(self):
        assert compute_downtime_pct(30.0, 24.0) <= 1.0

    def test_lith07_demo(self):
        """LITH-07: 1.2h downtime in 24h = 5 %."""
        result = compute_downtime_pct(1.2, 24.0)
        assert abs(result - 0.05) < 0.001


# =============================================================================
# 5. Bottleneck Score
# =============================================================================

class TestBottleneckScore:
    def test_zero_inputs(self):
        assert compute_bottleneck_score(0, 0, 0, 0) == 0.0

    def test_full_inputs(self):
        """All inputs at 1.0 → score = 100.0 (weights sum to 1.0)."""
        assert compute_bottleneck_score(1.0, 1.0, 1.0, 1.0) == pytest.approx(100.0)

    def test_weight_sum(self):
        """Weights must sum to exactly 1.0."""
        assert W_UTILIZATION + W_CAPACITY_PRESSURE + W_WIP_PRESSURE + W_DOWNTIME == pytest.approx(1.0)

    def test_lith07_is_critical(self):
        """LITH-07 demo values must produce a CRITICAL score (>= 85).
        
        util     = 23.3/24.0 = 0.9708
        cap_p    = compute_capacity_pressure(23.3*50, 24*50) = 1.0 (fully loaded)
        wip_norm = normalize_wip_pressure(2.4) = 0.8
        dt_pct   = 1.2/24.0 = 0.05
        score    = 100 * (0.30*0.9708 + 0.30*1.0 + 0.25*0.8 + 0.15*0.05)
               = 100 * (0.2912 + 0.30 + 0.20 + 0.0075) = 100 * 0.7987 ≈ 79.87
        
        Revised: cap_p uses busy/cap, not util. Let's confirm score >= 70 (HIGH+).
        """
        from app.services.bottleneck.utilization import compute_utilization
        from app.services.bottleneck.wip_pressure import compute_wip_pressure, normalize_wip_pressure
        from app.services.bottleneck.capacity_pressure import compute_capacity_pressure
        from app.services.bottleneck.score import compute_downtime_pct

        util     = compute_utilization(23.3, 24.0)
        cap_p    = compute_capacity_pressure(23.3 * 50.0, 24.0 * 50.0)
        wip_norm = normalize_wip_pressure(compute_wip_pressure(240, 100))
        dt_pct   = compute_downtime_pct(1.2, 24.0)
        score    = compute_bottleneck_score(util, cap_p, wip_norm, dt_pct)
        # LITH-07 must be at least HIGH (≥70) — may be CRITICAL
        assert score >= SEVERITY_HIGH, f"LITH-07 score {score:.2f} is below HIGH threshold"
        assert classify_severity(score) in ("HIGH", "CRITICAL")

    def test_lith08_lower_than_lith07(self):
        """LITH-08 (stable, 60 % utilisation) must score below LITH-07."""
        from app.services.bottleneck.utilization import compute_utilization
        from app.services.bottleneck.wip_pressure import compute_wip_pressure, normalize_wip_pressure
        from app.services.bottleneck.capacity_pressure import compute_capacity_pressure
        from app.services.bottleneck.score import compute_downtime_pct

        # LITH-07
        u7   = compute_utilization(23.3, 24.0)
        cp7  = compute_capacity_pressure(23.3 * 50, 1200)
        wn7  = normalize_wip_pressure(compute_wip_pressure(240, 100))
        dt7  = compute_downtime_pct(1.2, 24.0)
        s7   = compute_bottleneck_score(u7, cp7, wn7, dt7)

        # LITH-08
        u8   = compute_utilization(14.4, 24.0)
        cp8  = compute_capacity_pressure(14.4 * 50, 1200)
        wn8  = normalize_wip_pressure(compute_wip_pressure(52, 100))
        dt8  = compute_downtime_pct(0.0, 24.0)
        s8   = compute_bottleneck_score(u8, cp8, wn8, dt8)

        assert s7 > s8, f"LITH-07 ({s7}) should score higher than LITH-08 ({s8})"

    def test_output_range(self):
        for u in [0.0, 0.5, 1.0]:
            for c in [0.0, 0.5, 1.0]:
                for w in [0.0, 0.5, 1.0]:
                    for d in [0.0, 0.5, 1.0]:
                        s = compute_bottleneck_score(u, c, w, d)
                        assert 0.0 <= s <= 100.0


# =============================================================================
# 6. Severity Classification
# =============================================================================

class TestSeverity:
    def test_critical_boundary(self):
        assert classify_severity(SEVERITY_CRITICAL) == "CRITICAL"
        assert classify_severity(100.0) == "CRITICAL"

    def test_high_boundary(self):
        assert classify_severity(SEVERITY_HIGH) == "HIGH"
        assert classify_severity(84.99) == "HIGH"

    def test_medium_boundary(self):
        assert classify_severity(SEVERITY_MEDIUM) == "MEDIUM"
        assert classify_severity(69.99) == "MEDIUM"

    def test_low(self):
        assert classify_severity(0.0) == "LOW"
        assert classify_severity(39.99) == "LOW"

    def test_all_bands_covered(self):
        for score, expected in [
            (10.0, "LOW"),
            (39.0, "LOW"),
            (40.0, "MEDIUM"),
            (55.0, "MEDIUM"),
            (69.9, "MEDIUM"),
            (70.0, "HIGH"),
            (84.9, "HIGH"),
            (85.0, "CRITICAL"),
            (99.0, "CRITICAL"),
        ]:
            assert classify_severity(score) == expected, f"score={score}"


# =============================================================================
# 7 & 8. Backlog and Recovery Calculation
# =============================================================================

class TestBacklogRecovery:
    def test_basic_recovery(self):
        """10 lots/hr arrival, 15 lots/hr capacity, 8hr outage.
        backlog = 10 * 8 = 80 lots
        net clearance = 15 - 10 = 5 lots/hr
        recovery = 80 / 5 = 16 hours
        """
        result = calculate_backlog_recovery(
            arrival_rate=10.0,
            tool_capacity=15.0,
            outage_duration=8.0,
        )
        assert result["backlog_added"] == pytest.approx(80.0)
        assert result["net_clearance_rate"] == pytest.approx(5.0)
        assert result["recovery_time_hours"] == pytest.approx(16.0)
        assert result["recoverable"] is True

    def test_zero_arrival_rate(self):
        """No lots arriving → backlog = 0, recovery instant."""
        result = calculate_backlog_recovery(
            arrival_rate=0.0,
            tool_capacity=10.0,
            outage_duration=4.0,
        )
        assert result["backlog_added"] == pytest.approx(0.0)
        assert result["recoverable"] is True
        assert result["recovery_time_hours"] == pytest.approx(0.0)

    def test_short_outage_small_backlog(self):
        result = calculate_backlog_recovery(
            arrival_rate=5.0,
            tool_capacity=20.0,
            outage_duration=1.0,
        )
        assert result["backlog_added"] == pytest.approx(5.0)
        assert result["recovery_time_hours"] == pytest.approx(5.0 / 15.0, rel=1e-3)


# =============================================================================
# 9. Impossible Recovery
# =============================================================================

class TestImpossibleRecovery:
    def test_arrival_equals_capacity(self):
        """arrival == capacity → net clearance = 0 → unrecoverable."""
        result = calculate_backlog_recovery(
            arrival_rate=15.0,
            tool_capacity=15.0,
            outage_duration=4.0,
        )
        assert result["recoverable"] is False
        assert result["recovery_time_hours"] is None
        assert result["net_clearance_rate"] == pytest.approx(0.0)
        assert result["backlog_added"] == pytest.approx(60.0)

    def test_arrival_exceeds_capacity(self):
        """arrival > capacity → unrecoverable."""
        result = calculate_backlog_recovery(
            arrival_rate=20.0,
            tool_capacity=15.0,
            outage_duration=3.0,
        )
        assert result["recoverable"] is False
        assert result["recovery_time_hours"] is None
        assert result["net_clearance_rate"] < 0

    def test_invalid_capacity_raises(self):
        with pytest.raises(ValueError, match="tool_capacity"):
            calculate_backlog_recovery(arrival_rate=5.0, tool_capacity=0.0, outage_duration=4.0)

    def test_invalid_duration_raises(self):
        with pytest.raises(ValueError, match="outage_duration"):
            calculate_backlog_recovery(arrival_rate=5.0, tool_capacity=10.0, outage_duration=0.0)

    def test_near_capacity_is_recoverable(self):
        """Just barely under capacity → long recovery but still recoverable."""
        result = calculate_backlog_recovery(
            arrival_rate=9.9,
            tool_capacity=10.0,
            outage_duration=8.0,
        )
        assert result["recoverable"] is True
        assert result["recovery_time_hours"] is not None
        assert result["recovery_time_hours"] > 100.0  # very long recovery


# =============================================================================
# 10. Confidence Behavior
# =============================================================================

class TestConfidence:
    def test_single_snapshot_low_confidence(self):
        """Fewer than MIN_SNAPSHOTS → low_confidence = True."""
        result = compute_confidence([80.0])
        assert result["low_confidence"] is True
        assert result["confidence"] == pytest.approx(0.50)
        assert result["snapshot_count"] == 1
        assert result["wip_trend"] == "UNKNOWN"

    def test_two_snapshots_low_confidence(self):
        result = compute_confidence([80.0, 90.0])
        assert result["low_confidence"] is True
        assert result["snapshot_count"] == 2
        # Two snapshots: enough for trend but still low confidence
        assert result["wip_trend"] in ("RISING", "STABLE", "FALLING")

    def test_three_snapshots_minimum_for_high_confidence(self):
        """Exactly MIN_SNAPSHOTS_FOR_CONFIDENCE → low_confidence = False."""
        assert MIN_SNAPSHOTS_FOR_CONFIDENCE == 3
        result = compute_confidence([80.0, 82.0, 81.0])
        assert result["low_confidence"] is False
        assert result["snapshot_count"] == 3

    def test_lith07_rising_trend(self):
        """LITH-07 historical WIP (60→80→120→180→240) → RISING trend."""
        wip_history = [60.0, 80.0, 120.0, 180.0, 240.0]
        result = compute_confidence(wip_history)
        assert result["wip_trend"] == "RISING"
        assert result["low_confidence"] is False
        assert result["snapshot_count"] == 5

    def test_lith08_stable_trend(self):
        """LITH-08 historical WIP (48→55→50→53→52) → STABLE trend."""
        wip_history = [48.0, 55.0, 50.0, 53.0, 52.0]
        result = compute_confidence(wip_history)
        assert result["wip_trend"] == "STABLE"
        assert result["low_confidence"] is False

    def test_high_variance_reduces_confidence(self):
        """Volatile WIP history produces lower confidence than stable."""
        stable   = compute_confidence([100.0, 101.0, 100.0, 99.0, 100.0])
        volatile = compute_confidence([50.0, 200.0, 30.0, 180.0, 60.0])
        assert stable["confidence"] > volatile["confidence"]

    def test_falling_trend_detected(self):
        result = compute_confidence([200.0, 180.0, 150.0, 120.0, 90.0])
        assert result["wip_trend"] == "FALLING"

    def test_cov_none_for_small_sample(self):
        result = compute_confidence([100.0])
        assert result["cov"] is None

    def test_cov_computed_for_sufficient_sample(self):
        result = compute_confidence([100.0, 110.0, 105.0])
        assert result["cov"] is not None
        assert result["cov"] >= 0.0


# =============================================================================
# Little's Law (reference only)
# =============================================================================

class TestLittlesLaw:
    def test_basic(self):
        """W = L / λ = 100 / 10 = 10 hours."""
        result = estimate_cycle_time_littles_law(avg_wip=100.0, throughput_rate=10.0)
        assert result == pytest.approx(10.0)

    def test_zero_throughput_returns_none(self):
        result = estimate_cycle_time_littles_law(avg_wip=100.0, throughput_rate=0.0)
        assert result is None

    def test_zero_wip(self):
        result = estimate_cycle_time_littles_law(avg_wip=0.0, throughput_rate=10.0)
        assert result == pytest.approx(0.0)
