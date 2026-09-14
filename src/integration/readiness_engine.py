# src/integration/readiness_engine.py
"""Mission Readiness & Predictive Maintenance Copilot — Integration Layer.

This module:
1. Loads the three frozen model outputs (health anomaly, failure, RUL).
2. Aligns them by asset and latest cycle to produce one record per asset.
3. Derives health_score / health_status using the health model's own formula.
4. Calculates readiness_score, readiness_status, primary_reason, and
   recommended_action (Step 3).
5. Calculates maintenance_priority_score and maintenance_priority (Step 4).
6. Exposes mission-readiness queries (Step 5).

IMPORTANT — Model outputs are NEVER modified; thresholds are imported directly
from the models' own config modules rather than duplicated here.

Threshold sources
-----------------
Health:
  - ANOMALY_SCORE_MIN / ANOMALY_SCORE_MAX  →  health_config.py (0.5/99.5 pctile)
  - HEALTH_NORMAL_THRESHOLD = 70           →  health_config.py
  - HEALTH_WARNING_THRESHOLD = 40          →  health_config.py

Failure:
  - LOW_MEDIUM_BOUNDARY  = 0.40            →  failure/config.py
  - MEDIUM_HIGH_BOUNDARY = 0.70            →  failure/config.py
  - failure_status: LOW / MEDIUM / HIGH    →  failure_scores.csv

RUL:
  - THRESHOLD_HEALTHY   = 100              →  rul/config.py
  - THRESHOLD_CRITICAL  = 30              →  rul/config.py
  - rul_status: HEALTHY / ADVISORY / CRITICAL  →  rul_predictions.csv

Readiness logic
---------------
A combined readiness score in [0, 100] is computed as a weighted average of
the normalised health, failure-safety, and RUL signals:

  health_component    = health_score / 100          (higher = better)
  failure_component   = 1 - failure_probability     (higher = better)
  rul_component       = min(predicted_rul, RUL_CAP) / RUL_CAP
                        where RUL_CAP = THRESHOLD_HEALTHY (100 cycles)

  readiness_score = 100 × (
      W_HEALTH   × health_component
    + W_FAILURE  × failure_component
    + W_RUL      × rul_component
  )

Weights rationale (W_HEALTH=0.30, W_FAILURE=0.40, W_RUL=0.30, sum=1.00):
  - Failure probability is most immediately actionable → highest weight.
  - Health and RUL are complementary leading indicators → equal lower weight.

Readiness status thresholds:
  - READY      : readiness_score >= 70  (mirrors health NORMAL boundary)
  - ADVISORY   : readiness_score >= 40  (mirrors health WARNING boundary)
  - NOT_READY  : readiness_score <  40

These thresholds reuse the health model's own green/amber/red boundaries
(70 / 40) so the readiness scale is consistent across signals.

Maintenance priority
--------------------
priority_score = 100 - readiness_score  (lower readiness → higher urgency)

Priority categories:
  IMMEDIATE  : priority_score >= 70   (i.e. readiness_score <  30)
  HIGH       : priority_score >= 50   (i.e. readiness_score <  50)
  MEDIUM     : priority_score >= 30   (i.e. readiness_score <  70)
  LOW        : priority_score <  30   (i.e. readiness_score >= 70)

Mission readiness
-----------------
An asset is suitable for a mission if its readiness_status is READY.
No additional synthetic mission requirements are fabricated.  The mission
dataset fields used are: asset_id, mission_id, mission_type, mission_criticality.
"""

from __future__ import annotations

import pathlib
import re
from typing import Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Import thresholds directly from the frozen model configs
# ---------------------------------------------------------------------------
from src.models.health.health_config import (
    ANOMALY_SCORE_MAX,
    ANOMALY_SCORE_MIN,
    HEALTH_NORMAL_THRESHOLD,   # 70.0
    HEALTH_SCORE_MAX,          # 100.0
    HEALTH_SCORE_MIN,          # 0.0
    HEALTH_STATUS_CRITICAL,    # "CRITICAL"
    HEALTH_STATUS_NORMAL,      # "NORMAL"
    HEALTH_STATUS_WARNING,     # "WARNING"
    HEALTH_WARNING_THRESHOLD,  # 40.0
)
from src.models.health.health_scoring import normalize_anomaly, assign_status
from src.models.failure.config import (
    FAILURE_STATUS_HIGH,    # "HIGH"
    FAILURE_STATUS_LOW,     # "LOW"
    FAILURE_STATUS_MEDIUM,  # "MEDIUM"
    LOW_MEDIUM_BOUNDARY,    # 0.40
    MEDIUM_HIGH_BOUNDARY,   # 0.70
)
from src.models.rul.config import (
    THRESHOLD_CRITICAL as RUL_THRESHOLD_CRITICAL,  # 30
    THRESHOLD_HEALTHY  as RUL_THRESHOLD_HEALTHY,   # 100
)

