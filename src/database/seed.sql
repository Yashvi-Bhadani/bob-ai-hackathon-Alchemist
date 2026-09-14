-- =============================================================================
-- SEED DATA — SYNTHETIC / DEMO DATA ONLY
-- ⚠️  All data below is fabricated for demonstration purposes.
-- ⚠️  Supplier names, geopolitical risk levels, and market shares are
--     INVENTED for the hackathon demo. Do NOT treat as real-world facts.
-- =============================================================================

-- ─── Process Steps ────────────────────────────────────────────────────────────
INSERT INTO process_steps (step_name, step_order, typical_tool_prefix, cycle_time_hrs) VALUES
    ('Incoming Wafer Inspection',  1,  'INS',   1.0),
    ('Well Implant',               2,  'IMP',   3.0),
    ('Gate Oxidation',             3,  'OXI',   4.0),
    ('Lithography',                4,  'LITH',  2.5),
    ('Etch',                       5,  'ETCH',  2.0),
    ('Deposition (CVD)',           6,  'CVD',   3.5),
    ('CMP Planarization',          7,  'CMP',   2.0),
    ('Metal Fill (PVD)',           8,  'PVD',   2.5),
    ('Final Inspection & Test',    9,  'TEST',  1.5)
ON CONFLICT (step_name) DO NOTHING;

-- ─── Fab Tools ────────────────────────────────────────────────────────────────
INSERT INTO fab_tools (tool_id, tool_name, process_step, technology_node, max_capacity_wph, mttr_hours) VALUES
    ('LITH-07', 'EUV Scanner Unit 7',          'Lithography',            '7nm',  120.0, 8.0),
    ('LITH-08', 'EUV Scanner Unit 8',          'Lithography',            '7nm',  120.0, 8.0),
    ('ETCH-03', 'Plasma Etch Chamber 3',       'Etch',                   '7nm',  180.0, 3.0),
    ('ETCH-04', 'Plasma Etch Chamber 4',       'Etch',                   '7nm',  180.0, 3.0),
    ('CVD-11',  'LPCVD Furnace 11',            'Deposition (CVD)',        '7nm',  150.0, 4.0),
    ('CVD-12',  'LPCVD Furnace 12',            'Deposition (CVD)',        '7nm',  150.0, 4.0),
    ('CMP-02',  'CMP Polisher 2',              'CMP Planarization',       '7nm',  200.0, 2.5),
    ('IMP-05',  'Ion Implanter 5',             'Well Implant',            '7nm',  100.0, 5.0),
    ('PVD-06',  'PVD Sputter Tool 6',          'Metal Fill (PVD)',        '7nm',  160.0, 3.0),
    ('TEST-01', 'Electrical Test Station 1',   'Final Inspection & Test', '7nm',  250.0, 1.5)
ON CONFLICT (tool_id) DO NOTHING;

-- ─── Tool Utilization Snapshots (current shift — demo) ────────────────────────
INSERT INTO tool_utilization (tool_id, utilization_pct, wip_lots, downtime_hrs, throughput_wph) VALUES
    ('LITH-07', 94.5,  38, 0.5, 113.4),   -- CRITICAL bottleneck
    ('LITH-08', 71.2,  18, 0.0,  85.4),
    ('ETCH-03', 62.0,  14, 0.0, 111.6),
    ('ETCH-04', 58.5,  11, 1.0, 105.3),
    ('CVD-11',  45.0,   9, 0.0,  67.5),
    ('CVD-12',  43.0,   8, 0.0,  64.5),
    ('CMP-02',  55.0,  13, 0.0, 110.0),
    ('IMP-05',  70.0,  20, 2.0,  70.0),
    ('PVD-06',  48.0,   9, 0.0,  76.8),
    ('TEST-01', 30.0,   5, 0.0,  75.0);

