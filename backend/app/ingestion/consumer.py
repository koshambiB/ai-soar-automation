"""
Production Kafka Consumer with Alert Analysis
Consumes alerts, analyzes them, and stores results in PostgreSQL
"""

from confluent_kafka import Consumer, KafkaError
import json
import logging
from ..core.database import get_connection, get_cursor
from ..models.alert import insert_alert
from ..analysis.analyzer import AlertAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

KAFKA_CONFIG = {
    "bootstrap.servers": "localhost:9092",
    "group.id": "soar-consumer-group",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": True
}

TOPIC = "soar-alerts"

REQUIRED_FIELDS = ['alert_id', 'timestamp', 'severity', 'source', 'alert_type']

def validate_alert(alert_dict):
    """Validate that alert has required fields"""
    for field in REQUIRED_FIELDS:
        if field not in alert_dict:
            raise ValueError(f"Missing required field: {field}")
    return True

def consume_and_store_alerts():
    """Main consumer loop with analysis pipeline"""
    consumer = Consumer(KAFKA_CONFIG)
    consumer.subscribe([TOPIC])
    
    # Initialize analyzer
    analyzer = AlertAnalyzer()
    
    logger.info(f"Started consuming from topic: {TOPIC}")
    logger.info("Alert analysis pipeline enabled")
    
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    logger.error(f"Kafka error: {msg.error()}")
                    break
            
            try:
                # Decode alert
                alert_data = json.loads(msg.value().decode('utf-8'))
                
                # Validate required fields
                validate_alert(alert_data)
                
                # ANALYSIS PIPELINE: Analyze alert before storing
                analysis_results = analyzer.analyze_alert(alert_data)
                
                logger.info(
                    f"Analysis: {alert_data['alert_id']} → "
                    f"risk={analysis_results['risk_level']}, "
                    f"score={analysis_results['rule_score']}, "
                    f"rules={analysis_results['matched_rule_count']}"
                )
                
                # Store alert with analysis results
                with get_connection() as conn:
                    cursor = get_cursor(conn)
                    result_id = insert_alert(
                        cursor, 
                        alert_data,
                        analysis_results=analysis_results
                    )
                    
                    if result_id:
                        logger.info(
                            f"✓ Stored alert {alert_data['alert_id']} "
                            f"(DB ID: {result_id}, Risk: {analysis_results['risk_level']})"
                        )
                    else:
                        logger.warning(f"⚠ Duplicate alert skipped: {alert_data['alert_id']}")
                        
            except ValueError as e:
                logger.error(f"✗ Validation error: {e}")
                continue
            except json.JSONDecodeError as e:
                logger.error(f"✗ JSON decode error: {e}")
                continue
            except Exception as e:
                logger.error(f"✗ Error processing alert: {e}", exc_info=True)
                continue
                
    except KeyboardInterrupt:
        logger.info("Shutting down consumer...")
    finally:
        consumer.close()
        logger.info("Consumer closed")

if __name__ == "__main__":
    consume_and_store_alerts()