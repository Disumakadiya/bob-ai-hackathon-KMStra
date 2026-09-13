# Source Code

The source-code directory is reserved for the future implementation. It currently
contains no application, model, notebook, test, or dependency files.

## 📊 Project: Bob Copilot - Defense & Aerospace

| Field                 | Value                                                                                                                                                      |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Project Title**     | Mission Readiness & Predictive Maintenance Copilot                                                                                                         |
| **Track**             | Defense & Aerospace - Mission Readiness & Predictive Maintenance                                                                                           |
| **Team Lead**         | Disu Makadiya                                                                                                                                              |
| **Team Members**      | Vaibhavi Karia, Pushti Kansara, Rutvi Shah                                                                                                                 |
| **Problem**           | Teams need to connect condition signals, maintenance history, mission timing, and criticality when assessing readiness.                                    |
| **Proposed solution** | Use NASA C-MAPSS plus clearly identified synthetic operational context with planned anomaly, failure-risk, RUL, explainability, and prioritization layers. |

## Structure Guidelines

When implementation begins, organize the code around the data and model
ownership boundaries below. These are target conventions, not current files:

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

## Intended Important Files to Include

- `requirements.txt` — planned Python dependency manifest
- `.env.example` — template for environment variables (NEVER commit `.env`)
- Any database migration files
- Configuration files

## What NOT to Include in src/

- `.env` files with real secrets
- Large binary files (use Git LFS or link externally)
- `node_modules/` or `venv/` (these are in `.gitignore`)
- Build artifacts (`dist/`, `build/`, `__pycache__/`)

No implementation code or generated model results have been added as part of
this documentation task.
