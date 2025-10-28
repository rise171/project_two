import pytest
import requests
import uuid

USER_SERVICE_URL = "http://localhost:8001"

def test_user_service_health():
    response = requests.get(f"{USER_SERVICE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "user-service"
    print("health check passed")

def test_user_registration():
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    
    user_data = {
        "email": unique_email,
        "password": "password123",
        "name": "Test User"
    }
    
    response = requests.post(f"{USER_SERVICE_URL}/v1/auth/register", json=user_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    assert "id" in data["data"]
    print(f"User registration test passed - User ID: {data['data']['id']}")

def test_user_login():
    login_data = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    response = requests.post(f"{USER_SERVICE_URL}/v1/auth/login", json=login_data)
    assert response.status_code in [200, 400]
    
    if response.status_code == 200:
        data = response.json()
        assert data["success"] == True
        assert "access_token" in data["data"]
    print("login test passed")