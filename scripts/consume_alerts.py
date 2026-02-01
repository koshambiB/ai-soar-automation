"""
Alert Consumer for SOAR System
Consumes alerts from Kafka, validates against schema, and processes them

This is a basic consumer for testing. Production consumer will be in backend/app/ingestion/
"""

import json
import signal
import sys
from pathlib import Path
from datetime import datetime
from kafka import KafkaConsumer
from jsonschema import validate, ValidationError

# Kafka Configuration
KAFKA_BROKER = 'localhost:9092'
KAFKA_TOPIC = 'soar-alerts'
CONSUMER_GROUP = 'soar-consumer-group'

# Schema path
SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "alert_schema.json"

# Statistics tracking
stats = {
    "total_consumed": 0,
    "valid_alerts": 0,
    "invalid_alerts": 0,
    "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
    "alert_type_counts": {},
    "start_time": None
}


# ============================================================================
# Schema Validation
# ============================================================================

def load_schema():
    """Load the JSON schema"""
    try:
        with open(SCHEMA_PATH, 'r') as f:
            schema = json.load(f)
        print(f"✅ Loaded schema from: {SCHEMA_PATH}")
        return schema
    except Exception as e:
        print(f"⚠️  Could not load schema: {e}")
        print("   Continuing without validation...")
        return None


def validate_alert(alert_data, schema):
    """Validate alert against JSON schema"""
    if schema is None:
        return True, None
    
    try:
        validate(instance=alert_data, schema=schema)
        return True, None
    except ValidationError as e:
        return False, str(e.message)


# ============================================================================
# Alert Processing
# ============================================================================

def process_alert(alert_data, schema):
    """Process a consumed alert"""
    stats["total_consumed"] += 1
    
    # Validate
    is_valid, error = validate_alert(alert_data, schema)
    
    if is_valid:
        stats["valid_alerts"] += 1
        
        # Update statistics
        severity = alert_data.get("severity", "unknown")
        if severity in stats["severity_counts"]:
            stats["severity_counts"][severity] += 1
        
        alert_type = alert_data.get("alert_type", "unknown")
        stats["alert_type_counts"][alert_type] = stats["alert_type_counts"].get(alert_type, 0) + 1
        
        # Print alert summary
        print_alert_summary(alert_data)
        
    else:
        stats["invalid_alerts"] += 1
        print(f"\n❌ INVALID ALERT")
        print(f"   Alert ID: {alert_data.get('alert_id', 'UNKNOWN')}")
        print(f"   Error: {error}")
        print(f"   Raw data: {json.dumps(alert_data, indent=2)[:200]}...")


def print_alert_summary(alert):
    """Print a formatted summary of the alert"""
    severity_icons = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
        "info": "🔵"
    }
    
    icon = severity_icons.get(alert["severity"], "⚪")
    
    print(f"\n{icon} Alert #{stats['total_consumed']}")
    print(f"   ID: {alert['alert_id']}")
    print(f"   Type: {alert['alert_type']}")
    print(f"   Severity: {alert['severity'].upper()}")
    print(f"   Source: {alert['source']['system_name']} ({alert['source']['system_type']})")
    print(f"   Time: {alert['timestamp']}")
    print(f"   Description: {alert['description'][:80]}...")
    
    # Show affected assets
    if alert.get("affected_assets"):
        assets = [f"{a['asset_type']}:{a['asset_id']}" for a in alert['affected_assets'][:2]]
        print(f"   Assets: {', '.join(assets)}")
    
    # Show key indicators
    if alert.get("indicators"):
        indicators = alert["indicators"]
        if indicators.get("ip_addresses"):
            print(f"   IPs: {', '.join(indicators['ip_addresses'][:3])}")
        if indicators.get("domains"):
            print(f"   Domains: {', '.join(indicators['domains'][:2])}")
    
    # Show MITRE ATT&CK
    if alert.get("context", {}).get("mitre_techniques"):
        techniques = alert["context"]["mitre_techniques"][:2]
        print(f"   MITRE: {', '.join(techniques)}")


