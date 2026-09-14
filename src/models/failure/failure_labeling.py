# src/models/failure/failure_labeling.py
"""TASK 2 — Binary failure-risk label construction.

Purpose
-------
NASA C-MAPSS FD001 does not ship a direct binary failure column.
This module derives one from the Remaining Useful Life (RUL) column
that is present in the pre-processed training data.

Label definition
----------------
The binary label is called ``failure_label``:

    failure_label = 1   if RUL <= RUL_FAILURE_THRESHOLD   (approaching failure)
    failure_label = 0   if RUL >  RUL_FAILURE_THRESHOLD   (not approaching failure)

Threshold: RUL_FAILURE_THRESHOLD = 30  (configurable in config.py)

Rationale for threshold = 30
------------------------------
- 30 cycles is a commonly used early-warning horizon in the PHM08/C-MAPSS
  literature; it gives an operator roughly 30 operational cycles to respond.
- At this threshold the positive class covers approximately 15 % of training
  observations, which is imbalanced but workable for XGBoost
  (compensated via scale_pos_weight in train.py).
- Thresholds below ~20 produce a very small positive class (<10 %),
  making recall extremely difficult without large penalties.
- Thresholds above ~50 inflate the positive class toward 25 %+ and
  risk labeling observations that are still far from end-of-life as
  high-risk, reducing label precision.

CRITICAL data-leakage rules
----------------------------
1. RUL is used ONLY to construct ``failure_label``; it is NEVER included
   in the feature matrix X.
2. The test-split RUL (FD001_test_preprocessed.csv ``rul`` column) is never
   used for training labels.
3. Labels are constructed from the training data only.

Limitations
-----------
- The threshold is a design choice, not a ground truth.  Changing it will
  shift the class balance and alter model behaviour.
- The FD001 training set ends each engine trace at its actual failure cycle
  (RUL = 0), so the labeling is internally consistent, but it does not
  directly encode a specific component failure mode.
- The binary label reflects "within 30 cycles of end-of-life under FD001
  conditions", NOT a specific physical failure event.
"""

from __future__ import annotations

import logging
from typing import Tuple

import numpy as np
import pandas as pd

from .config import RUL_FAILURE_THRESHOLD

logger = logging.getLogger(__name__)


def create_failure_label(
    df: pd.DataFrame,
    rul_col: str = "rul",
    label_col: str = "failure_label",
    threshold: int = RUL_FAILURE_THRESHOLD,
) -> pd.DataFrame:
    """Add a binary ``failure_label`` column to *df* and return a copy.

    Parameters
    ----------
    df : pd.DataFrame
        Pre-processed FD001 training data.  Must contain *rul_col*.
    rul_col : str
        Name of the RUL column.  Defaults to ``"rul"``.
    label_col : str
        Name of the new binary label column.  Defaults to ``"failure_label"``.
    threshold : int
        RUL threshold (inclusive).  Observations with RUL <= threshold
        receive label 1.  Sourced from ``config.RUL_FAILURE_THRESHOLD``.

    Returns
    -------
    pd.DataFrame
        A copy of *df* with an additional integer column *label_col*
        containing only 0 and 1.

    Raises
    ------
    ValueError
        If *rul_col* is absent from *df* or if the resulting label
        contains unexpected values.
    """
    if rul_col not in df.columns:
        raise ValueError(
            f"RUL column '{rul_col}' not found in DataFrame. "
            f"Available columns: {list(df.columns)}"
        )

    out = df.copy()
    out[label_col] = (out[rul_col] <= threshold).astype(np.int8)

    # Sanity check
    unique_vals = set(out[label_col].unique())
    if not unique_vals.issubset({0, 1}):
        raise ValueError(
            f"Unexpected values in failure_label: {unique_vals}. "
            "Expected only 0 and 1."
        )

    return out


def get_class_distribution(
    labels: pd.Series,
) -> Tuple[dict, dict]:
    """Return counts and percentages for each class in *labels*.

    Parameters
    ----------
    labels : pd.Series
        Binary label series (0 and 1 values).

    Returns
    -------
    counts : dict  {class_value -> count}
    percentages : dict  {class_value -> percentage}
    """
    counts = labels.value_counts().sort_index().to_dict()
    total = len(labels)
    percentages = {k: round(v / total * 100, 2) for k, v in counts.items()}
    return counts, percentages


def report_label_distribution(
    df: pd.DataFrame,
    label_col: str = "failure_label",
    threshold: int = RUL_FAILURE_THRESHOLD,
) -> None:
    """Print a human-readable class distribution report to the logger.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing *label_col*.
    label_col : str
        Name of the binary label column.
    threshold : int
        The RUL threshold used to produce the labels (for display only).
    """
    if label_col not in df.columns:
        raise ValueError(f"Column '{label_col}' not found in DataFrame.")

    counts, pcts = get_class_distribution(df[label_col])
    total = sum(counts.values())

    report_lines = [
        "",
        "=" * 60,
        "FAILURE LABEL DISTRIBUTION",
        "=" * 60,
        f"  Threshold       : RUL <= {threshold} cycles",
        f"  Total rows      : {total:,}",
        f"  Class 0 (no risk): {counts.get(0, 0):,}  ({pcts.get(0, 0.0):.1f}%)",
        f"  Class 1 (at risk): {counts.get(1, 0):,}  ({pcts.get(1, 0.0):.1f}%)",
        "",
        "  Interpretation:",
        f"    Class 0 — RUL > {threshold}: engine is NOT approaching failure.",
        f"    Class 1 — RUL <= {threshold}: engine IS approaching end-of-life.",
        "",
        "  Usability check:",
    ]

    pos_pct = pcts.get(1, 0.0)
    if pos_pct < 5.0:
        report_lines.append(
            f"  WARNING: Positive class is very small ({pos_pct:.1f}%). "
            "Recall for failure risk will be difficult."
        )
    elif pos_pct > 50.0:
        report_lines.append(
            f"  WARNING: Positive class is very large ({pos_pct:.1f}%). "
            "Consider lowering the threshold."
        )
    else:
        report_lines.append(
            f"  OK: {pos_pct:.1f}% positive class — reasonable for classification. "
            "XGBoost scale_pos_weight will handle imbalance."
        )

    report_lines.append("=" * 60)
    logger.info("\n".join(report_lines))
    # Also print so standalone runs see the output
    print("\n".join(report_lines))


def build_labeled_dataset(
    df: pd.DataFrame,
    rul_col: str = "rul",
    label_col: str = "failure_label",
    threshold: int = RUL_FAILURE_THRESHOLD,
    verbose: bool = True,
) -> pd.DataFrame:
    """Convenience wrapper: label the dataset and optionally report distribution.

    Parameters
    ----------
    df : pd.DataFrame
        Pre-processed training data with a ``rul`` column.
    rul_col : str
        Name of the RUL column.
    label_col : str
        Name for the new binary label column.
    threshold : int
        RUL threshold (from ``config.RUL_FAILURE_THRESHOLD``).
    verbose : bool
        If True, print the class distribution report.

    Returns
    -------
    pd.DataFrame
        Copy of *df* with *label_col* added.
    """
    labeled = create_failure_label(df, rul_col=rul_col, label_col=label_col, threshold=threshold)
    if verbose:
        report_label_distribution(labeled, label_col=label_col, threshold=threshold)
    return labeled
