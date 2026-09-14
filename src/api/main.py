# src/api/main.py
"""FastAPI backend for Mission Readiness & Predictive Maintenance Copilot.

Architecture
------------
    Integration layer (asset_readiness.csv)
              ↓
        This API
              ↓
    [Dashboard — future]
              ↓
    [MCP / IBM Bob — future]

Endpoints
---------
    GET /assets
    GET /assets/{asset_id}
    GET /assets/{asset_id}/readiness
    GET /assets/{asset_id}/health
    GET /assets/{asset_id}/failure
    GET /assets/{asset_id}/rul
    GET /maintenance/priorities
    GET /missions/{mission_id}/readiness

All endpoints return real data from asset_readiness.csv.
No mock data, no hardcoded responses.

Running
-------
    # Build the readiness CSV first (if not already done):
    python -m src.integration.build_readiness

    # Start the API:
    uvicorn src.api.main:app --reload --port 8000

    # Or from project root:
    python -m src.api.main
"""

from __future__ import annotations

import pathlib
import sys
import logging
from functools import lru_cache
from typing import Any

import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root is on sys.path when run as __main__
_THIS_DIR = pathlib.Path(__file__).resolve().parent
_SRC_DIR  = _THIS_DIR.parent
_ROOT     = _SRC_DIR.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.integration.readiness_engine import (
    OUTPUT_CSV,
    MISSIONS_CSV,
    MissionReadiness,
    VALID_READINESS_STATUSES,
    VALID_PRIORITY_VALUES,
    READINESS_READY,
    normalize_mission_asset_id,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Mission Readiness & Predictive Maintenance Copilot API",
    description=(
        "Backend API exposing integrated ML model outputs for asset health, "
        "failure prediction, RUL estimation, readiness scoring, and mission "
        "readiness evaluation."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_readiness() -> pd.DataFrame:
    """Load asset_readiness.csv; raise 503 if not found."""
    if not OUTPUT_CSV.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                f"asset_readiness.csv not found at {OUTPUT_CSV}. "
                "Run: python -m src.integration.build_readiness"
            ),
        )
    df = pd.read_csv(OUTPUT_CSV)
    # Ensure asset_id is int for consistent lookups
    df["asset_id"] = df["asset_id"].astype(int)
    return df


@lru_cache(maxsize=1)
def _load_missions() -> pd.DataFrame:
    """Load missions.csv; return empty DataFrame if not found."""
    if not MISSIONS_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(MISSIONS_CSV)


def _get_asset_row(asset_id: int) -> pd.Series:
    """Return the readiness row for *asset_id* or raise 404."""
    df = _load_readiness()
    rows = df[df["asset_id"] == asset_id]
    if rows.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Asset {asset_id} not found. Valid range: 1–{df['asset_id'].max()}."
        )
    return rows.iloc[0]


def _row_to_dict(row: pd.Series) -> dict[str, Any]:
    """Convert a DataFrame row to a JSON-serialisable dict."""
    return {
        k: (None if pd.isna(v) else (int(v) if isinstance(v, float) and v == int(v) else
                                      (float(v) if isinstance(v, float) else
                                       (int(v) if hasattr(v, 'item') else v))))
        for k, v in row.items()
    }


def _invalidate_cache() -> None:
    """Clear the lru_cache so data is reloaded from disk on next request."""
    _load_readiness.cache_clear()
    _load_missions.cache_clear()


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

