"""RUL prediction training pipeline for NASA C-MAPSS FD001.

Pipeline (run via ``python -m src.models.rul.train_rul``):

1. Load the already-preprocessed CSVs from src/data/preprocessing/.
   If they are absent, call preprocess_fd001() as a fallback — but do NOT
   create a second preprocessing pipeline.
2. Build the feature matrix from all columns that are not id/target columns.
3. Apply a unit-aware chronological split: for every engine in the training
   data the last VAL_TAIL_CYCLES cycles are held out as a diagnostic
   validation set; earlier cycles form the training set.
   No random shuffling is performed anywhere in this file.
4. Clip the training RUL target at RUL_CAP to focus the model on the
   degradation window (cap is never applied to ground-truth evaluation).
5. Fit a RandomForestRegressor baseline.
6. Evaluate on the official NASA test set: take the last observed cycle per
   engine (the truncation point), predict, then compute MAE and RMSE against
   the true RUL from RUL_FD001.txt (already attached by the preprocessor).
7. Save predictions as rul_predictions.csv with schema:
       asset_id, cycle, predicted_rul, rul_status
8. Save the fitted model as rul_model.joblib for later API reuse.

Leakage guard: the chronological per-engine split and capped-target training
ensure no future information ever enters the model's training set.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.data.schemas.nasa_schema import (
    CYCLE,
    KEPT_FEATURE_COLUMNS,
    PROCESSED_TEST_FILE,
    PROCESSED_TRAIN_FILE,
    RUL_NAME,
    UNIT,
    feature_columns_for,
)
from src.models.rul.config import (
    MAX_DEPTH,
    MIN_SAMPLES_LEAF,
    MODEL_FILE,
    N_ESTIMATORS,
    N_JOBS,
    PREDICTIONS_FILE,
    RANDOM_STATE,
    RUL_CAP,
    THRESHOLD_CRITICAL,
    THRESHOLD_HEALTHY,
    VAL_TAIL_CYCLES,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_PREPROC_DIR: Path = (
    Path(__file__).resolve().parents[3] / "src" / "data" / "preprocessing"
)
_OUT_DIR: Path = Path(__file__).resolve().parent


def _preproc_dir() -> Path:
    """Return the preprocessing output directory (src/data/preprocessing/)."""
    # Walk up from src/models/rul/ → src/models/ → src/ → repo root,
    # then back down to src/data/preprocessing/.
    return Path(__file__).resolve().parents[2] / "data" / "preprocessing"


# ---------------------------------------------------------------------------
# Feature helpers
# ---------------------------------------------------------------------------
_NON_FEATURE: Tuple[str, ...] = (UNIT, CYCLE, RUL_NAME)


def _feature_columns(df: pd.DataFrame) -> List[str]:
    """All columns in df that are not id or target columns."""
    return [c for c in df.columns if c not in _NON_FEATURE]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_preprocessed() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load the preprocessed CSVs; run the preprocessor as a fallback."""
    preproc = _preproc_dir()
    train_path = preproc / PROCESSED_TRAIN_FILE
    test_path = preproc / PROCESSED_TEST_FILE

    if not train_path.exists() or not test_path.exists():
        print("Preprocessed CSVs not found — running preprocess_fd001() …")
        from src.data.preprocessing.preprocess_nasa import preprocess_fd001
        result = preprocess_fd001()
        train = result["train"]
        test = result["test"]
    else:
        train = pd.read_csv(train_path)
        test = pd.read_csv(test_path)

    return train, test


# ---------------------------------------------------------------------------
# Chronological per-engine split (no random shuffling)
# ---------------------------------------------------------------------------

