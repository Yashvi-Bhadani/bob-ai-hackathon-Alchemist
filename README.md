# 🏭 Fab Bottleneck & Supply Chain Risk Advisor

> **IBM Bob AI Innovation Hackathon — Team Alchemist**
> ⚠️ All data is synthetic/demo data. No real-world facts are claimed.

---

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | Alchemist |
| **Track** | AI |
| **Team Lead** | Team Alchemist Lead — alchemist.team@example.com |
| **Members** | Member 1 (Bottleneck), Member 2 (Supply Risk), Member 3 (Dashboard) |

---

## 🎯 Problem Statement

Semiconductor fabs suffer cascading production losses when manufacturing bottlenecks and supply-chain risks coincide. Operations teams lack a unified intelligence system that simultaneously detects which tools are bottlenecks, simulates what happens when they go down, and quantifies how vulnerable the required materials are — before a crisis forces a reactive response.

---

## 💡 Solution

We built an intelligence and decision-support system that executes the complete risk workflow:

**Detect → Quantify → Simulate → Trace → Assess → Recommend → Explain**

The backend uses deterministic engineering formulas (no ML models) to compute bottleneck scores, simulate outage backlog/recovery, calculate HHI concentration, detect single points of failure, and measure inventory coverage. IBM Bob (watsonx.ai Granite) explains every result in natural language. If Bob is unavailable, the application continues working with deterministic template narration.

---

## ✨ Key Features

- **Bottleneck Detection:** Composite Bottleneck Score = 50% utilisation + 30% WIP pressure + 20% capacity pressure. Identifies `LITH-07` as the critical fab bottleneck instantly.
- **Outage Simulator:** Simulates any tool outage duration. Calculates backlog accumulation, recovery time, and downstream process delay using queuing theory formulas.
- **Supply Chain Risk Engine:** HHI (Herfindahl-Hirschman Index) for supplier concentration, SPOF detection (≥70% single-supplier share), inventory coverage in days, and geopolitical risk scoring.
- **Combined Risk Assessment:** Fuses manufacturing risk (55%) + supply chain risk (45%) into a single tier-based score with prioritised mitigation recommendations (alternate tool, lot scheduling, inventory replenishment, supplier diversification).
- **IBM Bob Narration Layer:** Context-aware natural-language briefs for bottleneck status, outage impact, supply risk, and combined risk. Full deterministic fallback ensures the app works without Bob.

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | Python 3.11+, TypeScript |
| **Frameworks** | FastAPI, React 18, Vite, Tailwind CSS, Recharts, Pydantic, NumPy, Pandas |
| **IBM Technologies** | IBM Bob, watsonx.ai, IBM Granite 13B Instruct v2 |
| **Databases** | PostgreSQL / Supabase-compatible SQL |
| **Other** | asyncpg, uvicorn, httpx, pytest |

---

## 📁 Repository Structure

```
src/
  backend/
    app/
      main.py                  ← FastAPI entry point (Member 3)
      models.py                ← Pydantic response models
      database.py              ← asyncpg pool (demo-mode fallback)
      routers/
        bottleneck.py          ← Bottleneck & outage endpoints (Member 1)
        supply.py              ← Supply risk endpoints (Member 2)
        impact.py              ← Combined risk endpoint (Member 3)
        narration.py           ← Bob narration endpoint (Member 3)
      services/
        bottleneck_service.py  ← WIP pressure, capacity pressure, outage math
        supply_service.py      ← HHI, SPOF, inventory, geopolitical risk
        impact_service.py      ← Combined risk + recommendations
        bob_service.py         ← Bob API + deterministic fallback
    tests/
      test_calculations.py     ← Unit tests for all formulas
    requirements.txt
  frontend/
    src/
      App.tsx                  ← Main dashboard layout
      api.ts                   ← Typed API client
      types.ts                 ← TypeScript types (mirror Pydantic models)
      components/
        StatusBar.tsx           ← Live risk status header
        BottleneckPanel.tsx     ← Tool scores, radar chart, bar chart
        OutageSimulator.tsx     ← Duration slider, backlog chart, downstream
        SupplyRiskPanel.tsx     ← HHI donut, SPOF, inventory, geo risk
        CombinedRiskSummary.tsx ← Radial chart + recommendations
        BobNarrationPanel.tsx   ← Bob AI explanation panel
    package.json / vite.config.ts / tailwind.config.js
  database/
    migrations/
      001_fab.sql              ← Fab tools, WIP, utilisation (Member 1)
      002_supply.sql           ← Suppliers, materials, inventory (Member 2)
      003_impact.sql           ← Outage simulation, combined risk (Member 3)
    seed.sql                   ← Synthetic demo data
  .env.example
```

---

## ⚡ How to Run

See [`docs/setup-guide.md`](docs/setup-guide.md) for full instructions.

```bash
# Backend
cd src/backend
pip install -r requirements.txt
cp ../  .env.example ../.env   # edit .env with your values
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd src/frontend
npm install
npm run dev
# Open http://localhost:5173
```

The application runs **fully in demo mode without a database or Bob credentials**.

---

## 🖥️ Demo

| Artifact | Link |
|---|---|
| 📹 Demo Video | [See demo/demo-video-link.txt](demo/demo-video-link.txt) |
| 🌐 Live Demo | [See demo/live-demo-url.txt](demo/live-demo-url.txt) |
| 🖼️ Screenshots | [See demo/screenshots/](demo/screenshots/) |
| 📊 Presentation | [See presentation/](presentation/) |

---

## ⚠️ Known Limitations

- All data is synthetic demo data — supplier names, market shares, and geopolitical entries are **invented for demonstration purposes only**
- No authentication / authorisation (prototype scope)
- Geopolitical risk module uses static scenario data, not a live feed
- Frontend tested on Chrome/Edge; mobile layout not optimised

---

## 🏅 What We're Most Proud Of

The **complete deterministic calculation pipeline** — zero ML models, all pure engineering formulas that can be independently validated. The WIP pressure queuing model, the HHI concentration index, the SPOF detection logic, and the combined risk fusion formula are all grounded in industrial engineering practice. IBM Bob is genuinely load-bearing: it receives structured JSON results and produces context-aware, decision-ready natural-language briefs — and the application degrades gracefully to template narration if Bob is unavailable.
