"""Common feature engineering for the NASA C-MAPSS FD001 pipeline.

All features are computed per engine (grouped by ``unit``) and only from
past/current data within that engine, so no information leaks across engines
or from the future. Nothing here fits parameters on the test split.

Features produced per base column (sensors + operational settings):
  * ``{col}_roll_{mean|std|min|max}{W}`` - backward-looking rolling window,
    window ``W`` cycles including the current cycle.
  * ``{col}_delta{L}`` - value change vs ``L`` cycles earlier.

The standard deviation of a single observation is undefined, so the first
cycle of each engine is filled with 0 (no variation). Deltas at the first
cycle (no previous value) are likewise filled with 0.
"""

from typing import List, Optional

import numpy as np
import pandas as pd

from src.data.schemas.nasa_schema import (
    DELTA_LAG,
    KEPT_FEATURE_COLUMNS,
    ROLL_EXTREMES,
    ROLL_STATS,
    ROLL_WINDOW,
    RUL_NAME,
    delta_column_name,
    feature_columns_for,
    roll_column_name,
)


def add_features(
    frame: pd.DataFrame,
    columns: Optional[List[str]] = None,
    window: int = ROLL_WINDOW,
    lag: int = DELTA_LAG,
) -> pd.DataFrame:
    """Append rolling and delta features to a cleaned FD001 frame (in place of a copy).

    ``frame`` must already be sorted by ``(unit, cycle)``. ``rul`` and id
    columns are never used as feature sources.
    """
    if columns is None:
        columns = [c for c in KEPT_FEATURE_COLUMNS if c in frame.columns]

    df = frame
    grouped = df.groupby("unit", sort=False)

    for column in columns:
        series = df[column]
        roll_mean = grouped[column].rolling(window, min_periods=1).mean()
        roll_std = grouped[column].rolling(window, min_periods=2).std().fillna(0.0)
        roll_min = grouped[column].rolling(window, min_periods=1).min()
        roll_max = grouped[column].rolling(window, min_periods=1).max()

        # groupby.rolling returns group labels as the outer index level.
        df[roll_column_name(column, "mean", window)] = (
            roll_mean.reset_index(level=0, drop=True)
        )
        df[roll_column_name(column, "std", window)] = roll_std.reset_index(
            level=0, drop=True
        )
        df[roll_column_name(column, "min", window)] = roll_min.reset_index(
            level=0, drop=True
        )
        df[roll_column_name(column, "max", window)] = roll_max.reset_index(
            level=0, drop=True
        )

        delta = grouped[column].diff(lag).fillna(0.0)
        df[delta_column_name(column, lag)] = delta.reset_index(drop=True)

    return df


def feature_summary(frame: pd.DataFrame, window: int = ROLL_WINDOW) -> pd.DataFrame:
    """Small table of derived features: name, source column, and type."""
    rows = []
    for column in KEPT_FEATURE_COLUMNS:
        if column not in frame.columns:
            continue
        for stat in ROLL_STATS + ROLL_EXTREMES:
            rows.append(
                {
                    "feature": roll_column_name(column, stat, window),
                    "source": column,
                    "kind": f"rolling_{stat}_{window}",
                }
            )
        rows.append(
            {
                "feature": delta_column_name(column, DELTA_LAG),
                "source": column,
                "kind": f"delta{DELTA_LAG}",
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print(
        "Derived features per base column:",
        len(feature_columns_for(KEPT_FEATURE_COLUMNS)),
    )