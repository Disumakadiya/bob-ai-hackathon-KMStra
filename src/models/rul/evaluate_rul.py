"""Standalone RUL evaluation and reporting utility.

Loads the saved rul_predictions.csv and the FD001 test preprocessed CSV,
joins them, recomputes MAE and RMSE, then prints a metrics summary and a
sample of prediction rows.

Run (no re-training required):
    python -m src.models.rul.evaluate_rul
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error

from src.data.schemas.nasa_schema import (
    CYCLE,
    PROCESSED_TEST_FILE,
    RUL_NAME,
    UNIT,
)
from src.models.rul.config import (
    PREDICTIONS_FILE,
    THRESHOLD_CRITICAL,
    THRESHOLD_HEALTHY,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_RUL_DIR: Path = Path(__file__).resolve().parent
_PREPROC_DIR: Path = _RUL_DIR.parents[1] / "data" / "preprocessing"


def _load_true_rul() -> pd.DataFrame:
    """Extract the ground-truth RUL at the last observed cycle per engine."""
    test_path = _PREPROC_DIR / PROCESSED_TEST_FILE
    if not test_path.exists():
        raise FileNotFoundError(
            f"Preprocessed test CSV not found at {test_path}.\n"
            "Run: python -m src.models.rul.train_rul"
        )
    test_df = pd.read_csv(test_path)
    last_idx = test_df.groupby(UNIT)[CYCLE].idxmax()
    last = test_df.loc[last_idx, [UNIT, CYCLE, RUL_NAME]].copy()
    last = last.rename(columns={UNIT: "asset_id", RUL_NAME: "true_rul"})
    return last


def _load_predictions() -> pd.DataFrame:
    pred_path = _RUL_DIR / PREDICTIONS_FILE
    if not pred_path.exists():
        raise FileNotFoundError(
            f"Predictions file not found at {pred_path}.\n"
            "Run: python -m src.models.rul.train_rul"
        )
    return pd.read_csv(pred_path)


def evaluate() -> None:
    """Load saved predictions, compute metrics, and print a report."""
    predictions = _load_predictions()
    ground_truth = _load_true_rul()

    # Join on asset_id to align predicted vs true RUL
    merged = predictions.merge(ground_truth[["asset_id", "true_rul"]], on="asset_id", how="inner")

    if merged.empty:
        raise ValueError("No matching asset_ids between predictions and ground truth.")

    y_true = merged["true_rul"].to_numpy(dtype="float32")
    y_pred = merged["predicted_rul"].to_numpy(dtype="float32")

    mae = mean_absolute_error(y_true, y_pred)
    rmse = mean_squared_error(y_true, y_pred) ** 0.5

    # Status distribution
    status_counts = merged["rul_status"].value_counts()

    print("=" * 55)
    print("  RUL Evaluation Report — FD001 Test Set")
    print("=" * 55)
    print(f"  Engines evaluated : {len(merged)}")
    print(f"  MAE               : {mae:.3f} cycles")
    print(f"  RMSE              : {rmse:.3f} cycles")
    print()
    print("  RUL status thresholds:")
    print(f"    HEALTHY   : predicted_rul > {THRESHOLD_HEALTHY}")
    print(f"    ADVISORY  : {THRESHOLD_CRITICAL} < predicted_rul ≤ {THRESHOLD_HEALTHY}")
    print(f"    CRITICAL  : predicted_rul ≤ {THRESHOLD_CRITICAL}")
    print()
    print("  Status distribution:")
    for status in ["HEALTHY", "ADVISORY", "CRITICAL"]:
        count = status_counts.get(status, 0)
        pct = 100.0 * count / len(merged)
        print(f"    {status:<10} {count:>4} engines  ({pct:.1f}%)")
    print()
    print("  Sample predictions (first 10 rows):")
    print(
        merged[["asset_id", "cycle", "predicted_rul", "true_rul", "rul_status"]]
        .head(10)
        .to_string(index=False)
    )
    print("=" * 55)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    evaluate()
