# src/models/failure/failure_prediction.py
"""TASK 3 — Inference with the trained XGBoost failure-risk model.

Purpose
-------
Run inference on pre-processed FD001 data (training or test split) using
the saved XGBoost model and return a DataFrame with:

    unit  |  cycle  |  failure_probability

Rules enforced
--------------
- RUL is NEVER used as an input feature.
- ``unit`` and ``cycle`` are preserved in the output for identification
  and downstream joining, but are NOT fed to the model.
- The model is loaded from disk; it is never retrained here.
- ``failure_probability`` is always in [0, 1] (guaranteed by
  XGBoost's predict_proba output).
- Future information is not used: inference is row-wise from the
  already-computed features in the pre-processed CSV.

Typical call
------------
    from src.models.failure.failure_prediction import predict_failure_probability
    results = predict_failure_probability(df_test)
    # columns: unit, cycle, failure_probability
"""

from __future__ import annotations

import logging
from typing import List, Optional

import pandas as pd
from xgboost import XGBClassifier

from .config import (
    FAILURE_SCORES_PATH,
    MODEL_ARTIFACT_PATH,
    NON_FEATURE_COLUMNS,
    TEST_DATA_PATH,
)
from .train import get_feature_columns, load_model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core prediction function
# ---------------------------------------------------------------------------

def predict_failure_probability(
    df: pd.DataFrame,
    model: Optional[XGBClassifier] = None,
    model_path: str = MODEL_ARTIFACT_PATH,
    unit_col: str = "unit",
    cycle_col: str = "cycle",
) -> pd.DataFrame:
    """Compute per-observation failure probabilities from pre-processed data.

    Parameters
    ----------
    df : pd.DataFrame
        Pre-processed FD001 data (train or test split).
        Must contain ``unit``, ``cycle``, and all feature columns.
        May contain ``rul`` — it will be ignored (not fed to the model).
    model : XGBClassifier, optional
        A pre-loaded model.  If None, the model is loaded from *model_path*.
    model_path : str
        Path to the saved model artifact.  Used only if *model* is None.
    unit_col : str
        Column name for engine unit ID.
    cycle_col : str
        Column name for operational cycle.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
            unit               – engine identifier (int)
            cycle              – operational cycle (int)
            failure_probability – estimated failure risk in [0, 1] (float)

        Rows correspond 1-to-1 with the input rows, in the same order.

    Raises
    ------
    FileNotFoundError
        If *model_path* does not exist when *model* is None.
    ValueError
        If required columns are missing from *df*.
    """
    # Load model if not provided
    if model is None:
        model = load_model(model_path)

    # Validate required ID columns
    for col in (unit_col, cycle_col):
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in DataFrame.")

    # Determine feature columns (must match training-time columns)
    # We call get_feature_columns with a temporary view that drops the
    # failure_label column if present (it's a non-feature by config).
    feature_cols: List[str] = get_feature_columns(df)

    # Confirm no forbidden columns slipped through
    forbidden_present = [c for c in ("rul", "failure_label") if c in feature_cols]
    if forbidden_present:
        raise ValueError(
            f"Forbidden columns found in feature set: {forbidden_present}. "
            "These must be excluded from X."
        )

    logger.info(
        "Running inference: %d rows, %d features", len(df), len(feature_cols)
    )

    X = df[feature_cols]

    # predict_proba returns [[P(0), P(1)], …]
    proba = model.predict_proba(X)[:, 1]

    # Clip to [0, 1] as a defensive measure (XGBoost should already guarantee this)
    proba = proba.clip(0.0, 1.0)

    result = pd.DataFrame(
        {
            unit_col: df[unit_col].values,
            cycle_col: df[cycle_col].values,
            "failure_probability": proba,
        }
    )

    logger.info(
        "Prediction complete. failure_probability range: [%.4f, %.4f]",
        result["failure_probability"].min(),
        result["failure_probability"].max(),
    )
    return result


# ---------------------------------------------------------------------------
# Convenience: load test data and run inference
# ---------------------------------------------------------------------------

def run_test_inference(
    test_path: str = TEST_DATA_PATH,
    model_path: str = MODEL_ARTIFACT_PATH,
) -> pd.DataFrame:
    """Load the pre-processed test CSV and return failure predictions.

    Parameters
    ----------
    test_path : str
        Path to ``FD001_test_preprocessed.csv``.
    model_path : str
        Path to the saved XGBoost model.

    Returns
    -------
    pd.DataFrame
        Columns: unit, cycle, failure_probability
    """
    df_test = pd.read_csv(test_path)
    logger.info("Test data loaded: %s rows, %s cols", *df_test.shape)

    # The test CSV contains a 'rul' column (from preprocessing).
    # It is treated as evaluation-only ground truth and is NOT passed to
    # the model.  The predict_failure_probability function enforces this.
    results = predict_failure_probability(df_test, model_path=model_path)
    return results


