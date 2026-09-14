import unittest
import pandas as pd
import numpy as np
from src.models.health.health_scoring import compute_health, normalize_anomaly
from src.models.health.health_config import (
    ANOMALY_SCORE_MIN,
    ANOMALY_SCORE_MAX,
    HEALTH_STATUS_NORMAL,
    HEALTH_STATUS_WARNING,
    HEALTH_STATUS_CRITICAL
)

class TestHealthScoring(unittest.TestCase):
    def test_normal_input(self):
        # Normal input corresponding to the HEALTHY boundary
        # -0.04897802 is exactly 70.0. We use slightly less to ensure it is NORMAL.
        val = -0.048979
        score = normalize_anomaly(pd.Series([val])).iloc[0]
        self.assertTrue(score >= 70.0)

        df = pd.DataFrame({'unit': [1], 'cycle': [1], 'anomaly_score': [val]})
        result = compute_health(df)
        self.assertEqual(result['health_status'].iloc[0], HEALTH_STATUS_NORMAL)

    def test_warning_input(self):
        # Critical boundary corresponding to 40.0
        val = 0.017924
        score = normalize_anomaly(pd.Series([val])).iloc[0]
        self.assertAlmostEqual(score, 40.0, places=2)

        df = pd.DataFrame({'unit': [1], 'cycle': [1], 'anomaly_score': [val]})
        result = compute_health(df)
        self.assertEqual(result['health_status'].iloc[0], HEALTH_STATUS_WARNING)

    def test_anomalous_input(self):
        # The specific failing anomaly value from the bug report
        val = 0.2184
        score = normalize_anomaly(pd.Series([val])).iloc[0]
        self.assertTrue(0 < score < 40)
        self.assertNotEqual(score, 0.0)

        df = pd.DataFrame({'unit': [1], 'cycle': [1], 'anomaly_score': [val]})
        result = compute_health(df)
        self.assertEqual(result['health_status'].iloc[0], HEALTH_STATUS_CRITICAL)

        # Ensure monotonicity
        score_more_anomalous = normalize_anomaly(pd.Series([val + 0.1])).iloc[0]
        self.assertTrue(score_more_anomalous < score)

    def test_boundary_cases(self):
        # Very healthy
        val_min = ANOMALY_SCORE_MIN - 1.0
        score_min = normalize_anomaly(pd.Series([val_min])).iloc[0]
        self.assertTrue(0 <= score_min <= 100)

        # Very degraded
        val_max = ANOMALY_SCORE_MAX + 1.0
        score_max = normalize_anomaly(pd.Series([val_max])).iloc[0]
        self.assertTrue(0 <= score_max <= 100)
        self.assertNotEqual(score_max, 0.0)

if __name__ == '__main__':
    unittest.main()
