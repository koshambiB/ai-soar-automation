from backend.app.analysis.rule_engine import RuleEngine

def test_ransomware_matches_rules():
    sample_alert = {
        "alert_id": "A-1001",
        "alert_type": "ransomware",
        "severity": "critical",
        "timestamp": "2026-02-01T22:45:00Z",
        "source": {
            "system_type": "EDR"
        }
    }

    engine = RuleEngine("configs/rules.yaml")
    matched_rules = engine.match_rules(sample_alert)

    # Assertions (this is what pytest needs)
    assert len(matched_rules) >= 1

    rule_ids = [r["rule_id"] for r in matched_rules]
    assert "R001" in rule_ids  # ransomware rule
