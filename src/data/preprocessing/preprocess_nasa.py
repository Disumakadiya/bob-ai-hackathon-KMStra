"""Cleaning, target building and pipeline orchestration for NASA C-MAPSS FD001.

Pipeline (run via ``python -m src.data.preprocessing.preprocess_nasa``):

1. Load the three raw text files.
2. Validate them against the canonical schema.
3. Clean both splits: drop exactly-constant columns, sort by (unit, cycle).
4. Build the training RUL target per engine as ``max(cycle) - cycle``
   (raw, uncapped; run-to-failure so the last cycle is RUL=0).
5. Attach the true ``RUL_FD001`` values to the test split by engine-ID order
   for later evaluation only (never used to train).
6. Add per-engine backward-looking features.
7. Validate the processed frames, then save CSVs.

Leakage guard: every derived quantity is computed from the training data
(per engine, from past/current cycles) or from the ground-truth RUL file;
nothing is fitted on the test split.
"""

from pathlib import Path
from typing import Any, Dict

import pandas as pd

from src.data.ingestion.load_nasa import load_all
from src.data.preprocessing.feature_engineering import add_features
from src.data.preprocessing.validation import (
    raise_on_issues,
    validation_report,
    validate_duplicates,
    validate_infinite,
    validate_missing,
    validate_units,
    validate_alignment,
    validate_target,
)
from src.data.schemas.nasa_schema import (
    CONSTANT_COLUMNS,
    CYCLE,
    ID_COLUMNS,
    PROCESSED_TEST_FILE,
    PROCESSED_TRAIN_FILE,
    RUL_NAME,
    UNIT,
)

_OUT_DIR: Path = Path(__file__).resolve().parent


def clean(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop exactly-constant columns and enforce a deterministic row order."""
    df = frame.copy()
    drop_cols = [c for c in CONSTANT_COLUMNS if c in df.columns]
    df = df.drop(columns=drop_cols)
    df = df.sort_values(ID_COLUMNS).reset_index(drop=True)
    return df


def build_train_target(frame: pd.DataFrame) -> pd.DataFrame:
    """Ground-truth training RUL: remaining cycles to failure per engine.

    ``RUL = max(cycle) - cycle`` (raw and uncapped). The final cycle of each
    run-to-failure trajectory therefore has RUL 0.
    """
    df = frame.copy()
    max_cycle = df.groupby(UNIT)[CYCLE].transform("max")
    df[RUL_NAME] = (max_cycle - df[CYCLE]).astype("int32")
    return df


def attach_test_target(frame: pd.DataFrame, rul: pd.DataFrame) -> pd.DataFrame:
    """Attach true test RUL in engine-ID order (row ``i`` -> engine ``i``)."""
    from src.data.schemas.nasa_schema import N_ENGINES

    if len(rul) != N_ENGINES:
        raise ValueError(f"RUL file must have one row per engine ({N_ENGINES}), got {len(rul)}")
    values = rul[RUL_NAME].to_numpy(dtype="int32")
    df = frame.copy()
    index = df[UNIT].to_numpy(dtype="int32") - 1
    df[RUL_NAME] = values[index]
    return df


def preprocess_fd001(
    base_dir: None | str | Path = None,
    out_dir: None | str | Path = None,
    with_features: bool = True,
) -> Dict[str, Any]:
    """Run the full FD001 preparation pipeline and save the CSVs.

    Returns a dict with the cleaned frames, target columns and output paths.
    """
    data = load_all(base_dir)
    train_raw, test_raw, rul_raw = data["train"], data["test"], data["rul"]

    validation_report(train_raw, test_raw, rul_raw)

    train = build_train_target(clean(train_raw))
    test = attach_test_target(clean(test_raw), rul_raw)

    if with_features:
        train = add_features(train)
        test = add_features(test)

    train_issues: list = []
    validate_duplicates(train, train_issues, "train")
    validate_missing(train, train_issues, "train")
    validate_infinite(train, train_issues, "train")
    validate_units(train, train_issues)
    validate_target(train, train_issues)
    test_issues: list = []
    validate_duplicates(test, test_issues, "test")
    validate_missing(test, test_issues, "test")
    validate_infinite(test, test_issues, "test")
    validate_units(test, test_issues)
    validate_alignment(test, test_issues)
    raise_on_issues(train_issues, label="processed-train")
    raise_on_issues(test_issues, label="processed-test")

    out_dir = Path(out_dir) if out_dir is not None else _OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    train_path = out_dir / PROCESSED_TRAIN_FILE
    test_path = out_dir / PROCESSED_TEST_FILE
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)

    return {
        "train": train,
        "test": test,
        "target_columns": [RUL_NAME],
        "train_path": str(train_path),
        "test_path": str(test_path),
        "n_train_rows": len(train),
        "n_test_rows": len(test),
        "n_features": train.shape[1],
    }


if __name__ == "__main__":
    result = preprocess_fd001()
    print("FD001 preprocessing complete:")
    print(f"  train -> {result['n_train_rows']} rows x {result['n_features']} cols")
    print(f"  test  -> {result['n_test_rows']} rows")
    print(f"  saved {result['train_path']}")
    print(f"  saved {result['test_path']}")