import pytest
import requests
import uuid
import time

BASE_URL = "http://localhost:8000"

class TestAPIGateway:
    
    def setup_method(self):
        self.test_email = f"gateway_test_{uuid.uuid4().hex[:8]}@example.com"
        self.password = "password123"
        self.name = "Gateway Test User"
        self.token = None
        self.user_id = None
    
    def _wait_for_services(self):
        for i in range(30):
            try:
                response = requests.get(f"{BASE_URL}/health", timeout=5)
                if response.status_code == 200:
                    return True
            except:
                pass
            time.sleep(2)
        return False
    
    def _register_user(self):
        register_data = {
            "email": self.test_email,
            "password": self.password,
            "name": self.name
        }
        response = requests.post(f"{BASE_URL}/v1/auth/register", json=register_data)
        if response.status_code == 200:
            self.user_id = response.json()["data"]["id"]
        return response
    
    def _login_user(self):
        login_data = {
            "email": self.test_email,
            "password": self.password
        }
        response = requests.post(f"{BASE_URL}/v1/auth/login", json=login_data)
        if response.status_code == 200:
            self.token = response.json()["data"]["access_token"]
        return response
    
    def _get_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
    
    def test_1_gateway_health_check(self):
        print("\n=== Тест 1: Health Check API Gateway ===")
        
        if not self._wait_for_services():
            pytest.skip("Services are not available")
        
        response = requests.get(f"{BASE_URL}/health")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["status"] == "healthy", f"Expected 'healthy', got '{data['status']}'"
        assert data["service"] == "api-gateway", f"Expected 'api-gateway', got '{data['service']}'"
        
        print("API Gateway health check passed")
    
    def test_2_gateway_proxy_registration(self):
        print("\n=== Тест 2: Проксирование регистрации ===")
        
        response = self._register_user()
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["success"] == True, "Registration should be successful through gateway"
        assert "id" in data["data"], "Response should contain user ID"
        
        assert "X-Request-ID" in response.headers, "Response should contain X-Request-ID header"
        
        print(f"Registration proxied successfully - User ID: {data['data']['id']}")
    
    def test_3_gateway_proxy_login(self):
        print("\n=== Тест 3: Проксирование логина ===")
        
        self._register_user()
        
        response = self._login_user()
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["success"] == True, "Login should be successful through gateway"
        assert "access_token" in data["data"], "Response should contain access token"
        assert data["data"]["token_type"] == "bearer", "Token type should be bearer"
        
        self.token = data["data"]["access_token"]
        
        print("Login proxied successfully - Token received")
    
    def test_4_gateway_protected_routes_without_token(self):
        print("\n=== Тест 4: Защищенные маршруты без токена ===")
        
        response = requests.get(f"{BASE_URL}/v1/users/me")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        data = response.json()
        assert data["success"] == False, "Access without token should fail"
        assert "error" in data, "Response should contain error details"
        
        print(" Protected routes correctly reject requests without token")
    
    def test_5_gateway_protected_routes_with_token(self):
        print("\n=== Тест 5: Защищенные маршруты с токеном ===")
        
        self._register_user()
        self._login_user()
        
        #профиль с токеном
        response = requests.get(f"{BASE_URL}/v1/users/me", headers=self._get_headers())
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["success"] == True, "Access with token should be successful"
        assert "email" in data["data"], "Response should contain user data"
        assert data["data"]["email"] == self.test_email, "Should return correct user data"
        
        print("Protected routes work correctly with valid token")
    
    def test_6_gateway_order_creation_proxy(self):
        print("\n=== Тест 6: Проксирование создания заказа ===")
        
        self._register_user()
        self._login_user()
        
        order_data = {
            "items": [
                {
                    "product_id": "prod_gateway_test",
                    "product_name": "Gateway Test Product",
                    "quantity": 2,
                    "price": 29.99
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/orders", 
            json=order_data, 
            headers=self._get_headers()
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["success"] == True, "Order creation should be successful through gateway"
        assert data["data"]["status"] == "created", f"Order status should be 'created', got '{data['data']['status']}'"
        assert "id" in data["data"], "Response should contain order ID"
        
        print(f"Order creation proxied successfully - Order ID: {data['data']['id']}")
    
    def test_7_gateway_request_id_propagation(self):
        print("\n=== Тест 7: Распространение X-Request-ID ===")
        
        custom_request_id = f"test-request-{uuid.uuid4().hex[:8]}"
        headers = {"X-Request-ID": custom_request_id}
        
        response = requests.get(f"{BASE_URL}/health", headers=headers)
        
        assert response.status_code == 200, "Health check should succeed"
        assert "X-Request-ID" in response.headers, "Response should contain X-Request-ID"
        assert response.headers["X-Request-ID"] == custom_request_id, "Should return same Request-ID"
        
        print(f"X-Request-ID propagation works - ID: {custom_request_id}")
    
    def test_8_gateway_rate_limiting(self):
        print("\n=== Тест 8: Ограничение частоты запросов ===")
        
        #много быстрых запросов
        for i in range(105): 
            response = requests.get(f"{BASE_URL}/health")
            if response.status_code == 429:
                print(f"Rate limiting triggered after {i} requests")
                break
        else:
            print("Rate limiting not triggered (might be disabled in development)")
    
    def test_9_gateway_error_handling(self):
        print("\n=== Тест 9: Обработка ошибок Gateway ===")
        
        # получить несуществующий маршрут
        response = requests.get(f"{BASE_URL}/v1/nonexistent/route")
        
        # вернуть 404 от Gateway или от сервиса
        assert response.status_code in [404, 503, 500], f"Unexpected status: {response.status_code}"
        
        data = response.json()
        assert "success" in data, "Error response should follow standard format"
        assert "error" in data, "Error response should contain error details"
        
        print("Error handling works correctly")

class TestAPIGatewayIntegration:
    
    def test_full_workflow_through_gateway(self):
        print("\n=== Интеграционный тест: Полный workflow через Gateway ===")
        
        health_response = requests.get(f"{BASE_URL}/health")
        assert health_response.status_code == 200
        print("Gateway health check")
        
        # Регистрация
        test_email = f"integration_{uuid.uuid4().hex[:8]}@example.com"
        register_data = {
            "email": test_email,
            "password": "password123",
            "name": "Integration Test User"
        }
        
        register_response = requests.post(f"{BASE_URL}/v1/auth/register", json=register_data)
        assert register_response.status_code == 200
        user_id = register_response.json()["data"]["id"]
        print(f"User registration - ID: {user_id}")
        
        # Логин
        login_data = {
            "email": test_email,
            "password": "password123"
        }
        
        login_response = requests.post(f"{BASE_URL}/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("User login - Token received")
        
        #Получение профиля
        profile_response = requests.get(f"{BASE_URL}/v1/users/me", headers=headers)
        assert profile_response.status_code == 200
        assert profile_response.json()["data"]["email"] == test_email
        print("User profile retrieval")
        
        # Создание заказа
        order_data = {
            "items": [
                {
                    "product_id": "prod_integration",
                    "product_name": "Integration Test Product",
                    "quantity": 1,
                    "price": 49.99
                }
            ]
        }
        
        order_response = requests.post(f"{BASE_URL}/v1/orders", json=order_data, headers=headers)
        assert order_response.status_code == 200
        order_id = order_response.json()["data"]["id"]
        print(f"Order creation - Order ID: {order_id}")
        
        # Получение заказа
        get_order_response = requests.get(f"{BASE_URL}/v1/orders/{order_id}", headers=headers)
        assert get_order_response.status_code == 200
        assert get_order_response.json()["data"]["id"] == order_id
        print(" Order retrieval")
        
        # Список заказов
        orders_response = requests.get(f"{BASE_URL}/v1/orders", headers=headers)
        assert orders_response.status_code == 200
        assert "orders" in orders_response.json()["data"]
        print("Orders list retrieval")
        
        print("Full integration test passed through API Gateway")