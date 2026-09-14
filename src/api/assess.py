# src/api/assess.py
"""Sensor assessment engine for unseen engine data.

Accepts a CSV with multi-cycle sensor history, runs the existing
preprocessing + feature engineering pipeline, and scores with all 3
trained models (Health / Failure / RUL) — without retraining.

Pipeline
--------
    CSV bytes
      → parse + validate (schema, types, nulls, history length)
      → clean  (drop constant columns, sort by unit/cycle)
      → add_features  (rolling mean/std/min/max + delta per engine)
      → Health  model  → anomaly_score → health_score, health_status
      → Failure model  → failure_probability → failure_status
      → RUL     model  → predicted_rul_cycles
      → return latest cycle per engine

Input schema
------------
The CSV must contain either:
  • Full raw format  (26 columns):  unit, cycle, op1, op2, op3, s1 … s21
  • Cleaned format   (19 columns):  unit, cycle, op1, op2, s2, s3, s4,
                                     s6, s7, s8, s9, s11, s12, s13, s14,
                                     s15, s17, s20, s21

At least 2 cycles are required because rolling / delta features need
more than one observation.

RUL must NOT appear as an input column.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import joblib
import numpy as np
import pandas as pd

from src.data.preprocessing.feature_engineering import add_features
from src.data.preprocessing.preprocess_nasa import clean
from src.data.schemas.nasa_schema import (
    CYCLE,
    ID_COLUMNS,
    KEPT_FEATURE_COLUMNS,
    RAW_COLUMNS,
    UNIT,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MIN_CYCLES: int = 2

_RUL_MODEL_PATH: Path = (
    Path(__file__).resolve().parent.parent / "models" / "rul" / "rul_model.joblib"
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_input(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Check schema, data quality and constraints.  Read-only on *df*."""
    errors: List[str] = []
    cols = set(df.columns)

    # -- RUL must never be an input --
    if "rul" in cols:
        errors.append(
            "Column 'rul' found. RUL must not be provided as input; "
            "it is derived only during training."
        )

    # -- Required ID columns --
    for c in ("unit", "cycle"):
        if c not in cols:
            errors.append(f"Missing required column: '{c}'")
    if errors:
        return False, errors

    # -- Schema match: full raw OR cleaned format --
    raw_lower = {c.lower() for c in RAW_COLUMNS}
    kept_with_ids = {c.lower() for c in KEPT_FEATURE_COLUMNS} | {"unit", "cycle"}
    has_full = raw_lower.issubset(cols)
    has_clean = kept_with_ids.issubset(cols)
    if not has_full and not has_clean:
        errors.append(
            "CSV columns do not match expected schema. "
            f"Provide either the full raw format ({len(RAW_COLUMNS)} columns: "
            "unit, cycle, op1-op3, s1-s21) or the cleaned format "
            f"({len(KEPT_FEATURE_COLUMNS) + 2} columns: unit, cycle, "
            "op1, op2, s2-s4, s6-s9, s11-s15, s17, s20-s21)."
        )

    # -- Non-empty --
    if len(df) == 0:
        errors.append("CSV contains no data rows.")
        return False, errors

    # -- Sufficient history for rolling / delta features --
    n_cycles = int(df[CYCLE].nunique())
    if n_cycles < _MIN_CYCLES:
        errors.append(
            f"Insufficient history: at least {_MIN_CYCLES} cycles required "
            f"for rolling/delta features, got {n_cycles}."
        )

    # -- Numeric quality for every non-ID column --
    id_cols = {"unit", "cycle"}
    for col in sorted(cols - id_cols):
        try:
            pd.to_numeric(df[col], errors="raise")
        except (ValueError, TypeError):
            errors.append(f"Column '{col}' contains non-numeric values.")
            continue
        if df[col].isna().any():
            errors.append(f"Column '{col}' contains NaN values.")
        try:
            if np.isinf(df[col].astype(float)).any():
                errors.append(f"Column '{col}' contains infinite values.")
        except (ValueError, TypeError):
            pass

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Main assessment pipeline
# ---------------------------------------------------------------------------

