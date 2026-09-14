# src/models/health/train_anomaly.py
"""Training script for the IsolationForest anomaly detector.

The script loads the pre‑processed FD001 training CSV, selects the appropriate
feature columns, fits the model, persists it, and finally writes a CSV
containing ``unit``, ``cycle`` and the computed ``anomaly_score``.

The functions are reusable so that they can be imported elsewhere (e.g. a
CLI entry‑point) without executing on import.
"""

from __future__ import annotations

import pathlib
from typing import List

import pandas as pd

from ..health.anomaly_detector import AnomalyDetector
from ..health.anomaly_config import MODEL_PATH
from src.data.schemas.nasa_schema import (
    KEPT_FEATURE_COLUMNS,
    UNIT,
    CYCLE,
    PROCESSED_TRAIN_FILE,
)

# Resolve absolute paths based on project root
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[3]
_PROCESSED_DATA_DIR = _PROJECT_ROOT / "src" / "data" / "preprocessing"
_DEFAULT_TRAIN_PATH = _PROCESSED_DATA_DIR / PROCESSED_TRAIN_FILE
_DEFAULT_OUTPUT_PATH = _PROJECT_ROOT / "src" / "models" / "health" / "anomaly_scores.csv"

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def load_processed_train(csv_path: str | pathlib.Path = _DEFAULT_TRAIN_PATH) -> pd.DataFrame:
    """Load the processed FD001 training CSV.

    Parameters
    ----------
    csv_path:
        Path to the processed training file.  By default it resolves to the
        ``src/data/preprocessing`` directory.
    """
    path = pathlib.Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Processed training file not found at {path}")
    return pd.read_csv(path)


def select_features(df: pd.DataFrame, feature_columns: List[str] = KEPT_FEATURE_COLUMNS) -> pd.DataFrame:
    """Return a dataframe containing only the model input features.

    The function validates that all requested columns are present.
    """
    missing = set(feature_columns) - set(df.columns)
    if missing:
        raise KeyError(f"Missing expected feature columns: {missing}")
    return df[feature_columns].copy()

# ---------------------------------------------------------------------------
# Main training routine
# ---------------------------------------------------------------------------

def train_and_save_anomaly_scores(
    train_csv: str | pathlib.Path = _DEFAULT_TRAIN_PATH,
    output_csv: str | pathlib.Path = _DEFAULT_OUTPUT_PATH,
) -> None:
    """Train the IsolationForest model and write anomaly scores.

    Steps:
    1. Load processed training data.
    2. Select feature columns.
    3. Fit AnomalyDetector.
    4. Save the model.
    5. Compute anomaly scores (higher = more abnormal).
    6. Write CSV with ``unit``, ``cycle``, ``anomaly_score``.
    """
    df = load_processed_train(train_csv)
    identifiers = df[[UNIT, CYCLE]].copy()
    X = select_features(df)
    detector = AnomalyDetector()
    detector.fit(X)
    detector.save()
    scores = detector.anomaly_score(X)
    identifiers["anomaly_score"] = scores
    out_path = pathlib.Path(output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    identifiers.to_csv(out_path, index=False)
    print(f"Anomaly scores written to {out_path}")

# ---------------------------------------------------------------------------
# Convenience entry‑point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    train_and_save_anomaly_scores()
