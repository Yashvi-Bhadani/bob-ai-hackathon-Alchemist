"""
Demo / fallback seed data for the supply risk module.
======================================================

All data here is SYNTHETIC SCENARIO DATA created for hackathon demonstration.
⚠  No real supplier, pricing, or geopolitical fact is represented.
⚠  All geopolitical risk entries are clearly marked as Demo/Synthetic Scenario.

This module is imported by the API modules when the database is unavailable
(offline / demo mode).  It mirrors the schema defined in 002_supply.sql and the
seed rows that would be inserted into the live database.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# SUPPLIERS
# ---------------------------------------------------------------------------
DEMO_SUPPLIERS: list[dict] = [
    # --- Neon suppliers ---
    {
        "supplier_id": "SUP-NEON-A",
        "supplier_name": "NobleGas Solutions (Demo)",
        "country": "Ukraine",          # synthetic — no verified claim
        "region": "Eastern Europe",
        "qualification_status": "QUALIFIED",
    },
    {
        "supplier_id": "SUP-NEON-B",
        "supplier_name": "CryoSource Ltd (Demo)",
        "country": "Russia",           # synthetic — no verified claim
        "region": "Eastern Europe",
        "qualification_status": "PENDING",   # not qualified → triggers SPOF
    },
    # --- Gallium suppliers ---
    {
        "supplier_id": "SUP-GA-A",
        "supplier_name": "AsiaMetal Primary (Demo)",
        "country": "China",            # synthetic — no verified claim
        "region": "Asia-Pacific",
        "qualification_status": "QUALIFIED",
    },
    {
        "supplier_id": "SUP-GA-B",
        "supplier_name": "EuroGallium GmbH (Demo)",
        "country": "Germany",
        "region": "Europe",
        "qualification_status": "QUALIFIED",
    },
    {
        "supplier_id": "SUP-GA-C",
        "supplier_name": "AmeriMin Corp (Demo)",
        "country": "United States",
        "region": "North America",
        "qualification_status": "QUALIFIED",
    },
    # --- Germanium suppliers ---
    {
        "supplier_id": "SUP-GE-A",
        "supplier_name": "GeoChem Asia (Demo)",
        "country": "China",            # synthetic
        "region": "Asia-Pacific",
        "qualification_status": "QUALIFIED",
    },
    {
        "supplier_id": "SUP-GE-B",
        "supplier_name": "SpecialtyMetals EU (Demo)",
        "country": "Belgium",
        "region": "Europe",
        "qualification_status": "QUALIFIED",
    },
    # --- Photoresist suppliers ---
    {
        "supplier_id": "SUP-PR-A",
        "supplier_name": "AlphaResist JP (Demo)",
        "country": "Japan",
        "region": "Asia-Pacific",
        "qualification_status": "QUALIFIED",
    },
    {
        "supplier_id": "SUP-PR-B",
        "supplier_name": "BetaChem KR (Demo)",
        "country": "South Korea",
        "region": "Asia-Pacific",
        "qualification_status": "QUALIFIED",
    },
    {
        "supplier_id": "SUP-PR-C",
        "supplier_name": "ChemPro US (Demo)",
        "country": "United States",
        "region": "North America",
        "qualification_status": "QUALIFIED",
    },
]

# ---------------------------------------------------------------------------
# MATERIALS
# ---------------------------------------------------------------------------
DEMO_MATERIALS: list[dict] = [
    {
        "material_id": "NEON",
        "material_name": "Neon Gas",
        "material_category": "Gas",
        "criticality": "CRITICAL",
    },
    {
        "material_id": "GALLIUM",
        "material_name": "Gallium Metal",
        "material_category": "Metal",
        "criticality": "HIGH",
    },
    {
        "material_id": "GERMANIUM",
        "material_name": "Germanium Metal",
        "material_category": "Metal",
        "criticality": "HIGH",
    },
    {
        "material_id": "PHOTORESIST",
        "material_name": "EUV Photoresist",
        "material_category": "Photoresist",
        "criticality": "CRITICAL",
    },
]

# ---------------------------------------------------------------------------
# MATERIAL SUPPLIERS (supply_share_pct represents THIS FAB's sourcing)
# ---------------------------------------------------------------------------
DEMO_MATERIAL_SUPPLIERS: list[dict] = [
    # ── NEON ──────────────────────────────────────────────────────────────────
    # Only SUP-NEON-A is qualified → SPOF = True
    {
        "material_id": "NEON",
        "supplier_id": "SUP-NEON-A",
        "supplier_name": "NobleGas Solutions (Demo)",
        "supply_share_pct": 85.0,
        "qualified": True,
        "lead_time_days": 45,
        "country": "Ukraine",
        "region": "Eastern Europe",
    },
    {
        "material_id": "NEON",
        "supplier_id": "SUP-NEON-B",
        "supplier_name": "CryoSource Ltd (Demo)",
        "supply_share_pct": 15.0,
        "qualified": False,           # ← PENDING, so only 1 qualified → SPOF
        "lead_time_days": 60,
        "country": "Russia",
        "region": "Eastern Europe",
    },
    # ── GALLIUM ───────────────────────────────────────────────────────────────
    # HHI = 70² + 20² + 10² = 4900 + 400 + 100 = 5400  → HIGH concentration
    {
        "material_id": "GALLIUM",
        "supplier_id": "SUP-GA-A",
        "supplier_name": "AsiaMetal Primary (Demo)",
        "supply_share_pct": 70.0,
        "qualified": True,
        "lead_time_days": 30,
        "country": "China",
        "region": "Asia-Pacific",
    },
    {
        "material_id": "GALLIUM",
        "supplier_id": "SUP-GA-B",
        "supplier_name": "EuroGallium GmbH (Demo)",
        "supply_share_pct": 20.0,
        "qualified": True,
        "lead_time_days": 25,
        "country": "Germany",
        "region": "Europe",
    },
    {
        "material_id": "GALLIUM",
        "supplier_id": "SUP-GA-C",
        "supplier_name": "AmeriMin Corp (Demo)",
        "supply_share_pct": 10.0,
        "qualified": True,
        "lead_time_days": 20,
        "country": "United States",
        "region": "North America",
    },
    # ── GERMANIUM ─────────────────────────────────────────────────────────────
    {
        "material_id": "GERMANIUM",
        "supplier_id": "SUP-GE-A",
        "supplier_name": "GeoChem Asia (Demo)",
        "supply_share_pct": 60.0,
        "qualified": True,
        "lead_time_days": 35,
        "country": "China",
        "region": "Asia-Pacific",
    },
    {
        "material_id": "GERMANIUM",
        "supplier_id": "SUP-GE-B",
        "supplier_name": "SpecialtyMetals EU (Demo)",
        "supply_share_pct": 40.0,
        "qualified": True,
        "lead_time_days": 28,
        "country": "Belgium",
        "region": "Europe",
    },
    # ── PHOTORESIST ───────────────────────────────────────────────────────────
    # Multiple qualified suppliers — healthier supply posture (contrast case)
    {
        "material_id": "PHOTORESIST",
        "supplier_id": "SUP-PR-A",
        "supplier_name": "AlphaResist JP (Demo)",
        "supply_share_pct": 45.0,
        "qualified": True,
        "lead_time_days": 28,
        "country": "Japan",
        "region": "Asia-Pacific",
    },
    {
        "material_id": "PHOTORESIST",
        "supplier_id": "SUP-PR-B",
        "supplier_name": "BetaChem KR (Demo)",
        "supply_share_pct": 35.0,
        "qualified": True,
        "lead_time_days": 21,
        "country": "South Korea",
        "region": "Asia-Pacific",
    },
    {
        "material_id": "PHOTORESIST",
        "supplier_id": "SUP-PR-C",
        "supplier_name": "ChemPro US (Demo)",
        "supply_share_pct": 20.0,
        "qualified": True,
        "lead_time_days": 14,
        "country": "United States",
        "region": "North America",
    },
]

# ---------------------------------------------------------------------------
# MATERIAL INVENTORY
# ---------------------------------------------------------------------------
DEMO_INVENTORY: list[dict] = [
    # ── NEON: LOW coverage relative to safety stock ───────────────────────────
    {
        "material_id": "NEON",
        "material_name": "Neon Gas",
        "current_inventory_units": 60.0,     # units
        "daily_consumption_units": 15.0,     # → 4 days coverage
        "safety_stock_days": 14.0,
    },
    # ── GALLIUM: moderate coverage ────────────────────────────────────────────
    {
        "material_id": "GALLIUM",
        "material_name": "Gallium Metal",
        "current_inventory_units": 500.0,
        "daily_consumption_units": 20.0,     # → 25 days
        "safety_stock_days": 30.0,
    },
    # ── GERMANIUM: adequate coverage ──────────────────────────────────────────
    {
        "material_id": "GERMANIUM",
        "material_name": "Germanium Metal",
        "current_inventory_units": 900.0,
        "daily_consumption_units": 18.0,     # → 50 days
        "safety_stock_days": 30.0,
    },
    # ── PHOTORESIST: healthy coverage ─────────────────────────────────────────
    {
        "material_id": "PHOTORESIST",
        "material_name": "EUV Photoresist",
        "current_inventory_units": 1200.0,
        "daily_consumption_units": 25.0,     # → 48 days
        "safety_stock_days": 21.0,
    },
]
