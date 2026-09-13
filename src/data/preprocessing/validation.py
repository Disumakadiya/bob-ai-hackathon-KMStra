"""Dataset validation for the NASA C-MAPSS FD001 pipeline.

All checks return a list of human-readable issue strings (empty == healthy).
Call ``raise_on_issues`` to hard-fail the pipeline, or print the report for
interactive inspection. No pandas import is pinned to a specific version.
"""

from typing import Iterable, List

import numpy as np
import pandas as pd

from src.data.schemas.nasa_schema import (
    CONSTANT_COLUMNS,
    ENGINE_ID_MAX,
    ENGINE_ID_MIN,
    EXPECTED_N_ROWS,
    ID_COLUMNS,
    N_ENGINES,
    RUL_NAME,
    UNIT,
    CYCLE,
)

_ISSUES = List[str]


def _require(issues: _ISSUES, condition: bool, message: str) -> None:
    if not condition:
        issues.append(message)


def raise_on_issues(issues: Iterable[str], label: str = "validation") -> None:
    """Raise if there are any issues so downstream code never sees bad data."""
    issues = list(issues)
    if issues:
        raise ValueError(f"{label} failed ({len(issues)} issue(s)):\n" + "\n".join(issues))


# ---------------------------------------------------------------------------
# Raw-level checks (validate output of load_nasa)
# ---------------------------------------------------------------------------
def validate_raw(
    train: pd.DataFrame,
    test: pd.DataFrame,
    rul: pd.DataFrame,
) -> _ISSUES:
    """Full check of the three raw DataFrames against the schema."""
    issues: _ISSUES = []
    validate_basic_shape(train, "train", issues)
    validate_basic_shape(test, "test", issues)
    validate_basic_shape(rul, "rul", issues)
    validate_units(train, issues)
    validate_units(test, issues)
    validate_cycles(train, issues)
    validate_cycles(test, issues)
    validate_duplicates(train, issues, "train")
    validate_duplicates(test, issues, "test")
    validate_missing(train, issues, "train")
    validate_missing(test, issues, "test")
    validate_constant_columns(train, issues, "train")
    validate_constant_columns(test, issues, "test")
    validate_infinite(train, issues, "train")
    validate_infinite(test, issues, "test")
    validate_rul(rul, issues)
    return issues


def validate_basic_shape(df: pd.DataFrame, label: str, issues: _ISSUES = None) -> _ISSUES:
    if issues is None:
        issues = []
    _require(issues, df.shape[0] >= 0, f"[{label}] negative row count (trivial guard)")
    if label in EXPECTED_N_ROWS:
        _require(
            issues,
            df.shape[0] == EXPECTED_N_ROWS[label],
            f"[{label}] expected {EXPECTED_N_ROWS[label]} rows, got {df.shape[0]}",
        )
    return issues


def validate_units(df: pd.DataFrame, issues: _ISSUES = None) -> _ISSUES:
    if issues is None:
        issues = []
    units = sorted(df[UNIT].unique().tolist())
    expected = list(range(ENGINE_ID_MIN, ENGINE_ID_MAX + 1))
    _require(issues, units == expected,
             f"expected contiguous units {ENGINE_ID_MIN}..{ENGINE_ID_MAX}, got {units[:5]}...{units[-5:]}")
    return issues


def validate_cycles(df: pd.DataFrame, issues: _ISSUES = None) -> _ISSUES:
    if issues is None:
        issues = []
    first = df.groupby(UNIT)[CYCLE].min()
    diffs = df.groupby(UNIT)[CYCLE].apply(lambda s: (s.diff().dropna() == 1).all())
    _require(issues, bool((first == 1).all()),
             "all engines must start at cycle 1")
    _require(issues, bool(diffs.all()),
             "cycles must increment by exactly 1 within each engine")
    return issues


def validate_duplicates(df: pd.DataFrame, issues: _ISSUES = None, label: str = "") -> _ISSUES:
    if issues is None:
        issues = []
    n_dup = int(df.duplicated(subset=ID_COLUMNS).sum())
    _require(issues, n_dup == 0, f"[{label}] {n_dup} duplicate (unit, cycle) rows")
    return issues


