import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3308)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )
        return conn
    except Error as e:
        print(f"❌ Database connection error: {e}")
        raise


def run_query(query, params=None, fetch=True):
    """Execute a query and return rows as list of dicts (for SELECT),
    or None for INSERT/UPDATE/DELETE (use run_write for those)."""
    conn = get_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if fetch:
            rows = cursor.fetchall()
            return rows
        return None
    finally:
        cursor.close()
        conn.close()


def run_write(query, params=None):
    """Execute INSERT/UPDATE/DELETE, commit, and return affected row count
    (and lastrowid for INSERTs)."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        conn.commit()
        return {"rowcount": cursor.rowcount, "lastrowid": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()