"""
scripts/train_model.py
-----------------------
Pulls analyzed alerts from PostgreSQL, extracts features using the
existing FeatureExtractor, trains the Random Forest, and saves it.

Run from project root:
    python scripts/train_model.py
"""
import sys
import os
import random
import logging
from collections import Counter

# This adds the backend folder to Python's search path
# so that   from app.analysis...   works correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import psycopg
from app.analysis.feature_extractor import FeatureExtractor
from app.models.ml_model import train_and_save, RISK_LABELS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ── DB config - must match your docker-compose ────────────────────────────────
from app.core.database import get_connection_string
DB_DSN = get_connection_string()


# ── Step 1: Fetch alerts ──────────────────────────────────────────────────────

def fetch_analyzed_alerts() -> list:
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    alert_id,
                    severity,
                    alert_type,
                    source,
                    alert_timestamp AS timestamp,
                    raw_data,
                    risk_level,
                    rule_score
                FROM alerts
                WHERE risk_level IS NOT NULL
                  AND risk_level != ''
                ORDER BY alert_timestamp DESC
            """)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


# ── Step 2: Build one training sample ─────────────────────────────────────────

def build_sample(alert: dict, extractor: FeatureExtractor) -> tuple:
    # raw_data JSONB contains the full original alert
    raw = alert.get("raw_data") or {}

    reconstructed = {
        "alert_id":        alert["alert_id"],
        "severity":        alert["severity"],
        "alert_type":      alert["alert_type"],
        "timestamp":       str(alert["timestamp"]),
        "source":          raw.get("source", {"system_type": alert.get("source", "unknown")}),
        "affected_assets": raw.get("affected_assets", []),
        "indicators":      raw.get("indicators", {}),
        "mitre_attack":    raw.get("mitre_attack", {}),
        "metrics":         raw.get("metrics", {}),
        "context":         raw.get("context", {}),
        "tags":            raw.get("tags", []),
        "metadata":        raw.get("metadata", {}),
    }

    features = extractor.extract_features(reconstructed)

    label = alert.get("risk_level", "info")
    if label not in RISK_LABELS:
        label = "info"

    return features, label

def augment(samples: list, target: int = 20) -> list:
    features_list = [s[0] for s in samples]
    labels_list   = [s[1] for s in samples]
    counts = Counter(labels_list)
    logger.info(f"Class distribution before augmentation: {dict(counts)}")
    synthetic = []
    for label in RISK_LABELS:
        pool   = [(f, l) for f, l in zip(features_list, labels_list) if l == label]
        needed = max(0, target - len(pool))
        if needed > 0 and pool:
            logger.info(f"  Generating {needed} synthetic samples for '{label}'")
            for _ in range(needed):
                base_feat, _ = random.choice(pool)
                noisy = {}
                for k, v in base_feat.items():
                    try:
                        noisy[k] = float(v) * random.uniform(0.95, 1.05)
                    except (TypeError, ValueError):
                        noisy[k] = v
                synthetic.append((noisy, label))
    return samples + synthetic
# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 55)
    logger.info("  SOAR ML Training Script")
    logger.info("=" * 55)

    # 1. Fetch
    logger.info("Connecting to PostgreSQL and fetching alerts...")
    alerts = fetch_analyzed_alerts()
    logger.info(f"Fetched {len(alerts)} analyzed alerts")

    if len(alerts) < 10:
        logger.error(
            "Need at least 10 analyzed alerts. "
            "Run scripts/produce_alerts.py and the consumer first."
        )
        sys.exit(1)

    # 2. Extract features
    logger.info("Extracting features...")
    extractor = FeatureExtractor()
    samples   = []

    for alert in alerts:
        try:
            feat, label = build_sample(alert, extractor)
            samples.append((feat, label))
        except Exception as e:
            logger.warning(f"  Skipping alert {alert.get('alert_id', '?')}: {e}")

    logger.info(f"Successfully extracted features from {len(samples)} alerts")

    # 3. Augment
    samples = augment(samples, target=20)
    logger.info(f"Total samples after augmentation: {len(samples)}")

    # 4. Train
    logger.info("Training Random Forest classifier...")
    features_list = [s[0] for s in samples]
    labels_list   = [s[1] for s in samples]

    result = train_and_save(features_list, labels_list)

    # 5. Report
    logger.info("=" * 55)
    logger.info(f"  Training complete!")
    logger.info(f"  Accuracy  : {result['accuracy']:.4f}")
    logger.info(f"  Model at  : {result['model_path']}")
    logger.info("=" * 55)
    logger.info("\nClassification Report:\n" + result["report"])


if __name__ == "__main__":
    main()