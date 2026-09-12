# Source Code

Place all your project's source code in this folder.

## 📊 Project: Bob Copilot - Defense & Aerospace

| Field | Value |
|---|---|
| **Project Title** | Bob Copilot - Mission Readiness & Predictive Maintenance |
| **Track** | Defense & Aerospace - Mission Readiness & Predictive Maintenance |
| **Team Lead** | Disu Makadiya |
| **Team Members** | Vaibhavi Karia, Pushti Kansara, Rutvi Shah |
| **Problem** | Military organisations cannot reliably determine whether aircraft, vehicles, and equipment are mission-ready. Maintenance runs on fixed calendar schedules regardless of actual component condition. HUMS sensor data that could predict failures weeks in advance sits unanalysed. |
| **Solution** | Bob Copilot ingests sensor data and service records to identify non-ready assets, explain each readiness issue, predict which components will fail before the next mission window, and recommend a prioritised maintenance plan. |
| **Annual Maintenance Cost** | US military spends $90B/year on maintenance - shifting to predictive approaches saves billions |

## Structure Guidelines

Organize your code logically. Here are common patterns — use whatever fits
your project:

### Web Application
```
src/
  backend/        ← API server code
  frontend/       ← UI code
  shared/         ← Shared utilities/types
```

### Data / AI Project
```
src/
  data/           ← Data ingestion / preprocessing
  models/         ← ML model code
  api/            ← Serving layer
  notebooks/      ← Jupyter notebooks (exploration)
```

### CLI / Script-based Tool
```
src/
  cli/            ← CLI entry points
  lib/            ← Core logic
  utils/          ← Helpers
```

## Important Files to Include

- `requirements.txt` or `package.json` — dependency manifest
- `.env.example` — template for environment variables (NEVER commit `.env`)
- Any database migration files
- Configuration files

## What NOT to Include in src/

- `.env` files with real secrets
- Large binary files (use Git LFS or link externally)
- `node_modules/` or `venv/` (these are in `.gitignore`)
- Build artifacts (`dist/`, `build/`, `__pycache__/`)
