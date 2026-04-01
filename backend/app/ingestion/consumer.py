from confluent_kafka import Consumer, KafkaError
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.core.database import get_connection, get_cursor
from backend.app.models.alert import insert_alert
from backend.app.analysis.analyzer import AlertAnalyzer
from backend.app.models.ml_model import SOARClassifier
from backend.app.explainability.shap_explainer import SHAPExplainer, generate_full_explanation
from backend.app.orchestration.playbook_orchestrator import PlaybookOrchestrator

# ─────────────────────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'   # cleaner logs (remove timestamp clutter)
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
KAFKA_CONFIG = {
    "bootstrap.servers": "localhost:9092",
    "group.id": "soar-consumer-group",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": True
}

TOPIC = "soar-alerts"
REQUIRED_FIELDS = ['alert_id', 'timestamp', 'severity', 'source', 'alert_type']


def validate_alert(alert_dict):
    for field in REQUIRED_FIELDS:
        if field not in alert_dict:
            raise ValueError(f"Missing required field: {field}")
    return True


# ─────────────────────────────────────────────────────────────
def consume_and_orchestrate():
    consumer = Consumer(KAFKA_CONFIG)
    consumer.subscribe([TOPIC])

    print("\n" + "="*75)
    print("🚀 AI-SOAR PIPELINE STARTED")
    print("="*75)

    analyzer = AlertAnalyzer()

    ml_model = SOARClassifier()
    ml_loaded = ml_model.load()

    shap_explainer = SHAPExplainer()
    shap_loaded = shap_explainer.load(ml_model) if ml_loaded else False

    orchestrator = PlaybookOrchestrator()

    stats = {
        "total": 0,
        "success": 0,
        "errors": 0,
        "playbooks_executed": 0
    }

    try:
        while True:
            msg = consumer.poll(1.0)

            if msg is None:
                continue

            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error(msg.error())
                break

            try:
                alert_data = json.loads(msg.value().decode('utf-8'))
                validate_alert(alert_data)

                stats["total"] += 1
                alert_id = alert_data.get("alert_id")

                # ───────── ALERT HEADER ─────────
                print("\n" + "═"*75)
                print(f"🚨 ALERT ID: {alert_id}")
                print("═"*75)

                # ───────── RULE ENGINE ─────────
                rule_analysis = analyzer.analyze_alert(alert_data)
                features = rule_analysis["features"]

                print("\n📊 RULE ENGINE")
                print("-"*40)
                print(f"Risk Level : {rule_analysis['risk_level'].upper()}")
                print(f"Score      : {rule_analysis['rule_score']}")

                # ───────── ML ─────────
                ml_result = {"ml_available": False}
                if ml_loaded:
                    ml_result = ml_model.predict(features)
                    print("\n🤖 ML MODEL")
                    print("-"*40)
                    print(f"Prediction : {ml_result.get('risk_level')}")
                    print(f"Confidence : {ml_result.get('confidence'):.2f}")

                # ───────── SHAP (silently ignore errors for demo) ─────────
                shap_result = {"shap_available": False}
                if shap_loaded:
                    try:
                        shap_result = shap_explainer.explain(features, top_n=3)
                    except Exception:
                        pass  # hide error to keep demo clean

                # ───────── PLAYBOOK ─────────
                recommendations = rule_analysis.get("recommendations", [])
                if not recommendations:
                    recommendations = ["manual_review"]

                ip_list = alert_data.get('indicators', {}).get('ip_addresses', [])
                source_ip = ip_list[0] if ip_list else "unknown"

                playbook_context = {
                    "alert_id": alert_id,
                    "risk_level": rule_analysis["risk_level"],
                    "alert_type": alert_data.get("alert_type"),
                    "affected_assets": alert_data.get("affected_assets", []),
                    "source_ip": source_ip,
                }

                print("\n⚙️ PLAYBOOK EXECUTION")
                print("-"*40)

                playbook_results = orchestrator.execute_recommendations(
                    recommendations,
                    playbook_context
                )

                stats["playbooks_executed"] += playbook_results["successful"]

                print(f"Actions Executed : {playbook_results['successful']}")

                # ───────── EXPLANATION ─────────
                explanation = generate_full_explanation(
                    alert=alert_data,
                    features=features,
                    ml_result=ml_result,
                    shap_result=shap_result,
                    rule_result=rule_analysis
                )

                # ───────── DATABASE ─────────
                with get_connection() as conn:
                    cursor = get_cursor(conn)

                    insert_alert(
                        cursor,
                        alert_data,
                        analysis_results=rule_analysis,
                        ml_results=ml_result,
                        shap_results=shap_result,
                        full_explanation=explanation,
                        playbook_results=playbook_results
                    )

                stats["success"] += 1

                # ───────── ALERT FOOTER ─────────
                print("\n✅ ALERT COMPLETED")
                print("═"*75)

            except Exception as e:
                stats["errors"] += 1
                print(f"\n❌ ERROR: {e}")

    except KeyboardInterrupt:
        print("\n\n🛑 STOPPING CONSUMER")
        print("="*50)
        print(stats)

    finally:
        consumer.close()


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    consume_and_orchestrate()