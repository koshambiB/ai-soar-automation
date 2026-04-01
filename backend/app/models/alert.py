"""
Alert Data Model
Handles alert persistence with analysis results
"""

from psycopg.types.json import Jsonb
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def insert_alert(cursor, alert_dict, analysis_results=None, **kwargs):
    """
    Insert alert with optional analysis results
    Returns inserted row id or None if duplicate
    
    Args:
        alert_dict: Raw alert data
        analysis_results: Optional dict from AlertAnalyzer
    """
    query = """
    INSERT INTO alerts (
        alert_id, alert_timestamp, severity, source, alert_type, 
        raw_data, status, rule_score, risk_level, features, created_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (alert_id) DO NOTHING
    RETURNING id;
    """
    
    # Extract analysis results if provided
    if analysis_results:
        rule_score = analysis_results.get('rule_score')
        risk_level = analysis_results.get('risk_level')
        features = analysis_results.get('features')
        status = 'analyzed'
    else:
        rule_score = None
        risk_level = None
        features = None
        status = 'new'
    
    values = (
        alert_dict['alert_id'],
        alert_dict['timestamp'],
        alert_dict['severity'],
        alert_dict['source']['system_name'],
        alert_dict['alert_type'],
        Jsonb(alert_dict),
        status,
        rule_score,
        risk_level,
        Jsonb(features) if features else None,
        datetime.utcnow()
    )
    
    try:
        cursor.execute(query, values)
        result = cursor.fetchone()
        return result['id'] if result else None
    except Exception as e:
        logger.error(f"Failed to insert alert {alert_dict.get('alert_id')}: {e}")
        raise

def get_alert_by_id(cursor, alert_id):
    """Retrieve alert by alert_id"""
    query = "SELECT * FROM alerts WHERE alert_id = %s;"
    cursor.execute(query, (alert_id,))
    return cursor.fetchone()

def get_recent_alerts(cursor, limit=100):
    """Retrieve recent alerts"""
    query = "SELECT * FROM alerts ORDER BY created_at DESC LIMIT %s;"
    cursor.execute(query, (limit,))
    return cursor.fetchall()

def get_alerts_by_risk_level(cursor, risk_level, limit=50):
    """Retrieve alerts by risk level"""
    query = """
    SELECT * FROM alerts 
    WHERE risk_level = %s 
    ORDER BY created_at DESC 
    LIMIT %s;
    """
    cursor.execute(query, (risk_level, limit))
    return cursor.fetchall()

def get_high_risk_alerts(cursor, min_score=60, limit=50):
    """Retrieve high-risk alerts above threshold"""
    query = """
    SELECT * FROM alerts 
    WHERE rule_score >= %s 
    ORDER BY rule_score DESC, created_at DESC 
    LIMIT %s;
    """
    cursor.execute(query, (min_score, limit))
    return cursor.fetchall()