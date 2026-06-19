from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

from app.platform.core.config import settings
from app.platform.observability.logging import setup_logging
from app.platform.infrastructure.db.base import Base
from app.platform.infrastructure.db.session import engine
# Import models to ensure they are registered with Base
import app.modules.payments.models
import app.modules.users.models
import app.modules.wallets.models
import app.modules.transfers.models
import app.modules.deposits.models
import app.modules.withdrawals.models
import app.financial.ledger.models
import app.financial.idempotency.models
import app.platform.distributed.raft.models
import app.platform.distributed.zookeeper.models

# Distributed Subsystems will be initialized via lifespan

# 1. Initialize Structured Logging
# This must be done before anything else so startup errors are logged correctly.
logger = setup_logging()

# 2. Initialize Database Tables
# In a true production environment, you would use Alembic migrations (e.g., `alembic upgrade head`).
# For the purpose of this distributed system implementation and to ensure it runs out of the box 
# in Docker Compose without manual migration steps, we create tables directly on startup if they don't exist.
try:
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize database tables: {e}", exc_info=True)

from app.platform.distributed.zookeeper.client import ZKClientManager
from app.platform.distributed.raft.node import raft_node
from app.modules.payments.applier import raft_apply_callback

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────

    # 1. Initialize OpenTelemetry Distributed Tracing
    from app.platform.observability.tracing import init_tracing, instrument_app, shutdown_tracing
    init_tracing()
    instrument_app(app)

    # 2. Start Raft Consensus engine
    raft_node.set_apply_callback(raft_apply_callback)
    await raft_node.start()
    
    # 3. Start Clock Subsystem
    from app.platform.distributed.clock import start_clock_subsystem, stop_clock_subsystem
    start_clock_subsystem()
    
    logger.info("Application startup complete. Node is ready.")
    yield
    
    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down distributed subsystems...")
    stop_clock_subsystem()
    ZKClientManager.close()
    shutdown_tracing()
    logger.info("Application shutdown complete.")

# 3. Create FastAPI Application Instance
app = FastAPI(
    title=settings.APP_NAME,
    description="Fault-Tolerant Distributed Payment Processing System",
    version="1.0.0",
    lifespan=lifespan
)

# 4. Register Observability Middleware
# Middleware execution order in Starlette is LIFO — the last added is the
# first to execute. We want the execution order to be:
#   MetricsMiddleware → LoggingMiddleware → TracingMiddleware → handler
# So we add them in reverse order.
from app.platform.middleware.tracing_middleware import TracingMiddleware
from app.platform.middleware.logging_middleware import LoggingMiddleware
from app.platform.middleware.metrics_middleware import MetricsMiddleware

app.add_middleware(TracingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(MetricsMiddleware)

# 5. Global Exception Handler
# In a distributed system, you don't want unhandled exceptions returning raw HTML or 
# stack traces to other internal microservices. Everything must be structured JSON.
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception during request {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc) if settings.LOG_LEVEL == "DEBUG" else "An unexpected error occurred."}
    )

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "node": settings.NODE_ID,
        "status": "running"
    }

# We will include routers from Phase 6 here later.
from app.api.v1.router import api_router
app.include_router(api_router, prefix="/api/v1")
