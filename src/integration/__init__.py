# src/integration/__init__.py
"""Integration layer for Mission Readiness & Predictive Maintenance Copilot.

This package merges the outputs of the three ML models (health anomaly detection,
failure prediction, and RUL regression) into a unified asset-readiness dataset.

Architecture
------------
Existing ML models (frozen)
        ↓
Integration layer  ← this package
        ↓
Readiness Engine
        ↓
Maintenance Priority
        ↓
Mission Readiness
        ↓
Backend API

Public API
----------
    from src.integration import (
        load_model_outputs,
        build_unified_dataset,
        ReadinessEngine,
        MissionReadiness,
        normalize_mission_asset_id,
    )
"""

from .readiness_engine import (
    ReadinessEngine,
    MissionReadiness,
    load_model_outputs,
    build_unified_dataset,
    normalize_mission_asset_id,
)

__all__ = [
    "ReadinessEngine",
    "MissionReadiness",
    "load_model_outputs",
    "build_unified_dataset",
    "normalize_mission_asset_id",
]
