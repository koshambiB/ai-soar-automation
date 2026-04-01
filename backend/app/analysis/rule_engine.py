"""
Rule Engine for Alert Analysis
Matches alerts against YAML-defined rules
Returns ALL matching rules for aggregation
"""
import os
import yaml
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class RuleEngine:
    def __init__(self, rules_path: str = None):

        if rules_path is None:
            _root = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "..", "..")
            )
            rules_path = os.path.join(_root, "configs", "rules.yaml")

        # ✅ ALWAYS initialize rules
        self.rules = self._load_rules(rules_path)

        logger.info(f"Loaded {len(self.rules)} rules from {rules_path}")
    
    def _load_rules(self, path: str) -> List[Dict]:
        """Load and validate rules from YAML"""
        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
            
            rules = config.get('rules', [])
            
            # Filter enabled rules and sort by priority
            enabled_rules = [r for r in rules if r.get('enabled', True)]
            enabled_rules.sort(key=lambda r: r.get('priority', 999))
            
            return enabled_rules
        
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            return []
    
    def match_rules(self, alert: Dict) -> List[Dict]:
        """
        Find ALL rules that match this alert
        Returns list of matched rules with scores
        Multiple rules can match - Analyzer decides final outcome
        """
        matched = []
        
        for rule in self.rules:
            if self._rule_matches(rule, alert):
                matched.append({
                    'rule_id': rule['rule_id'],
                    'name': rule['name'],
                    'score': rule['score'],
                    'risk_level': rule['risk_level'],
                    'description': rule.get('description', ''),
                    'priority': rule.get('priority', 999)
                })
                logger.debug(f"Rule {rule['rule_id']} matched alert {alert.get('alert_id', 'UNKNOWN')}")
        
        if matched:
            logger.info(f"Alert {alert.get('alert_id', 'UNKNOWN')} matched {len(matched)} rule(s)")
        else:
            logger.warning(f"Alert {alert.get('alert_id', 'UNKNOWN')} matched NO rules")
        
        return matched
    
    def _rule_matches(self, rule: Dict, alert: Dict) -> bool:
        """Check if a rule matches an alert"""
        match_conditions = rule.get('match', {})
        
        for key, expected_value in match_conditions.items():
            # Handle special matching operators
            if key.endswith('_any'):
                # severity_any: check if value is in list
                field_name = key[:-4]  # Remove '_any' suffix
                actual_value = self._get_nested_value(alert, field_name)
                
                if actual_value not in expected_value:
                    return False
            
            else:
                # Exact match
                actual_value = self._get_nested_value(alert, key)
                
                if actual_value != expected_value:
                    return False
        
        return True
    
    def _get_nested_value(self, alert: Dict, key: str):
        """
        Get value from nested dict using dot notation
        Example: 'source.system_type' → alert['source']['system_type']
        """
        keys = key.split('.')
        value = alert
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return None
            else:
                return None
        
        return value
    
    def get_highest_scoring_rule(self, matched_rules: List[Dict]) -> Dict:
        """
        Get the highest scoring matched rule
        Used by Analyzer for final risk determination
        """
        if not matched_rules:
            return {
                'rule_id': 'NO_MATCH',
                'name': 'No Rules Matched',
                'score': 0,
                'risk_level': 'info',
                'description': 'Alert did not match any detection rules'
            }
        
        return max(matched_rules, key=lambda r: r['score'])