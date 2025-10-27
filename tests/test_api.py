import pytest
import requests

BASE_URL = "http://localhost:8000"

def test_api_gateway_health():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "api-gateway"
    print("API Gateway health check passed")

def test_api_gateway_proxy_auth():
    # Тестируем, что gateway правильно проксирует запрос на регистрацию
    register_data = {
        "email": "test@example.com",
        "password": "password123",
        "name": "Test User"
    }
    response = requests.post(f"{BASE_URL}/v1/auth/register", json=register_data)
    assert response.status_code in [200, 400]
    print("API Gateway auth proxy test passed")