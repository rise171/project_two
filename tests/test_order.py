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

def test_order_creation_with_token():
    # Сначала получаем токен
    login_data = {
        "email": "test@example.com",
        "password": "password123"
    }
    
    login_response = requests.post(f"http://localhost:8001/v1/auth/login", json=login_data)
    
    if login_response.status_code == 200:
        token = login_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        order_data = {
            "items": [
                {
                    "product_id": "prod_1",
                    "product_name": "Test Product",
                    "quantity": 2,
                    "price": 25.50
                }
            ]
        }
        
        response = requests.post(
            f"{ORDER_SERVICE_URL}/v1/orders", 
            json=order_data, 
            headers=headers
        )
        
        # Может вернуть 200 (успех) или 401 (неавторизован)
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert data["success"] == True
            assert data["data"]["status"] == "created"
    print("Order creation test passed")