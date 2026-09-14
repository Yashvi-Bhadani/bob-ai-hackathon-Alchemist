# Solution Overview

## What We Built

The **Fab Bottleneck & Supply Chain Risk Advisor** is an industrial intelligence and decision-support system for semiconductor fab operations. It executes the complete risk workflow — detect, quantify, simulate, trace, assess, recommend, and explain — from a single dashboard.

The system uses **deterministic engineering formulas** for all calculations (no ML models, no trained classifiers) and uses **IBM Bob (watsonx.ai Granite)** exclusively as the natural-language explanation and decision-brief layer.

## How It Works

1. **Bottleneck Detection:** The backend queries tool utilisation, WIP queue depth, and capacity data. For each tool it computes three sub-scores:
   - *Utilisation pressure* (0–1): raw utilisation / 100
   - *WIP pressure* (0–1): queue depth / theoretical shift capacity
   - *Capacity pressure* (0–1): linear ramp above 85% utilisation threshold
   - Composite **Bottleneck Score** = 0.50 × utilisation + 0.30 × WIP + 0.20 × capacity
   - Tools with score ≥ 0.75 are flagged CRITICAL. `LITH-07` (EUV lithography) is the critical bottleneck.

2. **Outage Simulation:** The user selects a tool and a downtime duration. The engine computes:
   - Backlog lots accumulating during outage (arrival_rate × outage_hours)
   - Recovery time = (total backlog) / (max processing rate − arrival rate)
   - Recovery is flagged IMPOSSIBLE if arrival rate ≥ max processing rate
   - Downstream step delays are calculated proportionally to step distance from the bottleneck

3. **Supply Chain Risk Assessment:** For the primary material consumed by the selected tool:
   - **HHI** (Herfindahl-Hirschman Index): Σ(share_i²) on 0–10,000 scale
   - **SPOF detection**: any supplier with ≥ 70% share OR only one qualified supplier
   - **Inventory coverage**: quantity_on_hand / daily_consumption in days
   - **Geopolitical risk**: risk level from scenario entries (synthetic demo data)
   - Combined supply score = 0.30 × HHI_norm + 0.30 × inventory_risk + 0.25 × SPOF + 0.15 × geo

4. **Combined Risk:** Fuses manufacturing risk (55% weight) and supply chain risk (45% weight) into a single 0–1 score with tier labels: GREEN / AMBER / RED / CRITICAL.

5. **Mitigation Recommendations:** Rule-based engine generates prioritised recommendations: alternate tool routing, lot scheduling, emergency inventory replenishment, supplier diversification.

6. **IBM Bob Narration:** The structured JSON result is sent to IBM Bob (watsonx.ai Granite 13B Instruct). Bob explains what the numbers mean, why they matter, and which recommendation is most urgent. If Bob is unavailable, a deterministic template narration activates automatically.

## Architecture Diagram

```
[User Browser]
    │
    ▼
[React Dashboard — Vite + TypeScript + Tailwind + Recharts]
    │  REST JSON
    ▼
[FastAPI Backend — Python + Pydantic]
    ├── /api/v1/bottleneck  ← WIP pressure, outage simulation
    ├── /api/v1/supply      ← HHI, SPOF, inventory, geo risk
    ├── /api/v1/impact      ← Combined risk + recommendations
    └── /api/v1/narration   ← IBM Bob prompt builder + API call
          │
          ├── [PostgreSQL / Supabase]   (live mode)
          │     001_fab.sql, 002_supply.sql, 003_impact.sql
          │
          └── [Demo Fallback Data]      (offline/no-DB mode)
                Built-in synthetic data in service layer

Bob Layer:
    FastAPI → IBM IAM Token Exchange → watsonx.ai Granite 13B
    If unavailable → Deterministic Template Fallback
```

See [`architecture.md`](architecture.md) for the detailed Mermaid diagram.

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Deterministic formulas, not ML | No training data available; formulas are directly grounded in industrial engineering (queuing theory, market concentration indices). Easier to validate, audit, and explain. |
| Bob for narration only, not calculation | Bob translates numbers into language — it does not generate the numbers. This prevents hallucinated risk scores and ensures reproducible results. |
| Full demo-mode fallback | The application works end-to-end with zero external dependencies (no DB, no Bob). Judges can run it locally immediately. |
| Separate migration files per member | Prevents schema conflicts in a 3-person parallel development workflow. |
| asyncpg + pool | Non-blocking I/O consistent with FastAPI's async model. |
| Tailwind dark industrial theme | The UI is designed to look like an industrial control system, not a generic web app — dark theme, monospace fonts, score bars, severity tiers. |

## IBM Technologies Used

- **IBM Bob (watsonx.ai):** The `ibm/granite-13b-instruct-v2` model is called via the watsonx.ai REST API. Bob receives structured JSON containing pre-computed risk scores and is prompted to produce: (1) bottleneck explanations, (2) outage decision briefs, (3) supply risk summaries, and (4) combined executive risk briefs with recommendation rationale. Bob is given an explicit system role ("you explain pre-calculated results; you do not perform calculations") to prevent hallucinated numbers.
- **IBM Granite:** The underlying model for all narration, selected for its instruction-following capability and industrial/technical language comprehension.
