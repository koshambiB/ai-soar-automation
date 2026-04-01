"""
ML Model for SOAR Risk Classification
--------------------------------------
Uses a Random Forest classifier to predict risk_level from alert features.
Feature columns here EXACTLY match what FeatureExtractor.extract_features() returns.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
# Resolves to data/models/ from project root regardless of where script is run
_HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR     = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "..", "data", "models"))
MODEL_PATH    = os.path.join(MODEL_DIR, "risk_classifier.joblib")
ENCODER_PATH  = os.path.join(MODEL_DIR, "label_encoder.joblib")
METADATA_PATH = os.path.join(MODEL_DIR, "model_metadata.json")

# ── Feature columns ────────────────────────────────────────────────────────────
# These MUST match the keys returned by FeatureExtractor.extract_features()
FEATURE_COLUMNS = [
    "severity_encoded",
    "alert_type_encoded",
    "system_type_encoded",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "is_after_hours",
    "confidence_score",
    "fp_likelihood_encoded",
    "mitre_tactic_count",
    "mitre_technique_count",
    "event_count",
    "failed_attempts",
    "duration_seconds",
    "data_volume_mb",
    "has_ip_addresses",
    "has_domains",
    "has_file_hashes",
    "has_urls",
    "has_email_addresses",
    "has_processes",
    "ioc_diversity",
    "asset_criticality_encoded",
    "affected_asset_count",
    "has_production_tag",
    "has_after_hours_tag",
    "tag_count",
]

# All possible risk labels - must be exhaustive so LabelEncoder is stable
RISK_LABELS = ["info", "low", "medium", "high", "critical"]


class SOARClassifier:
    """
    Wraps a scikit-learn RandomForest for SOAR risk classification.

    Typical usage:
        classifier = SOARClassifier()
        classifier.load()
        result = classifier.predict(feature_dict)
        # {"risk_level": "high", "confidence": 0.87, "probabilities": {...}, "ml_available": True}
    """

    def __init__(self):
        self.model: Optional[RandomForestClassifier] = None
        self.label_encoder: Optional[LabelEncoder] = None
        self.is_loaded = False
        self.metadata: dict = {}

    # ── Public API ─────────────────────────────────────────────────────────────

    def load(self) -> bool:
        """Load persisted model from disk. Returns True on success."""
        try:
            if not os.path.exists(MODEL_PATH):
                logger.warning(f"No model found at {MODEL_PATH}. Run scripts/train_model.py first.")
                return False

            self.model         = joblib.load(MODEL_PATH)
            self.label_encoder = joblib.load(ENCODER_PATH)

            if os.path.exists(METADATA_PATH):
                with open(METADATA_PATH) as f:
                    self.metadata = json.load(f)

            self.is_loaded = True
            logger.info(f"ML model loaded. Accuracy: {self.metadata.get('accuracy', 'unknown')}")
            return True

        except Exception as e:
            logger.error(f"Model load failed: {e}")
            return False

    def predict(self, features: dict) -> dict:
        """
        Predict risk level from a feature dictionary.

        Args:
            features: dict whose keys include FEATURE_COLUMNS (extras ignored)

        Returns:
            dict:
                risk_level    - predicted class string
                confidence    - probability of predicted class (0-1)
                probabilities - full class->probability map
                ml_available  - False means model not loaded, caller uses rule score
        """
        if not self.is_loaded:
            return {"risk_level": None, "confidence": 0.0,
                    "probabilities": {}, "ml_available": False}

        try:
            # Build feature vector in exact column order; missing -> 0
            vec = []
            for col in FEATURE_COLUMNS:
                val = features.get(col, 0)
                if val is None or (isinstance(val, float) and np.isnan(val)):
                    val = 0.0
                vec.append(float(val))

            X = np.array(vec).reshape(1, -1)

            pred_encoded  = self.model.predict(X)[0]
            probabilities = self.model.predict_proba(X)[0]
            risk_level    = self.label_encoder.inverse_transform([pred_encoded])[0]

            prob_dict = {
                label: round(float(prob), 4)
                for label, prob in zip(self.label_encoder.classes_, probabilities)
            }
            confidence = prob_dict[risk_level]

            return {
                "risk_level":    risk_level,
                "confidence":    confidence,
                "probabilities": prob_dict,
                "ml_available":  True,
            }

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {"risk_level": None, "confidence": 0.0,
                    "probabilities": {}, "ml_available": False}

    def get_feature_names(self) -> list:
        """Used by SHAP explainer to label features."""
        return FEATURE_COLUMNS


# ── Training helper (called by scripts/train_model.py) ────────────────────────

def train_and_save(training_data: list, labels: list) -> dict:
    """
    Train RandomForest on a list of feature-dicts and save model to disk.

    Args:
        training_data : list of dicts from FeatureExtractor.extract_features()
        labels        : list of risk_level strings aligned with training_data

    Returns:
        dict with accuracy, report, model_path, metadata
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    # Build DataFrame; fill any missing columns with 0
    df = pd.DataFrame(training_data)
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0
    X = df[FEATURE_COLUMNS].fillna(0).astype(float)

    # Encode labels - fit on ALL possible labels so encoder is always stable
    le = LabelEncoder()
    le.fit(RISK_LABELS)
    y = le.transform(labels)

    # Stratified split (fall back to plain split if only 1 class present)
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
    except ValueError:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

    # Train
    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=2,
        random_state=42,
        class_weight="balanced",   # handles class imbalance
    )
    clf.fit(X_train, y_train)

    # Evaluate
    y_pred   = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report   = classification_report(
        y_test, y_pred,
        target_names=le.classes_,
        zero_division=0
    )

    # Persist
    joblib.dump(clf, MODEL_PATH)
    joblib.dump(le,  ENCODER_PATH)

    metadata = {
        "trained_at":      datetime.utcnow().isoformat(),
        "accuracy":        round(float(accuracy), 4),
        "n_samples":       len(training_data),
        "n_features":      len(FEATURE_COLUMNS),
        "feature_columns": FEATURE_COLUMNS,
        "classes":         list(le.classes_),
        "model_type":      "RandomForestClassifier",
        "model_path":      MODEL_PATH,
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Model saved -> {MODEL_PATH}  accuracy={accuracy:.4f}")
    return {
        "accuracy":   accuracy,
        "report":     report,
        "model_path": MODEL_PATH,
        "metadata":   metadata,
    }