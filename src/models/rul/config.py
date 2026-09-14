"""RUL module configuration — single source of truth for all tunables.

All thresholds, hyperparameters, and output filenames are defined here so that
``train_rul.py`` and ``evaluate_rul.py`` never hard-code any of these values.
"""

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
RANDOM_STATE: int = 42

# ---------------------------------------------------------------------------
# Training target
# ---------------------------------------------------------------------------
# Raw training RUL reaches 300+ cycles at the start of each engine's life.
# That early portion carries no degradation signal and inflates regression
# error. Capping at 125 cycles focuses the model on the degradation window
# where predictions are operationally meaningful (standard C-MAPSS practice).
RUL_CAP: int = 125

# ---------------------------------------------------------------------------
# Model hyperparameters (RandomForestRegressor baseline)
# ---------------------------------------------------------------------------
N_ESTIMATORS: int = 200
MAX_DEPTH: int | None = None   # unlimited depth; let the forest decide
MIN_SAMPLES_LEAF: int = 2      # slight regularisation to reduce overfit
N_JOBS: int = -1               # use all available cores

# ---------------------------------------------------------------------------
# Chronological validation split (per-engine, no random shuffling)
# ---------------------------------------------------------------------------
# Number of trailing cycles per engine withheld from training for diagnostic
# validation. These are the most recent (closest-to-failure) cycles.
VAL_TAIL_CYCLES: int = 30

# ---------------------------------------------------------------------------
# RUL status thresholds
# ---------------------------------------------------------------------------
# Derived rul_status categories written to rul_predictions.csv:
#
#   predicted_rul > THRESHOLD_HEALTHY   → "HEALTHY"
#   THRESHOLD_CRITICAL < predicted_rul
#                     ≤ THRESHOLD_HEALTHY → "ADVISORY"
#   predicted_rul ≤ THRESHOLD_CRITICAL  → "CRITICAL"
#
# These values can be adjusted here without touching any other file.
THRESHOLD_HEALTHY: int = 100    # cycles; above this → no near-term risk
THRESHOLD_CRITICAL: int = 30    # cycles; at or below → imminent-failure zone

# ---------------------------------------------------------------------------
# Output file names (written to src/models/rul/)
# ---------------------------------------------------------------------------
PREDICTIONS_FILE: str = "rul_predictions.csv"
MODEL_FILE: str = "rul_model.joblib"
