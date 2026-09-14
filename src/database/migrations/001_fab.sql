-- =============================================================================
-- Migration 001: Fab Manufacturing & Bottleneck Tables
-- Member: 1 (feature/bottleneck)
-- Description: Core fab equipment, WIP lots, process steps, and utilization
--              snapshots used by the bottleneck detection engine.
-- =============================================================================

-- Equipment / tools on the fab floor
CREATE TABLE IF NOT EXISTS fab_tools (
    id              SERIAL PRIMARY KEY,
    tool_id         VARCHAR(20)  NOT NULL UNIQUE,   -- e.g. "LITH-07"
    tool_name       VARCHAR(100) NOT NULL,
    process_step    VARCHAR(80)  NOT NULL,           -- e.g. "Lithography"
    technology_node VARCHAR(20),                     -- e.g. "7nm"
    max_capacity_wph NUMERIC(10,2) NOT NULL,         -- wafers per hour
    mttr_hours      NUMERIC(6,2)  NOT NULL DEFAULT 4.0,  -- mean time to repair
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Real-time (or last-known) utilization snapshots
CREATE TABLE IF NOT EXISTS tool_utilization (
    id              SERIAL PRIMARY KEY,
    tool_id         VARCHAR(20) NOT NULL REFERENCES fab_tools(tool_id),
    snapshot_time   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    utilization_pct NUMERIC(5,2) NOT NULL,           -- 0-100
    wip_lots        INTEGER NOT NULL DEFAULT 0,       -- lots currently queued
    downtime_hrs    NUMERIC(6,2) NOT NULL DEFAULT 0, -- unplanned downtime this shift
    throughput_wph  NUMERIC(10,2),                   -- actual wafers/hr during snapshot
    CONSTRAINT chk_util_range CHECK (utilization_pct BETWEEN 0 AND 100)
);

-- WIP lot tracking
CREATE TABLE IF NOT EXISTS wip_lots (
    id              SERIAL PRIMARY KEY,
    lot_id          VARCHAR(30) NOT NULL UNIQUE,
    product_id      VARCHAR(30) NOT NULL,
    current_step    VARCHAR(80) NOT NULL,
    current_tool_id VARCHAR(20) REFERENCES fab_tools(tool_id),
    priority        SMALLINT NOT NULL DEFAULT 2,  -- 1=HOT, 2=NORMAL, 3=LOW
    qty_wafers      SMALLINT NOT NULL DEFAULT 25,
    queue_entry_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status          VARCHAR(20) NOT NULL DEFAULT 'QUEUED',  -- QUEUED|RUNNING|HOLD
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_priority CHECK (priority IN (1,2,3)),
    CONSTRAINT chk_status CHECK (status IN ('QUEUED','RUNNING','HOLD','COMPLETE'))
);

-- Bottleneck score history (computed by Python service, stored for trending)
CREATE TABLE IF NOT EXISTS bottleneck_scores (
    id              SERIAL PRIMARY KEY,
    tool_id         VARCHAR(20) NOT NULL REFERENCES fab_tools(tool_id),
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    utilization_pct NUMERIC(5,2) NOT NULL,
    wip_pressure    NUMERIC(5,4) NOT NULL,  -- dimensionless 0-1
    capacity_pressure NUMERIC(5,4) NOT NULL, -- dimensionless 0-1
    bottleneck_score NUMERIC(5,4) NOT NULL,  -- composite 0-1
    is_critical     BOOLEAN NOT NULL DEFAULT FALSE
);

-- Process step sequence (defines downstream dependency order)
CREATE TABLE IF NOT EXISTS process_steps (
    id              SERIAL PRIMARY KEY,
    step_name       VARCHAR(80) NOT NULL UNIQUE,
    step_order      SMALLINT NOT NULL,
    typical_tool_prefix VARCHAR(10),  -- e.g. "LITH" for lithography tools
    cycle_time_hrs  NUMERIC(6,2) NOT NULL DEFAULT 2.0
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_tool_util_tool_time
    ON tool_utilization(tool_id, snapshot_time DESC);

CREATE INDEX IF NOT EXISTS idx_wip_lots_tool
    ON wip_lots(current_tool_id, status);

CREATE INDEX IF NOT EXISTS idx_bottleneck_scores_tool
    ON bottleneck_scores(tool_id, computed_at DESC);
