# Failure Prediction Module — Member 2

## Overview

This module implements **engine failure-risk prediction** for the NASA C-MAPSS FD001 dataset using a binary XGBoost classifier.

It is one component of a larger predictive-maintenance pipeline:

| Member | Component | Output columns |
|--------|-----------|----------------|
| **Member 1** | Health / Anomaly Detection | `unit`, `cycle`, `anomaly_score`, `health_score`, `health_status` |
| **Member 2 (this module)** | Failure Prediction | `unit`, `cycle`, `failure_probability`, `failure_status` |
| **Member 3** | RUL Prediction | `unit`, `cycle`, `predicted_rul` |

---

## Module Structure

```
src/models/failure/
├── __init__.py           Public API exports
├── config.py             ALL thresholds, hyperparameters, paths
├── failure_labeling.py   TASK 2 — Build binary label from RUL
├── train.py              TASK 1 — Train XGBoost classifier
├── failure_prediction.py TASK 3 — Run inference
├── failure_scoring.py    TASK 4 — Map probability → LOW/MEDIUM/HIGH
└── README.md             (this file)
```

---

## Quick Start

```python
import pandas as pd
from src.models.failure import (
    build_labeled_dataset,
    run_training_pipeline,
    predict_failure_probability,
    score_failure_predictions,
)

# 1. Load pre-processed training data
df_train = pd.read_csv("src/data/preprocessing/FD001_train_preprocessed.csv")

# 2. Create failure label from RUL (threshold = 30, from config.py)
df_labeled = build_labeled_dataset(df_train)

# 3. Train the model (engine-aware split, saves artifact automatically)
model, feature_cols, metrics = run_training_pipeline(df_labeled)

# 4. Load test data and run inference
df_test = pd.read_csv("src/data/preprocessing/FD001_test_preprocessed.csv")
predictions = predict_failure_probability(df_test)

# 5. Score into LOW / MEDIUM / HIGH
scored = score_failure_predictions(predictions)
print(scored.head())
```

---

## Failure Label Construction

NASA C-MAPSS FD001 does not include a binary failure column. The label is derived from the `rul` (Remaining Useful Life) column:

```
failure_label = 1   if RUL <= 30   (approaching failure)
failure_label = 0   if RUL >  30   (not approaching failure)
```

**Threshold = 30 cycles** (configured in `config.RUL_FAILURE_THRESHOLD`)

Rationale:
- 30 cycles is a standard early-warning horizon in the PHM08/C-MAPSS literature
- At this threshold ~15% of observations are positive (class 1), which is workable for XGBoost with `scale_pos_weight`
- Gives operators ~30 cycles to take action before end-of-life

> **Critical:** `rul` is **never** used as an input feature. It is used solely to construct the training label.

---

## Features Used

All columns from the pre-processed CSV **except**:

| Excluded column | Reason |
|-----------------|--------|
| `rul` | Used only for label construction; would cause leakage |
| `unit` | Engine identifier; used for grouping only |
| `cycle` | Time index; preserved in output but not a predictive feature |
| `failure_label` | The target itself |

**Features included (100 columns):**
- Sensor base columns: `s2`, `s3`, `s4`, `s6`, `s7`, `s8`, `s9`, `s11`–`s15`, `s17`, `s20`, `s21`
- Operational settings: `op1`, `op2`
- Rolling features: `*_roll_mean5`, `*_roll_std5`, `*_roll_min5`, `*_roll_max5`
- Delta features: `*_delta1`

> **Note:** Sensor columns are NOT assigned physical interpretations (temperature, pressure, etc.) unless such mappings are verified in an authoritative source.

---

## Data Leakage Prevention

This module uses an **engine-aware (unit-aware) train/validation split**:

1. All 100 engine unit IDs are identified.
2. 80% of engines go to training, 20% to validation (configurable).
3. **All rows for a given engine go entirely to one split.**

This prevents:
- Temporal leakage (seeing later cycles during training)
- Cross-engine leakage (mixing same-engine observations across splits)

`rul` is never included in the feature matrix at any stage.

---

## Model

| Setting | Value |
|---------|-------|
| Algorithm | XGBoost Binary Classifier |
| `n_estimators` | 300 |
| `max_depth` | 6 |
| `learning_rate` | 0.05 |
| `subsample` | 0.8 |
| `colsample_bytree` | 0.8 |
| `min_child_weight` | 5 |
| `scale_pos_weight` | Computed dynamically from training class ratio |
| `random_state` | 42 |

All hyperparameters are in `config.XGBOOST_PARAMS`.

---

## Failure Status Mapping

| `failure_probability` range | `failure_status` |
|-----------------------------|-----------------|
| < 0.40 | `LOW` |
| 0.40 – 0.70 | `MEDIUM` |
| ≥ 0.70 | `HIGH` |

Thresholds are in `config.LOW_MEDIUM_BOUNDARY` and `config.MEDIUM_HIGH_BOUNDARY`.

> **Important:** `HIGH` means the model assigns a high probability that this observation is within 30 cycles of engine end-of-life. It does **not** guarantee certain failure.

---

## Output Contract

```
unit                – engine identifier (int)
cycle               – operational cycle (int)
failure_probability – float in [0.0, 1.0]
failure_status      – one of: LOW | MEDIUM | HIGH
```

---

## Do Not Modify

- `src/models/health/` — Member 1 (Health/Anomaly Detection)
- `src/data/preprocessing/` — shared preprocessing pipeline
- `src/data/ingestion/` — raw data ingestion
- `src/data/schemas/` — canonical schema

---

## Limitations

1. The binary label is based on a chosen RUL threshold (30 cycles), not a directly observed physical failure event.
2. The model predicts engine/asset failure risk — not component-level failure (no verified sensor-to-component mapping exists in the current dataset).
3. The model is trained on FD001 (single operating condition, single fault mode). Generalization to other C-MAPSS sub-datasets requires re-training.
4. Class imbalance (~15% positive) is handled by `scale_pos_weight` but recall may still be imperfect on out-of-distribution data.
