# Setup Guide

> **This guide is for local development and hackathon evaluation.**
> The application runs **fully in demo mode** without a database or Bob credentials.

## Prerequisites

- [ ] Python 3.11 or higher
- [ ] Node.js 18 or higher (for frontend)
- [ ] pip (Python package manager)
- [ ] npm (Node package manager)
- [ ] PostgreSQL (optional — app works without it in demo mode)
- [ ] IBM Cloud account with watsonx.ai access (optional — app uses template fallback without it)

## Environment Variables

```bash
cd src
cp .env.example .env
# Edit .env with your values (all are optional for demo mode)
```

| Variable | Description | Required for |
|---|---|---|
| `BOB_API_KEY` | IBM Cloud API key | Live Bob narration |
| `BOB_PROJECT_ID` | watsonx.ai project ID | Live Bob narration |
| `BOB_API_URL` | watsonx.ai inference endpoint | Live Bob narration |
| `BOB_MODEL_ID` | Model ID (default: ibm/granite-13b-instruct-v2) | Live Bob narration |
| `DATABASE_URL` | PostgreSQL connection string | Live database data |
| `ALLOWED_ORIGINS` | CORS origins (default: http://localhost:5173) | Frontend cross-origin |

> 💡 **Without any credentials:** the app uses built-in synthetic demo data and deterministic template narration. Everything is fully functional.

## Quick Start (Demo Mode — No Credentials Needed)

### Backend

```bash
# From repo root
cd src/backend

# Create virtual environment (recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start server (no .env needed for demo mode)
uvicorn app.main:app --reload --port 8000
```

Backend will be running at: `http://localhost:8000`
API docs available at: `http://localhost:8000/docs`

### Frontend

```bash
# From repo root (in a separate terminal)
cd src/frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend will be running at: `http://localhost:5173`

Open `http://localhost:5173` in your browser to see the dashboard.

---

## With PostgreSQL Database

```bash
# 1. Create database
createdb fab_risk_db

# 2. Run migrations in order
psql -d fab_risk_db -f src/database/migrations/001_fab.sql
psql -d fab_risk_db -f src/database/migrations/002_supply.sql
psql -d fab_risk_db -f src/database/migrations/003_impact.sql

# 3. Load synthetic demo data
psql -d fab_risk_db -f src/database/seed.sql

# 4. Set DATABASE_URL in src/.env
# DATABASE_URL=postgresql://postgres:password@localhost:5432/fab_risk_db

# 5. Start the backend
cd src/backend
uvicorn app.main:app --reload --port 8000
```

## With IBM Bob (watsonx.ai)

```bash
# In src/.env:
BOB_API_KEY=your_ibm_cloud_api_key
BOB_PROJECT_ID=your_watsonx_project_id
BOB_MODEL_ID=ibm/granite-13b-instruct-v2

# Restart the backend — Bob will be called for narration automatically.
# The TEMPLATE FALLBACK badge in the UI will change to the model name.
```

## Running Tests

```bash
cd src/backend
pytest tests/ -v
```

Expected output: All tests pass covering WIP pressure, capacity pressure, bottleneck scoring, outage simulation (including impossible-recovery case), HHI calculation, SPOF detection, and inventory coverage tiers.

## Running the Frontend Build

```bash
cd src/frontend
npm run build
# Output in src/frontend/dist/
```

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'app'` | Run uvicorn from `src/backend/` directory, not from `src/` |
| `Cannot find module 'recharts'` | Run `npm install` inside `src/frontend/` |
| `API 404 errors in frontend` | Confirm backend is running on port 8000; check Vite proxy in `vite.config.ts` |
| Bob narration shows TEMPLATE FALLBACK | Expected behaviour — set `BOB_API_KEY` and `BOB_PROJECT_ID` in `.env` for live Bob |
| Database connection refused | Expected in demo mode — app uses built-in data. Set `DATABASE_URL` for live mode. |
| `uvicorn: command not found` | Activate virtual environment or install: `pip install uvicorn` |
