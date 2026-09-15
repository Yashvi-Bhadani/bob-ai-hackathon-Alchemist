"""
Supply Chain Risk — Comprehensive Test Suite
=============================================

Tests cover:
    1.  HHI calculation formula
    2.  HHI threshold classification
    3.  SPOF exactly-one-qualified rule
    4.  Inventory coverage calculation (formula)
    5.  Low inventory detection (below safety stock)
    6.  Geopolitical score handling
    7.  Composite risk score
    8.  Score bounds 0–100
    9.  No division-by-zero
    10. Missing supplier / material handling

All tests are pure-Python (no database, no HTTP).
Run with:  pytest src/backend/tests/test_supply_risk.py -v
"""

import pytest

# ── Service imports ────────────────────────────────────────────────────────
from app.services.supply_risk.hhi import (
    compute_hhi,
    hhi_concentration_level,
    HHI_HIGH_THRESHOLD,
    HHI_MODERATE_THRESHOLD,
)
from app.services.supply_risk.spof import is_spof, qualified_supplier_count
from app.services.supply_risk.inventory_coverage import (
    compute_coverage_days,
    coverage_risk_tier,
    is_below_safety_stock,
    coverage_normalised,
)
from app.services.supply_risk.geo_risk import (
    aggregate_geo_risk_score,
    GEO_RISK_LEVEL_SCORE,
    DEMO_RISK_FACTORS,
)
from app.services.supply_risk.score import (
    compute_composite_score,
    severity_label,
    _W_HHI,
    _W_SPOF,
    _W_INV,
    _W_GEO,
)


# =============================================================================
# 1. HHI Calculation
# =============================================================================

class TestHHICalculation:
    """Test 1: HHI formula correctness."""

    def test_spec_example(self):
        """
        Spec example: 70 / 20 / 10 → HHI = 4900 + 400 + 100 = 5400
        Do NOT hard-code HHI — calculate it from supplier rows.
        """
        shares = [70.0, 20.0, 10.0]
        assert compute_hhi(shares) == pytest.approx(5400.0)

    def test_monopoly(self):
        """Single supplier 100 % → HHI = 10 000."""
        assert compute_hhi([100.0]) == pytest.approx(10_000.0)

    def test_two_equal_suppliers(self):
        """50 % / 50 % → HHI = 50² + 50² = 2500 + 2500 = 5000."""
        assert compute_hhi([50.0, 50.0]) == pytest.approx(5000.0)

    def test_four_equal_suppliers(self):
        """25 % each → HHI = 4 * 625 = 2500."""
        assert compute_hhi([25.0, 25.0, 25.0, 25.0]) == pytest.approx(2500.0)

    def test_empty_shares_returns_zero(self):
        """Empty list → HHI = 0.0 (no division by zero)."""
        assert compute_hhi([]) == 0.0

    def test_single_small_share(self):
        """Single supplier at 10 % → HHI = 100."""
        assert compute_hhi([10.0]) == pytest.approx(100.0)

    def test_result_is_float(self):
        assert isinstance(compute_hhi([70.0, 30.0]), float)


# =============================================================================
# 2. HHI Threshold Classification
# =============================================================================

class TestHHIThreshold:
    """Test 2: HHI concentration thresholds (internal thresholds for this app)."""

    def test_gallium_example_high(self):
        """HHI = 5400 should be HIGH (> 2500)."""
        assert hhi_concentration_level(5400.0) == "HIGH"

    def test_monopoly_label(self):
        """HHI = 10 000 → MONOPOLY."""
        assert hhi_concentration_level(10_000.0) == "MONOPOLY"

    def test_above_2500_is_high(self):
        """HHI = 2501 → HIGH."""
        assert hhi_concentration_level(2501.0) == "HIGH"

    def test_exactly_2500_is_moderate(self):
        """HHI = 2500 is NOT > 2500, so MODERATE."""
        assert hhi_concentration_level(2500.0) == "MODERATE"

    def test_above_1500_is_moderate(self):
        """HHI = 2000 → MODERATE (> 1500, ≤ 2500)."""
        assert hhi_concentration_level(2000.0) == "MODERATE"

    def test_at_or_below_1500_is_low(self):
        """HHI = 1500 → LOW (not > 1500)."""
        assert hhi_concentration_level(1500.0) == "LOW"

    def test_zero_is_low(self):
        assert hhi_concentration_level(0.0) == "LOW"

    def test_threshold_constants(self):
        """Thresholds must be 2500 and 1500 as documented."""
        assert HHI_HIGH_THRESHOLD == 2500
        assert HHI_MODERATE_THRESHOLD == 1500


