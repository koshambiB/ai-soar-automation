"""
Alert Producer for SOAR System
Generates realistic security alerts matching schemas/alert_schema.json
Publishes to Kafka topic: soar-alerts
"""

import json
import random
import time
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from confluent_kafka import Producer
from faker import Faker

fake = Faker()

# Kafka Configuration
KAFKA_BROKER = 'localhost:9092'
KAFKA_TOPIC = 'soar-alerts'

# Load schema for validation (optional but good practice)
SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "alert_schema.json"



SYSTEM_TYPES = {
    "SIEM": ["Splunk-SIEM-Prod", "QRadar-Enterprise", "Sentinel-Cloud"],
    "IDS": ["Snort-DMZ", "Suricata-Core"],
    "IPS": ["Palo-Alto-IPS", "Cisco-Firepower"],
    "EDR": ["CrowdStrike-EDR-Prod", "SentinelOne-Fleet", "Carbon-Black"],
    "Firewall": ["Cisco-ASA-01", "Fortinet-FW-DMZ", "Palo-Alto-NGFW"],
    "Email Gateway": ["Proofpoint-Gateway", "Mimecast-Secure"],
    "DLP": ["Symantec-DLP", "Forcepoint-DLP"],
    "Cloud Security": ["AWS-GuardDuty", "Azure-Defender", "GCP-SecurityCenter"]
}

SEVERITIES = ["critical", "high", "medium", "low", "info"]

ALERT_TYPES = [
    "malware_detection",
    "intrusion_attempt",
    "brute_force",
    "data_exfiltration",
    "privilege_escalation",
    "lateral_movement",
    "phishing",
    "anomalous_behavior",
    "policy_violation",
    "vulnerability_exploit",
    "ddos",
    "reconnaissance",
    "command_and_control",
    "ransomware",
    "suspicious_login",
    "data_leak",
    "insider_threat"
]

ATTACK_PHASES = [
    "reconnaissance",
    "weaponization",
    "delivery",
    "exploitation",
    "installation",
    "command_and_control",
    "actions_on_objectives"
]

MITRE_TACTICS = [
    "TA0001 - Initial Access",
    "TA0002 - Execution",
    "TA0003 - Persistence",
    "TA0004 - Privilege Escalation",
    "TA0005 - Defense Evasion",
    "TA0006 - Credential Access",
    "TA0007 - Discovery",
    "TA0008 - Lateral Movement",
    "TA0009 - Collection",
    "TA0010 - Exfiltration",
    "TA0011 - Command and Control",
    "TA0040 - Impact"
]

MITRE_TECHNIQUES = [
    "T1078 - Valid Accounts",
    "T1110.001 - Password Guessing",
    "T1110.003 - Password Spraying",
    "T1059.001 - PowerShell",
    "T1071.001 - Web Protocols",
    "T1486 - Data Encrypted for Impact",
    "T1566.001 - Spearphishing Attachment",
    "T1053.005 - Scheduled Task",
    "T1543.003 - Windows Service",
    "T1055 - Process Injection"
]



def generate_alert_id():
    """Generate unique alert ID matching pattern: ALT-[A-Z0-9]{8,16}"""
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    length = random.randint(8, 16)
    return f"ALT-{''.join(random.choices(chars, k=length))}"


def generate_timestamp():
    """Generate ISO 8601 timestamp (recent past to now)"""
    minutes_ago = random.randint(0, 60)
    ts = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_source():
    """Generate source system information"""
    system_type = random.choice(list(SYSTEM_TYPES.keys()))
    system_name = random.choice(SYSTEM_TYPES[system_type])
    
    return {
        "system_name": system_name,
        "system_type": system_type,
        "system_id": f"{system_type.lower()}-node-{random.randint(1, 10):02d}"
    }


def generate_affected_assets(alert_type):
    """Generate affected assets based on alert type"""
    assets = []
    
    # Always include a host
    assets.append({
        "asset_type": "host",
        "asset_id": f"{'prod' if random.random() > 0.3 else 'dev'}-{random.choice(['web', 'db', 'app', 'file'])}-{random.randint(1, 50):02d}",
        "asset_details": {
            "hostname": fake.hostname(),
            "ip": fake.ipv4_private(),
            "os": random.choice([
                "Ubuntu 22.04",
                "Windows Server 2022",
                "Windows 10 Enterprise",
                "RHEL 8.5",
                "macOS Ventura"
            ])
        }
    })
    
    # Add user for login-related alerts
    if alert_type in ["brute_force", "suspicious_login", "privilege_escalation", "insider_threat"]:
        assets.append({
            "asset_type": "user",
            "asset_id": fake.user_name(),
            "asset_details": {
                "email": fake.email(),
                "department": random.choice(["Finance", "IT", "HR", "Engineering", "Sales"])
            }
        })
    
    # Add IP for network-based alerts
    if alert_type in ["intrusion_attempt", "ddos", "reconnaissance", "command_and_control"]:
        assets.append({
            "asset_type": "ip_address",
            "asset_id": fake.ipv4(),
            "asset_details": {
                "is_internal": random.choice([True, False]),
                "country": fake.country_code() if random.random() > 0.5 else None
            }
        })
    
    return assets