# ---------------------------------------------------------------------------
# Paths (relative to the project root)
# ---------------------------------------------------------------------------
_THIS_DIR     = pathlib.Path(__file__).resolve().parent
_SRC_DIR      = _THIS_DIR.parent
_PROJECT_ROOT = _SRC_DIR.parent

HEALTH_CSV_PATH  = _SRC_DIR / "models" / "health"   / "anomaly_scores.csv"
FAILURE_CSV_PATH = _SRC_DIR / "models" / "failure"  / "failure_scores.csv"
RUL_CSV_PATH     = _SRC_DIR / "models" / "rul"      / "rul_predictions.csv"
MISSIONS_CSV     = _SRC_DIR / "data"   / "ingestion" / "synthetic" / "missions.csv"
OUTPUT_DIR       = _SRC_DIR / "data"   / "outputs"
OUTPUT_CSV       = OUTPUT_DIR / "asset_readiness.csv"

# ---------------------------------------------------------------------------
# Readiness engine weights (sum = 1.0)
# ---------------------------------------------------------------------------
W_HEALTH  = 0.30
W_FAILURE = 0.40
W_RUL     = 0.30

# RUL normalisation cap — reuses RUL_THRESHOLD_HEALTHY (100 cycles)
# Rationale: above 100 cycles predicted RUL is considered full health;
# contributions above this cap do not improve readiness further.
RUL_NORMALISATION_CAP: float = float(RUL_THRESHOLD_HEALTHY)  # 100.0

# ---------------------------------------------------------------------------
# Readiness thresholds (reuse health model's green/amber/red boundaries)
# ---------------------------------------------------------------------------
READINESS_READY_THRESHOLD     = HEALTH_NORMAL_THRESHOLD   # 70.0
READINESS_ADVISORY_THRESHOLD  = HEALTH_WARNING_THRESHOLD  # 40.0

# Maintenance priority thresholds (inverted readiness)
PRIORITY_IMMEDIATE_THRESHOLD = 70.0   # readiness < 30
PRIORITY_HIGH_THRESHOLD      = 50.0   # readiness < 50
PRIORITY_MEDIUM_THRESHOLD    = 30.0   # readiness < 70

# Status label constants
READINESS_READY     = "READY"
READINESS_ADVISORY  = "ADVISORY"
READINESS_NOT_READY = "NOT_READY"

PRIORITY_IMMEDIATE = "IMMEDIATE"
PRIORITY_HIGH      = "HIGH"
PRIORITY_MEDIUM    = "MEDIUM"
PRIORITY_LOW       = "LOW"

# All valid status sets (used for validation)
VALID_READINESS_STATUSES = frozenset({READINESS_READY, READINESS_ADVISORY, READINESS_NOT_READY})
VALID_PRIORITY_VALUES    = frozenset({PRIORITY_IMMEDIATE, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW})


# ===========================================================================
# Step 2 — Load and align model outputs
# ===========================================================================

