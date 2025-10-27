import pytest
import requests

ORDER_SERVICE_URL = "http://localhost:8002"

def test_order_service_health():
    response = requests.get(f"{ORDER_SERVICE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "order-service"
    print("health check passed")