-- ─── WIP Lots at LITH-07 (the critical bottleneck tool) ───────────────────────
INSERT INTO wip_lots (lot_id, product_id, current_step, current_tool_id, priority, qty_wafers, status) VALUES
    ('LOT-A001', 'PROD-7NM-CPU', 'Lithography', 'LITH-07', 1, 25, 'RUNNING'),
    ('LOT-A002', 'PROD-7NM-CPU', 'Lithography', 'LITH-07', 2, 25, 'QUEUED'),
    ('LOT-A003', 'PROD-7NM-GPU', 'Lithography', 'LITH-07', 2, 25, 'QUEUED'),
    ('LOT-A004', 'PROD-7NM-CPU', 'Lithography', 'LITH-07', 1, 25, 'QUEUED'),
    ('LOT-A005', 'PROD-7NM-GPU', 'Lithography', 'LITH-07', 3, 25, 'QUEUED'),
    ('LOT-A006', 'PROD-7NM-SYS', 'Lithography', 'LITH-07', 2, 25, 'QUEUED'),
    ('LOT-A007', 'PROD-7NM-CPU', 'Lithography', 'LITH-07', 2, 25, 'QUEUED'),
    ('LOT-A008', 'PROD-7NM-CPU', 'Lithography', 'LITH-07', 1, 25, 'QUEUED'),
    ('LOT-B001', 'PROD-7NM-GPU', 'Lithography', 'LITH-08', 2, 25, 'RUNNING'),
    ('LOT-B002', 'PROD-7NM-SYS', 'Lithography', 'LITH-08', 2, 25, 'QUEUED')
ON CONFLICT (lot_id) DO NOTHING;

-- ─── Materials ────────────────────────────────────────────────────────────────
INSERT INTO materials (material_id, material_name, material_type, unit, critical_flag) VALUES
    ('PHOTO-RES-EUV', 'EUV Photoresist',           'Photoresist', 'liter',    TRUE),
    ('PHOTO-RES-ARF', 'ArF Immersion Photoresist',  'Photoresist', 'liter',    TRUE),
    ('SPUTT-TGT-W',   'Tungsten Sputter Target',    'Metal Target','kg',       TRUE),
    ('SPUTT-TGT-CU',  'Copper Sputter Target',      'Metal Target','kg',       FALSE),
    ('CVD-TEOS',       'TEOS Precursor Gas',         'Gas',         'liter',    FALSE),
    ('CMP-SLUR-STI',   'STI CMP Slurry',             'Chemical',    'liter',    FALSE),
    ('IMP-BF3',        'BF3 Dopant Gas',             'Gas',         'liter',    TRUE),
    ('CLEAN-SC1',      'SC-1 Clean Chemical',        'Chemical',    'liter',    FALSE)
ON CONFLICT (material_id) DO NOTHING;

-- ─── Suppliers (SYNTHETIC — demo data only) ───────────────────────────────────
-- ⚠️ Supplier names and country associations are INVENTED for demonstration.
INSERT INTO suppliers (supplier_id, supplier_name, country, region, tier, qualified, lead_time_days) VALUES
    ('SUP-ALPHA-JP',   'Alpha Chem Industries (Demo)',   'Japan',          'Asia-Pacific',  1, TRUE,  35),
    ('SUP-BETA-KR',    'Beta Materials Corp (Demo)',     'South Korea',    'Asia-Pacific',  1, TRUE,  28),
    ('SUP-GAMMA-DE',   'Gamma Precision GmbH (Demo)',    'Germany',        'Europe',        1, TRUE,  45),
    ('SUP-DELTA-US',   'Delta Supply Co (Demo)',         'United States',  'North America', 1, TRUE,  21),
    ('SUP-EPSILON-TW', 'Epsilon Tech Ltd (Demo)',        'Taiwan',         'Asia-Pacific',  2, TRUE,  30),
    ('SUP-ZETA-NL',    'Zeta Specialty BV (Demo)',       'Netherlands',    'Europe',        2, TRUE,  40),
    ('SUP-ETA-CN',     'Eta Chemical Group (Demo)',      'China',          'Asia-Pacific',  1, TRUE,  25),
    ('SUP-THETA-US',   'Theta Advanced Mats (Demo)',     'United States',  'North America', 2, FALSE, 60)
ON CONFLICT (supplier_id) DO NOTHING;

-- ─── Supplier ↔ Material shares (SYNTHETIC — shows SPOF on EUV Resist) ────────
-- EUV Photoresist: 70% from one supplier → SPOF scenario
INSERT INTO supplier_materials (supplier_id, material_id, supply_share_pct) VALUES
    ('SUP-ALPHA-JP',   'PHOTO-RES-EUV', 70.0),   -- dominant supplier → SPOF
    ('SUP-BETA-KR',    'PHOTO-RES-EUV', 30.0),
    ('SUP-GAMMA-DE',   'PHOTO-RES-ARF', 50.0),
    ('SUP-DELTA-US',   'PHOTO-RES-ARF', 50.0),
    ('SUP-DELTA-US',   'SPUTT-TGT-W',  60.0),
    ('SUP-EPSILON-TW', 'SPUTT-TGT-W',  40.0),
    ('SUP-BETA-KR',    'SPUTT-TGT-CU', 45.0),
    ('SUP-DELTA-US',   'SPUTT-TGT-CU', 35.0),
    ('SUP-ZETA-NL',    'SPUTT-TGT-CU', 20.0),
    ('SUP-ETA-CN',     'CVD-TEOS',     55.0),
    ('SUP-DELTA-US',   'CVD-TEOS',     45.0),
    ('SUP-GAMMA-DE',   'CMP-SLUR-STI', 60.0),
    ('SUP-ZETA-NL',    'CMP-SLUR-STI', 40.0),
    ('SUP-ALPHA-JP',   'IMP-BF3',      80.0),    -- near-monopoly → SPOF
    ('SUP-DELTA-US',   'IMP-BF3',      20.0),
    ('SUP-DELTA-US',   'CLEAN-SC1',   100.0)     -- single source
