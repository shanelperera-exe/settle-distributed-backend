import psycopg2
import sys
try:
    conn = psycopg2.connect(host='postgres-1', port=5432, user='settle-user', password='settle@1234', dbname='settle', connect_timeout=2)
    cur = conn.cursor()
    cur.execute("SELECT pg_is_in_recovery();")
    print(f"Result: {cur.fetchone()}")
except Exception as e:
    print(f"Error: {e}")
