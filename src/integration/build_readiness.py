# src/integration/build_readiness.py
"""Build the unified asset-readiness dataset.

Runnable as:
    python -m src.integration.build_readiness

Steps executed
--------------
1.  Validate input CSVs exist and have required columns.
2.  Load the three model outputs (health, failure, RUL).
3.  Normalise asset identifiers (unit → asset_id).
4.  Align model outputs by asset and latest cycle.
5.  Compute health_score / health_status from anomaly_score.
6.  Build unified dataset (one record per asset).
7.  Calculate readiness score, status, reason, recommended_action.
8.  Calculate maintenance_priority_score and maintenance_priority.
9.  Evaluate basic mission-readiness for every mission in missions.csv.
10. Save src/data/outputs/asset_readiness.csv
11. Print a summary: assets, readiness distribution, priority distribution,
    output path.
"""

from __future__ import annotations

import sys
import pathlib
import logging

import pandas as pd

# Ensure project root is on sys.path when run as __main__
_THIS_DIR = pathlib.Path(__file__).resolve().parent
_SRC_DIR  = _THIS_DIR.parent
_ROOT     = _SRC_DIR.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.integration.readiness_engine import (
    load_model_outputs,
    build_unified_dataset,
    ReadinessEngine,
    MissionReadiness,
    OUTPUT_CSV,
    OUTPUT_DIR,
    MISSIONS_CSV,
    VALID_READINESS_STATUSES,
    VALID_PRIORITY_VALUES,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Expected output columns (exactly those required by the specification)
# ---------------------------------------------------------------------------
REQUIRED_OUTPUT_COLUMNS = [
    "asset_id",
    "cycle",
    "health_score",
    "health_status",
    "anomaly_score",
    "failure_probability",
    "failure_risk",
    "predicted_rul",
    "rul_status",
    "readiness_score",
    "readiness_status",
    "primary_reason",
    "recommended_action",
    "maintenance_priority_score",
    "maintenance_priority",
]


def build_and_save() -> pd.DataFrame:
    """Run the full pipeline and save asset_readiness.csv.

    Returns
    -------
    pd.DataFrame  — the full readiness dataset (15 columns, one row per asset).
    """
    log.info("=" * 60)
    log.info("Mission Readiness & Predictive Maintenance Copilot")
    log.info("Build Readiness Pipeline")
    log.info("=" * 60)

    # --- Step 1-2: Load (includes validation) ---------------------------------
    log.info("Step 1-2: Loading model outputs …")
    health_df, failure_df, rul_df = load_model_outputs()
    log.info(
        "  health   : %d rows, %d units",
        len(health_df), health_df["unit"].nunique()
    )
    log.info(
        "  failure  : %d rows, %d units",
        len(failure_df), failure_df["unit"].nunique()
    )
    log.info("  rul      : %d rows", len(rul_df))

    # --- Steps 3-6: Build unified dataset (normalise, align, merge) -----------
    log.info("Steps 3-6: Building unified dataset …")
    unified = build_unified_dataset(health_df, failure_df, rul_df)
    log.info("  Unified records: %d", len(unified))

    # --- Steps 7-8: Readiness + priority calculations -------------------------
    log.info("Steps 7-8: Calculating readiness and maintenance priority …")
    engine = ReadinessEngine()
    result = engine.calculate(unified)

    # Validate output schema
    missing_cols = [c for c in REQUIRED_OUTPUT_COLUMNS if c not in result.columns]
    if missing_cols:
        raise RuntimeError(f"Output is missing required columns: {missing_cols}")

    # Keep only the required columns in the specified order
    result = result[REQUIRED_OUTPUT_COLUMNS].copy()

    # Ensure deterministic sort
    result = result.sort_values("asset_id").reset_index(drop=True)

    # --- Step 9: Mission readiness --------------------------------------------
    mission_result_count = 0
    if MISSIONS_CSV.exists():
        log.info("Step 9: Evaluating mission readiness …")
        missions_df = pd.read_csv(MISSIONS_CSV)
        mr = MissionReadiness(result, missions_df)
        # Smoke-check: summarise first unique mission
        first_mission = missions_df["mission_id"].iloc[0]
        summary = mr.mission_readiness_summary(first_mission)
        mission_result_count = summary["suitable_count"]
        log.info(
            "  Mission %s → %d suitable / %d not-suitable assets",
            first_mission,
            summary["suitable_count"],
            summary["not_suitable_count"],
        )
    else:
        log.warning("missions.csv not found — skipping mission-readiness step.")

    # --- Step 10: Save --------------------------------------------------------
    log.info("Step 10: Saving output …")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_CSV, index=False)
    log.info("  Saved: %s", OUTPUT_CSV)

    # --- Step 11: Summary -----------------------------------------------------
    _print_summary(result)

    return result


def _print_summary(df: pd.DataFrame) -> None:
    """Print human-readable pipeline summary to stdout."""
    n_assets = len(df)
    readiness_dist = df["readiness_status"].value_counts().to_dict()
    priority_dist  = df["maintenance_priority"].value_counts().to_dict()

    print()
    print("=" * 60)
    print("  PIPELINE SUMMARY")
    print("=" * 60)
    print(f"  Output : {OUTPUT_CSV}")
    print(f"  Assets : {n_assets}")
    print()
    print("  Readiness distribution:")
    for status in ["READY", "ADVISORY", "NOT_READY"]:
        cnt = readiness_dist.get(status, 0)
        pct = 100.0 * cnt / n_assets if n_assets else 0
        print(f"    {status:<12} {cnt:>4}  ({pct:.1f}%)")
    print()
    print("  Maintenance priority distribution:")
    for prio in ["IMMEDIATE", "HIGH", "MEDIUM", "LOW"]:
        cnt = priority_dist.get(prio, 0)
        pct = 100.0 * cnt / n_assets if n_assets else 0
        print(f"    {prio:<12} {cnt:>4}  ({pct:.1f}%)")
    print()
    print("  Output columns:")
    print("    " + ", ".join(df.columns.tolist()))
    print("=" * 60)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    build_and_save()
