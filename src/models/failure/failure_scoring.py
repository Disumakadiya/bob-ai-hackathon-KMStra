# src/models/failure/failure_scoring.py
"""TASK 4 — Convert failure_probability into a human-readable risk level.

Purpose
-------
Map the continuous ``failure_probability`` output (range [0, 1]) from the
XGBoost model to a categorical ``failure_status``:

    LOW    — probability <  LOW_MEDIUM_BOUNDARY   (0.40)
    MEDIUM — probability >= LOW_MEDIUM_BOUNDARY   (0.40)
               AND probability < MEDIUM_HIGH_BOUNDARY (0.70)
    HIGH   — probability >= MEDIUM_HIGH_BOUNDARY  (0.70)

All threshold values live in ``config.py``.  They are NEVER duplicated here.

IMPORTANT
---------
HIGH failure_status means the model assigns a high probability that this
observation falls within ``RUL_FAILURE_THRESHOLD`` cycles of end-of-life.
It does NOT guarantee certain or imminent failure.

Typical call
------------
    from src.models.failure.failure_scoring import score_failure_predictions
    scored = score_failure_predictions(predictions_df)
    # columns: unit, cycle, failure_probability, failure_status

Output contract (for the future integration layer)
---------------------------------------------------
    unit                – engine identifier
    cycle               – operational cycle
    failure_probability – float in [0, 1]
    failure_status      – one of: LOW | MEDIUM | HIGH
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd

from .config import (
    FAILURE_STATUS_HIGH,
    FAILURE_STATUS_LOW,
    FAILURE_STATUS_MEDIUM,
    LOW_MEDIUM_BOUNDARY,
    MEDIUM_HIGH_BOUNDARY,
)

logger = logging.getLogger(__name__)

# The three valid status values (used for validation)
VALID_STATUSES = frozenset({FAILURE_STATUS_LOW, FAILURE_STATUS_MEDIUM, FAILURE_STATUS_HIGH})


# ---------------------------------------------------------------------------
# Core scoring function
# ---------------------------------------------------------------------------

def assign_failure_status(probability: float) -> str:
    """Map a single failure probability to a status string.

    Parameters
    ----------
    probability : float
        Failure probability in [0, 1].

    Returns
    -------
    str
        One of ``"LOW"``, ``"MEDIUM"``, or ``"HIGH"``.
    """
    if probability >= MEDIUM_HIGH_BOUNDARY:
        return FAILURE_STATUS_HIGH
    if probability >= LOW_MEDIUM_BOUNDARY:
        return FAILURE_STATUS_MEDIUM
    return FAILURE_STATUS_LOW


def score_failure_predictions(
    predictions: pd.DataFrame,
    prob_col: str = "failure_probability",
    unit_col: str = "unit",
    cycle_col: str = "cycle",
    status_col: str = "failure_status",
) -> pd.DataFrame:
    """Add a ``failure_status`` column to a predictions DataFrame.

    Parameters
    ----------
    predictions : pd.DataFrame
        Must contain columns: *unit_col*, *cycle_col*, *prob_col*.
        Typically the output of ``failure_prediction.predict_failure_probability()``.
    prob_col : str
        Name of the probability column.
    unit_col : str
        Name of the engine-ID column.
    cycle_col : str
        Name of the cycle column.
    status_col : str
        Name for the new status column.

    Returns
    -------
    pd.DataFrame
        Copy of *predictions* with *status_col* added.
        Columns: unit, cycle, failure_probability, failure_status.

    Raises
    ------
    ValueError
        If required columns are missing or if probabilities are out of [0, 1].
    """
    for col in (unit_col, cycle_col, prob_col):
        if col not in predictions.columns:
            raise ValueError(f"Required column '{col}' not found in DataFrame.")

    probs = predictions[prob_col]

    # Defensive range check
    if probs.lt(0.0).any() or probs.gt(1.0).any():
        raise ValueError(
            f"Column '{prob_col}' contains values outside [0, 1]. "
            f"Range: [{probs.min():.4f}, {probs.max():.4f}]"
        )

    out = predictions[[unit_col, cycle_col, prob_col]].copy()
    out[status_col] = np.where(
        probs >= MEDIUM_HIGH_BOUNDARY,
        FAILURE_STATUS_HIGH,
        np.where(
            probs >= LOW_MEDIUM_BOUNDARY,
            FAILURE_STATUS_MEDIUM,
            FAILURE_STATUS_LOW,
        ),
    )

    # Validate output values
    invalid = ~out[status_col].isin(VALID_STATUSES)
    if invalid.any():
        raise RuntimeError(
            f"Unexpected failure_status values generated: "
            f"{out.loc[invalid, status_col].unique()}"
        )

    logger.info(
        "Scoring complete. Status distribution:\n%s",
        out[status_col].value_counts().to_string(),
    )
    return out


# ---------------------------------------------------------------------------
# Distribution reporting
# ---------------------------------------------------------------------------

def report_status_distribution(
    scored: pd.DataFrame,
    status_col: str = "failure_status",
    prob_col: str = "failure_probability",
) -> None:
    """Print a summary of the failure_status distribution.

    Parameters
    ----------
    scored : pd.DataFrame
        Output of ``score_failure_predictions()``.
    status_col : str
        Name of the status column.
    prob_col : str
        Name of the probability column.
    """
    counts = scored[status_col].value_counts()
    total = len(scored)

    lines = [
        "",
        "=" * 60,
        "FAILURE STATUS DISTRIBUTION",
        "=" * 60,
        f"  Thresholds: LOW < {LOW_MEDIUM_BOUNDARY:.2f} <= MEDIUM < {MEDIUM_HIGH_BOUNDARY:.2f} <= HIGH",
        f"  Total predictions: {total:,}",
        "",
    ]
    for status in (FAILURE_STATUS_LOW, FAILURE_STATUS_MEDIUM, FAILURE_STATUS_HIGH):
        cnt = counts.get(status, 0)
        pct = cnt / total * 100
        lines.append(f"  {status:<8}: {cnt:>6,}  ({pct:.1f}%)")

    lines += [
        "",
        f"  Probability range: [{scored[prob_col].min():.4f}, {scored[prob_col].max():.4f}]",
        f"  Mean probability : {scored[prob_col].mean():.4f}",
        "",
        "  NOTE: HIGH = high model-estimated failure risk.",
        "        It does NOT guarantee certain failure.",
        "=" * 60,
    ]
    report_str = "\n".join(lines)
    logger.info(report_str)
    print(report_str)


# ---------------------------------------------------------------------------
# Sample output helper
# ---------------------------------------------------------------------------

def sample_predictions(
    scored: pd.DataFrame,
    n: int = 10,
    unit_col: str = "unit",
    cycle_col: str = "cycle",
    prob_col: str = "failure_probability",
    status_col: str = "failure_status",
) -> pd.DataFrame:
    """Return a sample of scored predictions for display.

    Selects rows across the probability range to illustrate all three statuses.

    Parameters
    ----------
    scored : pd.DataFrame
        Output of ``score_failure_predictions()``.
    n : int
        Approximate number of sample rows (spread across status classes).

    Returns
    -------
    pd.DataFrame
        Subset of rows sorted by *unit_col* and *cycle_col*.
    """
    samples = []
    per_class = max(1, n // 3)

    for status in (FAILURE_STATUS_LOW, FAILURE_STATUS_MEDIUM, FAILURE_STATUS_HIGH):
        subset = scored[scored[status_col] == status]
        if len(subset) > 0:
            samples.append(subset.sample(min(per_class, len(subset)), random_state=42))

    if not samples:
        return scored.head(n)

    return (
        pd.concat(samples)
        .sort_values([unit_col, cycle_col])
        .reset_index(drop=True)[[unit_col, cycle_col, prob_col, status_col]]
    )