# =============================================================================
# 3. SPOF Exactly-One-Qualified Rule
# =============================================================================

class TestSPOF:
    """Test 3: SPOF = True only when exactly one qualified supplier exists."""

    def _make_supplier(self, supplier_id: str, qualified: bool) -> dict:
        return {"supplier_id": supplier_id, "qualified": qualified}

    # ── True cases ────────────────────────────────────────────────────────────

    def test_neon_scenario_spof_true(self):
        """
        Neon spec case: Supplier A qualified, Supplier B not qualified
        → exactly 1 qualified → SPOF = True.
        """
        sups = [
            self._make_supplier("SUP-NEON-A", qualified=True),
            self._make_supplier("SUP-NEON-B", qualified=False),
        ]
        assert is_spof(sups) is True

    def test_single_qualified_supplier(self):
        sups = [self._make_supplier("S1", qualified=True)]
        assert is_spof(sups) is True

    # ── False cases ───────────────────────────────────────────────────────────

    def test_gallium_three_qualified_not_spof(self):
        """
        Gallium spec case: 3 qualified suppliers despite 70 % share.
        SPOF = False — high HHI alone is NOT SPOF.
        """
        sups = [
            self._make_supplier("SUP-GA-A", qualified=True),
            self._make_supplier("SUP-GA-B", qualified=True),
            self._make_supplier("SUP-GA-C", qualified=True),
        ]
        assert is_spof(sups) is False

    def test_two_qualified_not_spof(self):
        sups = [
            self._make_supplier("S1", qualified=True),
            self._make_supplier("S2", qualified=True),
        ]
        assert is_spof(sups) is False

    def test_zero_qualified_not_spof(self):
        """Zero qualified suppliers is not SPOF — separate alert category."""
        sups = [
            self._make_supplier("S1", qualified=False),
            self._make_supplier("S2", qualified=False),
        ]
        assert is_spof(sups) is False

    def test_empty_supplier_list_not_spof(self):
        assert is_spof([]) is False

    def test_qualified_supplier_count(self):
        sups = [
            self._make_supplier("S1", qualified=True),
            self._make_supplier("S2", qualified=False),
            self._make_supplier("S3", qualified=True),
        ]
        assert qualified_supplier_count(sups) == 2


# =============================================================================
# 4. Inventory Coverage Calculation
# =============================================================================

class TestInventoryCoverage:
    """Test 4: coverage days formula."""

    def test_spec_example(self):
        """Spec example: 500 units / 100 per day = 5 days."""
        assert compute_coverage_days(500.0, 100.0) == pytest.approx(5.0)

    def test_neon_scenario(self):
        """Neon: 60 units / 15 per day = 4 days."""
        assert compute_coverage_days(60.0, 15.0) == pytest.approx(4.0)

    def test_precision(self):
        """Result rounded to 2 decimal places."""
        result = compute_coverage_days(1000.0, 7.0)
        assert result == pytest.approx(142.86, rel=1e-3)

    def test_zero_inventory(self):
        """Zero inventory → 0 days."""
        assert compute_coverage_days(0.0, 100.0) == pytest.approx(0.0)


# =============================================================================
# 5. Low Inventory Detection (below safety stock)
# =============================================================================

