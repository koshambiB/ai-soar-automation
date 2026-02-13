"""
Feature Extraction for ML Pipeline
Converts raw alerts into numerical features
"""

from typing import Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FeatureExtractor:
    
    # Encoding mappings - avoid collisions with 'unknown' values
    SEVERITY_ENCODING = {
        'info': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4, 'unknown': 99
    }
    
    ALERT_TYPE_ENCODING = {
        'policy_violation': 0, 'reconnaissance': 1, 'anomalous_behavior': 2,
        'suspicious_login': 3, 'phishing': 4, 'vulnerability_exploit': 5,
        'intrusion_attempt': 6, 'brute_force': 7, 'ddos': 8,
        'malware_detection': 9, 'lateral_movement': 10, 'privilege_escalation': 11,
        'command_and_control': 12, 'data_leak': 13, 'insider_threat': 14,
        'data_exfiltration': 15, 'ransomware': 16, 'other': 17, 'unknown': 99
    }
    
    SYSTEM_TYPE_ENCODING = {
        'SIEM': 0, 'IDS': 1, 'IPS': 2, 'EDR': 3, 'Firewall': 4,
        'Email Gateway': 5, 'DLP': 6, 'Cloud Security': 7, 'Custom': 8, 'unknown': 99
    }
    
    ASSET_CRITICALITY_ENCODING = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3, 'unknown': 99}
    
    FP_LIKELIHOOD_ENCODING = {'low': 0, 'medium': 1, 'high': 2, 'unknown': 99}
    
    def extract_features(self, alert: Dict) -> Dict:
        """
        Extract ML-ready features from alert
        Returns dictionary of numerical features
        """
        try:
            features = {}
            
            # Basic alert features
            features['severity_encoded'] = self.SEVERITY_ENCODING.get(
                alert.get('severity'), 
                self.SEVERITY_ENCODING['unknown']
            )
            features['alert_type_encoded'] = self.ALERT_TYPE_ENCODING.get(
                alert.get('alert_type'), 
                self.ALERT_TYPE_ENCODING['unknown']
            )
            
            # Source system features
            source = alert.get('source', {})
            features['system_type_encoded'] = self.SYSTEM_TYPE_ENCODING.get(
                source.get('system_type'), 
                self.SYSTEM_TYPE_ENCODING['unknown']
            )
            
            # Temporal features
            features.update(self._extract_temporal_features(alert.get('timestamp', '')))
            
            # Context features
            context = alert.get('context', {})
            features['confidence_score'] = float(context.get('confidence_score', 0.5))
            features['fp_likelihood_encoded'] = self.FP_LIKELIHOOD_ENCODING.get(
                context.get('false_positive_likelihood', 'medium'), 
                self.FP_LIKELIHOOD_ENCODING['medium']
            )
            features['mitre_tactic_count'] = len(context.get('mitre_tactics', []))
            features['mitre_technique_count'] = len(context.get('mitre_techniques', []))
            
            # Metrics features - safe type conversion
            metrics = alert.get('metrics', {})
            features['event_count'] = int(metrics.get('event_count', 1))
            features['failed_attempts'] = int(metrics.get('failed_attempts', 0))
            features['duration_seconds'] = int(metrics.get('duration_seconds', 0))
            
            # Safe data volume conversion (handles strings and None)
            data_volume = metrics.get('data_volume_bytes', 0)
            try:
                features['data_volume_mb'] = float(data_volume) / 1048576 if data_volume else 0.0
            except (ValueError, TypeError):
                features['data_volume_mb'] = 0.0
            
            # Indicator features (IOC richness)
            indicators = alert.get('indicators', {})
            features['has_ip_addresses'] = 1 if indicators.get('ip_addresses') else 0
            features['has_domains'] = 1 if indicators.get('domains') else 0
            features['has_file_hashes'] = 1 if indicators.get('file_hashes') else 0
            features['has_urls'] = 1 if indicators.get('urls') else 0
            features['has_email_addresses'] = 1 if indicators.get('email_addresses') else 0
            features['has_processes'] = 1 if indicators.get('processes') else 0
            features['ioc_diversity'] = sum([
                features['has_ip_addresses'],
                features['has_domains'],
                features['has_file_hashes'],
                features['has_urls'],
                features['has_email_addresses'],
                features['has_processes']
            ])
            
            # Asset features
            metadata = alert.get('metadata', {})
            features['asset_criticality_encoded'] = self.ASSET_CRITICALITY_ENCODING.get(
                metadata.get('asset_criticality', 'medium'), 
                self.ASSET_CRITICALITY_ENCODING['medium']
            )
            features['affected_asset_count'] = len(alert.get('affected_assets', []))
            
            # Tag features
            tags = alert.get('tags', [])
            features['has_production_tag'] = 1 if 'production' in tags else 0
            features['has_after_hours_tag'] = 1 if 'after-hours' in tags else 0
            features['tag_count'] = len(tags)
            
            return features
        
        except Exception as e:
            logger.error(f"Feature extraction failed for alert {alert.get('alert_id', 'UNKNOWN')}: {e}")
            return self._get_default_features()
    
    def _extract_temporal_features(self, timestamp_str: str) -> Dict:
        """Extract time-based features"""
        try:
            # Parse ISO 8601 timestamp
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            return {
                'hour_of_day': dt.hour,
                'day_of_week': dt.weekday(),  # 0=Monday, 6=Sunday
                'is_weekend': 1 if dt.weekday() >= 5 else 0,
                'is_after_hours': 1 if dt.hour < 6 or dt.hour > 22 else 0
            }
        except Exception as e:
            logger.debug(f"Temporal feature extraction failed: {e}, using defaults")
            return {
                'hour_of_day': 12,
                'day_of_week': 2,
                'is_weekend': 0,
                'is_after_hours': 0
            }
    
    def _get_default_features(self) -> Dict:
        """Return default features if extraction fails"""
        return {
            'severity_encoded': self.SEVERITY_ENCODING['unknown'],
            'alert_type_encoded': self.ALERT_TYPE_ENCODING['unknown'],
            'system_type_encoded': self.SYSTEM_TYPE_ENCODING['unknown'],
            'hour_of_day': 12,
            'day_of_week': 2,
            'is_weekend': 0,
            'is_after_hours': 0,
            'confidence_score': 0.5,
            'fp_likelihood_encoded': self.FP_LIKELIHOOD_ENCODING['medium'],
            'mitre_tactic_count': 0,
            'mitre_technique_count': 0,
            'event_count': 1,
            'failed_attempts': 0,
            'duration_seconds': 0,
            'data_volume_mb': 0.0,
            'has_ip_addresses': 0,
            'has_domains': 0,
            'has_file_hashes': 0,
            'has_urls': 0,
            'has_email_addresses': 0,
            'has_processes': 0,
            'ioc_diversity': 0,
            'asset_criticality_encoded': self.ASSET_CRITICALITY_ENCODING['medium'],
            'affected_asset_count': 0,
            'has_production_tag': 0,
            'has_after_hours_tag': 0,
            'tag_count': 0
        }