def load_model_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the three frozen model output CSVs.

    Returns
    -------
    (health_df, failure_df, rul_df) — raw DataFrames exactly as produced by
    the models.  No transformations are applied here.

    Raises
    ------
    FileNotFoundError  if any CSV is missing.
    ValueError         if required columns are absent.
    """
    _validate_input_file(HEALTH_CSV_PATH,  ["unit", "cycle", "anomaly_score"])
    _validate_input_file(FAILURE_CSV_PATH, ["unit", "cycle", "failure_probability", "failure_status"])
    _validate_input_file(RUL_CSV_PATH,     ["asset_id", "cycle", "predicted_rul", "rul_status"])

    health_df  = pd.read_csv(HEALTH_CSV_PATH)
    failure_df = pd.read_csv(FAILURE_CSV_PATH)
    rul_df     = pd.read_csv(RUL_CSV_PATH)

    return health_df, failure_df, rul_df


def _validate_input_file(path: pathlib.Path, required_cols: list[str]) -> None:
    """Raise if file is missing or required columns are absent."""
    if not path.exists():
        raise FileNotFoundError(
            f"Required model output not found: {path}\n"
            "Ensure all three ML models have been run before calling build_readiness."
        )
    df = pd.read_csv(path, nrows=1)
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"File {path.name} is missing required columns: {missing}\n"
            f"Found: {list(df.columns)}"
        )


def build_unified_dataset(
    health_df: pd.DataFrame,
    failure_df: pd.DataFrame,
    rul_df: pd.DataFrame,
) -> pd.DataFrame:
    """Align three model outputs into one record per asset.

    Alignment strategy
    ------------------
    * The RUL output has exactly one record per asset (the test-set prediction
      at the final observed cycle).  Its (asset_id, cycle) pair is the anchor.
    * The failure output covers only test-set cycles; its last cycle per unit
      matches the RUL cycle exactly (confirmed by inspection).
    * The health output covers all historical cycles (train + test).  For each
      asset we retrieve the health row at the exact cycle matching the failure/
      RUL record.  If that cycle is absent in the health data (15 of 100 assets
      in the current data), we use the latest available health row.  This is
      documented in the output ``health_cycle_note`` auxiliary column (dropped
      before saving).

    Parameters
    ----------
    health_df, failure_df, rul_df : pd.DataFrame
        Raw outputs from :func:`load_model_outputs`.

    Returns
    -------
    pd.DataFrame
        One row per asset with columns:
        asset_id, cycle, health_score, health_status, anomaly_score,
        failure_probability, failure_risk, predicted_rul, rul_status
    """
    # --- Normalise identifier: 'unit' → 'asset_id' --------------------------
    health_df  = health_df.copy()
    failure_df = failure_df.copy()
    rul_df     = rul_df.copy()

    if "unit" in health_df.columns:
        health_df  = health_df.rename(columns={"unit": "asset_id"})
    if "unit" in failure_df.columns:
        failure_df = failure_df.rename(columns={"unit": "asset_id"})

    # Ensure asset_id is integer in all three sources (RUL is already int)
    health_df["asset_id"]  = health_df["asset_id"].astype(int)
    failure_df["asset_id"] = failure_df["asset_id"].astype(int)
    rul_df["asset_id"]     = rul_df["asset_id"].astype(int)

    # --- Compute health_score / health_status from anomaly_score --------------
    # Reuse the health model's own normalise + status functions (not duplicated)
    health_df["health_score"]  = normalize_anomaly(health_df["anomaly_score"]).round(2)
    health_df["health_status"] = assign_status(health_df["health_score"])

    # --- Get last failure row per asset (cycle = test-set final cycle) --------
    failure_last = (
        failure_df
        .sort_values(["asset_id", "cycle"])
        .groupby("asset_id", sort=False)
        .last()
        .reset_index()
    )
    # rename failure_status → failure_risk (column rename for unified schema)
    failure_last = failure_last.rename(columns={"failure_status": "failure_risk"})

    # --- Align health to the failure/RUL anchor cycle -------------------------
    health_aligned_rows = []
    exact_matches = 0
    for _, frow in failure_last.iterrows():
        asset  = int(frow["asset_id"])
        cycle  = int(frow["cycle"])
        exact  = health_df[(health_df["asset_id"] == asset) & (health_df["cycle"] == cycle)]
        if len(exact) > 0:
            health_aligned_rows.append(exact.iloc[0])
            exact_matches += 1
        else:
            # Fall back to the latest available health reading
            sub = health_df[health_df["asset_id"] == asset]
            health_aligned_rows.append(sub.loc[sub["cycle"].idxmax()])

    health_aligned = pd.DataFrame(health_aligned_rows).reset_index(drop=True)
    health_aligned["asset_id"] = health_aligned["asset_id"].astype(int)

    # --- Merge health + failure -----------------------------------------------
    merged = failure_last.merge(
        health_aligned[["asset_id", "anomaly_score", "health_score", "health_status"]],
        on="asset_id",
        how="inner",
    )

    # --- Merge with RUL -------------------------------------------------------
    merged = merged.merge(
        rul_df[["asset_id", "cycle", "predicted_rul", "rul_status"]],
        on=["asset_id", "cycle"],
        how="inner",
        suffixes=("", "_rul"),
    )

    # Drop duplicate cycle columns if any (cycle is the anchor from failure/rul)
    # Only drop exact suffix-collision columns like "cycle_rul", not "predicted_rul"
    dup_cols = [c for c in merged.columns if c.endswith("_rul") and c not in (
        "predicted_rul", "rul_status"
    )]
    merged.drop(columns=dup_cols, inplace=True, errors="ignore")

    # Drop rows with null asset_id (should not occur, but defensive)
    merged = merged.dropna(subset=["asset_id"])
    merged["asset_id"] = merged["asset_id"].astype(int)

    # --- Final column ordering ------------------------------------------------
    base_cols = [
        "asset_id", "cycle",
        "health_score", "health_status", "anomaly_score",
        "failure_probability", "failure_risk",
        "predicted_rul", "rul_status",
    ]
    extra = [c for c in merged.columns if c not in base_cols]
    merged = merged[base_cols + extra].sort_values("asset_id").reset_index(drop=True)

    return merged


# ===========================================================================
# Steps 3 & 4 — Readiness Engine + Maintenance Priority
# ===========================================================================

class ReadinessEngine:
    """Calculates readiness and maintenance priority for a unified asset dataset.

    Usage
    -----
        engine = ReadinessEngine()
        result = engine.calculate(unified_df)

    The returned DataFrame extends *unified_df* with:
        readiness_score, readiness_status, primary_reason, recommended_action,
        maintenance_priority_score, maintenance_priority
    """

    # ------------------------------------------------------------------
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply readiness + priority calculations to *df* in-place copy.

        Parameters
        ----------
        df : pd.DataFrame
            Output of :func:`build_unified_dataset`.

        Returns
        -------
        pd.DataFrame with all original columns plus the six readiness/
        priority columns appended.
        """
        result = df.copy()

        result["readiness_score"]  = result.apply(self._readiness_score, axis=1).round(2)
        result["readiness_status"] = result["readiness_score"].apply(self._readiness_status)
        result["primary_reason"]   = result.apply(self._primary_reason, axis=1)
        result["recommended_action"] = result["readiness_status"].apply(self._recommended_action)

        # Maintenance priority (Step 4)
        result["maintenance_priority_score"] = (
            (100.0 - result["readiness_score"]).clip(lower=0.0, upper=100.0).round(2)
        )
        result["maintenance_priority"] = result["maintenance_priority_score"].apply(
            self._maintenance_priority
        )

        return result

    # ------------------------------------------------------------------
    @staticmethod
    def _readiness_score(row: pd.Series) -> float:
        """Compute continuous readiness score in [0, 100].

        Formula (documented in module docstring):
            readiness = 100 × (
                W_HEALTH  × (health_score / 100)
              + W_FAILURE × (1 - failure_probability)
              + W_RUL     × min(predicted_rul, RUL_CAP) / RUL_CAP
            )
        """
        health_component  = float(row["health_score"]) / HEALTH_SCORE_MAX
        failure_component = 1.0 - float(row["failure_probability"])
        rul_val           = min(float(row["predicted_rul"]), RUL_NORMALISATION_CAP)
        rul_component     = rul_val / RUL_NORMALISATION_CAP

        score = 100.0 * (
            W_HEALTH  * health_component
          + W_FAILURE * failure_component
          + W_RUL     * rul_component
        )
        return float(np.clip(score, HEALTH_SCORE_MIN, HEALTH_SCORE_MAX))

    # ------------------------------------------------------------------
    @staticmethod
    def _readiness_status(score: float) -> str:
        """Map continuous readiness score to READY / ADVISORY / NOT_READY."""
        if score >= READINESS_READY_THRESHOLD:
            return READINESS_READY
        if score >= READINESS_ADVISORY_THRESHOLD:
            return READINESS_ADVISORY
        return READINESS_NOT_READY

    # ------------------------------------------------------------------
    @staticmethod
    def _primary_reason(row: pd.Series) -> str:
        """Identify the dominant reason an asset is at risk.

        Evaluation priority (worst signal first):
        1. CRITICAL health status
        2. HIGH failure risk
        3. CRITICAL RUL status
        4. WARNING health status
        5. MEDIUM failure risk
        6. ADVISORY RUL status
        7. Asset is healthy — no concerns
        """
        h_status = str(row.get("health_status", "")).upper()
        f_risk   = str(row.get("failure_risk", "")).upper()
        r_status = str(row.get("rul_status", "")).upper()

        # Critical / most severe signals first
        if h_status == HEALTH_STATUS_CRITICAL:
            return "Critical health anomaly detected"
        if f_risk == FAILURE_STATUS_HIGH:
            return "High failure probability"
        if r_status == "CRITICAL":
            return "RUL in critical zone"
        if h_status == HEALTH_STATUS_WARNING:
            return "Health in warning zone"
        if f_risk == FAILURE_STATUS_MEDIUM:
            return "Moderate failure risk"
        if r_status == "ADVISORY":
            return "RUL in advisory range"
        return "All systems nominal"

    # ------------------------------------------------------------------
    @staticmethod
    def _recommended_action(readiness_status: str) -> str:
        """Return a standard recommended action for a readiness status."""
        actions = {
            READINESS_READY:     "Routine monitoring",
            READINESS_ADVISORY:  "Schedule inspection and continue monitoring",
            READINESS_NOT_READY: "Immediate maintenance inspection required",
        }
        return actions.get(readiness_status, "Review asset condition")

    # ------------------------------------------------------------------
    @staticmethod
    def _maintenance_priority(priority_score: float) -> str:
        """Map priority_score (0-100) to maintenance priority category."""
        if priority_score >= PRIORITY_IMMEDIATE_THRESHOLD:
            return PRIORITY_IMMEDIATE
        if priority_score >= PRIORITY_HIGH_THRESHOLD:
            return PRIORITY_HIGH
        if priority_score >= PRIORITY_MEDIUM_THRESHOLD:
            return PRIORITY_MEDIUM
        return PRIORITY_LOW


