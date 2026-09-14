# src/models/failure/train.py
"""TASK 1 — XGBoost failure-classification model training.

Purpose
-------
Train a binary XGBoost classifier to predict engine failure risk.

The failure label is NOT created here.  It must arrive already attached
to the DataFrame (column ``failure_label``), produced by
``failure_labeling.build_labeled_dataset()``.

Engine-aware train/validation split
-------------------------------------
This is a per-engine time-series dataset.  Rows from the SAME engine must
stay together in either the training or the validation split.  Splitting
at the row level would cause leakage: the model would see later cycles of
an engine during training and earlier ones during validation (or vice versa).

Strategy
    1. Identify all unique engine unit IDs.
    2. Randomly split engine IDs (not rows) into train/val sets using
       ``VALIDATION_ENGINE_FRACTION`` (default 20 % of 100 = 20 engines).
    3. All rows belonging to a given engine go entirely to one split.

This prevents any form of temporal or cross-engine leakage.

Features used
-------------
All columns in the processed CSV EXCEPT those listed in
``config.NON_FEATURE_COLUMNS`` (rul, unit, cycle, failure_label).
Specifically:
    - Sensor base columns  : s2, s3, s4, s6, s7, s8, s9, s11..s15, s17, s20, s21
    - Operational settings : op1, op2
    - Rolling features     : *_roll_mean5, *_roll_std5, *_roll_min5, *_roll_max5
    - Delta features       : *_delta1
(100 feature columns total)

RUL is NEVER included in X.

Model evaluation
----------------
Metrics reported on the held-out validation engines:
  - Precision, Recall, F1-score (per class and weighted)
  - ROC-AUC
  - Confusion matrix

Recall for the failure-risk class (class 1) is emphasised because
a missed failure (false negative) is more costly than a false alarm.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from xgboost import XGBClassifier

from .config import (
    MODEL_ARTIFACT_PATH,
    NON_FEATURE_COLUMNS,
    RANDOM_STATE,
    VALIDATION_ENGINE_FRACTION,
    XGBOOST_PARAMS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Feature selection
# ---------------------------------------------------------------------------

def get_feature_columns(df: pd.DataFrame) -> List[str]:
    """Return ML-input feature columns: all columns except non-feature ones.

    Parameters
    ----------
    df : pd.DataFrame
        Labeled training DataFrame.

    Returns
    -------
    List[str]
        Sorted list of column names to use as features.
    """
    features = [c for c in df.columns if c not in NON_FEATURE_COLUMNS]
    return sorted(features)


# ---------------------------------------------------------------------------
# Engine-aware train / validation split
# ---------------------------------------------------------------------------

def engine_aware_split(
    df: pd.DataFrame,
    val_fraction: float = VALIDATION_ENGINE_FRACTION,
    random_state: int = RANDOM_STATE,
    unit_col: str = "unit",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split *df* into training and validation sets by engine unit ID.

    All rows belonging to the same engine go entirely to one split.
    This prevents any temporal or cross-engine data leakage.

    Parameters
    ----------
    df : pd.DataFrame
        Fully labeled dataset (must contain *unit_col*).
    val_fraction : float
        Fraction of engines to hold out for validation.
    random_state : int
        Random seed for reproducibility.
    unit_col : str
        Name of the engine-ID column.

    Returns
    -------
    train_df, val_df : pd.DataFrame, pd.DataFrame
    """
    rng = np.random.default_rng(random_state)
    all_units = df[unit_col].unique()
    rng.shuffle(all_units)

    n_val = max(1, int(len(all_units) * val_fraction))
    val_units = set(all_units[:n_val])
    train_units = set(all_units[n_val:])

    train_df = df[df[unit_col].isin(train_units)].copy()
    val_df = df[df[unit_col].isin(val_units)].copy()

    logger.info(
        "Engine-aware split: %d train engines (%d rows) | "
        "%d val engines (%d rows)",
        len(train_units), len(train_df),
        len(val_units), len(val_df),
    )
    return train_df, val_df


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------

