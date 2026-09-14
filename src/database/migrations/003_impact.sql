-- =============================================================================
-- Migration 003: Impact, Outage Simulation & Combined Risk Tables
-- Member: 3 (feature/dashboard)
-- Description: Outage simulation results, downstream process impact,
--              combined risk assessments, and mitigation recommendations.
-- =============================================================================

-- Outage simulation runs
CREATE TABLE IF NOT EXISTS outage_simulations (
    id              SERIAL PRIMARY KEY,
    simulation_id   UUID NOT NULL DEFAULT gen_random_uuid(),
    tool_id         VARCHAR(20) NOT NULL,      -- FK to fab_tools (cross-migration)
    outage_hours    NUMERIC(6,2) NOT NULL,
    simulated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Computed results (Python service populates)
    backlog_lots    INTEGER,
    recovery_hours  NUMERIC(8,2),
    is_recoverable  BOOLEAN,
    backlog_wafers  INTEGER,
    notes           TEXT,
    CONSTRAINT chk_outage_positive CHECK (outage_hours > 0)
);

-- Downstream process impact (which steps/tools are affected after an outage)
CREATE TABLE IF NOT EXISTS downstream_impact (
    id              SERIAL PRIMARY KEY,
    simulation_id   UUID NOT NULL,
    affected_step   VARCHAR(80) NOT NULL,
    affected_tool_id VARCHAR(20),
    delay_hours     NUMERIC(8,2) NOT NULL,
    affected_lots   INTEGER NOT NULL DEFAULT 0,
    impact_severity VARCHAR(10) NOT NULL DEFAULT 'MEDIUM',
    CONSTRAINT chk_severity CHECK (impact_severity IN ('LOW','MEDIUM','HIGH','CRITICAL'))
);

-- Combined risk assessments (manufacturing + supply chain together)
CREATE TABLE IF NOT EXISTS combined_risk_assessments (
    id              SERIAL PRIMARY KEY,
    assessment_id   UUID NOT NULL DEFAULT gen_random_uuid(),
    tool_id         VARCHAR(20) NOT NULL,
    material_id     VARCHAR(30),
    assessed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    manufacturing_risk_score  NUMERIC(5,4) NOT NULL,  -- 0-1
    supply_chain_risk_score   NUMERIC(5,4) NOT NULL,  -- 0-1
    combined_risk_score       NUMERIC(5,4) NOT NULL,  -- 0-1 weighted composite
    risk_tier       VARCHAR(10) NOT NULL,  -- GREEN|AMBER|RED|CRITICAL
    confidence_pct  SMALLINT NOT NULL DEFAULT 80,
    CONSTRAINT chk_combined_tier CHECK (risk_tier IN ('GREEN','AMBER','RED','CRITICAL'))
);

-- Mitigation recommendations (linked to a combined risk assessment)
CREATE TABLE IF NOT EXISTS mitigation_recommendations (
    id              SERIAL PRIMARY KEY,
    assessment_id   UUID NOT NULL,
    priority        SMALLINT NOT NULL DEFAULT 1,   -- 1=highest
    category        VARCHAR(30) NOT NULL,          -- TOOL|SCHEDULE|INVENTORY|SUPPLIER|OTHER
    recommendation  TEXT NOT NULL,
    expected_impact TEXT,
    feasibility     VARCHAR(10) NOT NULL DEFAULT 'HIGH', -- HIGH|MEDIUM|LOW
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_category CHECK (category IN ('TOOL','SCHEDULE','INVENTORY','SUPPLIER','OTHER')),
    CONSTRAINT chk_feasibility CHECK (feasibility IN ('HIGH','MEDIUM','LOW'))
);

-- Bob narration cache (stores AI-generated explanations for display/replay)
CREATE TABLE IF NOT EXISTS bob_narrations (
    id              SERIAL PRIMARY KEY,
    narration_id    UUID NOT NULL DEFAULT gen_random_uuid(),
    context_type    VARCHAR(30) NOT NULL,  -- BOTTLENECK|OUTAGE|SUPPLY_RISK|COMBINED|RECOMMENDATION
    reference_id    UUID,                  -- references e.g. simulation_id or assessment_id
    prompt_hash     VARCHAR(64),           -- SHA-256 of the prompt for caching
    narration_text  TEXT NOT NULL,
    is_fallback     BOOLEAN NOT NULL DEFAULT FALSE,  -- TRUE if Bob was unavailable
    model_used      VARCHAR(80),
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_outage_sim_tool
    ON outage_simulations(tool_id, simulated_at DESC);

CREATE INDEX IF NOT EXISTS idx_downstream_sim
    ON downstream_impact(simulation_id);

CREATE INDEX IF NOT EXISTS idx_combined_risk_tool
    ON combined_risk_assessments(tool_id, assessed_at DESC);

CREATE INDEX IF NOT EXISTS idx_mitigation_assessment
    ON mitigation_recommendations(assessment_id, priority);

CREATE INDEX IF NOT EXISTS idx_bob_narrations_context
    ON bob_narrations(context_type, reference_id);
