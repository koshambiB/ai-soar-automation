import psycopg
import sys

SCHEMA_SQL = """
-- Drop existing table if exists
DROP TABLE IF EXISTS alerts CASCADE;

-- Create alerts table
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(255) UNIQUE NOT NULL,
    alert_timestamp TIMESTAMP NOT NULL,
    severity VARCHAR(50) NOT NULL,
    source VARCHAR(255) NOT NULL,
    alert_type VARCHAR(100) NOT NULL,
    raw_data JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'new',
    rule_score INTEGER DEFAULT NULL,
    ml_prediction VARCHAR(50) DEFAULT NULL,
    ml_confidence FLOAT DEFAULT NULL,
    risk_level VARCHAR(50) DEFAULT NULL,
    explanation TEXT DEFAULT NULL,
    features JSONB DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_alert_id ON alerts(alert_id);
CREATE INDEX idx_alert_timestamp ON alerts(alert_timestamp);
CREATE INDEX idx_severity ON alerts(severity);
CREATE INDEX idx_status ON alerts(status);
CREATE INDEX idx_raw_data ON alerts USING GIN(raw_data);

-- Create function to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger
CREATE TRIGGER update_alerts_updated_at 
BEFORE UPDATE ON alerts
FOR EACH ROW 
EXECUTE FUNCTION update_updated_at_column();
"""

def init_database():
    conn = None
    try:
        print("Connecting to PostgreSQL...")
        conn = psycopg.connect(
            host="127.0.0.1",
            port=5432,
            dbname="soar_db",
            user="soar_user",
            password="soar_password"
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Creating schema...")
        cursor.execute(SCHEMA_SQL)
        
        print("Verifying tables...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        
        print(f"✓ Database initialized successfully!")
        print(f"✓ Tables created: {[t[0] for t in tables]}")
        
        cursor.close()
        
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    init_database()