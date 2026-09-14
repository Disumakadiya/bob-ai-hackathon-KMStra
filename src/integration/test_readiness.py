# src/integration/test_readiness.py
"""Integration tests for Mission Readiness & Predictive Maintenance Copilot.

Tests verify (without the frontend and without MCP):
  1.  Input files exist.
  2.  Required input columns exist.
  3.  Output file exists.
  4.  Required output columns exist.
  5.  Output is non-empty.
  6.  No null asset_ids.
  7.  Numeric columns are numeric.
  8.  Readiness statuses are valid.
  9.  Maintenance priority values are valid.
  10. No unexpected duplicate asset/cycle records.
  11. Mission-readiness functions execute successfully.
  12. API endpoints return real data (via FastAPI TestClient).

Run:
    python -m src.integration.test_readiness
    # or via pytest:
    pytest src/integration/test_readiness.py -v
"""

from __future__ import annotations

import sys
import pathlib
import traceback

import pandas as pd

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path
# ---------------------------------------------------------------------------
_THIS_DIR = pathlib.Path(__file__).resolve().parent
_SRC_DIR  = _THIS_DIR.parent
_ROOT     = _SRC_DIR.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.integration.readiness_engine import (
    HEALTH_CSV_PATH,
    FAILURE_CSV_PATH,
    RUL_CSV_PATH,
    OUTPUT_CSV,
    MISSIONS_CSV,
    VALID_READINESS_STATUSES,
    VALID_PRIORITY_VALUES,
    load_model_outputs,
    build_unified_dataset,
    ReadinessEngine,
    MissionReadiness,
    normalize_mission_asset_id,
)

# ---------------------------------------------------------------------------
# Test harness helpers
# ---------------------------------------------------------------------------
_PASS = "PASS"
_FAIL = "FAIL"
_results: list[tuple[str, str, str]] = []  # (name, status, detail)


def _check(name: str, condition: bool, detail: str = "") -> bool:
    status = _PASS if condition else _FAIL
    _results.append((name, status, detail))
    marker = "OK" if condition else "FAIL"
    print(f"  [{marker}] {name}" + (f": {detail}" if detail else ""))
    return condition


# ===========================================================================
# Tests
# ===========================================================================

def test_input_files_exist() -> None:
    print("\n[1] Input files exist")
    _check("health anomaly_scores.csv",  HEALTH_CSV_PATH.exists(),  str(HEALTH_CSV_PATH))
    _check("failure failure_scores.csv", FAILURE_CSV_PATH.exists(), str(FAILURE_CSV_PATH))
    _check("rul rul_predictions.csv",    RUL_CSV_PATH.exists(),     str(RUL_CSV_PATH))
    _check("missions.csv",               MISSIONS_CSV.exists(),      str(MISSIONS_CSV))


def test_input_columns() -> None:
    print("\n[2] Required input columns")
    health  = pd.read_csv(HEALTH_CSV_PATH)
    failure = pd.read_csv(FAILURE_CSV_PATH)
    rul     = pd.read_csv(RUL_CSV_PATH)

    for col in ["unit", "cycle", "anomaly_score"]:
        _check(f"health.{col}", col in health.columns)
    for col in ["unit", "cycle", "failure_probability", "failure_status"]:
        _check(f"failure.{col}", col in failure.columns)
    for col in ["asset_id", "cycle", "predicted_rul", "rul_status"]:
        _check(f"rul.{col}", col in rul.columns)


def test_output_file_exists() -> None:
    print("\n[3] Output file exists")
    _check("asset_readiness.csv", OUTPUT_CSV.exists(), str(OUTPUT_CSV))


def test_output_columns() -> None:
    print("\n[4] Required output columns present")
    required = [
        "asset_id", "cycle",
        "health_score", "health_status", "anomaly_score",
        "failure_probability", "failure_risk",
        "predicted_rul", "rul_status",
        "readiness_score", "readiness_status",
        "primary_reason", "recommended_action",
        "maintenance_priority_score", "maintenance_priority",
    ]
    if not OUTPUT_CSV.exists():
        _check("output_columns (skipped — no file)", False, "Run build_readiness first")
        return
    df = pd.read_csv(OUTPUT_CSV)
    for col in required:
        _check(f"output.{col}", col in df.columns)


def test_output_non_empty() -> None:
    print("\n[5] Output is non-empty")
    if not OUTPUT_CSV.exists():
        _check("non-empty (skipped)", False, "Run build_readiness first")
        return
    df = pd.read_csv(OUTPUT_CSV)
    _check("rows > 0", len(df) > 0, f"rows={len(df)}")


def test_no_null_asset_ids() -> None:
    print("\n[6] No null asset_ids")
    if not OUTPUT_CSV.exists():
        _check("no_null_asset_id (skipped)", False)
        return
    df = pd.read_csv(OUTPUT_CSV)
    null_count = df["asset_id"].isna().sum()
    _check("no null asset_id", null_count == 0, f"null_count={null_count}")