def print_statistics():
    """Print consumption statistics"""
    if stats["total_consumed"] == 0:
        return
    
    print("\n" + "=" * 80)
    print("📊 CONSUMPTION STATISTICS")
    print("=" * 80)
    
    # Calculate runtime
    if stats["start_time"]:
        runtime = (datetime.now() - stats["start_time"]).total_seconds()
        rate = stats["total_consumed"] / runtime if runtime > 0 else 0
        print(f"Runtime: {runtime:.1f}s | Rate: {rate:.2f} alerts/sec")
    
    print(f"Total Consumed: {stats['total_consumed']}")
    print(f"Valid: {stats['valid_alerts']} ({stats['valid_alerts']/stats['total_consumed']*100:.1f}%)")
    print(f"Invalid: {stats['invalid_alerts']} ({stats['invalid_alerts']/stats['total_consumed']*100:.1f}%)")
    
    # Severity distribution
    print("\n🔴 Severity Distribution:")
    for severity, count in stats["severity_counts"].items():
        if count > 0:
            pct = count / stats["total_consumed"] * 100
            bar = "█" * int(pct / 2)
            print(f"   {severity:8s}: {bar} {count:3d} ({pct:5.1f}%)")
    
    # Top alert types
    print("\n🎯 Top Alert Types:")
    sorted_types = sorted(stats["alert_type_counts"].items(), key=lambda x: x[1], reverse=True)
    for alert_type, count in sorted_types[:5]:
        pct = count / stats["total_consumed"] * 100
        print(f"   {alert_type:30s}: {count:3d} ({pct:5.1f}%)")
    
    print("=" * 80)


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n⏹️  Shutting down consumer...")
    print_statistics()
    sys.exit(0)



def main():
    """Main consumer loop"""
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 80)
    print("📥 SOAR Alert Consumer")
    print("=" * 80)
    print(f"📡 Kafka Broker: {KAFKA_BROKER}")
    print(f"📬 Topic: {KAFKA_TOPIC}")
    print(f"👥 Consumer Group: {CONSUMER_GROUP}")
    print(f"📋 Schema: {SCHEMA_PATH}")
    print("-" * 80)
    
    # Load schema
    schema = load_schema()
    
    # Initialize Kafka Consumer
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BROKER,
            group_id=CONSUMER_GROUP,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',  # Start from beginning if no offset
            enable_auto_commit=True,
            consumer_timeout_ms=1000  # Exit if no message for 1 second (for testing)
        )
        print("✅ Connected to Kafka")
        print("🎧 Listening for alerts... (Press Ctrl+C to stop)")
        print("=" * 80)
    except Exception as e:
        print(f"❌ Failed to connect to Kafka: {e}")
        return
    
    # Start timer
    stats["start_time"] = datetime.now()
    
    # Consumption loop
    try:
        for message in consumer:
            try:
                alert_data = message.value
                process_alert(alert_data, schema)
                
            except json.JSONDecodeError as e:
                print(f"❌ Failed to decode message: {e}")
            except Exception as e:
                print(f"❌ Error processing alert: {e}")
        
        # If we get here, consumer_timeout_ms was reached
        print("\n⏰ No more messages (timeout reached)")
        
    except KeyboardInterrupt:
        pass  # Handled by signal handler
    except Exception as e:
        print(f"\n❌ Consumer error: {e}")
    finally:
        consumer.close()
        print("\n👋 Consumer closed gracefully")
        print_statistics()



def consume_continuous():
    """Consume alerts continuously (no timeout)"""
    print("🔄 Running in CONTINUOUS mode (no timeout)")
    print("   Press Ctrl+C to stop")
    
    # Same as main but without consumer_timeout_ms
    signal.signal(signal.SIGINT, signal_handler)
    
    schema = load_schema()
    
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BROKER,
            group_id=CONSUMER_GROUP,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',  # Only new messages
            enable_auto_commit=True
        )
        print("✅ Connected to Kafka (continuous mode)")
        print("-" * 80)
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return
    
    stats["start_time"] = datetime.now()
    
    try:
        for message in consumer:
            alert_data = message.value
            process_alert(alert_data, schema)
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()
        print_statistics()


def consume_latest(count=10):
    """Consume only the latest N alerts"""
    print(f"📊 Consuming latest {count} alerts...")
    
    schema = load_schema()
    
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BROKER,
            group_id=f"{CONSUMER_GROUP}-latest-{datetime.now().timestamp()}",
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='latest',
            enable_auto_commit=False,
            consumer_timeout_ms=5000
        )
        print("✅ Connected to Kafka")
        print("-" * 80)
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return
    
    stats["start_time"] = datetime.now()
    consumed = 0
    
    try:
        for message in consumer:
            alert_data = message.value
            process_alert(alert_data, schema)
            consumed += 1
            if consumed >= count:
                break
    except:
        pass
    finally:
        consumer.close()
        print_statistics()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "continuous":
            consume_continuous()
        elif mode == "latest":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            consume_latest(count)
        else:
            print("Usage:")
            print("  python consume_alerts.py              # Consume all (with timeout)")
            print("  python consume_alerts.py continuous   # Continuous mode (no timeout)")
            print("  python consume_alerts.py latest [N]   # Latest N alerts (default: 10)")
    else:
        main()