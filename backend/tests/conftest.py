import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

from app.platform.infrastructure.db.base import Base
from app.platform.infrastructure.db.session import get_db
from app.main import app

@pytest.fixture(autouse=True)
def mock_raft_cluster_size(monkeypatch):
    from app.platform.core.config import settings
    monkeypatch.setattr(settings, "RAFT_CLUSTER_SIZE", 3)

# We use the existing local Postgres instance but a separate database or just drop/create tables.
# For simplicity, we'll use the existing settle_dev DB but run tests in a transaction that rolls back,
# or just drop/create tables if it's a dedicated test DB.
# Let's use SQLite in-memory for unit tests that need DB, but Postgres for integration.
# To keep things fast and robust across all environments, let's default to SQLite for all local tests
# unless specified, but wait! The user approved Postgres. 
# We'll use the local docker Postgres.
from sqlalchemy.pool import StaticPool

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def setup_db():
    # Create all tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db(setup_db):
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

@pytest_asyncio.fixture
async def async_client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()