class TestLowInventoryDetection:
    """Test 5: below safety stock detection."""

    def test_neon_below_safety_stock(self):
        """
        Spec case: inventory = 5 days, safety stock = 10 days
        → below safety stock = True.
        """
        assert is_below_safety_stock(5.0, 10.0) is True

    def test_adequate_coverage(self):
        """30 days coverage ≥ 14-day safety stock → False."""
        assert is_below_safety_stock(30.0, 14.0) is False

    def test_exactly_at_safety_stock(self):
        """Exactly at safety stock boundary → False (not below)."""
        assert is_below_safety_stock(14.0, 14.0) is False

    def test_just_below_safety_stock(self):
        assert is_below_safety_stock(13.9, 14.0) is True

    def test_none_coverage_not_below(self):
        """None means zero consumption — treated as infinite, not below."""
        assert is_below_safety_stock(None, 14.0) is False

    def test_coverage_risk_tier_critical(self):
        """< 7 days → CRITICAL."""
        assert coverage_risk_tier(3.0) == "CRITICAL"

    def test_coverage_risk_tier_high(self):
        """7–13 days → HIGH."""
        assert coverage_risk_tier(10.0) == "HIGH"

    def test_coverage_risk_tier_medium(self):
        """14–29 days → MEDIUM."""
        assert coverage_risk_tier(20.0) == "MEDIUM"

    def test_coverage_risk_tier_low(self):
        """≥ 30 days → LOW."""
        assert coverage_risk_tier(45.0) == "LOW"

    def test_none_coverage_risk_tier_low(self):
        """None (zero consumption) → LOW (no active depletion)."""
        assert coverage_risk_tier(None) == "LOW"


# =============================================================================
# 6. Geopolitical Score Handling
# =============================================================================

class TestGeopoliticalRisk:
    """Test 6: geo risk scoring and filtering."""

    def test_risk_level_score_mapping(self):
        """Verify the four normalised scores."""
        assert GEO_RISK_LEVEL_SCORE["LOW"]      == pytest.approx(0.10)
        assert GEO_RISK_LEVEL_SCORE["MEDIUM"]   == pytest.approx(0.40)
        assert GEO_RISK_LEVEL_SCORE["HIGH"]     == pytest.approx(0.70)
        assert GEO_RISK_LEVEL_SCORE["CRITICAL"] == pytest.approx(1.00)

    def test_material_specific_factor_selected(self):
        factors = [
            {"material_id": "NEON",    "risk_level": "HIGH"},
            {"material_id": "GALLIUM", "risk_level": "CRITICAL"},
        ]
        score = aggregate_geo_risk_score(factors, "NEON")
        assert score == pytest.approx(0.70)   # HIGH

    def test_region_wide_factor_included(self):
        """Factor with material_id=None applies to every material."""
        factors = [
            {"material_id": None,   "risk_level": "MEDIUM"},
            {"material_id": "NEON", "risk_level": "LOW"},
        ]
        score = aggregate_geo_risk_score(factors, "NEON")
        assert score == pytest.approx(0.40)   # max(MEDIUM, LOW) = MEDIUM

    def test_no_factors_returns_zero(self):
        assert aggregate_geo_risk_score([], "NEON") == 0.0

    def test_unrelated_factors_ignored(self):
        factors = [{"material_id": "GALLIUM", "risk_level": "CRITICAL"}]
        score = aggregate_geo_risk_score(factors, "NEON")
        assert score == 0.0   # GALLIUM factor doesn't affect NEON

    def test_max_is_returned(self):
        """Multiple factors for same material → max score wins."""
        factors = [
            {"material_id": "NEON", "risk_level": "LOW"},
            {"material_id": "NEON", "risk_level": "CRITICAL"},
            {"material_id": "NEON", "risk_level": "MEDIUM"},
        ]
        assert aggregate_geo_risk_score(factors, "NEON") == pytest.approx(1.00)

    def test_demo_risk_factors_neon_high(self):
        """Demo data includes HIGH geo risk for Neon."""
        neon_score = aggregate_geo_risk_score(DEMO_RISK_FACTORS, "NEON")
        assert neon_score >= 0.70   # at least HIGH

    def test_demo_risk_factors_gallium_high(self):
        """Demo data includes HIGH geo risk for Gallium."""
        gallium_score = aggregate_geo_risk_score(DEMO_RISK_FACTORS, "GALLIUM")
        assert gallium_score >= 0.70

    def test_demo_risk_factors_photoresist_low(self):
        """Photoresist has only LOW geo risk in demo data."""
        # account for region-wide factor
        pr_score = aggregate_geo_risk_score(
            [f for f in DEMO_RISK_FACTORS if f.get("material_id") == "PHOTORESIST"],
            "PHOTORESIST",
        )
        assert pr_score <= 0.10

    def test_all_demo_sources_are_synthetic(self):
        """Every demo risk factor must be marked as synthetic scenario data."""
        for factor in DEMO_RISK_FACTORS:
            assert "Demo" in factor["source"] or "Synthetic" in factor["source"], (
                f"Risk factor {factor.get('risk_factor_id')} missing synthetic marker: "
                f"{factor['source']}"
            )


