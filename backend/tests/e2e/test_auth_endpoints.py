import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_user(async_client: AsyncClient, db):
    payload = {
        "email": "testuser@example.com",
        "password": "strongpassword123",
        "full_name": "Test User"
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "testuser@example.com"
    assert "id" in data
    assert data["state"] == "ACTIVE"
    assert data["role"] == "USER"

@pytest.mark.asyncio
async def test_login_user(async_client: AsyncClient, db):
    # Register first
    payload = {
        "email": "loginuser@example.com",
        "password": "loginpassword123",
        "full_name": "Login User"
    }
    await async_client.post("/api/v1/auth/register", json=payload)

    # Login
    login_data = {
        "username": "loginuser@example.com",
        "password": "loginpassword123"
    }
    response = await async_client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_get_me(async_client: AsyncClient, db):
    # Register & Login
    payload = {
        "email": "meuser@example.com",
        "password": "mepassword123",
        "full_name": "Me User"
    }
    await async_client.post("/api/v1/auth/register", json=payload)
    login_data = {
        "username": "meuser@example.com",
        "password": "mepassword123"
    }
    login_response = await async_client.post("/api/v1/auth/login", data=login_data)
    token = login_response.json()["access_token"]

    # Get Me
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "meuser@example.com"