def assess_sensor_data(
    csv_content: bytes,
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Run the full assessment pipeline on an unseen sensor CSV.

    Parameters
    ----------
    csv_content : bytes
        Raw bytes of the uploaded CSV file.

    Returns
    -------
    dict  – single engine  (latest cycle)
    list  – multiple engines (one dict per engine)

    Raises
    ------
    ValueError
        On any validation, preprocessing, or model error.  The caller
        (API layer) converts these to clean HTTP responses.
    """
    # -- 1. Parse CSV --------------------------------------------------------
    try:
        df = pd.read_csv(io.BytesIO(csv_content))
    except Exception as exc:
        raise ValueError(f"Failed to parse CSV file: {exc}")

    if df.empty:
        raise ValueError("CSV file contains no data.")

    # Normalise column names (case-insensitive, strip whitespace)
    df.columns = df.columns.str.strip().str.lower()

    # -- 2. Validate ---------------------------------------------------------
    is_valid, errors = _validate_input(df)
    if not is_valid:
        raise ValueError("; ".join(errors))

    # Drop RUL column if present (safety net)
    if "rul" in df.columns:
        df = df.drop(columns=["rul"])

    # -- 3. Clean + Feature Engineering --------------------------------------
    #    clean(): drop constant columns (op3, s1, s5, s10, s16, s18, s19),
    #             sort by (unit, cycle), reset index.
    #    add_features(): per-engine rolling mean/std/min/max (window=5)
    #                     + cycle-to-cycle delta (lag=1) for each of the 17
    #                     base features.
    df = clean(df)
    df = add_features(df)

    logger.info(
        "Preprocessing complete: %d rows, %d columns", len(df), len(df.columns)
    )

    # -- 4. Health model (IsolationForest — base 17 features only) -----------
    from src.models.health.anomaly_detector import AnomalyDetector
    from src.models.health.health_scoring import compute_health

    health_feats = [c for c in KEPT_FEATURE_COLUMNS if c in df.columns]
    X_health = AnomalyDetector.select_features(df, health_feats)

    detector = AnomalyDetector.load()
    df["anomaly_score"] = detector.anomaly_score(X_health)

    health_df = compute_health(df[["unit", "cycle", "anomaly_score"]])
    df["health_score"] = health_df["health_score"].values
    df["health_status"] = health_df["health_status"].values

    logger.info("Health model scoring complete.")

    # -- 5. Failure model (XGBoost — base + derived features only) ----------
    #    Pass a view without the health-model output columns so that
    #    get_feature_columns() only sees the numeric pipeline columns.
    _HEALTH_COLS = {"anomaly_score", "health_score", "health_status"}
    from src.models.failure.failure_prediction import predict_failure_probability
    from src.models.failure.failure_scoring import score_failure_predictions

    df_for_failure = df.drop(columns=[c for c in _HEALTH_COLS if c in df.columns])
    fail_preds = predict_failure_probability(df_for_failure)
    fail_scored = score_failure_predictions(fail_preds)
    df["failure_probability"] = fail_scored["failure_probability"].values
    df["failure_status"] = fail_scored["failure_status"].values

    logger.info("Failure model scoring complete.")

    # -- 6. RUL model (RandomForest — base + derived features only) ----------
    #    Exclude all non-numeric / id / result columns from the feature set.
    _EXCLUDE_RUL = {"unit", "cycle", "rul", "anomaly_score", "health_score",
                    "health_status", "failure_probability", "failure_status"}
    rul_feat_cols = [c for c in df.columns if c not in _EXCLUDE_RUL]
    rul_model = joblib.load(_RUL_MODEL_PATH)
    X_rul = df[rul_feat_cols].to_numpy()
    raw_rul = rul_model.predict(X_rul)
    predicted_rul = np.clip(np.round(raw_rul), 0, None).astype("int32")
    df["predicted_rul_cycles"] = predicted_rul

    logger.info("RUL model scoring complete.")

    # -- 7. Extract latest cycle per unit ------------------------------------
    latest_idx = df.groupby("unit")[CYCLE].idxmax()
    latest = df.loc[latest_idx]

    results: List[Dict[str, Any]] = []
    for _, row in latest.iterrows():
        results.append(
            {
                "unit": str(int(row["unit"])),
                "cycle": int(row["cycle"]),
                "anomaly_score": round(float(row["anomaly_score"]), 6),
                "health_score": round(float(row["health_score"]), 2),
                "health_status": str(row["health_status"]),
                "failure_probability": round(float(row["failure_probability"]), 6),
                "failure_status": str(row["failure_status"]),
                "predicted_rul_cycles": int(row["predicted_rul_cycles"]),
            }
        )

    return results[0] if len(results) == 1 else results
