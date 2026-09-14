# src/models/failure/__init__.py
"""Failure-prediction module (Member 2).

Exposes the public API for the failure-prediction pipeline:

Training
--------
    from src.models.failure import build_labeled_dataset, run_training_pipeline

Prediction / Scoring
--------------------
    from src.models.failure import (
        predict_failure_probability,
        score_failure_predictions,
    )

Output contract
---------------
The combined output of this module is a DataFrame with:

    unit                – engine identifier
    cycle               – operational cycle
    failure_probability – float in [0, 1]
    failure_status      – one of: LOW | MEDIUM | HIGH
"""

from .failure_labeling import (
    build_labeled_dataset,
    create_failure_label,
    get_class_distribution,
    report_label_distribution,
)
from .failure_scoring import (
    assign_failure_status,
    report_status_distribution,
    sample_predictions,
    score_failure_predictions,
)

# failure_prediction and train are imported lazily to avoid a
# RuntimeWarning when running `python -m src.models.failure.train`.
# That command causes Python to import the package (this __init__.py)
# before executing train.py as __main__; if __init__.py imports train
# eagerly, the module ends up in sys.modules under its full dotted name
# before __main__ is set, triggering the warning.  Lazy loading via
# __getattr__ defers those imports until the name is first accessed,
# so the package can be initialised without touching train.py.
_LAZY: dict = {}


def __getattr__(name: str):
    global _LAZY
    _TRAIN = {
        "engine_aware_split", "evaluate_model", "get_feature_columns",
        "load_model", "run_training_pipeline", "save_model", "train_model",
    }
    _PRED = {
        "predict_failure_probability", "run_test_inference", "run_train_inference",
        "save_scores", "run_and_save_test_scores",
    }
    if name in _TRAIN:
        if "train" not in _LAZY:
            from . import train as _train_mod
            _LAZY["train"] = _train_mod
        return getattr(_LAZY["train"], name)
    if name in _PRED:
        if "failure_prediction" not in _LAZY:
            from . import failure_prediction as _pred_mod
            _LAZY["failure_prediction"] = _pred_mod
        return getattr(_LAZY["failure_prediction"], name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # labeling
    "build_labeled_dataset",
    "create_failure_label",
    "get_class_distribution",
    "report_label_distribution",
    # training (lazy)
    "engine_aware_split",
    "evaluate_model",
    "get_feature_columns",
    "load_model",
    "run_training_pipeline",
    "save_model",
    "train_model",
    # prediction (lazy)
    "predict_failure_probability",
    "run_test_inference",
    "run_train_inference",
    "save_scores",
    "run_and_save_test_scores",
    # scoring
    "assign_failure_status",
    "report_status_distribution",
    "sample_predictions",
    "score_failure_predictions",
]