def test_numeric_columns() -> None:
    print("\n[7] Numeric columns are numeric")
    if not OUTPUT_CSV.exists():
        _check("numeric_cols (skipped)", False)
        return
    df = pd.read_csv(OUTPUT_CSV)
    numeric_cols = [
        "health_score", "anomaly_score", "failure_probability",
        "predicted_rul", "readiness_score", "maintenance_priority_score",
    ]
    for col in numeric_cols:
        if col in df.columns:
            ok = pd.api.types.is_numeric_dtype(df[col])
            _check(f"numeric.{col}", ok, f"dtype={df[col].dtype}")


def test_valid_readiness_statuses() -> None:
    print("\n[8] Readiness statuses are valid")
    if not OUTPUT_CSV.exists():
        _check("readiness_statuses (skipped)", False)
        return
    df = pd.read_csv(OUTPUT_CSV)
    unique_vals = set(df["readiness_status"].unique())
    invalid = unique_vals - VALID_READINESS_STATUSES
    _check(
        "readiness_status values",
        len(invalid) == 0,
        f"found={unique_vals}" if invalid else f"valid values: {unique_vals}",
    )


def test_valid_priority_values() -> None:
    print("\n[9] Maintenance priority values are valid")
    if not OUTPUT_CSV.exists():
        _check("priority_values (skipped)", False)
        return
    df = pd.read_csv(OUTPUT_CSV)
    unique_vals = set(df["maintenance_priority"].unique())
    invalid = unique_vals - VALID_PRIORITY_VALUES
    _check(
        "maintenance_priority values",
        len(invalid) == 0,
        f"found={unique_vals}" if invalid else f"valid values: {unique_vals}",
    )


def test_no_duplicate_asset_cycle() -> None:
    print("\n[10] No duplicate asset/cycle records")
    if not OUTPUT_CSV.exists():
        _check("no_duplicates (skipped)", False)
        return
    df = pd.read_csv(OUTPUT_CSV)
    dup_count = df.duplicated(subset=["asset_id", "cycle"]).sum()
    _check("no duplicate (asset_id, cycle)", dup_count == 0, f"duplicates={dup_count}")


def test_mission_readiness_functions() -> None:
    print("\n[11] Mission-readiness functions execute successfully")
    if not OUTPUT_CSV.exists():
        _check("mission_readiness (skipped)", False)
        return
    if not MISSIONS_CSV.exists():
        _check("missions.csv not found", False)
        return

    try:
        df = pd.read_csv(OUTPUT_CSV)
        df["asset_id"] = df["asset_id"].astype(int)
        missions = pd.read_csv(MISSIONS_CSV)
        mr = MissionReadiness(df, missions)

        first_mission_id = missions["mission_id"].iloc[0]
        _check("MissionReadiness instantiation", True)

        summary = mr.mission_readiness_summary(first_mission_id)
        _check(
            "mission_readiness_summary",
            isinstance(summary, dict) and "suitable_count" in summary,
            f"mission_id={first_mission_id}, suitable={summary.get('suitable_count')}",
        )

        suitable = mr.suitable_assets(first_mission_id)
        _check(
            "suitable_assets returns DataFrame",
            isinstance(suitable, pd.DataFrame),
            f"shape={suitable.shape}",
        )

        unsuitable = mr.unsuitable_assets(first_mission_id)
        _check(
            "unsuitable_assets returns DataFrame",
            isinstance(unsuitable, pd.DataFrame),
            f"shape={unsuitable.shape}",
        )

        best = mr.lowest_risk_asset(first_mission_id)
        _check(
            "lowest_risk_asset",
            best is None or isinstance(best, pd.Series),
            f"asset={None if best is None else best['asset_id']}",
        )

        # Test can_assign with first mission asset
        first_mission_row = missions[missions["mission_id"] == first_mission_id].iloc[0]
        eng_id = int(first_mission_row["asset_id"].split("-")[-1])
        result = mr.can_assign(eng_id, first_mission_id)
        _check(
            "can_assign",
            isinstance(result, dict) and "suitable" in result,
            f"asset={eng_id}, suitable={result.get('suitable')}",
        )

    except Exception as exc:
        _check("mission_readiness_functions", False, str(exc))
        traceback.print_exc()


