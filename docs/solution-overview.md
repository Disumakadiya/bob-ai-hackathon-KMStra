# Solution Overview: Mission Readiness & Predictive Maintenance Copilot

## What We Built

**AstraPulse** is a fully implemented end-to-end Mission Readiness & Predictive
Maintenance Copilot. It turns raw turbofan sensor histories into per-asset
readiness decisions, maintenance priorities, and mission suitability assessments
— and exposes all of that to IBM Bob through a registered MCP server so
operators can ask questions in natural language.

## How It Works

### 1 — Data pipeline (`src/data/`)

NASA C-MAPSS FD001 raw text files (100 turbofan engines, 26 columns) are loaded
by `load_nasa.py`, cleaned by `preprocess_nasa.py` (7 constant columns dropped,
RUL target built from `max_cycle − cycle`), and enriched by
`feature_engineering.py` (per-engine rolling mean/std/min/max over 5 cycles +
cycle-delta for each of the 17 surviving base columns → 85 derived features).
All column names and feature policy live in a single `nasa_schema.py` schema
module so every pipeline stage shares the same contract.

Three synthetic CSV files (`assets.csv`, `missions.csv`, `maintenance.csv`)
provide operational context: asset metadata, mission schedules, and maintenance
history.

### 2 — Three trained ML models (`src/models/`)

| Model | Algorithm | Training detail | Output |
|---|---|---|---|
| **Health** | scikit-learn `IsolationForest` N=200 | Trained on 20,631 FD001 training cycles | `anomaly_score` → `health_score [0–100]` → NORMAL / WARNING / CRITICAL |
| **Failure Risk** | XGBoost `XGBClassifier` N=300, lr=0.05 | Label: RUL ≤ 30 cycles; engine-aware no-leakage split | `failure_probability [0,1]` → LOW / MEDIUM / HIGH |
| **RUL** | scikit-learn `RandomForestRegressor` N=200 | Chronological per-engine split; RUL capped at 125 cycles during training | `predicted_rul` (cycles) → HEALTHY / ADVISORY / CRITICAL |

All three models are trained with strict no-future-leakage guarantees: data is
split by engine ID (not row), chronologically, so no later cycle of an engine
ever informs an earlier prediction. The RUL target is capped at 125 cycles to
focus the regressor on the operationally relevant degradation window.

### 3 — Readiness engine (`src/integration/`)

`readiness_engine.py` merges the three model outputs by `(asset_id, cycle)` and
computes a weighted readiness score for each of the 100 test-set engines:

```
readiness_score = 100 × (
    0.30 × health_score / 100          +
    0.40 × (1 − failure_probability)   +
    0.30 × min(predicted_rul, 100) / 100
)
```

Thresholds are imported directly from each model's own `config.py` so the
integration layer can never silently drift from the models. The score maps to
`readiness_status` (READY ≥ 70 / ADVISORY ≥ 40 / NOT_READY < 40) and a
`maintenance_priority` (IMMEDIATE / HIGH / MEDIUM / LOW). A `primary_reason`
string and `recommended_action` are also derived. Output is saved to
`src/data/outputs/asset_readiness.csv` (100 rows × 15 columns).

### 4 — REST API (`src/api/main.py`) and unseen-data inference (`src/api/assess.py`)

FastAPI exposes 10 endpoints that read from `asset_readiness.csv` in memory.
The `POST /api/assess` endpoint accepts any unseen sensor CSV, runs the full
preprocessing pipeline (`clean → add_features`), scores with all three loaded
models, and returns the latest-cycle assessment per engine — without retraining.
Input accepts either the full raw 26-column format or the 19-column cleaned
format; at least 2 cycles are required for rolling/delta features.

### 5 — React frontend (`src/frontend/`)

Three pages built with React 19, Vite, React Router, and Recharts:

- **LandingPage** `/` — product overview
- **MissionIntelligence** `/mission-intelligence` — live fleet dashboard: KPI
  cards (READY / ADVISORY / NOT_READY counts), searchable asset list with
  status badges, per-asset Recharts time-series for health and failure probability
- **SensorAssessment** `/sensor-assessment` — CSV drag-and-drop or manual
  cycle-by-cycle entry, live metric cards (health score, failure probability,
  predicted RUL, anomaly score), risk explanation narrative, Recharts historical
  charts, and an "Ask Bob" button that pre-fills a structured context prompt

### 6 — IBM Bob MCP integration (`.bob/mcp.json`, `src/api/mcp_server.py`)

Five tools are registered via FastMCP and wired to the FastAPI layer:

| Tool | API endpoint |
|---|---|
| `get_fleet_readiness()` | `GET /api/readiness` |
| `get_asset_status(asset_id)` | `GET /assets/{id}` |
| `get_asset_timeseries(asset_id)` | `GET /api/assets/{id}/timeseries` |
| `get_maintenance_priorities()` | `GET /maintenance/priorities` |
| `get_mission_readiness(mission_id)` | `GET /missions/{id}/readiness` |

Bob calls these tools to ground its answers in real model data. The
`SensorAssessment` page constructs a structured `buildBobContext()` string from
all three live inference results (with an explicit limitations disclaimer) and
opens the Bob modal pre-populated — making the human-to-AI handoff a deliberate
UX step.

## Architecture Diagram

See [`architecture.md`](architecture.md) for the full verified Mermaid diagram,
component table, and end-to-end data flow.

## Key Design Decisions

| Decision | Rationale |
|---|---|
| `nasa_schema.py` as the single source of truth | Every pipeline stage imports column names and feature policy from one place; adding a feature requires a single-file change with no risk of silent schema drift |
| Thresholds imported from model `config.py` files into the integration layer | The readiness engine reuses the models' own thresholds (NORMAL ≥ 70, CRITICAL ≤ 30 cycles) rather than duplicating them, so they cannot drift independently |
| Offline training / online serving separation | Model `.joblib` artefacts are written once; the API only loads and scores — it never retrains; `asset_readiness.csv` is the single serialised integration output |
| NASA C-MAPSS FD001 (not FD002–FD004) | One operating condition and one fault mode for a cleaner initial model; the schema is parameterised so additional subsets can be added without rewriting the pipeline |
| RandomForestRegressor for RUL (not XGBoost) | Random Forest with chronological per-engine split and a capped target (125 cycles) gives stable predictions across the degradation window; XGBoost was considered and can replace it without changing any interface |
| Bob MCP integration over a separate LLM API | The MCP pattern means Bob calls the same verified API that the dashboard uses — there is no separate inference path that could give Bob stale or fabricated data |

## IBM Technologies Used

**IBM Bob** is the AI development partner used throughout design, implementation,
documentation, code review, and testing. It is also a runtime component: the
registered MCP server in `.bob/mcp.json` means Bob has direct, tool-mediated
access to live fleet data, maintenance priorities, and mission readiness results.

Bob is not the predictive model. The predictive work is done by the three
scikit-learn / XGBoost models trained on NASA C-MAPSS data. Bob interprets and
communicates their outputs.
