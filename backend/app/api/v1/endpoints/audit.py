import httpx
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from app.platform.core.config import settings
from app.platform.observability.logging import logger
from app.api.deps import get_current_user
import json

router = APIRouter()

@router.get("/logs", response_model=List[Dict[str, Any]])
async def get_audit_logs(
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch audit logs (immutable system ledger) from Loki.
    Only queries logs that have an 'event' label set (e.g. CHAOS_INJECTION, LEADER_ELECTION).
    """
    # Requires an event label to be present
    query = '{service="settle", event!=""}'
    
    url = f"{settings.LOKI_URL}/loki/api/v1/query_range"
    params = {
        "query": query,
        "limit": limit,
        "direction": "backward"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            # Parse Loki streams format
            if "data" in data and "result" in data["data"]:
                for stream_entry in data["data"]["result"]:
                    stream_labels = stream_entry.get("stream", {})
                    for value in stream_entry.get("values", []):
                        # value is [timestamp_ns, log_line_string]
                        if len(value) >= 2:
                            ts_ns = value[0]
                            log_str = value[1]
                            
                            try:
                                parsed_log = json.loads(log_str)
                            except json.JSONDecodeError:
                                # Fallback if log isn't valid JSON (shouldn't happen with our JSON formatter)
                                parsed_log = {"message": log_str}
                                
                            # Merge labels with log payload (log payload takes precedence)
                            audit_entry = {**stream_labels, **parsed_log}
                            # Ensure we have a timestamp (Loki ns converted to ms string or ISO)
                            # Actually our JSON formatter already puts 'timestamp' in the payload
                            
                            results.append(audit_entry)
                            
            # Sort by timestamp descending
            results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return results[:limit]
            
        except httpx.RequestError as e:
            logger.error(f"Error querying Loki for audit logs: {e}")
            raise HTTPException(status_code=503, detail="Audit log service unavailable")
        except Exception as e:
            logger.error(f"Failed to parse audit logs: {e}")
            raise HTTPException(status_code=500, detail="Internal server error parsing audit logs")