def train_model(
    X: pd.DataFrame,
    y: pd.Series,
    params: Optional[Dict] = None,
    random_state: int = RANDOM_STATE,
) -> XGBClassifier:
    """Train an XGBoost binary classifier.

    Parameters
    ----------
    X : pd.DataFrame
        Feature matrix.  Must NOT contain 'rul', 'unit', 'cycle', or any
        target column.
    y : pd.Series
        Binary failure label (0 or 1).
    params : dict, optional
        XGBoost parameters.  Defaults to ``config.XGBOOST_PARAMS``.
        ``scale_pos_weight`` is computed from the class distribution of *y*
        and injected automatically unless already present in *params*.
    random_state : int
        Overrides ``random_state`` inside *params* for reproducibility.

    Returns
    -------
    XGBClassifier
        Fitted model.
    """
    # Validate inputs
    if "rul" in X.columns:
        raise ValueError("'rul' must NOT be included in the feature matrix X.")
    for forbidden in ("unit", "cycle", "failure_label"):
        if forbidden in X.columns:
            raise ValueError(
                f"Column '{forbidden}' must NOT be in X. "
                "Pass only feature columns."
            )

    merged_params = dict(XGBOOST_PARAMS if params is None else params)
    merged_params["random_state"] = random_state

    # Compute scale_pos_weight from actual training distribution
    if "scale_pos_weight" not in merged_params:
        n_neg = (y == 0).sum()
        n_pos = (y == 1).sum()
        if n_pos > 0:
            spw = round(n_neg / n_pos, 4)
            merged_params["scale_pos_weight"] = spw
            logger.info(
                "Class distribution — neg: %d, pos: %d  →  "
                "scale_pos_weight = %.4f",
                n_neg, n_pos, spw,
            )
        else:
            logger.warning(
                "No positive samples in training set. Skipping scale_pos_weight.")

    # Remove keys that are not valid XGBClassifier init params
    merged_params.pop("use_label_encoder", None)

    model = XGBClassifier(**merged_params)
    model.fit(X, y)
    return model


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate_model(
    model: XGBClassifier,
    X_val: pd.DataFrame,
    y_val: pd.Series,
) -> Dict:
    """Evaluate the model on validation data and return a metrics dict.

    Parameters
    ----------
    model : XGBClassifier
        Trained model.
    X_val : pd.DataFrame
        Validation feature matrix.
    y_val : pd.Series
        True binary labels.

    Returns
    -------
    dict with keys:
        classification_report, roc_auc, confusion_matrix,
        y_pred, y_prob
    """
    y_pred = model.predict(X_val)
    y_prob = model.predict_proba(X_val)[:, 1]

    cr = classification_report(y_val, y_pred, target_names=[
                               "no_risk", "failure_risk"])
    cm = confusion_matrix(y_val, y_pred)
    try:
        auc = roc_auc_score(y_val, y_prob)
    except ValueError:
        auc = float("nan")

    metrics = {
        "classification_report": cr,
        "roc_auc": auc,
        "confusion_matrix": cm,
        "y_pred": y_pred,
        "y_prob": y_prob,
    }

    # Print report
    lines = [
        "",
        "=" * 60,
        "MODEL EVALUATION — VALIDATION SET",
        "=" * 60,
        cr,
        f"  ROC-AUC         : {auc:.4f}",
        "",
        "  Confusion matrix (rows=actual, cols=predicted):",
        f"    {cm}",
        "",
        "  NOTE: Recall for class 'failure_risk' is the primary metric.",
        "  A missed failure (false negative) is more costly than a false alarm.",
        "=" * 60,
    ]
    report_str = "\n".join(lines)
    logger.info(report_str)
    print(report_str)

    return metrics


# ---------------------------------------------------------------------------
# Model persistence
# ---------------------------------------------------------------------------

def save_model(model: XGBClassifier, path: str = MODEL_ARTIFACT_PATH) -> None:
    """Persist the trained model to *path* using joblib.

    Parameters
    ----------
    model : XGBClassifier
        Fitted model to save.
    path : str
        Destination file path.  Defaults to ``config.MODEL_ARTIFACT_PATH``.
    """
    joblib.dump(model, path)
    logger.info("Model saved to: %s", path)
    print(f"Model saved to: {path}")


def load_model(path: str = MODEL_ARTIFACT_PATH) -> XGBClassifier:
    """Load a persisted XGBClassifier from *path*.

    Parameters
    ----------
    path : str
        Source file path.  Defaults to ``config.MODEL_ARTIFACT_PATH``.

    Returns
    -------
    XGBClassifier
    """
    model = joblib.load(path)
    logger.info("Model loaded from: %s", path)
    return model


# ---------------------------------------------------------------------------
# Top-level training pipeline
# ---------------------------------------------------------------------------

def run_training_pipeline(
    df: pd.DataFrame,
    label_col: str = "failure_label",
    unit_col: str = "unit",
    save: bool = True,
    model_path: str = MODEL_ARTIFACT_PATH,
) -> Tuple[XGBClassifier, List[str], Dict]:
    """Full training pipeline: split → train → evaluate → (optionally save).

    This function assumes *df* already has a ``failure_label`` column
    created by ``failure_labeling.build_labeled_dataset()``.

    Parameters
    ----------
    df : pd.DataFrame
        Labeled, pre-processed training data.
    label_col : str
        Name of the binary label column.
    unit_col : str
        Name of the engine-ID column (used for leakage-free splitting).
    save : bool
        If True, persist the trained model to *model_path*.
    model_path : str
        Destination for the model artifact.

    Returns
    -------
    model : XGBClassifier
        Fitted model.
    feature_cols : List[str]
        Feature columns used during training.
    metrics : dict
        Evaluation metrics from the validation set.
    """
    if label_col not in df.columns:
        raise ValueError(
            f"Label column '{label_col}' not found. "
            "Run failure_labeling.build_labeled_dataset() first."
        )

    # 1. Engine-aware split
    train_df, val_df = engine_aware_split(df, unit_col=unit_col)

    # 2. Identify feature columns
    feature_cols = get_feature_columns(df)
    logger.info("Feature columns (%d): %s", len(
        feature_cols), feature_cols[:5])

    X_train = train_df[feature_cols]
    y_train = train_df[label_col]
    X_val = val_df[feature_cols]
    y_val = val_df[label_col]

    # 3. Train
    logger.info("Training XGBoost on %d rows …", len(X_train))
    model = train_model(X_train, y_train)

    # 4. Evaluate
    metrics = evaluate_model(model, X_val, y_val)

    # 5. Save
    if save:
        save_model(model, model_path)

    return model, feature_cols, metrics


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")

    import pandas as pd
    from .failure_labeling import build_labeled_dataset
    from .config import TRAIN_DATA_PATH

    df = pd.read_csv(TRAIN_DATA_PATH)
    df_labeled = build_labeled_dataset(df, verbose=True)
    run_training_pipeline(df_labeled)