def test_api_endpoints() -> None:
    print("\n[12] API endpoints return real data")
    if not OUTPUT_CSV.exists():
        _check("api_tests (skipped)", False, "Run build_readiness first")
        return

    try:
        from fastapi.testclient import TestClient
        # Clear lru_cache so TestClient gets fresh data
        import src.api.main as api_module
        api_module._load_readiness.cache_clear()
        api_module._load_missions.cache_clear()

        client = TestClient(api_module.app)

        # GET /assets
        resp = client.get("/assets")
        ok = resp.status_code == 200 and isinstance(resp.json(), list) and len(resp.json()) > 0
        _check(
            "GET /assets",
            ok,
            f"status={resp.status_code} count={len(resp.json()) if resp.status_code == 200 else '?'}",
        )

        # GET /assets/{asset_id}
        resp = client.get("/assets/1")
        ok = resp.status_code == 200 and resp.json().get("asset_id") == 1
        _check("GET /assets/1", ok, f"status={resp.status_code}")

        # GET /assets/{asset_id}/readiness
        resp = client.get("/assets/1/readiness")
        body = resp.json()
        ok = resp.status_code == 200 and "readiness_status" in body
        _check(
            "GET /assets/1/readiness",
            ok,
            f"status={resp.status_code} readiness_status={body.get('readiness_status')}",
        )

        # GET /assets/{asset_id}/health
        resp = client.get("/assets/1/health")
        body = resp.json()
        ok = resp.status_code == 200 and "health_score" in body
        _check(
            "GET /assets/1/health",
            ok,
            f"status={resp.status_code} health_score={body.get('health_score')}",
        )

        # GET /assets/{asset_id}/failure
        resp = client.get("/assets/1/failure")
        body = resp.json()
        ok = resp.status_code == 200 and "failure_probability" in body
        _check(
            "GET /assets/1/failure",
            ok,
            f"status={resp.status_code} failure_probability={body.get('failure_probability')}",
        )

        # GET /assets/{asset_id}/rul
        resp = client.get("/assets/1/rul")
        body = resp.json()
        ok = resp.status_code == 200 and "predicted_rul" in body
        _check(
            "GET /assets/1/rul",
            ok,
            f"status={resp.status_code} predicted_rul={body.get('predicted_rul')}",
        )

        # GET /maintenance/priorities
        resp = client.get("/maintenance/priorities")
        ok = resp.status_code == 200 and isinstance(resp.json(), list) and len(resp.json()) > 0
        _check(
            "GET /maintenance/priorities",
            ok,
            f"status={resp.status_code} count={len(resp.json()) if resp.status_code == 200 else '?'}",
        )

        # GET /missions/{mission_id}/readiness — use first real mission_id from CSV
        missions_df = pd.read_csv(MISSIONS_CSV)
        first_mid = missions_df["mission_id"].iloc[0]
        resp = client.get(f"/missions/{first_mid}/readiness")
        body = resp.json()
        ok = resp.status_code == 200 and "suitable_count" in body
        _check(
            f"GET /missions/{first_mid}/readiness",
            ok,
            f"status={resp.status_code} suitable={body.get('suitable_count')}",
        )

        # 404 for unknown asset
        resp = client.get("/assets/9999")
        _check("GET /assets/9999 -> 404", resp.status_code == 404, f"status={resp.status_code}")

        # 404 for unknown mission
        resp = client.get("/missions/MIS-NOTEXIST/readiness")
        _check(
            "GET /missions/MIS-NOTEXIST -> 404",
            resp.status_code == 404,
            f"status={resp.status_code}",
        )

    except ImportError as exc:
        _check("fastapi[testclient] available", False, str(exc))
    except Exception as exc:
        _check("api_tests", False, str(exc))
        traceback.print_exc()


# ===========================================================================
# Tests [13] — Identifier mapping (normalize_mission_asset_id + MIS-092)
# ===========================================================================

