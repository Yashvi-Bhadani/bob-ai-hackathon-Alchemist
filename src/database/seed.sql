-- =============================================================================
-- SEED DATA — SYNTHETIC / DEMO DATA ONLY
-- ⚠  All data is fabricated for hackathon demonstration purposes.
-- ⚠  No real fab, tool, or product data is represented.
-- =============================================================================

-- ─── Processes (sequence 1→5) ────────────────────────────────────────────────
-- Inserted in reverse so next_process_id FK can reference later rows
INSERT INTO fab_processes (process_id, process_name, process_sequence, next_process_id) VALUES
    (1, 'Lithography', 1, 2),
    (2, 'Etch',        2, 3),
    (3, 'CVD',         3, 4),
    (4, 'Inspection',  4, 5),
    (5, 'Packaging',   5, NULL)
ON CONFLICT (process_name) DO NOTHING;

-- Keep serial in sync
SELECT setval('fab_processes_process_id_seq', 5, true);

-- ─── Fab Tools ────────────────────────────────────────────────────────────────
INSERT INTO fab_tools
    (tool_id, tool_name, process_id, tool_type, available_hours, capacity_units_per_hour, compatible_products, status)
VALUES
    -- Lithography — LITH-07 is the critical bottleneck; LITH-08 is the qualified alternate
    ('LITH-07', 'EUV Scanner Unit 7',              1, 'EUV Scanner',       24.0,  50.0,
     ARRAY['PROD-7NM-CPU','PROD-7NM-GPU','PROD-7NM-SYS'], 'ACTIVE'),
    ('LITH-08', 'EUV Scanner Unit 8',              1, 'EUV Scanner',       24.0,  50.0,
     ARRAY['PROD-7NM-CPU','PROD-7NM-GPU'], 'ACTIVE'),
    -- Etch
    ('ETCH-03', 'Plasma Etch Chamber 3',           2, 'Plasma Etcher',     24.0,  75.0,
     ARRAY['PROD-7NM-CPU','PROD-7NM-GPU','PROD-7NM-SYS'], 'ACTIVE'),
    ('ETCH-04', 'Plasma Etch Chamber 4',           2, 'Plasma Etcher',     24.0,  75.0,
     ARRAY['PROD-7NM-CPU','PROD-7NM-SYS'], 'ACTIVE'),
    -- CVD
    ('CVD-11',  'LPCVD Furnace 11',                3, 'LPCVD Furnace',     24.0,  60.0,
     ARRAY['PROD-7NM-CPU','PROD-7NM-GPU','PROD-7NM-SYS'], 'ACTIVE'),
    -- Inspection
    ('INSP-01', 'Optical Inspection Unit 1',       4, 'Optical Inspector', 24.0, 120.0,
     ARRAY['PROD-7NM-CPU','PROD-7NM-GPU','PROD-7NM-SYS'], 'ACTIVE'),
    -- Packaging
    ('PKG-02',  'Die Attach & Wire Bond Station 2',5, 'Packaging Station', 24.0, 200.0,
     ARRAY['PROD-7NM-CPU','PROD-7NM-GPU'], 'ACTIVE')
ON CONFLICT (tool_id) DO NOTHING;

