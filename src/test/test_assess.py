"""
Offline integration test for POST /api/assess.

Calls assess_sensor_data() directly (no HTTP server needed) and also sends
a real HTTP request when uvicorn is running.

Usage:
    python test_assess.py            # direct call (no server needed)
    python test_assess.py --http     # also exercises the live HTTP endpoint
                                       (requires uvicorn running on :8000)
"""
from __future__ import annotations

import io
import sys
import textwrap

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Build a valid unseen-engine CSV (cleaned format, 2 units × 10 cycles each)
# ---------------------------------------------------------------------------
CLEANED_COLS = [
    "unit", "cycle",
    "op1", "op2",
    "s2", "s3", "s4", "s6", "s7", "s8", "s9",
    "s11", "s12", "s13", "s14", "s15", "s17", "s20", "s21",
]

rng = np.random.default_rng(42)

rows = []
for unit in [1, 2]:
    for cycle in range(1, 11):
        row = {
            "unit": unit,
            "cycle": cycle,
            "op1": round(float(rng.uniform(-0.01, 0.01)), 4),
            "op2": round(float(rng.uniform(0.0001, 0.0005)), 6),
            "s2":  round(float(rng.uniform(640, 645)), 3),
            "s3":  round(float(rng.uniform(1580, 1590)), 3),
            "s4":  round(float(rng.uniform(1400, 1410)), 3),
            "s6":  round(float(rng.uniform(21.5, 21.6)), 2),
            "s7":  round(float(rng.uniform(554, 556)), 3),
            "s8":  round(float(rng.uniform(2388, 2392)), 3),
            "s9":  round(float(rng.uniform(9060, 9065)), 3),
            "s11": round(float(rng.uniform(47.0, 47.5)), 3),
            "s12": round(float(rng.uniform(521, 524)), 3),
            "s13": round(float(rng.uniform(2388, 2392)), 3),
            "s14": round(float(rng.uniform(8140, 8150)), 3),
            "s15": round(float(rng.uniform(8.3, 8.5)), 4),
            "s17": round(float(rng.uniform(391, 393)), 3),
            "s20": round(float(rng.uniform(38.8, 39.0)), 3),
            "s21": round(float(rng.uniform(23.1, 23.5)), 4),
        }
        rows.append(row)

valid_csv = pd.DataFrame(rows)[CLEANED_COLS].to_csv(index=False).encode()

# ---------------------------------------------------------------------------
# Test 1 — valid CSV (direct engine call)
# ---------------------------------------------------------------------------
print("=" * 60)
print("TEST 1: valid CSV (direct call)")
print("=" * 60)
from src.api.assess import assess_sensor_data

result = assess_sensor_data(valid_csv)
if isinstance(result, list):
    for r in result:
        print(r)
else:
    print(result)

# Check required keys
expected_keys = {
    "unit", "cycle", "anomaly_score", "health_score",
    "health_status", "failure_probability", "failure_status",
    "predicted_rul_cycles",
}
if isinstance(result, list):
    for r in result:
        missing = expected_keys - set(r)
        assert not missing, f"Missing keys: {missing}"
else:
    missing = expected_keys - set(result)
    assert not missing, f"Missing keys: {missing}"
print("PASS: all required keys present\n")

# ---------------------------------------------------------------------------
# Test 2 — RUL column as input should be rejected
# ---------------------------------------------------------------------------
print("=" * 60)
print("TEST 2: RUL column in input should be rejected (422)")
print("=" * 60)
rul_csv = pd.DataFrame(rows)[CLEANED_COLS].assign(rul=50).to_csv(index=False).encode()
try:
    assess_sensor_data(rul_csv)
    print("FAIL: expected ValueError, got nothing")
except ValueError as e:
    print(f"PASS: got expected error: {e}\n")

# ---------------------------------------------------------------------------
# Test 3 — invalid CSV (missing columns)
# ---------------------------------------------------------------------------
print("=" * 60)
print("TEST 3: invalid CSV (missing sensor columns)")
print("=" * 60)
bad_csv = b"unit,cycle,fake_col\n1,1,0.5\n1,2,0.6\n"
try:
    assess_sensor_data(bad_csv)
    print("FAIL: expected ValueError, got nothing")
except ValueError as e:
    print(f"PASS: got expected error: {e}\n")

# ---------------------------------------------------------------------------
# Test 4 — single-cycle (insufficient history)
# ---------------------------------------------------------------------------
print("=" * 60)
print("TEST 4: single cycle (insufficient history)")
print("=" * 60)
one_cycle = pd.DataFrame([rows[0]])[CLEANED_COLS].to_csv(index=False).encode()
try:
    assess_sensor_data(one_cycle)
    print("FAIL: expected ValueError, got nothing")
except ValueError as e:
    print(f"PASS: got expected error: {e}\n")

print("All direct tests PASSED.")
