from psycopg.types.json import Jsonb
from datetime import datetime

def insert_alert(cursor, alert_dict):
    """
    Insert alert into database.
    Returns inserted row id or None if duplicate.
    """
    query = """
    INSERT INTO alerts (
        alert_id, alert_timestamp, severity, source, alert_type, raw_data, status, created_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (alert_id) DO NOTHING
    RETURNING id;
    """
    
    values = (
        alert_dict['alert_id'],
        alert_dict['timestamp'],
        alert_dict['severity'],
        alert_dict['source']['system_name'],  # Extract system_name from source dict
        alert_dict['alert_type'],  # Changed from 'type'
        Jsonb(alert_dict),
        'new',
        datetime.utcnow()
    )
    
    cursor.execute(query, values)
    result = cursor.fetchone()
    return result['id'] if result else None

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