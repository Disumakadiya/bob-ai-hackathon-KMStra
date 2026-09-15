# Mission Readiness & Predictive Maintenance Copilot — AstraPulse

> A fully implemented end-to-end predictive maintenance copilot built on NASA C-MAPSS FD001,
> with a FastAPI backend, React 19 frontend, and IBM Bob integration via MCP.

---

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | KMStra |
| **Track** | AI |
| **Team Lead** | Disu Makadiya — disumakadiya@gmail.com |
| **Members** | Vaibhavi Kariya, Pushti Kansara, Rutvi Shah |

---

## 🎯 Problem Statement

Maintenance and operations teams need to determine whether aircraft, vehicles, and other mission-critical equipment can meet an upcoming mission window. Sensor/HUMS data and maintenance history contain early degradation signals, but those signals are difficult to connect to component risk, remaining useful life (RUL), mission timing, and maintenance priority.

---

## 💡 Solution

**AstraPulse** is a fully implemented Mission Readiness & Predictive Maintenance Copilot.

Three ML models trained on the NASA C-MAPSS FD001 turbofan dataset score each asset:

| Model | Algorithm | Output |
|---|---|---|
| Health / Anomaly | scikit-learn `IsolationForest` (N=200) | `anomaly_score` → `health_score [0–100]` → `NORMAL / WARNING / CRITICAL` |
| Failure Risk | XGBoost `XGBClassifier` (N=300, label: RUL ≤ 30) | `failure_probability [0,1]` → `LOW / MEDIUM / HIGH` |
| RUL | scikit-learn `RandomForestRegressor` (N=200, cap=125) | `predicted_rul` (cycles) → `HEALTHY / ADVISORY / CRITICAL` |

A weighted **readiness engine** combines the three signals — `0.30 × health + 0.40 × failure_safety + 0.30 × RUL` — into a single `readiness_score [0–100]` and `readiness_status` (READY / ADVISORY / NOT_READY) for each of the 100 test-set engines.

A **FastAPI** backend serves the results via 10 REST endpoints, including a `POST /api/assess` endpoint that runs the full three-model pipeline on any unseen sensor CSV in real time.

A **React 19** frontend provides two operational views:
- **Mission Intelligence** — fleet dashboard with KPI cards and per-asset time-series charts
- **Sensor Assessment** — CSV upload or manual entry, live inference, metric cards, and a direct handoff to IBM Bob

**IBM Bob** connects via a registered **MCP server** with five tools (`get_fleet_readiness`, `get_asset_status`, `get_asset_timeseries`, `get_maintenance_priorities`, `get_mission_readiness`) so operators can ask fleet and mission readiness questions in natural language.

---

## ✨ Key Features

- **Trained asset health model** — IsolationForest on 20,631 C-MAPSS training cycles; `isolation_forest_model.joblib`
- **Trained failure risk model** — XGBoost classifier; engine-aware no-leakage split; `xgboost_failure_model.joblib`
- **Trained RUL model** — RandomForestRegressor; chronological per-engine split; capped target; `rul_model.joblib`
- **Weighted readiness engine** — derives readiness score, status, maintenance priority, and plain-English reason per asset
- **Real-time unseen-data inference** — `POST /api/assess` validates, preprocesses, and scores any multi-cycle sensor CSV
- **Fleet dashboard** — `GET /api/readiness` feeds a React 19 dashboard with Recharts time-series and status badges
- **Mission readiness queries** — `GET /missions/{id}/readiness` evaluates assigned asset and recommends lowest-risk READY alternative
- **IBM Bob MCP integration** — 5 MCP tools registered in `.bob/mcp.json`; Sensor Assessment UI pre-fills a structured Bob prompt from live inference results

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Languages** | Python 3.12, JavaScript (ES2022) |
| **ML / Data** | scikit-learn 1.9, XGBoost 3.4, Pandas 3.0, NumPy 2.5, joblib 1.5 |
| **API** | FastAPI 0.141, Uvicorn 0.41, python-multipart 0.0.22 |
| **Frontend** | React 19, Vite 8, React Router 7, Recharts 3, lucide-react |
| **Bob integration** | IBM Bob, FastMCP (`mcp` library), `.bob/mcp.json` |
| **Data** | NASA C-MAPSS FD001 (public), synthetic assets/missions/maintenance CSVs |
| **Tooling** | GitHub Actions, oxlint |

---

## 📁 Repository Structure

