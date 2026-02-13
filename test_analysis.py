"""
Quick test of the analysis pipeline
"""

import json
from backend.app.analysis.analyzer import AlertAnalyzer

# Load a sample alert
with open('data/samples/brute_force_ssh.json', 'r') as f:
    alert = json.load(f)

# Initialize analyzer
print("Initializing analyzer...")
analyzer = AlertAnalyzer()

# Analyze the alert
print("\nAnalyzing alert...")
result = analyzer.analyze_alert(alert)

# Print results
print("="*80)
print(f"Alert ID: {result['alert_id']}")
print(f"Risk Score: {result['rule_score']}")
print(f"Risk Level: {result['risk_level']}")
print(f"Matched Rules: {result['matched_rules']}")
print(f"Rule Count: {result['matched_rule_count']}")
print(f"Recommendations: {result['recommendations']}")
print("="*80)
print(f"\nHighest Priority Rule:")
print(f"  ID: {result['highest_priority_rule']['rule_id']}")
print(f"  Name: {result['highest_priority_rule']['name']}")
print(f"  Score: {result['highest_priority_rule']['score']}")
print("="*80)
print(f"\nExtracted Features (first 10):")
features = list(result['features'].items())[:10]
for key, value in features:
    print(f"  {key}: {value}")
print("="*80)