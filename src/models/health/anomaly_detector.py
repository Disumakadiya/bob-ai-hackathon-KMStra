# src/models/health/anomaly_detector.py
"""Anomaly detection model based on Isolation Forest.

The model is deliberately simple: it trains an IsolationForest on the selected
features from the processed FD001 training data and provides a method to compute
anomaly scores for new observations.

Higher ``anomaly_score`` indicates a more abnormal observation.
"""

from __future__ import annotations

import pathlib
from typing import List

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ..health.anomaly_config import (
    CONTAMINATION,
    MAX_SAMPLES,
    N_ESTIMATORS,
    RANDOM_STATE,
    MODEL_PATH,
)

class AnomalyDetector:
    """Wrapper around :class:`sklearn.ensemble.IsolationForest`.

    The class handles training, persistence and scoring.  It expects a pandas
    ``DataFrame`` that contains the feature columns defined in the NASA schema
    (operational settings + sensor columns that are not constant).  Identifier
    columns such as ``unit``, ``cycle`` and ``rul`` must be removed before the
    data is passed to :meth:`fit`.
    """

    def __init__(self) -> None:
        self.model: IsolationForest | None = None

    # ---------------------------------------------------------------------
    # Training utilities
    # ---------------------------------------------------------------------
    def fit(self, X: pd.DataFrame) -> None:
        """Fit the IsolationForest on ``X``.

        Parameters
        ----------
        X:
            Feature matrix (no identifier columns).  The dataframe is copied
            internally to avoid side‑effects.
        """
        if X.empty:
            raise ValueError("Feature matrix X is empty – cannot train model.")

        self.model = IsolationForest(
            n_estimators=N_ESTIMATORS,
            max_samples=MAX_SAMPLES,
            contamination=CONTAMINATION,
            random_state=RANDOM_STATE,
        )
        self.model.fit(X.values)

    # ---------------------------------------------------------------------
    # Persistence utilities
    # ---------------------------------------------------------------------
    def save(self, path: str | pathlib.Path | None = None) -> None:
        """Persist the trained model to ``path``.

        If ``path`` is ``None`` the default ``MODEL_PATH`` from the config is used.
        """
        if self.model is None:
            raise RuntimeError("No model trained – call `fit` before saving.")
        target = pathlib.Path(path) if path else pathlib.Path(MODEL_PATH)
        target.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, target)

    @classmethod
    def load(cls, path: str | pathlib.Path | None = None) -> "AnomalyDetector":
        """Load a persisted model and return an ``AnomalyDetector`` instance."""
        target = pathlib.Path(path) if path else pathlib.Path(MODEL_PATH)
        if not target.exists():
            raise FileNotFoundError(f"Model file not found at {target}")
        detector = cls()
        detector.model = joblib.load(target)
        return detector

    # ---------------------------------------------------------------------
    # Scoring utilities
    # ---------------------------------------------------------------------
    def anomaly_score(self, X: pd.DataFrame) -> np.ndarray:
        """Return a *higher‑is‑more‑abnormal* score for each row in ``X``.

        Internally ``IsolationForest.decision_function`` is used, which yields
        higher values for normal points.  We invert the sign so that larger values
        correspond to greater abnormality – this matches the requirement in the
        task description.
        """
        if self.model is None:
            raise RuntimeError("Model has not been trained or loaded.")
        # ``decision_function`` returns shape (n_samples,).  Negate to get the
        # desired orientation.
        raw_score = self.model.decision_function(X.values)
        return -raw_score

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict binary labels: ``1`` for normal, ``-1`` for anomaly.

        This mirrors the scikit‑learn API.  The method is provided for convenience
        when a simple flag is needed.
        """
        if self.model is None:
            raise RuntimeError("Model has not been trained or loaded.")
        return self.model.predict(X.values)

    # ---------------------------------------------------------------------
    # Helper for end‑to‑end pipelines
    # ---------------------------------------------------------------------
    @staticmethod
    def select_features(df: pd.DataFrame, feature_columns: List[str]) -> pd.DataFrame:
        """Return a dataframe containing only ``feature_columns``.

        ``feature_columns`` should be derived from the canonical schema (e.g.
        ``KEPT_FEATURE_COLUMNS``).  The function does **not** modify the original
        dataframe.
        """
        missing = set(feature_columns) - set(df.columns)
        if missing:
            raise KeyError(f"Requested feature columns missing from input: {missing}")
        return df[feature_columns].copy()

# End of file
