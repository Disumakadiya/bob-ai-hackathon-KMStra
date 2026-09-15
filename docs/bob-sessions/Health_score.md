# FIX HEALTH SCORE — TRACE AND CORRECT ONLY THE SCORING LOGIC

Investigate why Unit 101 CSV inference produces:
- Anomaly Score = 0.2184
- Health Score = 0.0/100

Trace the complete path:
Isolation Forest output → anomaly score → health score → health status → /api/assess → frontend.

Requirements:
- Keep the existing Isolation Forest model unchanged.
- Do NOT retrain.
- Do NOT change preprocessing or features.
- Do NOT hardcode a health score.
- Health Score must be a meaningful continuous 0–100 value derived from the existing anomaly output.
- Verify the score mapping handles unseen assets and does not collapse valid anomaly values to exactly 0 unless genuinely critical.
- Preserve existing health thresholds/status logic unless the current implementation is demonstrably wrong.
- Add/keep tests for normal, anomalous, and unseen-asset inputs.
- Show the exact root cause and formula currently used.
- Fix only the health-score conversion if needed.

Then test sample_sensor_history.csv and unseen_asset_test_20_cycles.csv and report the resulting anomaly score, health score, and health status.check this fix is done

---

**Status:** error  **Date:** 2026-09-14

---

### 👤 User

FIX HEALTH SCORE — TRACE AND CORRECT ONLY THE SCORING LOGIC

Investigate why Unit 101 CSV inference produces:
- Anomaly Score = 0.2184
- Health Score = 0.0/100

Trace the complete path:
Isolation Forest output → anomaly score → health score → health status → /api/assess → frontend.

Requirements:
- Keep the existing Isolation Forest model unchanged.
- Do NOT retrain.
- Do NOT change preprocessing or features.
- Do NOT hardcode a health score.
- Health Score must be a meaningful continuous 0–100 value derived from the existing anomaly output.
- Verify the score mapping handles unseen assets and does not collapse valid anomaly values to exactly 0 unless genuinely critical.
- Preserve existing health thresholds/status logic unless the current implementation is demonstrably wrong.
- Add/keep tests for normal, anomalous, and unseen-asset inputs.
- Show the exact root cause and formula currently used.
- Fix only the health-score conversion if needed.

Then test sample_sensor_history.csv and unseen_asset_test_20_cycles.csv and report the resulting anomaly score, health score, and health status.check this fix is done