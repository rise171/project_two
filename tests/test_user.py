import pytest
import requests
import uuid
import time

BASE_URL = "http://localhost:8000"  # API Gateway

def test_success_register(user_client):
    r = user_client.post("/v1/auth/register", json={
        "email": "user1@example.com",
        "password": "123456",
        "name": "Test User"
    })
    data = r.json()
    assert data["success"] is True
    assert "id" in data["data"]

def test_duplicate_register(user_client):
    user_client.post("/v1/auth/register", json={
        "email": "dup@example.com",
        "password": "123456",
        "name": "User"
    })
    r = user_client.post("/v1/auth/register", json={
        "email": "dup@example.com",
        "password": "123456",
        "name": "User"
    })
    data = r.json()
    assert data["success"] is False
    assert data["error"]["code"] == "USER_EXISTS"

def test_login_success(user_client):
    user_client.post("/v1/auth/register", json={
        "email": "login@example.com",
        "password": "123456",
        "name": "Login User"
    })
    r = user_client.post("/v1/auth/login", json={
        "email": "login@example.com",
        "password": "123456"
    })
    assert r.json()["success"] is True
    assert "access_token" in r.json()["data"]

def test_access_protected_without_token(user_client):
    r = user_client.get("/v1/users/me")
    assert r.status_code in (401, 403)