# Source Code

The `src/` directory contains the full AstraPulse predictive maintenance copilot implementation, organized into functional modules:

- **`api/`** — FastAPI application with 12 REST endpoints serving asset health, failure risk, RUL models, readiness engine, maintenance priorities, mission readiness, and CSV assessment
  - `main.py` — FastAPI app factory with all endpoints
  - `assess.py` — POST `/api/assess` pipeline
  - `mcp_server.py` — FastMCP server — 5 tools for IBM Bob
- **`data/`** — Data pipeline
  - `ingestion/` — NASA C-MAPSS parsing, synthetic CSVs
  - `preprocessing/` — clean(), feature_engineering(), validation
  - `schemas/` — nasa_schema.py (single source of truth)
- **`models/`** — Trained model artefacts
  - `health/` — `isolation_forest_model.joblib`
  - `failure/` — `xgboost_failure_model.joblib`
  - `rul/` — `rul_model.joblib`
- **`integration/`** — Orchestration
  - `readiness_engine.py` — ReadinessEngine + MissionReadiness
  - `build_readiness.py` — Offline pipeline orchestrator
- **`frontend/`** — React 19 + Vite (LandingPage, MissionIntelligence, SensorAssessment)

## MCP Tool Mapping (`.bob/mcp.json`)

| MCP Tool | API Endpoint |
|---|---|
| `get_fleet_readiness()` | `GET /api/readiness` |
| `get_asset_status(asset_id)` | `GET /assets/{id}` |
| `get_asset_timeseries(asset_id)` | `GET /api/assets/{id}/timeseries` |
| `get_maintenance_priorities()` | `GET /maintenance/priorities` |
| `get_mission_readiness(mission_id)` | `GET /missions/{id}/readiness` |

## Guidelines

- Keep model‑config thresholds imported from each model's own `config.py` rather than duplicated
- When adding new API routes, edit `src/api/main.py` and update `.bob/mcp.json`
- Keep `requirements.txt` and `requirements-dev.txt` in sync
- Do not commit `.env` files with real secrets
- Do not commit `node_modules/` or `venv/`
- Do not commit build artifacts (`dist/`, `build/`, `__pycache__/`)