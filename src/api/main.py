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
from fastapi import FastAPI, HTTPException, UploadFile, File
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
    allow_methods=["GET", "POST"],
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


@app.get(
    "/api/assets/{asset_id}/timeseries",
    tags=["assets"],
    summary="Get timeseries history for an asset",
)
def get_asset_timeseries(asset_id: str) -> list[dict]:
    """Return historical time series data for charts."""
    try:
        if asset_id.startswith("ENG-"):
            numeric_id = int(asset_id.replace("ENG-", ""))
        else:
            numeric_id = int(asset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid asset_id format.")

    import pandas as pd
    import pathlib
    
    base_dir = pathlib.Path(__file__).resolve().parents[2]
    health_path = base_dir / "src" / "models" / "health" / "health_scores.csv"
    failure_path = base_dir / "src" / "models" / "failure" / "failure_scores.csv"
    rul_path = base_dir / "src" / "models" / "rul" / "rul_predictions.csv"
    
    if not health_path.exists() or not failure_path.exists():
         raise HTTPException(status_code=503, detail="Timeseries data not found.")
    
    df_health = pd.read_csv(health_path)
    df_failure = pd.read_csv(failure_path)
    
    df_health = df_health[df_health["unit"] == numeric_id]
    df_failure = df_failure[df_failure["unit"] == numeric_id]
    
    if df_health.empty:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found in timeseries data.")
        
    df_merged = pd.merge(df_health, df_failure, on=["unit", "cycle"], how="left")
    
    if rul_path.exists():
        df_rul = pd.read_csv(rul_path)
        if "unit" in df_rul.columns:
            df_rul = df_rul.rename(columns={"unit": "asset_id"})
        if "asset_id" in df_rul.columns:
            df_merged = pd.merge(
                df_merged,
                df_rul[["asset_id", "cycle", "predicted_rul"]],
                left_on=["unit", "cycle"],
                right_on=["asset_id", "cycle"],
                how="left"
            )
    
    records = []
    for _, row in df_merged.iterrows():
        record = {
            "asset_id": asset_id,
            "cycle": int(row["cycle"]),
            "health_score": float(row["health_score"]) if pd.notna(row.get("health_score")) else -1,
            "failure_probability": float(row["failure_probability"]) if pd.notna(row.get("failure_probability")) else -1,
        }
        if "predicted_rul" in row and pd.notna(row["predicted_rul"]):
            record["predicted_rul"] = float(row["predicted_rul"])
        else:
            record["predicted_rul"] = -1
        records.append(record)
        
    return records


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
# Readiness fleet endpoint (consumed by Mission Intelligence frontend)
# ---------------------------------------------------------------------------

@app.get("/api/readiness", tags=["readiness"], summary="Full fleet readiness for the dashboard")
def get_fleet_readiness() -> list[dict]:
    """Return one record per asset combining all readiness fields plus next-mission context.

    asset_id is returned in ENG-XXX format so the frontend can display it directly.
    readiness_status: READY | ADVISORY | NOT_READY (from the readiness engine).
    """
    df = _load_readiness().copy()
    missions_df = _load_missions()

    # Format asset_id as ENG-XXX
    df["asset_id"] = df["asset_id"].apply(lambda x: f"ENG-{int(x):03d}")

    # Join next mission per asset (earliest mission_date)
    if not missions_df.empty:
        missions_df = missions_df.copy()
        missions_df["mission_date_dt"] = pd.to_datetime(
            missions_df["mission_date"], errors="coerce"
        )
        next_missions = (
            missions_df.sort_values("mission_date_dt")
            .groupby("asset_id")
            .first()
            .reset_index()[
                ["asset_id", "mission_type", "mission_criticality", "mission_date"]
            ]
        )
        next_missions["mission_date"] = pd.to_datetime(
            next_missions["mission_date"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")
        df = df.merge(next_missions, on="asset_id", how="left")

    df = df.fillna("")
    return df.to_dict(orient="records")


# ---------------------------------------------------------------------------
# Sensor Assessment (unseen engine CSV)
# ---------------------------------------------------------------------------

@app.post("/api/assess", tags=["assess"], summary="Assess unseen engine sensor history")
async def assess_engine(file: UploadFile = File(...)) -> dict | list:
    """Accept an unseen engine sensor-history CSV and return combined model output.

    The CSV must contain multiple cycles of sensor history using the exact
    columns required by the pipeline:

        unit, cycle, op1, op2, [op3,] s1..s21  (full raw, 26 cols)
      OR
        unit, cycle, op1, op2, s2–s4, s6–s9, s11–s15, s17, s20–s21  (cleaned, 19 cols)

    At least 2 cycles are required for rolling/delta features.
    RUL must NOT appear as an input column.

    Returns the latest-cycle assessment per engine unit (dict for single
    engine, list for multiple engines).
    """
    from src.api.assess import assess_sensor_data

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be a CSV (filename must end with .csv).",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = assess_sensor_data(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        log.exception("Unexpected error during sensor assessment")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during assessment: {type(exc).__name__}",
        )

    return result


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
