from fastapi import APIRouter
from typing import List, Dict, Any
import concurrent.futures
from app.platform.observability.db_metrics import get_db_metrics, get_slow_queries
from app.platform.core.config import settings

router = APIRouter()

DB_HOSTS = [f"postgres-{i}" for i in range(1, 6)]

@router.get("/metrics", response_model=List[Dict[str, Any]])
def get_cluster_db_metrics():
    """
    Fetches real-time metrics from all postgres nodes concurrently.
    """
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_host = {
            executor.submit(
                get_db_metrics, 
                host, 
                settings.POSTGRES_PORT, 
                settings.POSTGRES_USER, 
                settings.POSTGRES_PASSWORD, 
                settings.POSTGRES_DB
            ): host for host in DB_HOSTS
        }
        for future in concurrent.futures.as_completed(future_to_host):
            results.append(future.result())
            
    # Sort to ensure consistent ordering (postgres-1, postgres-2, etc.)
    return sorted(results, key=lambda x: x["id"])

@router.get("/slow_queries", response_model=List[Dict[str, Any]])
def get_cluster_slow_queries():
    """
    Fetches real-time slow queries from all postgres nodes concurrently.
    """
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_host = {
            executor.submit(
                get_slow_queries, 
                host, 
                settings.POSTGRES_PORT, 
                settings.POSTGRES_USER, 
                settings.POSTGRES_PASSWORD, 
                settings.POSTGRES_DB
            ): host for host in DB_HOSTS
        }
        for future in concurrent.futures.as_completed(future_to_host):
            results.extend(future.result())
            
    # Sort by duration descending across the whole cluster
    return sorted(results, key=lambda x: x.get("duration", 0), reverse=True)
