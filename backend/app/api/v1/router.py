from fastapi import APIRouter, Depends
from app.api.v1.endpoints import health, payments, clock, webhooks, raft, raft_health, metrics_endpoint, auth, users, wallets, transfers, deposits, withdrawals, ws
from app.api.dependencies.auth import verify_api_key, verify_raft_token

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["Health & Cluster State"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments API"], dependencies=[Depends(verify_api_key)])
api_router.include_router(clock.router, prefix="/clock", tags=["Time Synchronization"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(raft.router, prefix="/raft", tags=["Raft Consensus"], dependencies=[Depends(verify_raft_token)])
api_router.include_router(raft_health.router, prefix="/health", tags=["Raft Health"])
api_router.include_router(metrics_endpoint.router, tags=["Monitoring"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(wallets.router, prefix="/wallets", tags=["Wallets"])
api_router.include_router(transfers.router, prefix="/transfers", tags=["Transfers"])
api_router.include_router(deposits.router, prefix="/deposits", tags=["Deposits"])
api_router.include_router(withdrawals.router, prefix="/withdrawals", tags=["Withdrawals"])
api_router.include_router(ws.router, prefix="/ws", tags=["WebSockets"])