ON CONFLICT (supplier_id, material_id) DO NOTHING;

-- ─── Tool ↔ Material requirements ────────────────────────────────────────────
INSERT INTO tool_material_requirements (tool_id, material_id, consumption_per_lot) VALUES
    ('LITH-07', 'PHOTO-RES-EUV', 2.5),
    ('LITH-08', 'PHOTO-RES-EUV', 2.5),
    ('ETCH-03', 'CLEAN-SC1',     1.0),
    ('ETCH-04', 'CLEAN-SC1',     1.0),
    ('CVD-11',  'CVD-TEOS',      3.0),
    ('CVD-12',  'CVD-TEOS',      3.0),
    ('CMP-02',  'CMP-SLUR-STI',  4.0),
    ('IMP-05',  'IMP-BF3',       0.8),
    ('PVD-06',  'SPUTT-TGT-W',   0.05)
ON CONFLICT (tool_id, material_id) DO NOTHING;

-- ─── Inventory Snapshots ──────────────────────────────────────────────────────
INSERT INTO inventory_snapshots (material_id, quantity_on_hand, daily_consumption, reorder_point, safety_stock) VALUES
    ('PHOTO-RES-EUV', 62.5,  12.5, 37.5, 25.0),   -- 5-day coverage (low!)
    ('PHOTO-RES-ARF', 300.0,  8.0, 40.0, 24.0),   -- 37-day coverage
    ('SPUTT-TGT-W',   18.0,   0.9,  5.4,  2.7),   -- 20-day coverage
    ('SPUTT-TGT-CU',  55.0,   1.2,  7.2,  3.6),   -- 45-day coverage
    ('CVD-TEOS',      420.0,  15.0, 90.0, 45.0),  -- 28-day coverage
    ('CMP-SLUR-STI',  900.0,  20.0, 80.0, 40.0),  -- 45-day coverage
    ('IMP-BF3',        8.0,   1.6,  9.6,  4.8),   -- 5-day coverage (CRITICAL!)
    ('CLEAN-SC1',    1200.0,  25.0, 75.0, 37.5)   -- 48-day coverage
ON CONFLICT (material_id, snapshot_date) DO NOTHING;

-- ─── Geopolitical Risk Entries (SYNTHETIC SCENARIO DATA) ─────────────────────
-- ⚠️ These are entirely fictional scenarios for hackathon demonstration.
-- ⚠️ Do NOT interpret as statements about real geopolitical situations.
INSERT INTO geopolitical_risks (risk_id, affected_region, affected_material_id, risk_level, risk_reason, source, source_date) VALUES
    ('GEO-001',
     'Asia-Pacific',
     'PHOTO-RES-EUV',
     'HIGH',
     '[DEMO SCENARIO] Hypothetical export licensing delays for specialty photochemical precursors affecting regional supply chains.',
     'Demo/Synthetic Scenario — Not Real',
     '2025-01-01'),
    ('GEO-002',
     'Asia-Pacific',
     'IMP-BF3',
     'HIGH',
     '[DEMO SCENARIO] Simulated regional logistics disruption causing lead-time extension for specialty dopant gases.',
     'Demo/Synthetic Scenario — Not Real',
     '2025-01-01'),
    ('GEO-003',
     'Europe',
     'SPUTT-TGT-W',
     'MEDIUM',
     '[DEMO SCENARIO] Hypothetical energy-cost surcharge increasing unit cost of refractory metal targets from European suppliers.',
     'Demo/Synthetic Scenario — Not Real',
     '2025-01-01'),
    ('GEO-004',
     'Asia-Pacific',
     NULL,
     'MEDIUM',
     '[DEMO SCENARIO] Simulated shipping lane congestion scenario increasing transit time by 7-14 days for Asia-Pacific routes.',
     'Demo/Synthetic Scenario — Not Real',
     '2025-01-01')
ON CONFLICT (risk_id) DO NOTHING;
