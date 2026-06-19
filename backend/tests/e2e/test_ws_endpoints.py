import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from app.main import app
from app.platform.infrastructure.db.session import get_db

@pytest.fixture
async def get_token(async_client: AsyncClient, db):
    await async_client.post("/api/v1/auth/register", json={"email": "ws@example.com", "password": "password", "full_name": "WS User"})
    res = await async_client.post("/api/v1/auth/login", data={"username": "ws@example.com", "password": "password"})
    return res.json()["access_token"]

@pytest.mark.asyncio
async def test_websocket_connect(get_token, db, monkeypatch):
    token = get_token
    
    # Mock get_current_user_ws directly
    from app.modules.users.models import User
    async def mock_get_user(token):
        return User(id="user_ws", email="ws@example.com")
    monkeypatch.setattr("app.api.v1.endpoints.ws.get_current_user_ws", mock_get_user)
    
    # We use TestClient for websocket testing as AsyncClient doesn't natively support it well
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    
    with client.websocket_connect(f"/api/v1/ws/stream?token={token}") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert data == "pong"
        
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_websocket_invalid_token(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    
    client = TestClient(app)
    
    with pytest.raises(Exception) as exc_info:
        with client.websocket_connect("/api/v1/ws/stream?token=invalid_token") as websocket:
            pass # Should fail to connect
            
    app.dependency_overrides.clear()
