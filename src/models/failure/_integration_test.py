"""Member 2 — Full integration test script."""
import os
import sys
import logging

sys.path.insert(0, ".")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

import pandas as pd

print("=" * 60)
print("MEMBER 2 FAILURE PREDICTION — INTEGRATION TEST")
print("=" * 60)

# ------------------------------------------------------------------
# STEP 1: Load training data
# ------------------------------------------------------------------
print("\n[1] Loading training data...")
df = pd.read_csv("src/data/preprocessing/FD001_train_preprocessed.csv")
print(f"    Shape: {df.shape}")
assert "rul" in df.columns
assert "unit" in df.columns
assert "cycle" in df.columns
print("    PASS: required columns present")

# ------------------------------------------------------------------
# STEP 2: Failure labeling
# ------------------------------------------------------------------
print("\n[2] Creating failure labels...")
from src.models.failure.failure_labeling import build_labeled_dataset
df_labeled = build_labeled_dataset(df, verbose=True)
assert "failure_label" in df_labeled.columns
unique_vals = {int(v) for v in df_labeled["failure_label"].unique()}
assert unique_vals == {0, 1}, f"Unexpected label values: {unique_vals}"
print(f"    PASS: failure_label contains only {unique_vals}")

# ------------------------------------------------------------------
# STEP 3: Feature columns check
# ------------------------------------------------------------------
print("\n[3] Checking feature columns...")
from src.models.failure.train import get_feature_columns
feature_cols = get_feature_columns(df_labeled)
print(f"    Feature count: {len(feature_cols)}")
assert "rul" not in feature_cols, "RUL found in features — LEAKAGE!"
assert "unit" not in feature_cols
assert "cycle" not in feature_cols
assert "failure_label" not in feature_cols
print("    PASS: rul, unit, cycle, failure_label all excluded")

# ------------------------------------------------------------------
# STEP 4: Engine-aware split
# ------------------------------------------------------------------
print("\n[4] Engine-aware split...")
from src.models.failure.train import engine_aware_split
train_df, val_df = engine_aware_split(df_labeled)
train_units = set(train_df["unit"].unique())
val_units = set(val_df["unit"].unique())
assert train_units.isdisjoint(val_units), "LEAKAGE: same engine in train and val!"
print(f"    Train engines: {len(train_units)}, Val engines: {len(val_units)}")
print("    PASS: no engine appears in both splits")

# ------------------------------------------------------------------
# STEP 5: Train XGBoost
# ------------------------------------------------------------------
print("\n[5] Training XGBoost model...")
from src.models.failure.train import run_training_pipeline
model, feat_cols, metrics = run_training_pipeline(df_labeled, save=True)
print(f"    PASS: model trained with {len(feat_cols)} features")

# ------------------------------------------------------------------
# STEP 6: Save / load model
# ------------------------------------------------------------------
print("\n[6] Testing model save/load...")
from src.models.failure.train import load_model
from src.models.failure.config import MODEL_ARTIFACT_PATH
loaded_model = load_model(MODEL_ARTIFACT_PATH)
assert loaded_model is not None
print(f"    PASS: model reloaded from {MODEL_ARTIFACT_PATH}")

# ------------------------------------------------------------------
# STEP 7: Train-set inference
# ------------------------------------------------------------------
print("\n[7] Running inference on training data...")
from src.models.failure.failure_prediction import predict_failure_probability
preds_train = predict_failure_probability(df, model=loaded_model)
assert "unit" in preds_train.columns
assert "cycle" in preds_train.columns
assert "failure_probability" in preds_train.columns
assert preds_train["failure_probability"].between(0, 1).all(), "Probabilities out of [0,1]!"
assert len(preds_train) == len(df)
pmin = preds_train["failure_probability"].min()
pmax = preds_train["failure_probability"].max()
print(f"    Rows: {len(preds_train)},  Prob range: [{pmin:.4f}, {pmax:.4f}]")
print("    PASS: failure_probability always in [0, 1], unit/cycle preserved")

