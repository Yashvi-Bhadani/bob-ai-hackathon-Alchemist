-- =============================================================================
-- Migration 002: Supply Chain & Risk Tables
-- Member: 2 (feature/supply-risk)
-- Description: Suppliers, materials, inventory, geopolitical risk, and
--              SPOF/HHI data used by the supply-chain risk engine.
-- =============================================================================

-- Materials required in the fab process
CREATE TABLE IF NOT EXISTS materials (
    id              SERIAL PRIMARY KEY,
    material_id     VARCHAR(30) NOT NULL UNIQUE,  -- e.g. "PHOTO-RES-EUV"
    material_name   VARCHAR(100) NOT NULL,
    material_type   VARCHAR(50) NOT NULL,         -- e.g. "Photoresist", "Gas", "Chemical"
    unit            VARCHAR(20) NOT NULL DEFAULT 'kg',
    critical_flag   BOOLEAN NOT NULL DEFAULT FALSE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Suppliers
CREATE TABLE IF NOT EXISTS suppliers (
    id              SERIAL PRIMARY KEY,
    supplier_id     VARCHAR(30) NOT NULL UNIQUE,  -- e.g. "SUP-JSR-JP"
    supplier_name   VARCHAR(100) NOT NULL,
    country         VARCHAR(60) NOT NULL,
    region          VARCHAR(60) NOT NULL,
    tier            SMALLINT NOT NULL DEFAULT 1,  -- 1=primary, 2=secondary
    qualified       BOOLEAN NOT NULL DEFAULT TRUE,
    lead_time_days  SMALLINT NOT NULL DEFAULT 30,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Supplier ↔ Material mapping (many-to-many with share %)
CREATE TABLE IF NOT EXISTS supplier_materials (
    id              SERIAL PRIMARY KEY,
    supplier_id     VARCHAR(30) NOT NULL REFERENCES suppliers(supplier_id),
    material_id     VARCHAR(30) NOT NULL REFERENCES materials(material_id),
    supply_share_pct NUMERIC(5,2) NOT NULL,        -- 0-100, must sum to ~100 per material
    unit_price_usd  NUMERIC(12,4),
    last_updated    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(supplier_id, material_id),
    CONSTRAINT chk_share_range CHECK (supply_share_pct BETWEEN 0 AND 100)
);

-- Tool ↔ Material mapping (which tools consume which materials)
CREATE TABLE IF NOT EXISTS tool_material_requirements (
    id              SERIAL PRIMARY KEY,
    tool_id         VARCHAR(20) NOT NULL,          -- FK to fab_tools; cross-migration ref
    material_id     VARCHAR(30) NOT NULL REFERENCES materials(material_id),
    consumption_per_lot NUMERIC(10,4) NOT NULL,    -- units consumed per lot processed
    UNIQUE(tool_id, material_id)
);

-- Inventory snapshots
CREATE TABLE IF NOT EXISTS inventory_snapshots (
    id              SERIAL PRIMARY KEY,
    material_id     VARCHAR(30) NOT NULL REFERENCES materials(material_id),
    snapshot_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    quantity_on_hand NUMERIC(14,4) NOT NULL,
    daily_consumption NUMERIC(10,4) NOT NULL,      -- baseline daily burn rate
    reorder_point   NUMERIC(10,4) NOT NULL,
    safety_stock    NUMERIC(10,4) NOT NULL,
    UNIQUE(material_id, snapshot_date)
);

-- Geopolitical / export-control risk entries
-- NOTE: All entries are scenario/demo data — not verified real-world claims.
CREATE TABLE IF NOT EXISTS geopolitical_risks (
    id              SERIAL PRIMARY KEY,
    risk_id         VARCHAR(30) NOT NULL UNIQUE,
    affected_region VARCHAR(80) NOT NULL,
    affected_material_id VARCHAR(30) REFERENCES materials(material_id),
    risk_level      VARCHAR(10) NOT NULL,           -- LOW | MEDIUM | HIGH | CRITICAL
    risk_reason     TEXT NOT NULL,
    source          VARCHAR(100) NOT NULL DEFAULT 'Demo/Synthetic Scenario',
    source_date     DATE NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_risk_level CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL'))
);

-- Computed HHI scores cache (Python service writes here)
CREATE TABLE IF NOT EXISTS hhi_scores (
    id              SERIAL PRIMARY KEY,
    material_id     VARCHAR(30) NOT NULL REFERENCES materials(material_id),
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    hhi_value       NUMERIC(8,2) NOT NULL,   -- 0-10000 (HH Index)
    supplier_count  SMALLINT NOT NULL,
    concentration_level VARCHAR(15) NOT NULL, -- LOW|MODERATE|HIGH|MONOPOLY
    CONSTRAINT chk_hhi_range CHECK (hhi_value BETWEEN 0 AND 10000)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_supplier_materials_material
    ON supplier_materials(material_id);

CREATE INDEX IF NOT EXISTS idx_inventory_material_date
    ON inventory_snapshots(material_id, snapshot_date DESC);

CREATE INDEX IF NOT EXISTS idx_geo_risk_material
    ON geopolitical_risks(affected_material_id, is_active);