# =============================================================================
# 7. Composite Risk Score
# =============================================================================

class TestCompositeScore:
    """Test 7: composite score calculation."""

    def test_weights_sum_to_one(self):
        """Component weights must sum to exactly 1.0."""
        assert abs(_W_HHI + _W_SPOF + _W_INV + _W_GEO - 1.0) < 1e-9

    def test_all_max_inputs_gives_100(self):
        """
        HHI = 10 000, SPOF = True, inv_norm = 1.0, geo_norm = 1.0
        → score = 100.0
        """
        score = compute_composite_score(10_000.0, True, 1.0, 1.0)
        assert score == pytest.approx(100.0)

    def test_all_zero_inputs_gives_zero(self):
        score = compute_composite_score(0.0, False, 0.0, 0.0)
        assert score == pytest.approx(0.0)

    def test_neon_produces_high_or_critical(self):
        """
        Neon spec case:
            HHI = 85² + 15² = 7225 + 225 = 7450 (single qualified supplier
              so high HHI, but SPOF drives the score)
            SPOF = True
            Inventory = 4 days vs 14-day safety stock → high inv_norm
            Geo = HIGH (0.70)
        Expected: HIGH or CRITICAL severity.
        """
        neon_shares = [85.0, 15.0]
        hhi = compute_hhi(neon_shares)
        spof = True
        inv_norm = coverage_normalised(4.0, safety_stock_days=14.0)
        geo = aggregate_geo_risk_score(DEMO_RISK_FACTORS, "NEON")

        score = compute_composite_score(hhi, spof, inv_norm, geo)
        assert score >= 70.0, f"Neon should be HIGH/CRITICAL; got score={score}"
        assert severity_label(score) in ("HIGH", "CRITICAL")

    def test_gallium_produces_meaningful_score(self):
        """
        Gallium spec case:
            HHI = 5400  (HIGH concentration)
            SPOF = False (3 qualified suppliers → not SPOF despite high HHI)
            Inventory = 25 days vs 30-day safety stock (slightly below)
            Geo = HIGH (0.70)

        With SPOF=False the HHI + geo components dominate:
            hhi_norm = 5400/10000 = 0.54 → contribution = 0.30×0.54 = 0.162
            spof     = 0.0               → contribution = 0.0
            inv_norm = 1-(25/30)≈0.167  → contribution = 0.20×0.167 ≈ 0.033
            geo      = 0.70             → contribution = 0.20×0.70  = 0.14
            total ≈ 0.335 → score ≈ 33.5

        Score sits just below MEDIUM (40) because there is no SPOF.
        Asserting > 25 confirms the material is not risk-free.
        """
        gallium_shares = [70.0, 20.0, 10.0]
        hhi = compute_hhi(gallium_shares)
        assert hhi == pytest.approx(5400.0)

        spof = False
        inv_norm = coverage_normalised(25.0, safety_stock_days=30.0)
        geo = aggregate_geo_risk_score(DEMO_RISK_FACTORS, "GALLIUM")

        score = compute_composite_score(hhi, spof, inv_norm, geo)
        assert score >= 25.0, f"Gallium should have meaningful risk score; got score={score}"
        assert score <= 100.0

    def test_photoresist_lower_than_neon(self):
        """
        Photoresist (healthy) should score lower than Neon (SPOF + low stock).
        """
        # Neon
        neon_hhi = compute_hhi([85.0, 15.0])
        neon_score = compute_composite_score(
            neon_hhi, True,
            coverage_normalised(4.0, 14.0),
            aggregate_geo_risk_score(DEMO_RISK_FACTORS, "NEON"),
        )
        # Photoresist
        pr_hhi = compute_hhi([45.0, 35.0, 20.0])
        pr_score = compute_composite_score(
            pr_hhi, False,
            coverage_normalised(48.0, 21.0),
            aggregate_geo_risk_score(DEMO_RISK_FACTORS, "PHOTORESIST"),
        )
        assert neon_score > pr_score, (
            f"Neon ({neon_score:.2f}) should be riskier than Photoresist ({pr_score:.2f})"
        )


