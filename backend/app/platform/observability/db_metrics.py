import psycopg2
import time
import random
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def get_db_metrics(host: str, port: int, user: str, password: str, dbname: str) -> Dict[str, Any]:
    try:
        conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname, connect_timeout=2)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Role
        role = "PRIMARY" if host == "postgres-1" else "REPLICA"
        
        # Connections
        cur.execute("SELECT count(*) FROM pg_stat_activity WHERE backend_type = 'client backend';")
        connections = cur.fetchone()[0]
        
        # TPS (xact_commit + xact_rollback)
        cur.execute("SELECT sum(xact_commit + xact_rollback) FROM pg_stat_database;")
        tps = cur.fetchone()[0] or 0
        
        # Storage
        cur.execute("SELECT sum(pg_database_size(datname)) FROM pg_database;")
        storage_bytes = float(cur.fetchone()[0] or 0)
        storage_gb = storage_bytes / (1024 ** 3)
        storage_percent = min(100.0, (storage_gb / 10.0) * 100) # Mock 10GB disk
        
        # Latency (Replication Lag in ms)
        latency = 0
        if role == "REPLICA":
            try:
                cur.execute("SELECT extract(epoch from now() - pg_last_xact_replay_timestamp()) * 1000;")
                res = cur.fetchone()
                latency = int(res[0]) if res and res[0] else 0
            except Exception:
                latency = 0
                

        
        cur.close()
        conn.close()
        
        return {
            "id": host,
            "role": role,
            "status": "HEALTHY",
            "connections": connections,

            "storage": storage_percent,
            "tps": float(tps),
            "latency": latency
        }
    except Exception as e:
        logger.error(f"Failed to fetch metrics for {host}: {e}")
        return {
            "id": host,
            "role": "UNKNOWN",
            "status": "DOWN",
            "connections": 0,

            "storage": 0.0,
            "tps": 0.0,
            "latency": 0
        }

def get_slow_queries(host: str, port: int, user: str, password: str, dbname: str) -> List[Dict[str, Any]]:
    try:
        conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname, connect_timeout=2)
        conn.autocommit = True
        cur = conn.cursor()
        
        cur.execute("""
            SELECT pid, query, state, extract(epoch from now() - query_start) as duration 
            FROM pg_stat_activity 
            WHERE state != 'idle' 
              AND query NOT ILIKE '%pg_stat_activity%'
              AND extract(epoch from now() - query_start) > 0.001
            ORDER BY duration DESC 
            LIMIT 5;
        """)
        
        queries = []
        for row in cur.fetchall():
            queries.append({
                "id": str(row[0]),
                "node": host,
                "query": row[1],
                "state": row[2],
                "duration": int(row[3] * 1000) if row[3] else 0 # duration in ms
            })
            
        cur.close()
        conn.close()
        return queries
    except Exception:
        return []
