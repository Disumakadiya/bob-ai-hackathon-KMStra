"""Canonical schema for the NASA C-MAPSS FD001 run-to-failure dataset.

Single source of truth for column names, dtypes, expected shapes and the
cleaning/feature-engineering policy used across the data pipeline.

Source format: whitespace-separated text, no header, 26 columns per row:
    unit, cycle, op1, op2, op3, s1..s21
The readme's ``26`` total columns therefore include the two ID columns and
the three operational settings; there are only 21 sensor measurements.
"""

from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Raw files and column layout
# ---------------------------------------------------------------------------
RAW_FILENAMES: Dict[str, str] = {
    "train": "train_FD001.txt",
    "test": "test_FD001.txt",
    "rul": "RUL_FD001.txt",
    "readme": "readme.txt",
}

UNIT: str = "unit"
CYCLE: str = "cycle"
RUL_NAME: str = "rul"
ID_COLUMNS: List[str] = [UNIT, CYCLE]

OPERATIONAL_SETTINGS: List[str] = ["op1", "op2", "op3"]
SENSOR_COLUMNS: List[str] = [f"s{i}" for i in range(1, 22)]  # s1..s21

RAW_COLUMNS: List[str] = ID_COLUMNS + OPERATIONAL_SETTINGS + SENSOR_COLUMNS
N_RAW_COLUMNS: int = len(RAW_COLUMNS)  # 26

DTYPE_MAP: Dict[str, object] = {
    UNIT: "int32",
    CYCLE: "int32",
    RUL_NAME: "int32",
}

FLOAT_COLUMNS: List[str] = OPERATIONAL_SETTINGS + SENSOR_COLUMNS

# ---------------------------------------------------------------------------
# Cleaning policy
# ---------------------------------------------------------------------------
# Exactly-constant columns across both splits -> dropped.
CONSTANT_COLUMNS: List[str] = ["op3", "s1", "s5", "s10", "s16", "s18", "s19"]
# Near-constant but kept by default (single operating condition; FD001).
NEAR_CONSTANT_COLUMNS: List[str] = ["op1", "op2", "s6", "s17"]

# Columns that survive cleaning and are used as the base for feature creation.
KEPT_FEATURE_COLUMNS: List[str] = [
    c for c in (OPERATIONAL_SETTINGS + SENSOR_COLUMNS) if c not in CONSTANT_COLUMNS
]

# Documented as informative in the PHM08 literature (kept for reference).
INFORMATIVE_SENSORS: List[str] = [
    "s2", "s3", "s4", "s7", "s8", "s9",
    "s11", "s12", "s13", "s14", "s15", "s17", "s20", "s21",
]

# ---------------------------------------------------------------------------
# Expected dataset shape (verified against the raw files)
# ---------------------------------------------------------------------------
EXPECTED_N_ROWS: Dict[str, int] = {"train": 20631, "test": 13096, "rul": 100}
N_ENGINES: int = 100
ENGINE_ID_MIN: int = 1
ENGINE_ID_MAX: int = 100
TRAIN_CYCLE_RANGE: Tuple[int, int] = (128, 362)
TEST_CYCLE_RANGE: Tuple[int, int] = (31, 303)

# ---------------------------------------------------------------------------
# Feature-engineering policy
# ---------------------------------------------------------------------------
ROLL_WINDOW: int = 5
ROLL_STATS: List[str] = ["mean", "std"]
ROLL_EXTREMES: List[str] = ["min", "max"]
DELTA_LAG: int = 1  # cycle-to-cycle difference

_NON_FEATURE_COLUMNS: Tuple[str, ...] = (UNIT, CYCLE, RUL_NAME)


def roll_column_name(column: str, stat: str, window: int) -> str:
    return f"{column}_roll_{stat}{window}"


def delta_column_name(column: str, lag: int) -> str:
    return f"{column}_delta{lag}"


def feature_columns_for(
    base_columns: List[str],
    window: int = ROLL_WINDOW,
    lag: int = DELTA_LAG,
) -> List[str]:
    """Names of the derived features produced for a set of base columns."""
    derived: List[str] = []
    for stat in ROLL_STATS + ROLL_EXTREMES:
        derived.extend(roll_column_name(c, stat, window) for c in base_columns)
    derived.extend(delta_column_name(c, lag) for c in base_columns)
    return derived


# ---------------------------------------------------------------------------
# Processed outputs
# ---------------------------------------------------------------------------
PROCESSED_TRAIN_FILE: str = "FD001_train_preprocessed.csv"
PROCESSED_TEST_FILE: str = "FD001_test_preprocessed.csv"

