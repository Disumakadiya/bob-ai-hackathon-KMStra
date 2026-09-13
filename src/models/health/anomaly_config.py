# src/models/health/anomaly_config.py
"""Configuration for the anomaly detection model.

All hyperparameters are defined here so that they can be easily tweaked
without touching the training logic.
"""

# Random seed for reproducibility
RANDOM_STATE = 42

# IsolationForest hyper‑parameters
N_ESTIMATORS = 200  # number of trees in the forest
MAX_SAMPLES = "auto"  # number of samples to draw to train each base estimator
CONTAMINATION = "auto"  # proportion of outliers in the data (auto lets the model infer)

# Path where the trained model will be persisted
MODEL_PATH = "e:/bob-ai-hackathon-KMStra/src/models/health/isolation_forest_model.joblib"
