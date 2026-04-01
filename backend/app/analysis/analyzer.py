"""
Alert Analyzer - Main Analysis Pipeline
Orchestrates rule matching, feature extraction, and risk scoring
"""
import os
import yaml
from pathlib import Path
from typing import Dict, List
import logging
from .rule_engine import RuleEngine
from .feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)

class AlertAnalyzer:
    def __init__(self,
             rules_path: str = None,
                weights_path: str = None):
        """Initialize analyzer with rule engine and feature extractor"""
        # Resolve paths relative to project root regardless of cwd
        _root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        if rules_path is None:
            rules_path = os.path.join(_root, "configs", "rules.yaml")
        if weights_path is None:
            weights_path = os.path.join(_root, "configs", "weights.yaml")
        
        self.rule_engine = RuleEngine(rules_path)
        self.feature_extractor = FeatureExtractor()
        self.weights = self._load_weights(weights_path)
        logger.info("AlertAnalyzer initialized successfully")
    
    def _load_weights(self, path: str) -> Dict:
        """Load scoring weights from YAML"""
        try:
            with open(path, 'r') as f:
                weights = yaml.safe_load(f)
            logger.info(f"Loaded weights from {path}")
            return weights
        except Exception as e:
            logger.error(f"Failed to load weights: {e}, using defaults")
            return self._get_default_weights()
    
    def _get_default_weights(self) -> Dict:
        """Return default weights if loading fails"""
        return {
            'risk_thresholds': {
                'critical': 80,
                'high': 60,
                'medium': 40,
                'low': 20
            }
        }
    
    def analyze_alert(self, alert: Dict) -> Dict:
        """
        Complete analysis pipeline for a single alert
        
        Returns:
        {
            'alert_id': str,
            'rule_score': int,
            'risk_level': str,
            'matched_rules': List[str],
            'matched_rule_count': int,
            'highest_priority_rule': Dict,
            'features': Dict,
            'recommendations': List[str]
        }
        """
        alert_id = alert.get('alert_id', 'UNKNOWN')
        
        try:
            logger.info(f"Starting analysis for alert {alert_id}")
            
            # Step 1: Extract features
            features = self.feature_extractor.extract_features(alert)
            logger.debug(f"Extracted {len(features)} features for {alert_id}")
            
            # Step 2: Match rules
            matched_rules = self.rule_engine.match_rules(alert)
            logger.info(f"Alert {alert_id} matched {len(matched_rules)} rule(s)")
            
            # Step 3: Get highest scoring rule
            highest_rule = self.rule_engine.get_highest_scoring_rule(matched_rules)
            
            # Step 4: Calculate final risk score
            rule_score = highest_rule['score']
            
            # Step 5: Determine risk level from score
            risk_level = self._classify_risk_level(rule_score)
            
            # Step 6: Generate recommendations
            recommendations = self._generate_recommendations(
                alert, 
                matched_rules, 
                risk_level
            )
            
            result = {
                'alert_id': alert_id,
                'rule_score': rule_score,
                'risk_level': risk_level,
                'matched_rules': [r['rule_id'] for r in matched_rules],
                'matched_rule_count': len(matched_rules),
                'highest_priority_rule': highest_rule,
                'features': features,
                'recommendations': recommendations
            }
            
            logger.info(f"Analysis complete for {alert_id}: risk={risk_level}, score={rule_score}")
            return result
        
        except Exception as e:
            logger.error(f"Analysis failed for alert {alert_id}: {e}")
            return self._get_failed_analysis(alert_id)
    
    def _classify_risk_level(self, score: int) -> str:
        """
        Map numerical score to risk level
        Uses thresholds from weights.yaml
        """
        thresholds = self.weights.get('risk_thresholds', {})
        
        if score >= thresholds.get('critical', 80):
            return 'critical'
        elif score >= thresholds.get('high', 60):
            return 'high'
        elif score >= thresholds.get('medium', 40):
            return 'medium'
        elif score >= thresholds.get('low', 20):
            return 'low'
        else:
            return 'info'
    
    def _generate_recommendations(self, 
                                  alert: Dict, 
                                  matched_rules: List[Dict], 
                                  risk_level: str) -> List[str]:
        """
        Generate recommended actions based on alert and matched rules
        Returns list of playbook names or actions
        """
        recommendations = []
        alert_type = alert.get('alert_type', '')
        
        # Critical risk - immediate action
        if risk_level == 'critical':
            recommendations.append('notify_soc_lead')
            
            if alert_type == 'ransomware':
                recommendations.extend(['isolate_host', 'disable_user_account', 'backup_forensics'])
            elif alert_type == 'data_exfiltration':
                recommendations.extend(['block_destination_ip', 'isolate_host', 'preserve_logs'])
            else:
                recommendations.append('isolate_host')
        
        # High risk - containment
        elif risk_level == 'high':
            recommendations.append('notify_analyst')
            
            if alert_type == 'malware_detection':
                recommendations.extend(['quarantine_file', 'scan_endpoint'])
            elif alert_type == 'brute_force':
                recommendations.extend(['block_source_ip', 'reset_password'])
            elif alert_type == 'privilege_escalation':
                recommendations.extend(['disable_user_account', 'audit_permissions'])
            else:
                recommendations.append('investigate_further')
        
        # Medium risk - monitoring
        elif risk_level == 'medium':
            recommendations.append('create_ticket')
            
            if alert_type == 'phishing':
                recommendations.extend(['quarantine_email', 'notify_user'])
            elif alert_type == 'suspicious_login':
                recommendations.extend(['verify_user_identity', 'monitor_account'])
            else:
                recommendations.append('monitor_activity')
        
        # Low risk - log and review
        else:
            recommendations.extend(['log_event', 'periodic_review'])
        
        return recommendations
    
    def _get_failed_analysis(self, alert_id: str) -> Dict:
        """Return safe default when analysis fails"""
        return {
            'alert_id': alert_id,
            'rule_score': 0,
            'risk_level': 'info',
            'matched_rules': [],
            'matched_rule_count': 0,
            'highest_priority_rule': {
                'rule_id': 'ANALYSIS_FAILED',
                'name': 'Analysis Failed',
                'score': 0,
                'risk_level': 'info'
            },
            'features': self.feature_extractor._get_default_features(),
            'recommendations': ['manual_review']
        }