import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends

from app.api.dependencies.auth import verify_api_key, verify_raft_token
from app.platform.core.config import settings

app = FastAPI()

@app.get("/public")
def public_route():
    return {"status": "ok"}

@app.get("/protected_api", dependencies=[Depends(verify_api_key)])
def protected_api():
    return {"status": "ok"}

@app.get("/protected_raft", dependencies=[Depends(verify_raft_token)])
def protected_raft():
    return {"status": "ok"}

client = TestClient(app)

def test_public_route():
    response = client.get("/public")
    assert response.status_code == 200

def test_api_key_missing():
    response = client.get("/protected_api")
    assert response.status_code == 401

def test_api_key_invalid():
    response = client.get("/protected_api", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401

def test_api_key_valid():
    response = client.get("/protected_api", headers={"Authorization": f"Bearer {settings.API_KEY}"})
    assert response.status_code == 200

def test_raft_token_missing():
    response = client.get("/protected_raft")
    assert response.status_code == 403 or response.status_code == 422

def test_raft_token_invalid():
    response = client.get("/protected_raft", headers={"X-Raft-Token": "invalid"})
    assert response.status_code == 403 or response.status_code == 401

def test_raft_token_valid():
    response = client.get("/protected_raft", headers={"X-Raft-Token": settings.RAFT_INTERNAL_TOKEN})
    assert response.status_code == 200