def test_identifier_mapping() -> None:
    print("\n[13] Identifier mapping: ENG-XXX -> numeric model asset ID")

    # 1. ENG-001 -> 1
    try:
        result = normalize_mission_asset_id("ENG-001")
        _check("ENG-001 -> 1", result == 1, f"got {result}")
    except Exception as exc:
        _check("ENG-001 -> 1", False, str(exc))

    # 2. ENG-082 -> 82
    try:
        result = normalize_mission_asset_id("ENG-082")
        _check("ENG-082 -> 82", result == 82, f"got {result}")
    except Exception as exc:
        _check("ENG-082 -> 82", False, str(exc))

    # 3. ENG-100 -> 100
    try:
        result = normalize_mission_asset_id("ENG-100")
        _check("ENG-100 -> 100", result == 100, f"got {result}")
    except Exception as exc:
        _check("ENG-100 -> 100", False, str(exc))

    # 4. malformed ID -> validation error
    raised = False
    try:
        normalize_mission_asset_id("INVALID-ID")
    except ValueError as exc:
        raised = True
        _check("malformed ID raises ValueError", True, str(exc)[:60])
    if not raised:
        _check("malformed ID raises ValueError", False, "no exception raised")

    # 5. unknown asset (valid format but not in dataset) -> validation error
    if OUTPUT_CSV.exists():
        df = pd.read_csv(OUTPUT_CSV)
        valid_ids = set(df["asset_id"].astype(int).unique())
        raised = False
        try:
            normalize_mission_asset_id("ENG-999", valid_ids)
        except ValueError as exc:
            raised = True
            _check("ENG-999 not in dataset raises ValueError", True, str(exc)[:60])
        if not raised:
            _check("ENG-999 not in dataset raises ValueError", False, "no exception raised")
    else:
        _check("unknown asset validation (skipped)", False, "Run build_readiness first")

    # 6–9. MIS-092 resolves ENG-082 -> model asset 82 and checks readiness
    if not OUTPUT_CSV.exists() or not MISSIONS_CSV.exists():
        for name in [
            "MIS-092 assigned_asset_id is ENG-082",
            "MIS-092 assigned_asset_model_id is 82",
            "MIS-092 assigned asset readiness from CSV",
            "MIS-092 suitable/unsuitable classification correct",
        ]:
            _check(name, False, "Run build_readiness first")
        return

    try:
        df = pd.read_csv(OUTPUT_CSV)
        df["asset_id"] = df["asset_id"].astype(int)
        missions = pd.read_csv(MISSIONS_CSV)
        mr = MissionReadiness(df, missions)

        # 6. MIS-092 correctly resolves ENG-082 -> model asset 82
        eval_result = mr.assigned_asset_evaluation("MIS-092")
        _check(
            "MIS-092 assigned_asset_id is ENG-082",
            eval_result["assigned_asset_id"] == "ENG-082",
            f"got {eval_result['assigned_asset_id']}",
        )
        _check(
            "MIS-092 assigned_asset_model_id is 82",
            eval_result["assigned_asset_model_id"] == 82,
            f"got {eval_result['assigned_asset_model_id']}",
        )

        # 7. assigned asset readiness comes from asset_readiness.csv
        csv_row = df[df["asset_id"] == 82].iloc[0]
        expected_score  = float(csv_row["readiness_score"])
        expected_status = str(csv_row["readiness_status"])
        _check(
            "MIS-092 assigned asset readiness_score from CSV",
            eval_result["assigned_asset_readiness_score"] == expected_score,
            f"eval={eval_result['assigned_asset_readiness_score']} csv={expected_score}",
        )
        _check(
            "MIS-092 assigned asset readiness_status from CSV",
            eval_result["assigned_asset_readiness_status"] == expected_status,
            f"eval={eval_result['assigned_asset_readiness_status']} csv={expected_status}",
        )

        # 8. suitable/unsuitable classification matches readiness_status
        expected_suitable = (expected_status == "READY")
        _check(
            "MIS-092 suitable classification correct",
            eval_result["assigned_asset_suitable"] == expected_suitable,
            f"suitable={eval_result['assigned_asset_suitable']} expected={expected_suitable}",
        )

        # 9. alternative recommendation: lowest_risk_asset still returns a valid result
        best = mr.lowest_risk_asset("MIS-092")
        best_id = None if best is None else int(best["asset_id"])
        _check(
            "alternative recommendation returns valid asset",
            best_id is not None and best_id > 0,
            f"recommended_asset={best_id}",
        )

        # 10. existing mission_readiness_summary includes assigned-asset fields
        summary = mr.mission_readiness_summary("MIS-092")
        has_fields = (
            "assigned_asset_id" in summary
            and "assigned_asset_model_id" in summary
            and "assigned_asset_readiness_status" in summary
            and "assigned_asset_suitable" in summary
        )
        _check(
            "mission_readiness_summary has assigned-asset fields",
            has_fields,
            f"keys={list(summary.keys())}",
        )

    except Exception as exc:
        _check("identifier_mapping_MIS-092", False, str(exc))
        traceback.print_exc()


# ===========================================================================
# Runner
# ===========================================================================

def run_all_tests() -> int:
    """Run all tests; return exit code (0=pass, 1=fail)."""
    print("=" * 60)
    print("  Mission Readiness - Integration Test Suite")
    print("=" * 60)

    test_input_files_exist()
    test_input_columns()
    test_output_file_exists()
    test_output_columns()
    test_output_non_empty()
    test_no_null_asset_ids()
    test_numeric_columns()
    test_valid_readiness_statuses()
    test_valid_priority_values()
    test_no_duplicate_asset_cycle()
    test_mission_readiness_functions()
    test_api_endpoints()
    test_identifier_mapping()

    # Summary
    passed = sum(1 for _, s, _ in _results if s == _PASS)
    failed = sum(1 for _, s, _ in _results if s == _FAIL)
    total  = passed + failed

    print()
    print("=" * 60)
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    if failed:
        print()
        print("  FAILED tests:")
        for name, status, detail in _results:
            if status == _FAIL:
                print(f"    [FAIL] {name}" + (f": {detail}" if detail else ""))
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