@app.get("/", tags=["root"])
def root() -> dict:
    """API health check."""
    return {
        "service": "Mission Readiness & Predictive Maintenance Copilot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------

@app.get("/assets", tags=["assets"], summary="List all assets with readiness summary")
def list_assets() -> list[dict]:
    """Return all assets with their readiness and priority information."""
    df = _load_readiness()
    cols = [
        "asset_id", "cycle",
        "health_status", "failure_risk", "rul_status",
        "readiness_score", "readiness_status",
        "maintenance_priority",
    ]
    available = [c for c in cols if c in df.columns]
    return df[available].to_dict(orient="records")


@app.get("/assets/{asset_id}", tags=["assets"], summary="Full record for a single asset")
def get_asset(asset_id: int) -> dict:
    """Return the complete readiness record for *asset_id*."""
    row = _get_asset_row(asset_id)
    return _row_to_dict(row)


@app.get(
    "/assets/{asset_id}/readiness",
    tags=["assets"],
    summary="Readiness details for a single asset",
)
def get_asset_readiness(asset_id: int) -> dict:
    """Return readiness score, status, reason, and recommended action."""
    row = _get_asset_row(asset_id)
    return {
        "asset_id":           int(row["asset_id"]),
        "readiness_score":    float(row["readiness_score"]),
        "readiness_status":   str(row["readiness_status"]),
        "primary_reason":     str(row["primary_reason"]),
        "recommended_action": str(row["recommended_action"]),
    }


@app.get(
    "/assets/{asset_id}/health",
    tags=["assets"],
    summary="Health model output for a single asset",
)
def get_asset_health(asset_id: int) -> dict:
    """Return health score, status, and anomaly score."""
    row = _get_asset_row(asset_id)
    return {
        "asset_id":     int(row["asset_id"]),
        "cycle":        int(row["cycle"]),
        "anomaly_score": float(row["anomaly_score"]),
        "health_score": float(row["health_score"]),
        "health_status": str(row["health_status"]),
    }


@app.get(
    "/assets/{asset_id}/failure",
    tags=["assets"],
    summary="Failure model output for a single asset",
)
def get_asset_failure(asset_id: int) -> dict:
    """Return failure probability and risk level."""
    row = _get_asset_row(asset_id)
    return {
        "asset_id":            int(row["asset_id"]),
        "cycle":               int(row["cycle"]),
        "failure_probability": float(row["failure_probability"]),
        "failure_risk":        str(row["failure_risk"]),
    }


@app.get(
    "/assets/{asset_id}/rul",
    tags=["assets"],
    summary="RUL model output for a single asset",
)
def get_asset_rul(asset_id: int) -> dict:
    """Return predicted remaining useful life and status."""
    row = _get_asset_row(asset_id)
    return {
        "asset_id":      int(row["asset_id"]),
        "cycle":         int(row["cycle"]),
        "predicted_rul": int(row["predicted_rul"]),
        "rul_status":    str(row["rul_status"]),
    }


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

@app.get(
    "/maintenance/priorities",
    tags=["maintenance"],
    summary="Assets ranked by maintenance urgency",
)
def get_maintenance_priorities() -> list[dict]:
    """Return all assets sorted by maintenance priority score (highest urgency first)."""
    df = _load_readiness()
    cols = [
        "asset_id", "cycle",
        "maintenance_priority_score", "maintenance_priority",
        "readiness_status", "primary_reason", "recommended_action",
    ]
    available = [c for c in cols if c in df.columns]
    result = (
        df[available]
        .sort_values("maintenance_priority_score", ascending=False)
        .reset_index(drop=True)
        .to_dict(orient="records")
    )
    return result


# ---------------------------------------------------------------------------
# Missions
# ---------------------------------------------------------------------------

@app.get(
    "/missions/{mission_id}/readiness",
    tags=["missions"],
    summary="Mission readiness evaluation",
)
def get_mission_readiness(mission_id: str) -> dict:
    """Evaluate whether assets are suitable for *mission_id*.

    Response includes:
    - mission_id
    - assigned_asset_id          — original operational ID (ENG-XXX)
    - assigned_asset_model_id    — numeric model ID resolved via normalize_mission_asset_id
    - assigned_asset_readiness_status / score / suitable / reason
    - recommended_asset          — lowest-risk READY asset (may equal assigned asset)
    - suitable_count / not_suitable_count
    - suitable_assets list
    """
    missions_df = _load_missions()
    if missions_df.empty:
        raise HTTPException(
            status_code=503,
            detail="missions.csv not found.",
        )

    valid_ids = missions_df["mission_id"].unique().tolist()
    if mission_id not in valid_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Mission '{mission_id}' not found. Sample valid IDs: {valid_ids[:5]}",
        )

    readiness_df = _load_readiness()
    mr = MissionReadiness(readiness_df, missions_df)
    summary = mr.mission_readiness_summary(mission_id)

    # Build suitable assets list (lightweight columns)
    suitable = mr.suitable_assets(mission_id)
    suitable_list = suitable[["asset_id", "readiness_score", "maintenance_priority"]].to_dict(
        orient="records"
    ) if not suitable.empty else []

    return {
        **summary,
        "suitable_assets": suitable_list,
    }


# ---------------------------------------------------------------------------
# Entry point for direct execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info",
    )