def generate_indicators(alert_type):
    """Generate IoCs based on alert type"""
    indicators = {}
    
    # Always include some IPs
    indicators["ip_addresses"] = [fake.ipv4() for _ in range(random.randint(1, 3))]
    
    # Malware/ransomware gets file hashes
    if alert_type in ["malware_detection", "ransomware", "vulnerability_exploit"]:
        indicators["file_hashes"] = {
            "sha256": [hashlib.sha256(fake.binary(32)).hexdigest() for _ in range(random.randint(1, 2))]
        }
        indicators["processes"] = [
            random.choice([
                "powershell.exe",
                "cmd.exe",
                "rundll32.exe",
                "regsvr32.exe",
                "/usr/bin/wget",
                "/tmp/suspicious.sh"
            ])
        ]
    
    # Phishing/C2 gets domains and URLs
    if alert_type in ["phishing", "command_and_control", "data_leak"]:
        indicators["domains"] = [fake.domain_name() for _ in range(random.randint(1, 2))]
        indicators["urls"] = [f"http://{fake.domain_name()}/{fake.uri_path()}" for _ in range(random.randint(1, 2))]
    
    # Email-based alerts
    if alert_type in ["phishing", "insider_threat"]:
        indicators["email_addresses"] = [fake.email() for _ in range(random.randint(1, 2))]
    
    return indicators


def generate_context(alert_type, severity):
    """Generate contextual information"""
    context = {
        "attack_phase": random.choice(ATTACK_PHASES),
        "mitre_tactics": random.sample(MITRE_TACTICS, k=random.randint(1, 3)),
        "mitre_techniques": random.sample(MITRE_TECHNIQUES, k=random.randint(1, 2)),
        "confidence_score": round(random.uniform(0.6, 0.99), 2),
        "false_positive_likelihood": random.choice(["low", "medium", "high"])
    }
    
    # Higher severity = higher confidence, lower FP likelihood
    if severity in ["critical", "high"]:
        context["confidence_score"] = round(random.uniform(0.85, 0.99), 2)
        context["false_positive_likelihood"] = random.choice(["low", "medium"])
    
    return context


def generate_metrics(alert_type):
    """Generate quantitative metrics"""
    metrics = {
        "event_count": random.randint(1, 500)
    }
    
    if alert_type in ["brute_force", "suspicious_login"]:
        metrics["failed_attempts"] = random.randint(5, 100)
        metrics["duration_seconds"] = random.randint(60, 3600)
    
    if alert_type in ["data_exfiltration", "data_leak"]:
        metrics["data_volume_bytes"] = random.randint(1048576, 107374182)  # 1MB to 100MB
        metrics["duration_seconds"] = random.randint(300, 7200)
    
    if alert_type == "ddos":
        metrics["event_count"] = random.randint(10000, 1000000)
        metrics["duration_seconds"] = random.randint(60, 1800)
    
    return metrics


def generate_full_alert():
    """Generate a complete security alert matching the schema"""
    alert_type = random.choice(ALERT_TYPES)
    severity = random.choice(SEVERITIES)
    source = generate_source()
    
    alert = {
        "alert_id": generate_alert_id(),
        "timestamp": generate_timestamp(),
        "source": source,
        "severity": severity,
        "alert_type": alert_type,
        "description": generate_description(alert_type, severity),
        "affected_assets": generate_affected_assets(alert_type),
        "indicators": generate_indicators(alert_type),
        "context": generate_context(alert_type, severity),
        "metrics": generate_metrics(alert_type),
        "tags": generate_tags(alert_type, severity),
        "metadata": {
            "compliance_frameworks": random.sample(["PCI-DSS", "HIPAA", "GDPR", "SOX", "ISO27001"], k=random.randint(1, 2)),
            "business_unit": random.choice(["Finance", "IT", "HR", "Engineering", "Sales", "Operations"]),
            "asset_criticality": random.choice(["critical", "high", "medium", "low"])
        }
    }
    
    # Add raw_log for some alerts
    if random.random() > 0.5:
        alert["raw_log"] = generate_raw_log(alert_type)
    
    return alert


