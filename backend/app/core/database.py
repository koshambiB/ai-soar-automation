import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from contextlib import contextmanager
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "dbname": os.getenv("POSTGRES_DB", "soar_db"),
    "user": os.getenv("POSTGRES_USER", "soar_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "soar_password")
}

connection_pool = None

def get_connection_string():
    return f"host={DB_CONFIG['host']} port={DB_CONFIG['port']} dbname={DB_CONFIG['dbname']} user={DB_CONFIG['user']} password={DB_CONFIG['password']}"

def init_connection_pool(min_size=1, max_size=10):
    global connection_pool
    if connection_pool is None:
        connection_pool = ConnectionPool(
            conninfo=get_connection_string(),
            min_size=min_size,
            max_size=max_size
        )
    return connection_pool

@contextmanager
def get_connection():
    global connection_pool
    if connection_pool is None:
        init_connection_pool()
    
    with connection_pool.connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e

def get_cursor(conn):
    return conn.cursor(row_factory=dict_row)