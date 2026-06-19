from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.platform.core.config import settings
from app.platform.observability.logging import logger

# Create the SQLAlchemy engine
# pool_pre_ping checks the connection validity before returning it from the pool, 
# preventing "MySQL/Postgres has gone away" errors.
try:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

# SessionLocal is the factory for creating database sessions.
# autocommit=False and autoflush=False give us explicit control over transactions.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Dependency generator for FastAPI to yield a database session per request.
    Ensures the session is closed cleanly after the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
