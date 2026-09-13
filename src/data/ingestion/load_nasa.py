"""Loading of the raw NASA C-MAPSS FD001 text files.

Responsibility: parse the raw whitespace-separated files into DataFrames
using the canonical schema. No cleaning, feature creation or target
building happens here.

The engine data files have no header; ``RUL_FD001.txt`` has a single value
per line, one per engine, in engine-ID order (row ``i`` -> engine ``i``).
"""

from pathlib import Path
from typing import Dict

import pandas as pd

from src.data.schemas.nasa_schema import (
    DTYPE_MAP,
    RAW_COLUMNS,
    RUL_NAME,
    UNIT,
)

_DEFAULT_BASE: Path = Path(__file__).resolve().parents[2] / "data" / "ingestion" / "nasa"


def _resolve_base(base_dir: None | str | Path) -> Path:
    if base_dir is None:
        return _DEFAULT_BASE
    return Path(base_dir)


def _read_raw(base_dir: Path, filename: str) -> pd.DataFrame:
    df = pd.read_csv(
        base_dir / filename,
        sep=r"\s+",
        header=None,
        names=RAW_COLUMNS,
        engine="python",
    )
    for col, dtype in DTYPE_MAP.items():
        if col in df.columns:
            df[col] = df[col].astype(dtype)
    return df


def load_train(base_dir: None | str | Path = None) -> pd.DataFrame:
    """Load ``train_FD001.txt`` (run-to-failure trajectories)."""
    return _read_raw(_resolve_base(base_dir), "train_FD001.txt")


def load_test(base_dir: None | str | Path = None) -> pd.DataFrame:
    """Load ``test_FD001.txt`` (truncated trajectories)."""
    return _read_raw(_resolve_base(base_dir), "test_FD001.txt")


def load_rul(base_dir: None | str | Path = None) -> pd.DataFrame:
    """Load ``RUL_FD001.txt`` (true RUL per engine, engine-ID order)."""
    base_dir = _resolve_base(base_dir)
    rul = pd.read_csv(
        base_dir / "RUL_FD001.txt",
        sep=r"\s+",
        header=None,
        names=[RUL_NAME],
        engine="python",
    )
    rul[RUL_NAME] = rul[RUL_NAME].astype("int32")
    return rul


def load_all(base_dir: None | str | Path = None) -> Dict[str, pd.DataFrame]:
    """Load the three FD001 files into one dict (``train``/``test``/``rul``)."""
    base_dir = _resolve_base(base_dir)
    return {
        "train": load_train(base_dir),
        "test": load_test(base_dir),
        "rul": load_rul(base_dir),
    }


if __name__ == "__main__":
    data = load_all()
    for name, frame in data.items():
        extra = f"{frame[UNIT].nunique()} units" if UNIT in frame.columns else f"{len(frame)} values"
        print(f"{name}: {frame.shape} | {extra}")