```
src/
├── api/
│   ├── main.py              # FastAPI app — 10 REST endpoints
│   ├── assess.py            # POST /api/assess — unseen CSV inference pipeline
│   └── mcp_server.py        # FastMCP server — 5 tools for IBM Bob
├── data/
│   ├── ingestion/
│   │   ├── load_nasa.py     # Parse raw C-MAPSS text files
│   │   ├── nasa/            # train_FD001.txt, test_FD001.txt, RUL_FD001.txt
│   │   └── synthetic/       # assets.csv, missions.csv, maintenance.csv
│   ├── preprocessing/
│   │   ├── preprocess_nasa.py   # clean(), build_train_target(), attach_test_target()
│   │   ├── feature_engineering.py  # add_features() — rolling + delta
│   │   └── validation.py    # Quality gate
│   ├── schemas/
│   │   └── nasa_schema.py   # Single source of truth for all column names/policy
│   └── outputs/
│       └── asset_readiness.csv  # 100 rows × 15 columns — API source of truth
├── models/
│   ├── health/              # IsolationForest — isolation_forest_model.joblib
│   ├── failure/             # XGBoost — xgboost_failure_model.joblib
│   └── rul/                 # RandomForest — rul_model.joblib
├── integration/
│   ├── readiness_engine.py  # ReadinessEngine + MissionReadiness
│   └── build_readiness.py   # Offline pipeline orchestrator
└── frontend/                # React 19 + Vite (LandingPage, MissionIntelligence, SensorAssessment)
docs/
├── architecture.md          # Full verified architecture diagram + component table
├── setup-guide.md           # Install + run instructions
├── solution-overview.md     # What was built and why
└── problem-statement.md
.bob/mcp.json                # MCP server registration for IBM Bob
submission.yaml
requirements.txt
```

---

## 🔌 API Endpoints

All endpoints are listed task-wise below. The full FastAPI app with automatic Swagger UI is available at `http://localhost:8000/docs`.

### 🔍 Asset Health & Status
| Method | Path | Description |
|---|---|---|
| `GET` | `/` | API health check |
| `GET` | `/assets` | List all assets with readiness summary |
| `GET` | `/assets/{asset_id}` | Full record for a single asset |
| `GET` | `/assets/{asset_id}/readiness` | Readiness details for a single asset |
| `GET` | `/assets/{asset_id}/health` | Health model output (anomaly_score, health_score, health_status) |
| `GET` | `/assets/{asset_id}/failure` | Failure model output (failure_probability, failure_risk) |
| `GET` | `/assets/{asset_id}/rul` | RUL model output (predicted_rul, rul_status) |

### 📊 Timeseries & Charts
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/assets/{id}/timeseries` | Timeseries history for charts (cycle, health_score, failure_probability, predicted_rul) |

### 🛠️ Maintenance & Priorities
| Method | Path | Description |
|---|---|---|
| `GET` | `/maintenance/priorities` | Assets ranked by maintenance urgency (sorted by priority_score desc) |

### 🚀 Mission Readiness
| Method | Path | Description |
|---|---|---|
| `GET` | `/missions/{mission_id}/readiness` | Mission readiness evaluation (assigned asset suitability + recommended alternative) |

### 📈 Fleet Dashboard
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/readiness` | Full fleet readiness for dashboard (100 assets with ENG-XXX IDs + mission context) |

### 🧪 Assessment
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/assess` | Assess unseen engine sensor CSV — validates schema, runs all 3 models, returns latest-cycle assessment per engine |

---

## ⚡ How to Run

### 1 — Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

### 2 — (Optional) Rebuild model outputs

The trained model artefacts and `asset_readiness.csv` are already committed. To retrain from scratch:

```bash
# Preprocess NASA C-MAPSS FD001
python -m src.data.preprocessing.preprocess_nasa

# Train models
python -m src.models.health.train_anomaly
python -m src.models.failure.train
python -m src.models.rul.train_rul

# Rebuild the integration CSV
python -m src.integration.build_readiness
```

### 3 — Start the API

```bash
uvicorn src.api.main:app --reload --port 8000
```

API docs available at **http://localhost:8000/docs**

### 4 — Start the frontend (separate terminal)

```bash
cd src/frontend
npm install
npm run dev
```

Frontend available at **http://localhost:5173**

### 5 — Start the Bob MCP server

The MCP server is registered in [`.bob/mcp.json`](.bob/mcp.json) and starts automatically when Bob opens this workspace. To run it manually:

```bash
python src/api/mcp_server.py
```

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

- All degradation data is from NASA C-MAPSS FD001 — a simulated single-operating-condition turbofan dataset, not real aircraft.
- The three synthetic CSVs (assets, missions, maintenance) provide operational context but are not sourced from real mission records.
- Mission suitability is based solely on `readiness_status = READY`; `missions.csv` carries no quantitative mission requirements (e.g. minimum RUL per mission type).
- SHAP explanations are not yet implemented; per-feature contribution drill-down is a planned extension.
- CORS is open (`allow_origins=["*"]`) and all endpoints are unauthenticated — suitable for local demo only, not production deployment.

---

## 🏅 What We're Most Proud Of

A complete working system where every layer traces directly to verified code:

1. **Rigorous ML pipeline** — three models trained with strict no-leakage guarantees: chronological per-engine splits, a single `nasa_schema.py` as the canonical schema contract, and capped RUL targets that focus learning on the degradation window.
2. **Readiness engine integrity** — thresholds are imported directly from each model's own `config.py` rather than duplicated, so the integration layer can never silently drift from the models.
3. **Bob as a load-bearing component** — the MCP server exposes real model outputs to Bob, and the `SensorAssessment` UI constructs a structured prompt from live inference results and hands it to Bob as an explicit UX step — not an afterthought.
4. **Clean data boundaries** — public NASA C-MAPSS data, synthetic operational context, and model outputs are kept in strictly separate files with documented provenance.

---