-- ─── WIP Lots ─────────────────────────────────────────────────────────────────
INSERT INTO wip_lots (lot_id, product_id, process_id, tool_id, quantity, arrival_time, priority, status) VALUES
    ('LOT-L7-001', 'PROD-7NM-CPU', 1, 'LITH-07', 25, NOW() - INTERVAL '6 hours',  1, 'RUNNING'),
    ('LOT-L7-002', 'PROD-7NM-GPU', 1, 'LITH-07', 25, NOW() - INTERVAL '5 hours',  2, 'QUEUED'),
    ('LOT-L7-003', 'PROD-7NM-CPU', 1, 'LITH-07', 25, NOW() - INTERVAL '4 hours',  1, 'QUEUED'),
    ('LOT-L7-004', 'PROD-7NM-SYS', 1, 'LITH-07', 25, NOW() - INTERVAL '4 hours',  2, 'QUEUED'),
    ('LOT-L7-005', 'PROD-7NM-CPU', 1, 'LITH-07', 25, NOW() - INTERVAL '3 hours',  2, 'QUEUED'),
    ('LOT-L7-006', 'PROD-7NM-GPU', 1, 'LITH-07', 25, NOW() - INTERVAL '3 hours',  3, 'QUEUED'),
    ('LOT-L7-007', 'PROD-7NM-CPU', 1, 'LITH-07', 25, NOW() - INTERVAL '2 hours',  1, 'QUEUED'),
    ('LOT-L7-008', 'PROD-7NM-SYS', 1, 'LITH-07', 25, NOW() - INTERVAL '1 hour',   2, 'QUEUED'),
    ('LOT-L8-001', 'PROD-7NM-CPU', 1, 'LITH-08', 25, NOW() - INTERVAL '3 hours',  2, 'RUNNING'),
    ('LOT-L8-002', 'PROD-7NM-GPU', 1, 'LITH-08', 25, NOW() - INTERVAL '2 hours',  2, 'QUEUED'),
    ('LOT-E3-001', 'PROD-7NM-CPU', 2, 'ETCH-03', 25, NOW() - INTERVAL '2 hours',  2, 'RUNNING'),
    ('LOT-E4-001', 'PROD-7NM-SYS', 2, 'ETCH-04', 25, NOW() - INTERVAL '2 hours',  2, 'RUNNING')
ON CONFLICT (lot_id) DO NOTHING;

-- ─── fab_snapshots ────────────────────────────────────────────────────────────
-- LITH-07: 5 snapshots showing rising WIP trend (60→80→120→180→240)
INSERT INTO fab_snapshots (tool_id, snapshot_time, wip_units, busy_hours, available_hours, capacity_units, downtime_hours) VALUES
    ('LITH-07', NOW() - INTERVAL '96 hours',  60,  14.0, 24.0, 1200.0, 0.0),
    ('LITH-07', NOW() - INTERVAL '72 hours',  80,  17.0, 24.0, 1200.0, 0.3),
    ('LITH-07', NOW() - INTERVAL '48 hours', 120,  20.5, 24.0, 1200.0, 0.5),
    ('LITH-07', NOW() - INTERVAL '24 hours', 180,  22.0, 24.0, 1200.0, 0.8),
    ('LITH-07', NOW(),                        240,  23.3, 24.0, 1200.0, 1.2),
    -- LITH-08: 5 stable snapshots
    ('LITH-08', NOW() - INTERVAL '96 hours',  48,  12.0, 24.0, 1200.0, 0.0),
    ('LITH-08', NOW() - INTERVAL '72 hours',  55,  14.0, 24.0, 1200.0, 0.0),
    ('LITH-08', NOW() - INTERVAL '48 hours',  50,  13.5, 24.0, 1200.0, 0.0),
    ('LITH-08', NOW() - INTERVAL '24 hours',  53,  14.2, 24.0, 1200.0, 0.0),
    ('LITH-08', NOW(),                         52,  14.4, 24.0, 1200.0, 0.0),
    -- ETCH-03: 3 snapshots (stable)
    ('ETCH-03', NOW() - INTERVAL '48 hours', 105,  14.0, 24.0, 1800.0, 0.0),
    ('ETCH-03', NOW() - INTERVAL '24 hours', 108,  14.5, 24.0, 1800.0, 0.0),
    ('ETCH-03', NOW(),                        110,  14.9, 24.0, 1800.0, 0.0),
    -- ETCH-04: 3 snapshots (slight decline, with downtime)
    ('ETCH-04', NOW() - INTERVAL '48 hours',  98,  13.0, 24.0, 1800.0, 0.5),
    ('ETCH-04', NOW() - INTERVAL '24 hours',  96,  13.1, 24.0, 1800.0, 0.8),
    ('ETCH-04', NOW(),                         95,  13.2, 24.0, 1800.0, 1.0),
    -- Single snapshots for remaining tools
    ('CVD-11',  NOW(),                         70,  10.8, 24.0, 1440.0, 0.0),
    ('INSP-01', NOW(),                         40,   7.2, 24.0, 2880.0, 0.0),
    ('PKG-02',  NOW(),                         30,   6.0, 24.0, 4800.0, 0.0);