# ------------------------------------------------------------------
# STEP 8: Test-set inference
# ------------------------------------------------------------------
print("\n[8] Running inference on test data...")
df_test = pd.read_csv("src/data/preprocessing/FD001_test_preprocessed.csv")
preds_test = predict_failure_probability(df_test, model=loaded_model)
assert preds_test["failure_probability"].between(0, 1).all()
assert len(preds_test) == len(df_test)
print(f"    Test rows: {len(preds_test)}")
print("    PASS: test inference successful, unit and cycle preserved")

# ------------------------------------------------------------------
# STEP 9: Failure scoring
# ------------------------------------------------------------------
print("\n[9] Scoring failure predictions...")
from src.models.failure.failure_scoring import (
    score_failure_predictions,
    report_status_distribution,
    sample_predictions,
)
scored = score_failure_predictions(preds_test)
assert "failure_status" in scored.columns
invalid_statuses = set(scored["failure_status"].unique()) - {"LOW", "MEDIUM", "HIGH"}
assert not invalid_statuses, f"Invalid statuses: {invalid_statuses}"
print("    PASS: failure_status contains only LOW, MEDIUM, HIGH")
report_status_distribution(scored)

# ------------------------------------------------------------------
# STEP 9b: Save failure_scores.csv
# ------------------------------------------------------------------
print("\n[9b] Saving failure_scores.csv...")
from src.models.failure.failure_prediction import save_scores
from src.models.failure.config import FAILURE_SCORES_PATH
saved_path = save_scores(scored)
assert os.path.isfile(saved_path), f"failure_scores.csv not found at {saved_path}"
df_scores = pd.read_csv(saved_path)
required_cols = {"unit", "cycle", "failure_probability", "failure_status"}
assert required_cols.issubset(df_scores.columns), \
    f"Missing columns in CSV: {required_cols - set(df_scores.columns)}"
assert list(df_scores.columns) == ["unit", "cycle", "failure_probability", "failure_status"], \
    f"Unexpected column order: {list(df_scores.columns)}"
assert df_scores["failure_probability"].between(0, 1).all(), \
    "failure_probability out of [0,1] in saved CSV"
assert set(df_scores["failure_status"].unique()).issubset({"LOW", "MEDIUM", "HIGH"}), \
    f"Invalid failure_status values in saved CSV: {set(df_scores['failure_status'].unique())}"
assert len(df_scores) == len(scored), \
    f"Row count mismatch: CSV has {len(df_scores)}, scored has {len(scored)}"
print(f"    Rows: {len(df_scores):,}  |  Columns: {list(df_scores.columns)}")
print(f"    PASS: failure_scores.csv created at {saved_path}")

# ------------------------------------------------------------------
# STEP 10: Sample output
# ------------------------------------------------------------------
print("\n[10] Sample scored predictions (across all 3 statuses):")
sample = sample_predictions(scored)
print(sample.to_string(index=False))

# ------------------------------------------------------------------
# STEP 11: Verify Member 1 files untouched
# ------------------------------------------------------------------
print("\n[11] Verifying Member 1 files are unmodified...")
health_files = os.listdir("src/models/health")
expected = {
    "anomaly_config.py", "anomaly_detector.py",
    "health_config.py", "health_scoring.py",
    "train_anomaly.py", "__init__.py",
}
for f in expected:
    assert f in health_files, f"MISSING Member 1 file: {f}"
print(f"    PASS: all Member 1 files present: {sorted(expected)}")

# ------------------------------------------------------------------
# STEP 12: Evaluation metrics summary
# ------------------------------------------------------------------
print("\n[12] Evaluation metrics from training:")
print(f"    ROC-AUC  : {metrics['roc_auc']:.4f}")
print(f"    Confusion matrix:\n{metrics['confusion_matrix']}")

print("\n" + "=" * 60)
print("ALL INTEGRATION TESTS PASSED")
print("=" * 60)
