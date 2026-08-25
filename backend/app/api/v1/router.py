from fastapi import APIRouter, Depends
from app.api.v1.endpoints import health, payments, clock, webhooks, raft, raft_health, metrics_endpoint, database, chaos, alerts, auth
from app.api.dependencies.auth import verify_api_key, verify_raft_token
from app.api.deps import get_admin_user, get_current_user

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(health.router, prefix="/health", tags=["Health & Cluster State"], dependencies=[Depends(get_current_user)])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments API"], dependencies=[Depends(verify_api_key)])
api_router.include_router(clock.router, prefix="/clock", tags=["Time Synchronization"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(raft.router, prefix="/raft", tags=["Raft Consensus"], dependencies=[Depends(verify_raft_token)])
api_router.include_router(raft_health.router, prefix="/health", tags=["Raft Health"])
api_router.include_router(metrics_endpoint.router, tags=["Monitoring"])
api_router.include_router(database.router, prefix="/database", tags=["Database Metrics"], dependencies=[Depends(get_current_user)])
api_router.include_router(chaos.router, prefix="/chaos", tags=["Chaos Engineering"], dependencies=[Depends(get_admin_user)])
api_router.include_router(alerts.router, prefix="/alerts", tags=["System Alerts"], dependencies=[Depends(get_current_user)])
