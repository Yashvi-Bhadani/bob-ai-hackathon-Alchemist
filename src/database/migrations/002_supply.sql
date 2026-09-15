-- =============================================================================
-- Migration 002: Supply Chain & Geopolitical Risk Tables
-- Member 2 — feature/supply-risk
-- Description: Suppliers, materials, inventory, geopolitical risk factors,
--              process-material links, and pre-computed supply risk results.
--
-- Run AFTER migration 001_fab.sql (references fab_processes).
-- All demo seed data is in seed.sql or the Python service demo fallback.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. suppliers
--    Tracks every known material supplier.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id          VARCHAR(30)   NOT NULL PRIMARY KEY,
    supplier_name        VARCHAR(100)  NOT NULL,
    country              VARCHAR(60)   NOT NULL,
    region               VARCHAR(80)   NOT NULL,
    qualification_status VARCHAR(20)   NOT NULL DEFAULT 'QUALIFIED'
        CONSTRAINT chk_qual_status CHECK (qualification_status IN ('QUALIFIED','PENDING','DISQUALIFIED')),
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 2. materials
--    Master list of process materials tracked in the supply-risk engine.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS materials (
    material_id       VARCHAR(30)   NOT NULL PRIMARY KEY,
    material_name     VARCHAR(100)  NOT NULL,
    material_category VARCHAR(50)   NOT NULL,   -- e.g. "Gas", "Photoresist", "Metal"
    criticality       VARCHAR(20)   NOT NULL DEFAULT 'HIGH'
        CONSTRAINT chk_criticality CHECK (criticality IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 3. material_suppliers
--    Many-to-many: which suppliers provide which materials, at what share.
--    supply_share_pct represents THIS FAB's sourcing concentration from that
--    supplier (0-100, all rows per material should sum to ~100).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS material_suppliers (
    material_id       VARCHAR(30)   NOT NULL REFERENCES materials(material_id),
    supplier_id       VARCHAR(30)   NOT NULL REFERENCES suppliers(supplier_id),
    supply_share_pct  NUMERIC(5,2)  NOT NULL
        CONSTRAINT chk_share_range CHECK (supply_share_pct BETWEEN 0 AND 100),
    qualified         BOOLEAN       NOT NULL DEFAULT TRUE,
    lead_time_days    SMALLINT      NOT NULL DEFAULT 30,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    PRIMARY KEY (material_id, supplier_id)
);

CREATE INDEX IF NOT EXISTS idx_material_suppliers_material
    ON material_suppliers(material_id);

CREATE INDEX IF NOT EXISTS idx_material_suppliers_supplier
    ON material_suppliers(supplier_id);

-- ---------------------------------------------------------------------------
-- 4. material_inventory
--    Current stock snapshot per material.
--    inventory_coverage_days is a GENERATED column:
--      current_inventory_units / daily_consumption_units
--    When daily_consumption_units = 0, coverage is treated as NULL (infinite).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS material_inventory (
    material_id              VARCHAR(30)   NOT NULL PRIMARY KEY
        REFERENCES materials(material_id),
    current_inventory_units  NUMERIC(14,4) NOT NULL DEFAULT 0,
    daily_consumption_units  NUMERIC(10,4) NOT NULL DEFAULT 0,
    -- Computed column: NULL when consumption is zero (division-by-zero guard)
    inventory_coverage_days  NUMERIC(10,2) GENERATED ALWAYS AS (
        CASE
            WHEN daily_consumption_units > 0
            THEN ROUND(current_inventory_units / daily_consumption_units, 2)
            ELSE NULL
        END
    ) STORED,
    safety_stock_days        NUMERIC(8,2)  NOT NULL DEFAULT 14,
    last_updated             TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- 5. process_materials
--    Links fab process steps to the materials they consume.
--    Enables downstream impact logic (Member 3) to map process → material.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS process_materials (
    process_id           INTEGER       NOT NULL REFERENCES fab_processes(process_id),
    material_id          VARCHAR(30)   NOT NULL REFERENCES materials(material_id),
    consumption_per_unit NUMERIC(10,4) NOT NULL DEFAULT 1,
    criticality          VARCHAR(20)   NOT NULL DEFAULT 'HIGH'
        CONSTRAINT chk_pm_criticality CHECK (criticality IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    PRIMARY KEY (process_id, material_id)
);

CREATE INDEX IF NOT EXISTS idx_process_materials_material
    ON process_materials(material_id);

-- ---------------------------------------------------------------------------
-- 6. risk_factors
--    Source/date-aware geopolitical and supply risk events.
--    ⚠  All demo entries MUST be marked with source = 'Demo/Synthetic Scenario'.
--    Do NOT hard-code unsupported real-world geopolitical facts.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS risk_factors (
    risk_factor_id  SERIAL        PRIMARY KEY,
    material_id     VARCHAR(30)   REFERENCES materials(material_id),   -- NULL = region-wide
    risk_type       VARCHAR(40)   NOT NULL
        CONSTRAINT chk_risk_type CHECK (risk_type IN (
            'export_control',
            'geopolitical_instability',
            'trade_restriction',
            'transportation_risk',
            'regional_dependency'
        )),
    risk_level      VARCHAR(10)   NOT NULL
        CONSTRAINT chk_rf_level CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    reason          TEXT          NOT NULL,
    source          VARCHAR(120)  NOT NULL DEFAULT 'Demo/Synthetic Scenario',
    source_date     DATE          NOT NULL,
    affected_region VARCHAR(80)   NOT NULL,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_factors_material
    ON risk_factors(material_id);

CREATE INDEX IF NOT EXISTS idx_risk_factors_region
    ON risk_factors(affected_region);

-- ---------------------------------------------------------------------------
-- 7. supply_risk_results
--    Computed supply risk cache written by the Python service.
--    Refreshed on demand; Member 3 reads this for the combined risk engine.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS supply_risk_results (
    material_id              VARCHAR(30)   NOT NULL PRIMARY KEY
        REFERENCES materials(material_id),
    hhi                      NUMERIC(8,2)  NOT NULL,   -- 0 – 10 000
    spof                     BOOLEAN       NOT NULL DEFAULT FALSE,
    inventory_coverage_days  NUMERIC(10,2),             -- NULL when consumption = 0
    geopolitical_risk        NUMERIC(5,4)  NOT NULL,   -- 0.0 – 1.0 normalised
    composite_score          NUMERIC(5,2)  NOT NULL,   -- 0 – 100
    severity                 VARCHAR(10)   NOT NULL
        CONSTRAINT chk_severity CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    calculated_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_hhi_range   CHECK (hhi BETWEEN 0 AND 10000),
    CONSTRAINT chk_geo_range   CHECK (geopolitical_risk BETWEEN 0 AND 1),
    CONSTRAINT chk_score_range CHECK (composite_score  BETWEEN 0 AND 100)
);

-- ---------------------------------------------------------------------------
-- Indexes summary
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_supply_risk_severity
    ON supply_risk_results(severity, composite_score DESC);
