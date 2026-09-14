"""Connect real model outputs into the Mission Intelligence frontend.

Reads the actual model artifacts / score CSVs and writes the two JSON files
the frontend imports (src/frontend/src/data/actualData.json and
timeSeriesData.json):

  health   -> IsolationForest (saved model) re-scored on the preprocessed
              FD001 TEST split, normalised with compute_health (fixed bounds
              from health_config).
  failure  -> src/models/failure/failure_scores.csv (test-set XGBoost inference).
  RUL      -> saved RandomForest RUL model run over every test row, using the
              same transform as train_rul (round, clip >= 0).

All three signals share the same (unit, cycle) grid (FD001 test split) so
the dashboard is internally coherent.

Run from the repo root:
    python -m src.generate_frontend_data
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sys

# Repo root on the import path so `src.*` packages resolve.
_SRC = Path(__file__).resolve().parent
_ROOT = _SRC.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.data.schemas.nasa_schema import (  # noqa: E402
    CYCLE,
    KEPT_FEATURE_COLUMNS,
    PROCESSED_TEST_FILE,
    UNIT,
)
from src.models.health.anomaly_detector import AnomalyDetector  # noqa: E402
from src.models.health.health_scoring import compute_health  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_PREPROC_DIR = _SRC / "data" / "preprocessing"
_SYNTH_DIR = _SRC / "data" / "ingestion" / "synthetic"
_HEALTH_DIR = _SRC / "models" / "health"
_FAILURE_DIR = _SRC / "models" / "failure"
_RUL_DIR = _SRC / "models" / "rul"
_OUT_DIR = _SRC / "frontend" / "src" / "data"

_HEALTH_MODEL = _HEALTH_DIR / "isolation_forest_model.joblib"
_HEALTH_SCORES = _HEALTH_DIR / "health_scores.csv"
_FAILURE_SCORES = _FAILURE_DIR / "failure_scores.csv"
_RUL_MODEL = _RUL_DIR / "rul_model.joblib"
_RUL_PREDICTIONS = _RUL_DIR / "rul_predictions.csv"

_HEALTHY_RUL_THRESHOLD = 100.0  # from src/models/rul/config.py THRESHOLD_HEALTHY


def _to_asset_id(unit: pd.Series) -> pd.Series:
    """Map integer unit IDs to the 'ENG-xxx' identifier used by the frontend."""
    return unit.astype(int).apply(lambda u: f"ENG-{u:03d}")


# ---------------------------------------------------------------------------
# Model signals (all on the FD001 TEST grid)
# ---------------------------------------------------------------------------

def _score_health_on_test(test: pd.DataFrame) -> pd.DataFrame:
    """Re-score the saved IsolationForest on the test split -> health_score."""
    detector = AnomalyDetector.load(_HEALTH_MODEL)
    anomaly = detector.anomaly_score(test[KEPT_FEATURE_COLUMNS])
    frame = pd.DataFrame({UNIT: test[UNIT].values, CYCLE: test[CYCLE].values})
    frame["anomaly_score"] = anomaly
    return compute_health(frame)[[UNIT, CYCLE, "anomaly_score", "health_score"]]


def _load_failure_scores() -> pd.DataFrame:
    """Test-set failure probabilities from the XGBoost failure module."""
    frame = pd.read_csv(_FAILURE_SCORES)
    required = {UNIT, CYCLE, "failure_probability"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            f"failure_scores.csv missing columns {missing}. "
            "Run the failure module first (src/models/failure/_integration_test.py)."
        )
    return frame[[UNIT, CYCLE, "failure_probability"]]


def _predict_rul_per_cycle(test: pd.DataFrame) -> pd.DataFrame:
    """Run the saved RandomForest RUL model over every test row."""
    if not _RUL_MODEL.exists():
        raise FileNotFoundError(
            f"RUL model not found at {_RUL_MODEL}. "
            "Run: python -m src.models.rul.train_rul"
        )
    model = joblib.load(_RUL_MODEL)
    feature_cols = [c for c in test.columns if c not in (UNIT, CYCLE, "rul")]
    pred_raw = model.predict(test[feature_cols].to_numpy())
    pred = np.clip(np.round(pred_raw), 0, None).astype("int32")
    frame = pd.DataFrame({UNIT: test[UNIT].values, CYCLE: test[CYCLE].values})
    frame["predicted_rul"] = pred
    return frame


# ---------------------------------------------------------------------------
# Operational context
# ---------------------------------------------------------------------------

def _load_assets() -> pd.DataFrame:
    return pd.read_csv(_SYNTH_DIR / "assets.csv")


def _load_next_missions() -> pd.DataFrame:
    missions = pd.read_csv(_SYNTH_DIR / "missions.csv")
    missions["mission_date"] = pd.to_datetime(missions["mission_date"])
    next_missions = (
        missions.sort_values("mission_date")
        .groupby("asset_id")
        .first()
        .reset_index()[["asset_id", "mission_type", "mission_criticality", "mission_date"]]
    )
    next_missions["mission_date"] = pd.to_datetime(next_missions["mission_date"]).dt.strftime("%Y-%m-%d")
    return next_missions


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def generate_frontend_data() -> None:
    """Regenerate actualData.json and timeSeriesData.json from model outputs."""
    print("Loading preprocessed test data …")
    test = pd.read_csv(_PREPROC_DIR / PROCESSED_TEST_FILE)
    print(f"  test: {test.shape[0]} rows × {test.shape[1]} cols")

    # --- per-cycle signals (aligned on the test grid) ---
    print("Scoring health (IsolationForest on test) …")
    health = _score_health_on_test(test)
    print("Loading failure scores (test) …")
    failure = _load_failure_scores()
    print("Predicting RUL per cycle (RandomForest) …")
    rul = _predict_rul_per_cycle(test)

    series = (
        test[[UNIT, CYCLE]]
        .merge(health, on=[UNIT, CYCLE], how="left")
        .merge(failure, on=[UNIT, CYCLE], how="left")
        .merge(rul, on=[UNIT, CYCLE], how="left")
    )
    series["asset_id"] = _to_asset_id(series[UNIT])
    series["health_score"] = series["health_score"].round(2)
    series["anomaly_score"] = series["anomaly_score"].round(6)
    series["failure_probability"] = series["failure_probability"].round(6)
    series = series.fillna(-1)
    print(f"  series: {len(series)} rows over {series['asset_id'].nunique()} assets")

    # --- per-asset snapshot (last test cycle per engine) ---
    snap = series.sort_values([UNIT, CYCLE]).groupby(UNIT).last().reset_index()
    snap["asset_id"] = _to_asset_id(snap[UNIT])

    assets = _load_assets()
    assets["asset_id"] = assets["asset_id"].astype(str)
    next_missions = _load_next_missions()
    next_missions["asset_id"] = next_missions["asset_id"].astype(str)

    actual = (
        assets.merge(next_missions, on="asset_id", how="left")
        .merge(
            snap[["asset_id", "health_score", "anomaly_score",
                  "failure_probability", "predicted_rul"]],
            on="asset_id",
            how="left",
        )
    )
    actual = actual.fillna(-1)
    print(f"  snapshot: {len(actual)} assets")

    # --- time series (last 50 cycles per asset used by the page) ---
    ts_cols = ["asset_id", "cycle", "health_score", "failure_probability", "predicted_rul"]
    ts_dict = {
        asset_id: group[ts_cols].to_dict(orient="records")
        for asset_id, group in series.groupby("asset_id")
    }

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    actual_path = _OUT_DIR / "actualData.json"
    series_path = _OUT_DIR / "timeSeriesData.json"
    actual_path.write_text(json.dumps(actual.to_dict(orient="records")), "utf-8")
    series_path.write_text(json.dumps(ts_dict), "utf-8")
    print(f"Wrote {actual_path}")
    print(f"Wrote {series_path}")

    # --- summary sanity checks ---
    print("\nSanity check — per-asset snapshot:")
    print(actual[["asset_id", "health_score", "failure_probability", "predicted_rul"]].describe().round(2).to_string())
    n_healthy = int((actual["predicted_rul"] > _HEALTHY_RUL_THRESHOLD).sum())
    print(f"  assets with predicted_rul > {_HEALTHY_RUL_THRESHOLD:.0f} (HEALTHY): {n_healthy}")


if __name__ == "__main__":
    generate_frontend_data()