# Setup Guide

> **This file is read by the automated evaluation pipeline. Be precise and complete.**

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.12+ | Tested on 3.12; 3.11 should also work |
| Node.js | 18+ | Required for the React frontend only |
| npm | 9+ | Comes with Node.js |
| Git | any | To clone the repository |

## Environment Variables

Copy `src/.env.example` to `src/.env` and fill in values only if you need them.
The application runs fully without any environment variables for local demo purposes.

| Variable | Description | Required |
|---|---|---|
| `APP_PORT` | API server port (default: 8000) | No |
| `APP_ENV` | `development` or `production` | No |
| `WATSONX_API_KEY` | IBM watsonx.ai key (not used by current code) | No |
| `DATABASE_URL` | PostgreSQL URL (no database is used; flat CSV only) | No |

> The application uses **no database**. All persistent data is flat CSV files in `src/data/`.

## Installation

### Python dependencies

```bash
# From the repository root
python -m pip install -r requirements.txt
```

This installs: `numpy`, `pandas`, `scikit-learn`, `xgboost`, `joblib`, `fastapi`, `uvicorn`, `python-multipart`, `mcp`.

### Frontend dependencies

```bash
cd src/frontend
npm install
```

## Running the Application

### Step 1 — Start the FastAPI backend

```bash
# From the repository root
uvicorn src.api.main:app --reload --port 8000
```

The API starts at **http://localhost:8000**.
Interactive docs are available at **http://localhost:8000/docs**.

The API reads from `src/data/outputs/asset_readiness.csv` (already committed).
If that file is missing, run `python -m src.integration.build_readiness` first (see below).

### Step 2 — Start the React frontend

In a **separate terminal**:

```bash
cd src/frontend
npm run dev
```

The frontend starts at **http://localhost:5173** and proxies `/api/*` to the backend on port 8000.

### Step 3 — IBM Bob MCP server

The MCP server is declared in [`.bob/mcp.json`](../.bob/mcp.json) and starts automatically when IBM Bob opens this workspace. To verify or run it manually:

```bash
python src/api/mcp_server.py
```

## Rebuilding Model Outputs (Optional)

The trained model artefacts (`.joblib` files) and `asset_readiness.csv` are already committed to the repository. To reproduce them from scratch:

```bash
# 1. Preprocess NASA C-MAPSS FD001 raw text files
python -m src.data.preprocessing.preprocess_nasa

# 2. Train the health / anomaly model (IsolationForest)
python -m src.models.health.train_anomaly

# 3. Train the failure risk model (XGBoost)
python -m src.models.failure.train

# 4. Train the RUL model (RandomForestRegressor)
python -m src.models.rul.train_rul

# 5. Rebuild the integration CSV (asset_readiness.csv)
python -m src.integration.build_readiness
```

## Running Tests

```bash
# API endpoint tests (requires running backend on port 8000)
python test_endpoints.py

# Sensor assessment pipeline test
python test_assess.py

# Health model unit tests
python -m pytest src/models/health/test_health_scoring.py

# Failure model integration test
python -m pytest src/models/failure/_integration_test.py

# Integration layer test
python -m pytest src/integration/test_readiness.py
```

## Quick Demo

Once the backend and frontend are running:

1. Open **http://localhost:5173/mission-intelligence** — fleet dashboard showing all 100 assets with readiness status, health scores, failure probability, and RUL.
2. Open **http://localhost:5173/sensor-assessment** — upload `unseen_asset_test_20_cycles.csv` from the repository root to run real-time inference on an unseen engine.
3. Ask IBM Bob (via the MCP integration): *"Which assets need immediate maintenance?"* or *"Can ENG-047 fly mission MIS-053?"*

## Troubleshooting

| Issue | Solution |
|---|---|
| `503 asset_readiness.csv not found` | Run `python -m src.integration.build_readiness` |
| `FileNotFoundError: isolation_forest_model.joblib` | Run `python -m src.models.health.train_anomaly` |
| Frontend shows `API error 503` | Ensure the FastAPI backend is running on port 8000 |
| `POST /api/assess` returns 422 | CSV must have ≥ 2 cycles and no `rul` column; see `src/api/assess.py` for schema |
| MCP tools not visible in Bob | Check `.bob/mcp.json` exists and `python src/api/mcp_server.py` runs without error |