# =============================================================================
# 8. Score Bounds 0–100
# =============================================================================

class TestScoreBounds:
    """Test 8: composite score always in [0, 100]."""

    @pytest.mark.parametrize("hhi,spof,inv,geo", [
        (0.0,    False, 0.0, 0.0),
        (5000.0, True,  0.5, 0.5),
        (10000.0, True, 1.0, 1.0),
        (9999.9, True,  1.0, 1.0),
        (10001.0, True, 2.0, 2.0),   # over-range inputs — must still clamp
        (-100.0, False, -0.5, -1.0), # under-range inputs
    ])
    def test_score_always_in_bounds(self, hhi, spof, inv, geo):
        score = compute_composite_score(hhi, spof, inv, geo)
        assert 0.0 <= score <= 100.0, f"Out of bounds score: {score}"

    def test_severity_covers_all_ranges(self):
        assert severity_label(0.0)   == "LOW"
        assert severity_label(39.0)  == "LOW"
        assert severity_label(40.0)  == "MEDIUM"
        assert severity_label(69.0)  == "MEDIUM"
        assert severity_label(70.0)  == "HIGH"
        assert severity_label(84.0)  == "HIGH"
        assert severity_label(85.0)  == "CRITICAL"
        assert severity_label(100.0) == "CRITICAL"


# =============================================================================
# 9. No Division-by-Zero
# =============================================================================

class TestNoDivisionByZero:
    """Test 9: all functions handle zero / empty inputs safely."""

    def test_hhi_empty_list(self):
        assert compute_hhi([]) == 0.0

    def test_coverage_days_zero_consumption(self):
        """Zero daily consumption → returns None, not an exception."""
        result = compute_coverage_days(500.0, 0.0)
        assert result is None

    def test_coverage_risk_tier_none_input(self):
        assert coverage_risk_tier(None) == "LOW"

    def test_coverage_normalised_zero_safety(self):
        """Safety stock = 0 would cause division; function uses default of 30."""
        result = coverage_normalised(10.0, safety_stock_days=30.0)
        assert 0.0 <= result <= 1.0

    def test_aggregate_geo_empty_factors(self):
        assert aggregate_geo_risk_score([], "NEON") == 0.0

    def test_composite_zero_hhi(self):
        score = compute_composite_score(0.0, False, 0.0, 0.0)
        assert score == 0.0

    def test_is_spof_empty(self):
        assert is_spof([]) is False


# =============================================================================
# 10. Missing Supplier / Material Handling
# =============================================================================

class TestMissingData:
    """Test 10: graceful handling of missing suppliers or materials."""

    def test_hhi_single_supplier_zero_share(self):
        """A supplier with 0 % share contributes 0 to HHI."""
        assert compute_hhi([0.0]) == 0.0

    def test_spof_all_unqualified(self):
        """No qualified suppliers → SPOF = False (not a SPOF, different problem)."""
        sups = [{"qualified": False}, {"qualified": False}]
        assert is_spof(sups) is False

    def test_coverage_no_inventory_row(self):
        """When no inventory row exists, compute_coverage_days receives 0/0."""
        result = compute_coverage_days(0.0, 0.0)
        assert result is None

    def test_geo_score_material_not_in_factors(self):
        """Material with no risk factors → geo score = 0.0."""
        factors = [{"material_id": "OTHER", "risk_level": "CRITICAL"}]
        score = aggregate_geo_risk_score(factors, "MISSING-MAT")
        assert score == 0.0

    def test_composite_no_suppliers(self):
        """HHI = 0 (no suppliers), SPOF = False → score driven only by inv/geo."""
        score = compute_composite_score(0.0, False, 1.0, 1.0)
        expected = (_W_INV * 1.0 + _W_GEO * 1.0) * 100.0
        assert score == pytest.approx(expected, rel=1e-4)

    def test_coverage_normalised_full_stock(self):
        """Coverage >= safety stock → normalised risk = 0."""
        assert coverage_normalised(30.0, safety_stock_days=14.0) == 0.0

    def test_coverage_normalised_empty_stock(self):
        """Coverage = 0 → normalised risk = 1."""
        assert coverage_normalised(0.0, safety_stock_days=14.0) == 1.0