# ===========================================================================
# Identifier normalisation helper
# ===========================================================================

# Pattern that matches "ENG-" followed by one or more digits (case-insensitive).
_ENG_ID_RE = re.compile(r"^ENG-(\d+)$", re.IGNORECASE)


def normalize_mission_asset_id(
    operational_id: str,
    valid_model_ids: Optional[set[int]] = None,
) -> int:
    """Convert an operational mission asset ID to the numeric model asset ID.

    The mapping is deterministic and explicit:
        ENG-001  →  1
        ENG-082  →  82
        ENG-100  →  100

    Parameters
    ----------
    operational_id : str
        The operational identifier as it appears in missions.csv, e.g. "ENG-082".
    valid_model_ids : set[int] | None
        When provided, the resulting integer is validated against this set.
        Pass the set of asset_id values present in asset_readiness.csv to
        catch IDs that are syntactically well-formed but not in the dataset.

    Returns
    -------
    int
        Numeric model asset ID.

    Raises
    ------
    ValueError
        If *operational_id* does not match the expected "ENG-NNN" format.
    ValueError
        If the extracted numeric ID is not in *valid_model_ids* (when provided).
    """
    m = _ENG_ID_RE.match(str(operational_id).strip())
    if m is None:
        raise ValueError(
            f"Malformed operational asset ID: {operational_id!r}. "
            "Expected format: ENG-NNN (e.g. 'ENG-082')."
        )
    numeric_id = int(m.group(1))
    if valid_model_ids is not None and numeric_id not in valid_model_ids:
        raise ValueError(
            f"Operational asset ID {operational_id!r} maps to model ID {numeric_id}, "
            f"which is not present in the readiness dataset. "
            f"Valid range: {min(valid_model_ids)}–{max(valid_model_ids)}."
        )
    return numeric_id


