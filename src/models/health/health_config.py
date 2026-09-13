# src/models/health/health_config.py
"""Configuration and rationale for health scoring (Part 2).

The ``health_score`` is derived from the ``anomaly_score`` produced by the
IsolationForest in Part 1.  Higher ``anomaly_score`` means a more abnormal,
hence more degraded, observation, so the score is inverted and rescaled to the
interval ``[0, 100]`` where ``100`` = perfect health and ``0`` = most degraded.

Scoring formula
---------------
health_score = clip(
    (ANOMALY_SCORE_MAX - anomaly_score) / (ANOMALY_SCORE_MAX - ANOMALY_SCORE_MIN) * 100,
    0, 100,
)

The reference bounds are fixed constants (documented below), never recomputed
at runtime, so the transformation is deterministic and reproducible and can be
re-applied unchanged to new anomaly-score data.

Reference bounds (why percentiles, not raw min/max)
---------------------------------------------------
``ANOMALY_SCORE_MIN`` and ``ANOMALY_SCORE_MAX`` are the 0.5th and 99.5th
percentiles of the Part 1 training anomaly scores (20,631 rows in
``src/models/health/anomaly_scores.csv``):

- ``ANOMALY_SCORE_MIN = -0.1158800957``  (0.5th percentile)
- ``ANOMALY_SCORE_MAX =  0.1071268208``  (99.5th percentile)

Percentiles are used instead of the observed min/max because the observed
maximum is a single extreme point (``0.1848``) that a min/max scaling would
let dominate the entire scale.  Clipping at the 0.5th/99.5th percentiles keeps
the scale stable, while scores outside the bounds still collapse to the 0/100
end-points (100 = healthiest, 0 = most degraded).

Thresholds (health_status)
--------------------------
The continuous score maps to exactly one of three states:

- ``NORMAL``   : ``health_score >= 70``
- ``WARNING``  : ``40 <= health_score < 70``
- ``CRITICAL`` : ``health_score < 40``

Rounded thresholds (70 / 40) follow the common green / amber / red convention
in condition monitoring.  They are not arbitrary: anchored to the reference
distribution above they correspond to hard anomaly-score cut-offs

- NORMAL  when ``anomaly_score <= -0.048978''  (covers the healthiest ~67%
  of the training data),
- CRITICAL when ``anomaly_score > 0.017924``   (the most degraded ~8% tail),
- WARNING for the ~24% band between the two.
"""

# ---------------------------------------------------------------------------
# Fixed reference bounds for normalisation (see module docstring)
# ---------------------------------------------------------------------------
ANOMALY_SCORE_MIN = -0.11588009566255214  # 0.5th percentile of Part 1 scores
ANOMALY_SCORE_MAX = 0.10712682078544834   # 99.5th percentile of Part 1 scores

# ---------------------------------------------------------------------------
# Health-score thresholds (health_score >= threshold)
# ---------------------------------------------------------------------------
HEALTH_NORMAL_THRESHOLD = 70.0  # >= 70                 -> NORMAL
HEALTH_WARNING_THRESHOLD = 40.0  # >= 40 and < 70       -> WARNING
#                 < 40           -> CRITICAL

# ---------------------------------------------------------------------------
# Categorical labels (must be exactly these strings)
# ---------------------------------------------------------------------------
HEALTH_STATUS_NORMAL = "NORMAL"
HEALTH_STATUS_WARNING = "WARNING"
HEALTH_STATUS_CRITICAL = "CRITICAL"

# Health score range
HEALTH_SCORE_MAX = 100.0
HEALTH_SCORE_MIN = 0.0