def generate_description(alert_type, severity):
    """Generate human-readable description"""
    descriptions = {
        "brute_force": f"Multiple failed authentication attempts detected from {fake.ipv4()}",
        "malware_detection": f"Malicious file detected: {hashlib.md5(fake.binary(16)).hexdigest()[:8]}.exe",
        "data_exfiltration": f"Unusual outbound data transfer to {fake.domain_name()} detected",
        "privilege_escalation": f"Unauthorized privilege escalation attempt by user {fake.user_name()}",
        "phishing": f"Phishing email detected with malicious link to {fake.domain_name()}",
        "ransomware": f"Ransomware encryption activity detected on {fake.hostname()}",
        "suspicious_login": f"Login from unusual location: {fake.country()} ({fake.ipv4()})",
        "ddos": f"Distributed denial of service attack detected - {random.randint(10000, 100000)} requests/sec",
        "command_and_control": f"C2 beacon activity detected to {fake.domain_name()}",
        "intrusion_attempt": f"Network intrusion attempt from {fake.ipv4()} on port {random.choice([22, 3389, 445])}"
    }
    
    base_desc = descriptions.get(alert_type, f"{alert_type.replace('_', ' ').title()} detected")
    return f"[{severity.upper()}] {base_desc}"


def generate_tags(alert_type, severity):
    """Generate relevant tags"""
    tags = [alert_type, severity]
    
    # Add environment tags
    tags.append(random.choice(["production", "staging", "development"]))
    
    # Add time-based tags
    hour = datetime.now().hour
    if hour < 6 or hour > 22:
        tags.append("after-hours")
    
    # Add specific tags based on type
    if alert_type in ["malware_detection", "ransomware"]:
        tags.append("endpoint-security")
    
    if alert_type in ["brute_force", "suspicious_login"]:
        tags.append("authentication")
    
    return tags


def generate_raw_log(alert_type):
    """Generate sample raw log entry"""
    logs = {
        "brute_force": f"Jan 10 {datetime.now().strftime('%H:%M:%S')} sshd[{random.randint(10000, 99999)}]: Failed password for {fake.user_name()} from {fake.ipv4()} port {random.randint(40000, 60000)} ssh2",
        "malware_detection": f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ALERT: Malware detected - File: C:\\Users\\{fake.user_name()}\\Downloads\\malicious.exe, Signature: Trojan.Generic",
        "data_exfiltration": f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Firewall: ALLOW outbound {fake.ipv4_private()}:{random.randint(40000, 60000)} -> {fake.ipv4()}:443 (bytes: {random.randint(1000000, 10000000)})"
    }
    
    return logs.get(alert_type, f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Security event: {alert_type}")


def delivery_report(err, msg):
    """Callback for message delivery reports"""
    if err is not None:
        print(f'❌ Message delivery failed: {err}')


def main():
    """Main producer loop"""
    print("=" * 80)
    print("🚀 SOAR Alert Producer")
    print("=" * 80)
    print(f"📡 Kafka Broker: {KAFKA_BROKER}")
    print(f"📬 Topic: {KAFKA_TOPIC}")
    print(f"📋 Schema: {SCHEMA_PATH}")
    print("-" * 80)
    
    # Initialize Kafka Producer
    try:
        producer_config = {
            'bootstrap.servers': KAFKA_BROKER,
            'compression.type': 'gzip'
        }
        producer = Producer(producer_config)
        print("✅ Connected to Kafka")
        print("-" * 80)
    except Exception as e:
        print(f"❌ Failed to connect to Kafka: {e}")
        return
    
    # Production loop
    count = 0
    try:
        while True:
            # Generate alert
            alert = generate_full_alert()
            
            # Send to Kafka
            producer.produce(
                KAFKA_TOPIC,
                value=json.dumps(alert).encode('utf-8'),
                callback=delivery_report
            )
            producer.poll(0)  # Trigger callbacks
            
            count += 1
            
            # Pretty print
            print(f"✅ [{count:4d}] {alert['alert_id']:20s} | "
                  f"{alert['alert_type']:25s} | "
                  f"{alert['severity']:8s} | "
                  f"{alert['source']['system_type']:15s}")
            
            # Random delay (1-5 seconds)
            time.sleep(random.uniform(1, 5))
            
    except KeyboardInterrupt:
        print("\n" + "-" * 80)
        print(f"⏹️  Stopping producer...")
        print(f"📊 Total alerts produced: {count}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        producer.flush()  # Wait for outstanding messages
        print("👋 Producer closed gracefully")
        print("=" * 80)


if __name__ == "__main__":
    main()