# ===========================================================================
# Step 5 — Mission Readiness
# ===========================================================================

class MissionReadiness:
    """Evaluate asset suitability for missions using readiness data.

    Limitation note
    ---------------
    The missions.csv dataset provides mission_type and mission_criticality but
    no quantitative mission requirements (e.g. minimum RUL needed per mission
    type).  Therefore the suitability decision is based solely on the asset's
    readiness_status (READY = suitable).  This is the safe/conservative
    approach documented by the prompt.  If mission requirements are added to
    the dataset in the future, this class can be extended without changing the
    rest of the pipeline.

    Parameters
    ----------
    readiness_df : pd.DataFrame
        Full output of :meth:`ReadinessEngine.calculate`, keyed on integer
        asset_id (1-100).
    missions_df : pd.DataFrame
        Raw missions.csv DataFrame.  asset_id here is "ENG-XXX" format;
        it is normalised to integer via :func:`normalize_mission_asset_id`.
    """

    def __init__(self, readiness_df: pd.DataFrame, missions_df: pd.DataFrame) -> None:
        self._readiness = readiness_df.copy()
        self._readiness["asset_id"] = self._readiness["asset_id"].astype(int)
        self._valid_model_ids: set[int] = set(self._readiness["asset_id"].unique())

        missions = missions_df.copy()
        # Normalise "ENG-XXX" → integer using the explicit, validated helper.
        # Rows with malformed IDs get NaN so they can be identified; they will
        # not appear in valid mission lookups.
        def _safe_normalize(x: str) -> Optional[int]:
            try:
                return normalize_mission_asset_id(x, self._valid_model_ids)
            except ValueError:
                return None

        missions["asset_id_int"] = missions["asset_id"].apply(_safe_normalize)
        self._missions = missions

    # ------------------------------------------------------------------
    def can_assign(self, asset_id: int, mission_id: str) -> dict:
        """Check if a specific asset can be assigned to a specific mission.

        Parameters
        ----------
        asset_id  : int   (1-100, corresponding to engine unit number)
        mission_id : str  (e.g. "MIS-001")

        Returns
        -------
        dict with keys:
            asset_id, mission_id, suitable (bool),
            readiness_status, readiness_score, reason
        """
        asset_row     = self._get_asset(asset_id)
        mission_rows  = self._missions[self._missions["mission_id"] == mission_id]

        if asset_row is None:
            return {
                "asset_id": asset_id,
                "mission_id": mission_id,
                "suitable": False,
                "readiness_status": "UNKNOWN",
                "readiness_score": None,
                "reason": f"Asset {asset_id} not found in readiness data",
            }

        if mission_rows.empty:
            return {
                "asset_id": asset_id,
                "mission_id": mission_id,
                "suitable": False,
                "readiness_status": str(asset_row["readiness_status"]),
                "readiness_score": float(asset_row["readiness_score"]),
                "reason": f"Mission {mission_id} not found",
            }

        suitable = asset_row["readiness_status"] == READINESS_READY
        reason = (
            "Asset is mission-ready"
            if suitable
            else f"Asset not ready: {asset_row['primary_reason']}"
        )
        return {
            "asset_id": asset_id,
            "mission_id": mission_id,
            "suitable": bool(suitable),
            "readiness_status": str(asset_row["readiness_status"]),
            "readiness_score": float(asset_row["readiness_score"]),
            "reason": reason,
        }

    # ------------------------------------------------------------------
    def suitable_assets(self, mission_id: str) -> pd.DataFrame:
        """Return all assets that are suitable (READY) for a given mission.

        Parameters
        ----------
        mission_id : str

        Returns
        -------
        pd.DataFrame sorted by maintenance_priority_score ascending
        (lowest risk first).
        """
        ready = self._readiness[self._readiness["readiness_status"] == READINESS_READY].copy()
        ready = ready.sort_values("maintenance_priority_score", ascending=True).reset_index(drop=True)
        return ready

    # ------------------------------------------------------------------
    def unsuitable_assets(self, mission_id: str) -> pd.DataFrame:
        """Return all assets that are NOT suitable for a given mission."""
        not_ready = self._readiness[
            self._readiness["readiness_status"] != READINESS_READY
        ].copy()
        not_ready = not_ready.sort_values(
            "maintenance_priority_score", ascending=False
        ).reset_index(drop=True)
        return not_ready

    # ------------------------------------------------------------------
    def lowest_risk_asset(self, mission_id: str) -> Optional[pd.Series]:
        """Return the suitable asset with the lowest maintenance risk."""
        candidates = self.suitable_assets(mission_id)
        if candidates.empty:
            return None
        return candidates.iloc[0]

    # ------------------------------------------------------------------
    def assigned_asset_evaluation(self, mission_id: str) -> dict:
        """Evaluate the asset that is specifically assigned to *mission_id*.

        Resolves the mission's operational asset ID (ENG-XXX) to a numeric
        model ID, looks up its readiness, and determines suitability.

        Parameters
        ----------
        mission_id : str

        Returns
        -------
        dict with keys:
            assigned_asset_id         (str | None)  — original ENG-XXX value
            assigned_asset_model_id   (int | None)  — numeric model asset ID
            assigned_asset_readiness_status (str)
            assigned_asset_readiness_score  (float | None)
            assigned_asset_suitable   (bool)
            assigned_asset_reason     (str)

        Notes
        -----
        If the mission is not found or has no assigned asset, all fields
        are None / False with an explanatory reason.
        """
        mission_rows = self._missions[self._missions["mission_id"] == mission_id]
        if mission_rows.empty:
            return {
                "assigned_asset_id":               None,
                "assigned_asset_model_id":         None,
                "assigned_asset_readiness_status": "UNKNOWN",
                "assigned_asset_readiness_score":  None,
                "assigned_asset_suitable":         False,
                "assigned_asset_reason":           f"Mission {mission_id} not found",
            }

        first_row       = mission_rows.iloc[0]
        operational_id  = str(first_row["asset_id"])          # "ENG-082"
        model_id_raw    = first_row.get("asset_id_int", None) # pre-normalised integer

        if model_id_raw is None or pd.isna(model_id_raw):
            return {
                "assigned_asset_id":               operational_id,
                "assigned_asset_model_id":         None,
                "assigned_asset_readiness_status": "UNKNOWN",
                "assigned_asset_readiness_score":  None,
                "assigned_asset_suitable":         False,
                "assigned_asset_reason":           (
                    f"Operational asset ID {operational_id!r} could not be "
                    "mapped to a valid model asset ID."
                ),
            }

        model_id   = int(model_id_raw)
        asset_row  = self._get_asset(model_id)

        if asset_row is None:
            return {
                "assigned_asset_id":               operational_id,
                "assigned_asset_model_id":         model_id,
                "assigned_asset_readiness_status": "UNKNOWN",
                "assigned_asset_readiness_score":  None,
                "assigned_asset_suitable":         False,
                "assigned_asset_reason":           (
                    f"Model asset ID {model_id} not found in readiness dataset."
                ),
            }

        suitable = asset_row["readiness_status"] == READINESS_READY
        return {
            "assigned_asset_id":               operational_id,
            "assigned_asset_model_id":         model_id,
            "assigned_asset_readiness_status": str(asset_row["readiness_status"]),
            "assigned_asset_readiness_score":  float(asset_row["readiness_score"]),
            "assigned_asset_suitable":         bool(suitable),
            "assigned_asset_reason": (
                "Assigned asset is mission-ready"
                if suitable
                else f"Assigned asset not ready: {asset_row['primary_reason']}"
            ),
        }

    # ------------------------------------------------------------------
    def mission_readiness_summary(self, mission_id: str) -> dict:
        """Return a summary dict for a mission.

        Parameters
        ----------
        mission_id : str

        Returns
        -------
        dict with keys:
            mission_id, mission_info (dict or None),
            assigned_asset_id, assigned_asset_model_id,
            assigned_asset_readiness_status, assigned_asset_readiness_score,
            assigned_asset_suitable, assigned_asset_reason,
            total_assets, suitable_count, not_suitable_count,
            recommended_asset (int or None),
            recommended_asset_readiness_score (float or None)

        The recommended_asset is the lowest-maintenance-risk READY asset.
        When the assigned asset is already suitable it is still listed as
        recommended_asset (it may be the same ID).
        """
        mission_rows = self._missions[self._missions["mission_id"] == mission_id]
        mission_info = (
            mission_rows.iloc[0][
                [c for c in ["mission_id", "mission_type", "mission_criticality",
                              "mission_date", "asset_id"] if c in mission_rows.columns]
            ].to_dict()
            if not mission_rows.empty
            else None
        )

        assigned     = self.assigned_asset_evaluation(mission_id)
        suitable     = self.suitable_assets(mission_id)
        unsuitable   = self.unsuitable_assets(mission_id)
        best         = self.lowest_risk_asset(mission_id)

        return {
            "mission_id":   mission_id,
            "mission_info": mission_info,
            # Assigned-asset fields (explicit identifier mapping)
            **assigned,
            # Fleet summary
            "total_assets":        len(self._readiness),
            "suitable_count":      len(suitable),
            "not_suitable_count":  len(unsuitable),
            # Best available alternative (lowest maintenance risk among READY assets)
            "recommended_asset":   int(best["asset_id"]) if best is not None else None,
            "recommended_asset_readiness_score": (
                float(best["readiness_score"]) if best is not None else None
            ),
        }

    # ------------------------------------------------------------------
    def _get_asset(self, asset_id: int) -> Optional[pd.Series]:
        """Return the readiness row for *asset_id*, or None if missing."""
        rows = self._readiness[self._readiness["asset_id"] == asset_id]
        return rows.iloc[0] if not rows.empty else None