def validate_missing(df: pd.DataFrame, issues: _ISSUES = None, label: str = "") -> _ISSUES:
    if issues is None:
        issues = []
    n_missing = int(df.isna().sum().sum())
    _require(issues, n_missing == 0, f"[{label}] {n_missing} missing values")
    return issues


def validate_infinite(df: pd.DataFrame, issues: _ISSUES = None, label: str = "") -> _ISSUES:
    if issues is None:
        issues = []
    numeric = df.select_dtypes(include=np.number)
    n_inf = int(np.isinf(numeric).sum().sum())
    _require(issues, n_inf == 0, f"[{label}] {n_inf} infinite values")
    return issues


def validate_constant_columns(df: pd.DataFrame, issues: _ISSUES = None, label: str = "") -> _ISSUES:
    """Constant columns documented in the schema must be constant in the data."""
    if issues is None:
        issues = []
    present = [c for c in CONSTANT_COLUMNS if c in df.columns]
    nunique = df[present].nunique() if present else pd.Series(dtype=int)
    non_const = [c for c, n in nunique.items() if n != 1]
    _require(issues, not non_const,
             f"[{label}] documented constant columns not constant: {non_const}")
    return issues


def validate_rul(rul: pd.DataFrame, issues: _ISSUES = None) -> _ISSUES:
    if issues is None:
        issues = []
    _require(issues, len(rul) == EXPECTED_N_ROWS["rul"],
             f"[rul] expected {EXPECTED_N_ROWS['rul']} RUL values, got {len(rul)}")
    if RUL_NAME in rul.columns:
        _require(issues, bool((rul[RUL_NAME] >= 0).all()),
                 "[rul] found negative RUL values")
    return issues


# ---------------------------------------------------------------------------
# Processed-level checks (validate output of preprocess_nasa)
# ---------------------------------------------------------------------------
def validate_processed(train: pd.DataFrame, test: pd.DataFrame, issues: _ISSUES = None) -> _ISSUES:
    """Check the preprocessed frames: targets present, aligned, no NaNs."""
    if issues is None:
        issues = []
    for label, df in (("train", train), ("test", test)):
        validate_duplicates(df, issues, label)
        validate_missing(df, issues, label)
        validate_infinite(df, issues, label)
    validate_target(train, issues)
    validate_alignment(test, issues)
    return issues


def validate_target(train: pd.DataFrame, issues: _ISSUES = None) -> _ISSUES:
    if issues is None:
        issues = []
    _require(issues, RUL_NAME in train.columns, "[train] missing RUL target column")
    if RUL_NAME in train.columns:
        _require(issues, bool((train[RUL_NAME] >= 0).all()),
                 "[train] negative RUL target values")
        last_per_engine = train.sort_values(CYCLE).groupby(UNIT).tail(1)
        nonzero_last = last_per_engine[last_per_engine[RUL_NAME] != 0]
        _require(issues, len(nonzero_last) == 0,
                 "[train] engines must end at RUL=0 (run-to-failure); "
                 f"{len(nonzero_last)} violate")
    return issues


def validate_alignment(test: pd.DataFrame, issues: _ISSUES = None) -> _ISSUES:
    if issues is None:
        issues = []
    _require(issues, RUL_NAME in test.columns,
             "[test] missing attached RUL (from RUL_FD001) for later evaluation")
    if RUL_NAME in test.columns:
        _require(issues, bool((test[RUL_NAME] >= 0).all()),
                 "[test] negative attached RUL values")
    return issues


def validation_report(train: pd.DataFrame, test: pd.DataFrame, rul: pd.DataFrame) -> _ISSUES:
    """Combined report for the raw inputs. Raises on hard failures."""
    issues = validate_raw(train, test, rul)
    raise_on_issues(issues, label="raw-data")
    return issues


if __name__ == "__main__":
    from src.data.ingestion.load_nasa import load_all

    data = load_all()
    issues = validation_report(data["train"], data["test"], data["rul"])
    print(f"Raw-data validation OK ({len(issues)} checks clean).")