# ---------------------------------------------------------------------------
# Convenience: load training data and run inference (for validation/QA)
# ---------------------------------------------------------------------------

def run_train_inference(
    train_path: str = "src/data/preprocessing/FD001_train_preprocessed.csv",
    model_path: str = MODEL_ARTIFACT_PATH,
) -> pd.DataFrame:
    """Load the pre-processed train CSV and return failure predictions.

    Useful for inspecting in-sample predictions or QA checks.

    Parameters
    ----------
    train_path : str
        Path to ``FD001_train_preprocessed.csv``.
    model_path : str
        Path to the saved XGBoost model.

    Returns
    -------
    pd.DataFrame
        Columns: unit, cycle, failure_probability
    """
    df_train = pd.read_csv(train_path)
    logger.info("Train data loaded: %s rows, %s cols", *df_train.shape)
    results = predict_failure_probability(df_train, model_path=model_path)
    return results


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

def save_scores(
    scored: pd.DataFrame,
    output_path: str = FAILURE_SCORES_PATH,
    unit_col: str = "unit",
    cycle_col: str = "cycle",
    prob_col: str = "failure_probability",
    status_col: str = "failure_status",
) -> str:
    """Save the final scored predictions to a CSV file.

    Writes exactly four columns in the required order:
        unit, cycle, failure_probability, failure_status

    Parameters
    ----------
    scored : pd.DataFrame
        Output of ``failure_scoring.score_failure_predictions()``.
        Must contain *unit_col*, *cycle_col*, *prob_col*, *status_col*.
    output_path : str
        Destination file path.  Defaults to ``config.FAILURE_SCORES_PATH``
        (``src/models/failure/failure_scores.csv``).
    unit_col, cycle_col, prob_col, status_col : str
        Column names in *scored*.

    Returns
    -------
    str
        The absolute path where the CSV was written.

    Raises
    ------
    ValueError
        If any required column is missing or if constraints are violated.
    """
    required = [unit_col, cycle_col, prob_col, status_col]
    missing = [c for c in required if c not in scored.columns]
    if missing:
        raise ValueError(f"Missing required columns in scored DataFrame: {missing}")

    # Defensive constraint checks before writing
    if scored[prob_col].lt(0.0).any() or scored[prob_col].gt(1.0).any():
        raise ValueError(
            f"'{prob_col}' contains values outside [0, 1]. Refusing to save."
        )
    invalid_statuses = set(scored[status_col].unique()) - {"LOW", "MEDIUM", "HIGH"}
    if invalid_statuses:
        raise ValueError(
            f"'{status_col}' contains invalid values: {invalid_statuses}. "
            "Expected only LOW, MEDIUM, HIGH."
        )

    out = scored[[unit_col, cycle_col, prob_col, status_col]].copy()
    out.to_csv(output_path, index=False)
    logger.info("Failure scores saved to: %s  (%d rows)", output_path, len(out))
    print(f"Failure scores saved to: {output_path}  ({len(out):,} rows)")
    return output_path


def run_and_save_test_scores(
    test_path: str = TEST_DATA_PATH,
    model_path: str = MODEL_ARTIFACT_PATH,
    output_path: str = FAILURE_SCORES_PATH,
) -> pd.DataFrame:
    """Full inference + scoring + CSV save for the test split.

    Convenience function for the integration layer:
        1. Load FD001_test_preprocessed.csv
        2. Run XGBoost inference  → failure_probability
        3. Score                  → failure_status
        4. Save                   → failure_scores.csv

    Parameters
    ----------
    test_path : str
        Path to the pre-processed test CSV.
    model_path : str
        Path to the saved XGBoost model artifact.
    output_path : str
        Destination for the output CSV.

    Returns
    -------
    pd.DataFrame
        Scored DataFrame with columns:
            unit, cycle, failure_probability, failure_status
    """
    from .failure_scoring import score_failure_predictions  # local to avoid circular

    predictions = run_test_inference(test_path=test_path, model_path=model_path)
    scored = score_failure_predictions(predictions)
    save_scores(scored, output_path=output_path)
    return scored
