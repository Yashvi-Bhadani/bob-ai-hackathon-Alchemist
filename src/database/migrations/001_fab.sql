-- =============================================================================
-- Migration 001: Fab Manufacturing & Bottleneck Tables  (Member 1)
-- Schema version: 2 — full rework per spec
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. fab_processes
--    Defines the ordered sequence of wafer manufacturing process steps.
--    next_process_id enables downstream-impact traversal.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fab_processes (
    process_id        SERIAL PRIMARY KEY,
    process_name      VARCHAR(80)  NOT NULL UNIQUE,   -- e.g. "Lithography"
    process_sequence  SMALLINT     NOT NULL,           -- 1 = first step
    next_process_id   INTEGER      REFERENCES fab_processes(process_id),
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fab_processes_seq
    ON fab_processes(process_sequence);

-- ---------------------------------------------------------------------------
-- 2. fab_tools
--    Physical equipment on the fab floor.
--    compatible_products is a TEXT[] array so Member 3 can verify whether
--    an alternate tool can handle a given product before recommending it.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fab_tools (
    tool_id               VARCHAR(20)   NOT NULL PRIMARY KEY,  -- e.g. "LITH-07"
    tool_name             VARCHAR(100)  NOT NULL,
    process_id            INTEGER       NOT NULL REFERENCES fab_processes(process_id),
    tool_type             VARCHAR(50)   NOT NULL,               -- e.g. "EUV Scanner"
    available_hours       NUMERIC(6,2)  NOT NULL DEFAULT 24.0,  -- per day
    capacity_units_per_hour NUMERIC(10,2) NOT NULL,             -- wafers per hour
    compatible_products   TEXT[]        NOT NULL DEFAULT '{}',  -- product IDs this tool can run
    status                VARCHAR(20)   NOT NULL DEFAULT 'ACTIVE',
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_tool_status   CHECK (status IN ('ACTIVE','DOWN','MAINTENANCE','STANDBY')),
    CONSTRAINT chk_avail_hours   CHECK (available_hours > 0),
    CONSTRAINT chk_capacity_pos  CHECK (capacity_units_per_hour > 0)
);

-- ---------------------------------------------------------------------------
-- 3. wip_lots
--    Work-in-progress lots currently tracked through the fab.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS wip_lots (
    lot_id      VARCHAR(30)  NOT NULL PRIMARY KEY,
    product_id  VARCHAR(30)  NOT NULL,
    process_id  INTEGER      NOT NULL REFERENCES fab_processes(process_id),
    tool_id     VARCHAR(20)  REFERENCES fab_tools(tool_id),
    quantity    INTEGER      NOT NULL DEFAULT 25,          -- wafers per lot
    arrival_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),       -- when lot arrived at this step
    priority    SMALLINT     NOT NULL DEFAULT 2,           -- 1=HOT  2=NORMAL  3=LOW
    status      VARCHAR(20)  NOT NULL DEFAULT 'QUEUED',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_wip_priority CHECK (priority IN (1,2,3)),
    CONSTRAINT chk_wip_status   CHECK (status IN ('QUEUED','RUNNING','HOLD','COMPLETE')),
    CONSTRAINT chk_quantity_pos CHECK (quantity > 0)
);

CREATE INDEX IF NOT EXISTS idx_wip_lots_tool_status
    ON wip_lots(tool_id, status);

CREATE INDEX IF NOT EXISTS idx_wip_lots_process
    ON wip_lots(process_id, status);

-- ---------------------------------------------------------------------------
-- 4. fab_snapshots
--    Periodic observations of tool state — used for confidence / trend analysis.
--    At least 3 snapshots per tool are required for high-confidence scoring.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fab_snapshots (
    snapshot_id       BIGSERIAL    PRIMARY KEY,
    tool_id           VARCHAR(20)  NOT NULL REFERENCES fab_tools(tool_id),
    snapshot_time     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    wip_units         INTEGER      NOT NULL DEFAULT 0,      -- lots queued at snapshot time
    busy_hours        NUMERIC(6,2) NOT NULL DEFAULT 0,      -- hours tool was busy in period
    available_hours   NUMERIC(6,2) NOT NULL DEFAULT 24.0,   -- hours tool was available
    capacity_units    NUMERIC(10,2) NOT NULL,               -- max units/hr * available_hours
    downtime_hours    NUMERIC(6,2) NOT NULL DEFAULT 0,      -- unplanned downtime in period
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_snap_busy_le_avail   CHECK (busy_hours <= available_hours + downtime_hours),
    CONSTRAINT chk_snap_avail_pos       CHECK (available_hours >= 0),
    CONSTRAINT chk_snap_downtime_ge_0   CHECK (downtime_hours >= 0)
);

CREATE INDEX IF NOT EXISTS idx_fab_snapshots_tool_time
    ON fab_snapshots(tool_id, snapshot_time DESC);

-- ---------------------------------------------------------------------------
-- 5. bottleneck_results
--    Computed bottleneck assessment records written by the Python service.
--    Stored for historical trending and audit; not a cache.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bottleneck_results (
    result_id         BIGSERIAL    PRIMARY KEY,
    tool_id           VARCHAR(20)  NOT NULL REFERENCES fab_tools(tool_id),
    calculated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    utilization       NUMERIC(6,4) NOT NULL,   -- ratio 0–1
    wip_pressure      NUMERIC(8,4) NOT NULL,   -- raw ratio (can exceed 1)
    capacity_pressure NUMERIC(6,4) NOT NULL,   -- ratio 0–1
    downtime_pct      NUMERIC(6,4) NOT NULL,   -- ratio 0–1
    bottleneck_score  NUMERIC(6,2) NOT NULL,   -- 0–100
    severity          VARCHAR(10)  NOT NULL,   -- LOW | MEDIUM | HIGH | CRITICAL
    confidence        NUMERIC(5,4) NOT NULL,   -- 0–1
    low_confidence    BOOLEAN      NOT NULL DEFAULT FALSE,
    CONSTRAINT chk_br_util         CHECK (utilization BETWEEN 0 AND 1),
    CONSTRAINT chk_br_score        CHECK (bottleneck_score BETWEEN 0 AND 100),
    CONSTRAINT chk_br_severity     CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    CONSTRAINT chk_br_confidence   CHECK (confidence BETWEEN 0 AND 1)
);

CREATE INDEX IF NOT EXISTS idx_bottleneck_results_tool_time
    ON bottleneck_results(tool_id, calculated_at DESC);
