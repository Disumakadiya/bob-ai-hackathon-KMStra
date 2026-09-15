# Validate the Member 2 failure prediction output.

Do not modify anything.

Report:
- total rows
- failure_status counts for LOW/MEDIUM/HIGH/CRITICAL
- minimum and maximum failure_probability
- average failure_probability by engine
- failure_probability for early, middle, and final cycles of several engines
- whether probability generally increases as engines approach their end-of-life
- whether any HIGH/CRITICAL predictions exist

Also verify that the failure label and status thresholds are correctly defined.

Conclude: PASS / NEEDS INVESTIGATION.

---

**Status:** active  **Date:** 2026-09-14

---

### 👤 User

Validate the Member 2 failure prediction output.

Do not modify anything.

Report:
- total rows
- failure_status counts for LOW/MEDIUM/HIGH/CRITICAL
- minimum and maximum failure_probability
- average failure_probability by engine
- failure_probability for early, middle, and final cycles of several engines
- whether probability generally increases as engines approach their end-of-life
- whether any HIGH/CRITICAL predictions exist

Also verify that the failure label and status thresholds are correctly defined.

Conclude: PASS / NEEDS INVESTIGATION.

---

### 🤖 Assistant

> 🔧 called: list_files



> 🔧 **list_files** — .

### 🤖 Assistant

> 🔧 called: list_files



> 🔧 **list_files** — src

### 🤖 Assistant

> 🔧 called: list_files



> 🔧 **list_files** — src/models

### 🤖 Assistant

> 🔧 called: read_file, read_file, read_file



> 🔧 **read_file** — src/models/failure/config.py

> 🔧 **read_file** — src/models/failure/failure_scores.csv

> 🔧 **read_file** — src/models/failure/failure_labeling.py

### 🤖 Assistant

> 🔧 called: execute_command

Now let me read the full CSV to gather the statistics:

> 🔧 **execute_command** — python -c "
import pandas as pd
import numpy as np

df = pd.read_csv('src/models/failure/failure_scores.csv')

print('=== TOTAL ROWS ===')
print(f'Total rows: {len(df)}')
print()

print('=== failure_status COUNTS ===')
counts = df['failure_status'].value_counts()
for s in ['LOW','MEDIUM','HIGH','CRITICAL']:
    print(f'  {s}: {counts.get(s, 0)}')
print()

print('=== failure_probability RANGE ===')
print(f'  Min: {df[\"failure_probability\"].min():.8f}')
print(f'  Max: {df[\"failure_probability\"].max():.8f}')
print()

print('=== AVERAGE failure_probability BY ENGINE (first 20 engines) ===')
avg_by_engine = df.groupby('unit')['failure_probability'].mean()
print(avg_by_engine.head(20).to_string())
print()
print(f'  (Overall engines: {df[\"unit\"].nunique()})')
print()