def _chronological_split(
    train_df: pd.DataFrame,
    val_tail: int = VAL_TAIL_CYCLES,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split training data into train/val using a per-engine tail holdout.

    For every engine the last ``val_tail`` cycles (closest to failure) are
    reserved for validation; all earlier cycles go to training. The data is
    already sorted by (unit, cycle) by the preprocessor, so no re-sorting
    is needed.

    This is a strict temporal split: no future cycle ever appears in the
    training portion, and no random shuffling is performed.
    """
    is_val = (
        train_df.groupby(UNIT)[CYCLE]
        .rank(method="first", ascending=False)
        <= val_tail
    )
    return train_df[~is_val].copy(), train_df[is_val].copy()


# ---------------------------------------------------------------------------
# RUL status derivation
# ---------------------------------------------------------------------------

def _rul_status(predicted_rul: pd.Series) -> pd.Series:
    """Derive rul_status from predicted RUL using thresholds from config.py.

    Thresholds (all values from src/models/rul/config.py):
      predicted_rul > THRESHOLD_HEALTHY   → "HEALTHY"
      THRESHOLD_CRITICAL < predicted_rul
                         ≤ THRESHOLD_HEALTHY → "ADVISORY"
      predicted_rul ≤ THRESHOLD_CRITICAL  → "CRITICAL"
    """
    status = pd.Series("ADVISORY", index=predicted_rul.index, dtype=object)
    status[predicted_rul > THRESHOLD_HEALTHY] = "HEALTHY"
    status[predicted_rul <= THRESHOLD_CRITICAL] = "CRITICAL"
    return status


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def train_rul() -> dict:
    """Run the full RUL training and evaluation pipeline.

    Returns a dict with model, metrics, and output paths.
    """
    # ------------------------------------------------------------------
    # 1. Load preprocessed data
    # ------------------------------------------------------------------
    print("Loading preprocessed data …")
    train_df, test_df = _load_preprocessed()
    print(f"  train: {train_df.shape[0]} rows × {train_df.shape[1]} cols")
    print(f"  test : {test_df.shape[0]} rows × {test_df.shape[1]} cols")

    # ------------------------------------------------------------------
    # 2. Feature columns
    # ------------------------------------------------------------------
    feature_cols = _feature_columns(train_df)
    print(f"  features: {len(feature_cols)} columns")

    # ------------------------------------------------------------------
    # 3. Chronological per-engine split
    # ------------------------------------------------------------------
    tr, val = _chronological_split(train_df)
    print(
        f"  train split: {len(tr)} rows | val split (tail {VAL_TAIL_CYCLES} cycles/engine): {len(val)} rows"
    )

    X_tr = tr[feature_cols].to_numpy()
    y_tr_raw = tr[RUL_NAME].to_numpy(dtype="float32")
    y_tr = np.clip(y_tr_raw, 0, RUL_CAP)           # capped target for training only

    X_val = val[feature_cols].to_numpy()
    y_val = val[RUL_NAME].to_numpy(dtype="float32")  # true RUL, uncapped

    # ------------------------------------------------------------------
    # 4. Train RandomForest baseline
    # ------------------------------------------------------------------
    print(f"\nTraining RandomForestRegressor (n_estimators={N_ESTIMATORS}, seed={RANDOM_STATE}) …")
    model = RandomForestRegressor(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        min_samples_leaf=MIN_SAMPLES_LEAF,
        random_state=RANDOM_STATE,
        n_jobs=N_JOBS,
    )
    model.fit(X_tr, y_tr)

    # ------------------------------------------------------------------
    # 5. Diagnostic validation metrics (within-training-data holdout)
    # ------------------------------------------------------------------
    val_pred = model.predict(X_val)
    val_mae = mean_absolute_error(y_val, val_pred)
    val_rmse = mean_squared_error(y_val, val_pred) ** 0.5
    print(f"\nValidation (last {VAL_TAIL_CYCLES} cycles/engine):")
    print(f"  MAE  = {val_mae:.3f}")
    print(f"  RMSE = {val_rmse:.3f}")

    # ------------------------------------------------------------------
    # 6. Official NASA test-set evaluation
    #    NASA convention: predict at the last observed cycle per engine
    # ------------------------------------------------------------------
    last_cycle_idx = test_df.groupby(UNIT)[CYCLE].idxmax()
    test_last = test_df.loc[last_cycle_idx].copy()

    X_test = test_last[feature_cols].to_numpy()
    y_test_true = test_last[RUL_NAME].to_numpy(dtype="float32")

    test_pred_raw = model.predict(X_test)
    test_pred = np.clip(np.round(test_pred_raw), 0, None).astype("int32")

    test_mae = mean_absolute_error(y_test_true, test_pred)
    test_rmse = mean_squared_error(y_test_true, test_pred) ** 0.5
    print(f"\nOfficial test-set evaluation (100 engines, last cycle per engine):")
    print(f"  MAE  = {test_mae:.3f}")
    print(f"  RMSE = {test_rmse:.3f}")

    # ------------------------------------------------------------------
    # 7. Build predictions DataFrame with integration schema
    # ------------------------------------------------------------------
    predictions = pd.DataFrame(
        {
            "asset_id": test_last[UNIT].to_numpy(),
            "cycle": test_last[CYCLE].to_numpy(),
            "predicted_rul": test_pred,
            "rul_status": _rul_status(pd.Series(test_pred)).to_numpy(),
        }
    )

    # ------------------------------------------------------------------
    # 8. Save outputs
    # ------------------------------------------------------------------
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    pred_path = _OUT_DIR / PREDICTIONS_FILE
    model_path = _OUT_DIR / MODEL_FILE

    predictions.to_csv(pred_path, index=False)
    joblib.dump(model, model_path)

    print(f"\nSaved predictions -> {pred_path}")
    print(f"Saved model       -> {model_path}")

    return {
        "model": model,
        "feature_columns": feature_cols,
        "val_mae": val_mae,
        "val_rmse": val_rmse,
        "test_mae": test_mae,
        "test_rmse": test_rmse,
        "predictions_path": str(pred_path),
        "model_path": str(model_path),
        "n_test_engines": len(predictions),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = train_rul()
    print("\n--- Summary ---")
    print(f"  Val  MAE / RMSE : {result['val_mae']:.3f} / {result['val_rmse']:.3f}")
    print(f"  Test MAE / RMSE : {result['test_mae']:.3f} / {result['test_rmse']:.3f}")
    print(f"  Engines evaluated: {result['n_test_engines']}")
    print(f"  Predictions : {result['predictions_path']}")
    print(f"  Model       : {result['model_path']}")
