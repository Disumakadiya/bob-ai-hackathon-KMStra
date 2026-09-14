# src/models/failure/config.py
"""Centralised configuration for the failure-prediction module (Member 2).

All thresholds, hyperparameters, and file paths live here.
Do NOT scatter these values throughout other modules.

Threshold rationale
-------------------
RUL_FAILURE_THRESHOLD = 30
    The binary failure-risk label is 1 when an observation's RUL is
    <= 30 cycles.  30 cycles was chosen because:
      - The 15th percentile of the training-set RUL distribution is ~30,
        so the positive class covers the 15% of observations closest to end
        of life without being severely imbalanced.
      - It is a commonly cited early-warning horizon in the PHM08/C-MAPSS
        literature (gives the operator ~30 operational cycles to react).
      - At threshold=30 the class split is ~15 % positive / 85 % negative,
        which is imbalanced but typical for anomaly/failure classification;
        XGBoost's scale_pos_weight parameter compensates automatically.

Failure-status thresholds
--------------------------
LOW    : failure_probability < LOW_MEDIUM_BOUNDARY
MEDIUM : LOW_MEDIUM_BOUNDARY <= failure_probability < MEDIUM_HIGH_BOUNDARY
HIGH   : failure_probability >= MEDIUM_HIGH_BOUNDARY

LOW_MEDIUM_BOUNDARY  = 0.40  (below 40 % estimated failure risk -> LOW)
MEDIUM_HIGH_BOUNDARY = 0.70  (above 70 % estimated failure risk -> HIGH)

Note: HIGH status means high *model-estimated* failure risk under the
defined labeling target.  It does NOT guarantee certain failure.
"""

import os

# ---------------------------------------------------------------------------
# Random seed – used for train/validation split and XGBoost
# ---------------------------------------------------------------------------
RANDOM_STATE: int = 42

# ---------------------------------------------------------------------------
# Failure-label target construction (failure_labeling.py)
# ---------------------------------------------------------------------------
# Observations with RUL <= this value are labeled 1 (approaching failure).
RUL_FAILURE_THRESHOLD: int = 30

# ---------------------------------------------------------------------------
# Feature selection (train.py / failure_prediction.py)
# ---------------------------------------------------------------------------
# Columns that are NEVER used as ML input features.
# - rul        : used only to construct the label; must not be a feature.
# - unit       : engine identifier (used for grouping only).
# - cycle      : time index (retained in output, not a predictive feature).
# - failure_label : the target itself; never a feature.
NON_FEATURE_COLUMNS = {"rul", "unit", "cycle", "failure_label"}

# ---------------------------------------------------------------------------
# Engine-aware train / validation split
# ---------------------------------------------------------------------------
# Fraction of engines (units) held out for validation.
# At 20 % of 100 engines → 20 validation engines, 80 training engines.
VALIDATION_ENGINE_FRACTION: float = 0.20

# ---------------------------------------------------------------------------
# XGBoost hyperparameters
# ---------------------------------------------------------------------------
XGBOOST_PARAMS: dict = {
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "gamma": 0.1,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "eval_metric": "logloss",
    "use_label_encoder": False,
    "random_state": RANDOM_STATE,
    "n_jobs": -1,
    # scale_pos_weight is computed dynamically from the training class
    # distribution inside train.py and NOT hard-coded here, because it
    # depends on the actual split.
}

# ---------------------------------------------------------------------------
# Failure-probability → failure_status mapping
# ---------------------------------------------------------------------------
# failure_probability in [0, 1].
FAILURE_STATUS_LOW = "LOW"
FAILURE_STATUS_MEDIUM = "MEDIUM"
FAILURE_STATUS_HIGH = "HIGH"

LOW_MEDIUM_BOUNDARY: float = 0.40   # P < 0.40  → LOW
MEDIUM_HIGH_BOUNDARY: float = 0.70  # P >= 0.70 → HIGH
#                                     0.40 <= P < 0.70 → MEDIUM

# ---------------------------------------------------------------------------
# Model artifact path
# ---------------------------------------------------------------------------
# Matches the convention used by Member 1: store under the model sub-package.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_ARTIFACT_PATH: str = os.path.join(_THIS_DIR, "xgboost_failure_model.joblib")

# ---------------------------------------------------------------------------
# Data paths (relative to repo root, used in standalone scripts)
# ---------------------------------------------------------------------------
TRAIN_DATA_PATH: str = "src/data/preprocessing/FD001_train_preprocessed.csv"
TEST_DATA_PATH: str = "src/data/preprocessing/FD001_test_preprocessed.csv"

# Output CSV for the final scored test predictions (consumed by the integration layer)
FAILURE_SCORES_PATH: str = os.path.join(_THIS_DIR, "failure_scores.csv")