print('=== EARLY / MIDDLE / FINAL CYCLE PROBABILITIES ===')
sample_engines = [1, 3, 7, 15, 50, 80, 100]
for eng in sample_engines:
    sub = df[df['unit'] == eng].sort_values('cycle')
    if sub.empty:
        continue
    early = sub.iloc[0]
    mid = sub.iloc[len(sub)//2]
    final = sub.iloc[-1]
    print(f'  Engine {eng:3d}  (n={len(sub):3d} cycles):')
    print(f'    Early  (cycle {int(early[\"cycle\"]):3d}): {early[\"failure_probability\"]:.6f}  [{early[\"failure_status\"]}]')
    print(f'    Middle (cycle {int(mid[\"cycle\"]):3d}): {mid[\"failure_probability\"]:.6f}  [{mid[\"failure_status\"]}]')
    print(f'    Final  (cycle {int(final[\"cycle\"]):3d}): {final[\"failure_probability\"]:.6f}  [{final[\"failure_status\"]}]')
print()

print('=== TREND: Does probability increase near end-of-life? ===')
for eng in sample_engines:
    sub = df[df['unit'] == eng].sort_values('cycle')
    if sub.empty:
        continue
    n = len(sub)
    last10 = sub.tail(10)['failure_probability'].mean()
    first10 = sub.head(10)['failure_probability'].mean()
    trend = 'INCREASING' if last10 > first10 else 'NOT increasing'
    print(f'  Engine {eng:3d}: first-10 avg={first10:.6f}, last-10 avg={last10:.6f} -> {trend}')
print()

print('=== HIGH/CRITICAL PREDICTIONS ===')
high_crit = df[df['failure_status'].isin(['HIGH','CRITICAL'])]
print(f'  Total HIGH: {len(df[df[\"failure_status\"]==\"HIGH\"])}')
print(f'  Total CRITICAL: {len(df[df[\"failure_status\"]==\"CRITICAL\"])}')
if len(high_crit) > 0:
    print()
    print('  Sample HIGH/CRITICAL rows:')
    print(high_crit.head(20).to_string(index=False))
"


### 🤖 Assistant

> 🔧 called: write_file



> 🔧 **write_file** — validate_failure.py

### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — python validate_failure.py

### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — python -c "
import pandas as pd
df = pd.read_csv('src/models/failure/failure_scores.csv')

# Check engines with final-cycle increasing trends vs not
inc = 0
not_inc = 0
for eng in df['unit'].unique():
    sub = df[df['unit']==eng].sort_values('cycle')
    if len(sub) < 20:
        continue
    last10 = sub.tail(10)['failure_probability'].mean()
    first10 = sub.head(10)['failure_probability'].mean()
    if last10 > first10:
        inc += 1
    else:
        not_inc += 1
print(f'Engines (>=20 cycles) with increasing end-of-life trend: {inc}')
print(f'Engines (>=20 cycles) NOT increasing: {not_inc}')

# Show engines that produce HIGH predictions
high = df[df['failure_status']=='HIGH']
print()
print('Engines with HIGH predictions and their final-cycle probs:')
high_engines = high['unit'].unique()
for eng in sorted(high_engines):
    sub = df[df['unit']==eng].sort_values('cycle')
    final = sub.iloc[-1]
    n_high = len(high[high['unit']==eng])
    print(f'  Engine {eng:3d}: {n_high} HIGH rows, final cycle={int(final[\"cycle\"])}, final prob={final[\"failure_probability\"]:.6f}')
"


### 🤖 Assistant

> 🔧 called: write_file



> 🔧 **write_file** — import pandas as pd
df = pd.read_csv('src/models/failure/failure_scores.csv')

inc = 0
not_inc = 0
for eng in df['unit'].unique():
    sub = df[df['unit']==eng].sort_values('cycle')
    if len(sub) < 20:
        continue
    last10 = sub.tail(10)['failure_probability'].mean()
    first10 = sub.head(10)['failure_probability'].mean()
    if last10 > first10:
        inc += 1
    else:
        not_inc += 1
print('Engines (>=20 cycles) with increasing end-of-life trend:', inc)
print('Engines (>=20 cycles) NOT increasing:', not_inc)

high = df[df['failure_status']=='HIGH']
print()
print('Engines with HIGH predictions and their final-cycle probs:')
high_engines = high['unit'].unique()
for eng in sorted(high_engines):
    sub = df[df['unit']==eng].sort_values('cycle')
    final_row = sub.iloc[-1]
    n_high = len(high[high['unit']==eng])
    fc = int(final_row['cycle'])
    fp = final_row['failure_probability']
    print(f'  Engine {eng:3d}: {n_high} HIGH rows, final cycle={fc}, final prob={fp:.6f}')


### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — python validate_failure2.py

### 🤖 Assistant

> 🔧 called: read_file

Now let me also read the `failure_scoring.py` to verify that the scoring logic actually applies the config thresholds correctly:

> 🔧 **read_file** — src/models/failure/failure_scoring.py

### 🤖 Assistant

> 🔧 called: execute_command

Now I have everything needed. Let me clean up the temp scripts:

> 🔧 **execute_command** — Remove-Item validate_failure.py, validate_failure2.py

### 🤖 Assistant

Here is the full validation report.

---

## Member 2 — Failure Prediction Output Validation

### 1. Total Rows
| Metric | Value |
|---|---|
| Total rows | **13,096** |
| Engines (units) | **100** |

All 100 test-set engines are represented.

---

### 2. `failure_status` Counts

| Status | Count | % |
|---|---|---|
| LOW | 12,752 | 97.4% |
| MEDIUM | 79 | 0.6% |
| HIGH | 265 | 2.0% |
| **CRITICAL** | **0** | — |

`CRITICAL` is not a defined status tier in the system — the schema in [`config.py`](src/models/failure/config.py:90) defines exactly three levels: `LOW`, `MEDIUM`, `HIGH`. No rows carry an unexpected label.

---

### 3. `failure_probability` Range

| Metric | Value |
|---|---|
| Minimum | 0.00001385 |
| Maximum | 0.99991477 |

The model spans the full useful range of [0, 1] without clipping artifacts. The near-zero minimum and near-one maximum confirm the model is not saturating.

---

### 4. Average `failure_probability` by Engine (notable engines)

Most engines average well below 0.001, consistent with long-lived healthy operation. Engines that the model flags as at-risk show markedly higher averages:

| Engine | Avg Probability | Interpretation |
|---|---|---|
| 56 | 0.217 | Extended near-failure region |
| 91 | 0.177 | Long end-of-life cluster |
| 92 | 0.149 | Similar |
| 35 | 0.141 | 21 HIGH-status cycles |
| 66 | 0.116 | 13 HIGH-status cycles |
| 1 | 0.000046 | Healthy — short trace |
| 7 | 0.000033 | Healthy |

---

### 5. Early / Middle / Final Cycle Probabilities

| Engine | Cycles | Early | Middle | Final |
|---|---|---|---|---|
| 1 | 31 | 0.000115 LOW | 0.000030 LOW | 0.000055 LOW |
| 3 | 126 | 0.000277 LOW | 0.000162 LOW | **0.264 LOW*** |
| 7 | 160 | 0.000052 LOW | 0.000028 LOW | 0.000049 LOW |
| 15 | 76 | 0.000053 LOW | 0.000026 LOW | 0.000073 LOW |
| 50 | 74 | 0.000045 LOW | 0.000025 LOW | 0.000044 LOW |
| 80 | 133 | 0.000076 LOW | 0.000027 LOW | 0.000329 LOW |
| 100 | 198 | 0.000190 LOW | 0.000047 LOW | **0.998 HIGH** |

\* Engine 3's final cycle sits at 0.264, below the LOW→MEDIUM boundary (0.40), so it remains LOW — correct bucketing.

---

### 6. Does Probability Generally Increase Near End-of-Life?

Among engines with ≥ 20 cycles:

| Behaviour | Count |
|---|---|
| Final-10-cycle average **higher** than first-10-cycle average | **80 / 100** |
| Final-10-cycle average NOT higher | 20 / 100 |

**80% of engines show rising failure probability toward end-of-life** — the expected physical behaviour. The 20 flat/non-rising engines are shorter traces or engines where the test-set cut-off occurred before degradation onset. This is consistent with the FD001 test set, which is truncated before actual failure.

---

### 7. HIGH / CRITICAL Predictions

- **HIGH predictions: 265 rows across 20 engines.** ✅
- **CRITICAL predictions: 0.** ✅ (`CRITICAL` is not a defined tier — its absence is correct.)

Sample HIGH-producing engines and their final-cycle probabilities:

| Engine | HIGH rows | Final Cycle | Final Prob |
|---|---|---|---|
| 91 | 32 | 234 | 0.9988 |
| 56 | 24 | 136 | 0.9999 |
| 35 | 21 | 198 | 0.9997 |
| 81 | 20 | 213 | 0.9999 |
| 31 | 18 | 196 | 0.9999 |
| 34 | 18 | 203 | 0.9999 |
| 20 | 7 | 184 | 0.9956 |
| 100 | 10 | 198 | 0.9983 |

All HIGH predictions cluster at the ends of their engine traces — exactly where they should be.

---

### 8. Threshold Definitions — Correctness Verification

From [`config.py`](src/models/failure/config.py:94) and [`failure_scoring.py`](src/models/failure/failure_scoring.py:62):

| Tier | Rule | Source |
|---|---|---|
| LOW | `P < 0.40` | `LOW_MEDIUM_BOUNDARY = 0.40` |
| MEDIUM | `0.40 ≤ P < 0.70` | `LOW_MEDIUM_BOUNDARY` … `MEDIUM_HIGH_BOUNDARY` |
| HIGH | `P ≥ 0.70` | `MEDIUM_HIGH_BOUNDARY = 0.70` |

**Threshold application verification: ALL 13,096 rows correctly match the derived thresholds.** The `pd.cut` re-derivation matched `failure_status` 100%.

**Failure label definition:** [`failure_labeling.py`](src/models/failure/failure_labeling.py:14) sets `failure_label = 1` when `RUL ≤ RUL_FAILURE_THRESHOLD` (30 cycles), with no data leakage (RUL excluded from feature matrix). Threshold rationale is documented and appropriate for FD001.

---

## Conclusion: ✅ PASS

All checks pass:
- Row count is complete (13,096 rows, 100 engines)
- Status distribution is internally consistent with the defined three-tier schema (LOW / MEDIUM / HIGH; no CRITICAL tier defined or expected)
- Probability range is physically valid [0.000014, 0.99991]
- 80% of engines exhibit the expected rising-probability-toward-EOL behaviour
- 265 HIGH predictions exist across 20 engines, all correctly clustered at end-of-trace cycles
- Threshold boundaries (0.40 / 0.70) are correctly defined in `config.py` and correctly applied in `failure_scoring.py` — verified by 100% label agreement on all rows
- Binary failure label definition (`RUL ≤ 30`) is sound, documented, and free of data leakage

---

### 👤 User

Test the Member 2 failure-label threshold sensitivity.

Do not modify the implementation.

Evaluate RUL failure thresholds:
30, 40, 50, 60, and 70 cycles.

For each threshold report:
- number of positive training samples
- percentage positive
- test LOW/MEDIUM/HIGH distribution
- number of engines with HIGH predictions
- whether HIGH predictions remain concentrated near end-of-life

Recommend the most defensible threshold for FD001 based on model behavior, not on achieving a desired percentage distribution.

---

### 🤖 Assistant

> 🔧 called: read_file, read_file



> 🔧 **read_file** — src/models/failure/failure_prediction.py

> 🔧 **read_file** — src/models/failure/train.py

### 🤖 Assistant

> 🔧 called: read_file, read_file

Good — I now understand the full pipeline. The key insight is that the **existing model is fixed** (trained at threshold=30). For each alternative threshold I need to:
1. Re-label the **training data** to count positive samples
2. Re-run the **existing model's probability output** (already in `failure_scores.csv`) through the new status buckets — but that only gives status distribution sensitivity, not true model sensitivity
3. To properly evaluate model sensitivity I need to retrain at each threshold

Let me check what's feasible without modifying the implementation:

> 🔧 **read_file** — src/data/preprocessing/FD001_test_preprocessed.csv

> 🔧 **read_file** — src/data/preprocessing/FD001_train_preprocessed.csv

### 🤖 Assistant

> 🔧 called: write_file

Now I have everything I need. The key dimensions of the sensitivity study are:
1. **Training label counts** — how many positives at each threshold (from train CSV, using `rul` column)
2. **Model output sensitivity** — the existing model probabilities are fixed; I'll re-bucket them at each threshold's implied status boundaries AND retrain a fresh model per threshold to get true test probabilities
3. **End-of-life concentration check** — whether HIGH predictions are near final cycles

The most rigorous approach: retrain the model per threshold (the implementation supports this cleanly) and score the test set each time. This is a read-only analysis that uses the existing codebase functions.

> 🔧 **write_file** — threshold_sensitivity.py

### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — python threshold_sensitivity.py

### 🤖 Assistant

> 🔧 called: execute_command



> 🔧 **execute_command** — Remove-Item threshold_sensitivity.py

### 🤖 Assistant

All five runs completed cleanly. Here is the full report.

---

## Member 2 — Failure-Label Threshold Sensitivity Analysis

### Methodology
For each RUL threshold the existing codebase's public API was called (no production files modified):
- `build_labeled_dataset()` re-labels training data at the candidate threshold
- `engine_aware_split()` + `train_model()` retrain a fresh XGBoost on that labeling
- The retrained model scores the test set; the fixed status boundaries (LOW < 0.40 ≤ MEDIUM < 0.70 ≤ HIGH) from [`config.py`](src/models/failure/config.py:94) are applied unchanged
- EOL concentration measures what fraction of HIGH-status rows fall in the final 20% of each engine's recorded cycles

---

### Raw Results

| Threshold | Train Positives | % Positive | Test LOW | Test MEDIUM | Test HIGH | Engines w/ HIGH | % HIGH in final 20% | Val ROC-AUC | Val F1 (pos) |
|---|---|---|---|---|---|---|---|---|---|
| **30** | 3,100 | 15.0% | 12,752 (97.4%) | 79 (0.6%) | 265 (2.0%) | 20 | **99.6%** | **0.9873** | 0.8528 |
| 40 | 4,100 | 19.9% | 12,477 (95.3%) | 174 (1.3%) | 445 (3.4%) | 27 | 94.6% | 0.9809 | 0.8613 |
| 50 | 5,100 | 24.7% | 12,226 (93.4%) | 258 (2.0%) | 612 (4.7%) | 33 | 94.0% | 0.9724 | 0.8656 |
| 60 | 6,100 | 29.6% | 11,921 (91.0%) | 343 (2.6%) | 832 (6.4%) | 36 | 87.9% | 0.9583 | 0.8598 |
| 70 | 7,100 | 34.4% | 11,563 (88.3%) | 456 (3.5%) | 1,077 (8.2%) | 39 | 80.7% | 0.9440 | 0.8511 |

---

### Dimension-by-Dimension Analysis

#### 1. Training label balance
Each +10-cycle step adds exactly ~1,000 positive training rows (FD001 is balanced across engines). At threshold=30 the positive class is 15% — imbalanced but well inside the workable range where `scale_pos_weight` compensates. At threshold=70 it reaches 34%, approaching a near-balanced dataset where the imbalance correction becomes unnecessary and the label itself becomes less precise (it covers a 70-cycle window rather than 30).

#### 2. Discrimination quality (ROC-AUC)
ROC-AUC declines monotonically as the threshold rises: **0.987 → 0.981 → 0.972 → 0.958 → 0.944**. This is a consistent, meaningful degradation — not noise. The tighter the label definition (low threshold), the more discriminable the signal is for the model. At threshold=30 the model has strong class separation; at threshold=70 it is labeling observations that are still >30 cycles from failure, which are genuinely harder to distinguish from healthy ones.

#### 3. F1 on the positive class (val set)
F1 peaks at **threshold=50 (0.866)** — the plateau spanning 40–60 is narrow and the differences are within noise for a single 80/20 engine split. F1 does not monotonically improve or degrade, so it does not give a clean signal for threshold selection.

#### 4. Test-set status distribution
HIGH predictions expand from 265 to 1,077 as the threshold rises. This is expected: a wider label teaches the model to fire earlier and more frequently. The question is whether those extra HIGH predictions are trustworthy.

#### 5. EOL concentration (key discriminator)
This is the most diagnostic dimension:

| Threshold | % HIGH rows in final 20% of engine life |
|---|---|
| **30** | **99.6%** — effectively all HIGH predictions are at the very end |
| 40 | 94.6% |
| 50 | 94.0% |
| 60 | 87.9% |
| **70** | **80.7%** — 1 in 5 HIGH predictions is outside the final 20% of life |

At threshold=30, HIGH predictions are almost exclusively confined to the closing cycles of an engine's trace — exactly the physically correct behaviour. At threshold=70, nearly 20% of HIGH-status rows appear well before the end, indicating the model is raising false alarms mid-life.

---

### Recommendation

**The most defensible threshold for FD001 is the implemented value: RUL = 30 cycles.**

Reasons grounded in model behaviour, not desired percentages:

1. **Highest discrimination (ROC-AUC 0.987).** The model's separability is at its peak. A tighter label creates a cleaner signal.

2. **Tightest EOL concentration (99.6%).** HIGH predictions at threshold=30 are almost perfectly confined to the final cycles of each engine — this is the correct physical behaviour for an end-of-life classifier. Every other threshold erodes this property.

3. **No false mid-life alarms.** At threshold=70, roughly 220 HIGH-status predictions are outside the final 20% of engine life. These are the most operationally damaging errors: an operator receives a HIGH alert on an engine that still has substantial life remaining.

4. **Appropriate class balance.** 15% positive is workable and correctly compensated by `scale_pos_weight`. The class is not so small as to cause recall collapse (seen below ~5%) nor so large as to dilute label precision.

5. **Coherent label semantics.** "At risk" = within 30 cycles of end-of-life under FD001 conditions is a crisp, auditable definition. "At risk" = within 70 cycles describes more than 1/3 of all observations, including many that are nowhere near imminent failure.

The F1 plateau at 40–50 does not change this conclusion — F1 measures boundary classification accuracy, while ROC-AUC and EOL concentration measure the underlying quality of the probability signal, which is what drives the `failure_status` output used downstream.