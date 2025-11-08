import pytest
import requests
import uuid

BASE_URL = "http://localhost:8000"  # API Gateway

class TestOrderService:
    
    def setup_method(self):
        self.test_email = f"order_test_{uuid.uuid4().hex[:8]}@example.com"
        self.password = "password123"
        self.name = "Order Test User"
        self.token = None
        self.user_id = None
        self.order_ids = []
        
        self._register_and_login()
    
    def _register_and_login(self):
        # Регистрация
        register_data = {
            "email": self.test_email,
            "password": self.password,
            "name": self.name
        }
        reg_response = requests.post(f"{BASE_URL}/v1/auth/register", json=register_data)
        if reg_response.status_code == 200:
            self.user_id = reg_response.json()["data"]["id"]
        
        # Вход
        login_data = {
            "email": self.test_email,
            "password": self.password
        }
        login_response = requests.post(f"{BASE_URL}/v1/auth/login", json=login_data)
        if login_response.status_code == 200:
            self.token = login_response.json()["data"]["access_token"]
    
    def _get_headers(self):
        return {"Authorization": f"Bearer {self.token}"}
    
    def _create_test_order(self):
        order_data = {
            "items": [
                {
                    "product_id": "prod_test_1",
                    "product_name": "Test Product 1",
                    "quantity": 2,
                    "price": 25.50
                }
            ]
        }
        
        response = requests.post(
            f"{BASE_URL}/v1/orders", 
            json=order_data, 
            headers=self._get_headers()
        )
        
        if response.status_code == 200:
            order_id = response.json()["data"]["id"]
            self.order_ids.append(order_id)
            return order_id
        return None
    
    def test_1_create_order_authenticated(self):
        print("\n=== Тест 1: Создание заказа авторизованным пользователем ===")
        
        order_data = {
            "items": [
                {
                    "product_id": "prod_1",
                    "product_name": "Test Product 1",
                    "quantity": 2,
                    "price": 25.50
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
        assert data["success"] == True
        assert data["data"]["status"] == "created"
        assert data["data"]["user_id"] == self.user_id
        assert data["data"]["total_amount"] == 51.00
        
        order_id = data["data"]["id"]
        self.order_ids.append(order_id)
        print(f"Успешное создание заказа - ID: {order_id}")
    
    def test_2_get_own_order(self):
        print("\n=== Тест 2: Получение собственного заказа ===")
        
        # Создаем заказ
        order_id = self._create_test_order()
        assert order_id is not None
        # Получаем заказ
        response = requests.get(
            f"{BASE_URL}/v1/orders/{order_id}", 
            headers=self._get_headers()
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["data"]["id"] == order_id
        assert data["data"]["user_id"] == self.user_id
        print(f" Успешное получение заказа - ID: {order_id}")
    
    def test_3_order_list_with_pagination(self):
        print("\n=== Тест 3: Список заказов с пагинацией ===")
        
        # Создаем несколько заказов
        for i in range(3):
            order_data = {
                "items": [
                    {
                        "product_id": f"prod_{i}",
                        "product_name": f"Product {i}",
                        "quantity": i + 1,
                        "price": (i + 1) * 10.0
                    }
                ]
            }
            requests.post(
                f"{BASE_URL}/v1/orders", 
                json=order_data, 
                headers=self._get_headers()
            )
        
        # Получаем список с пагинацией
        response = requests.get(
            f"{BASE_URL}/v1/orders?page=1&limit=2", 
            headers=self._get_headers()
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "orders" in data["data"]
        assert "pagination" in data["data"]
        
        pagination = data["data"]["pagination"]
        assert pagination["page"] == 1
        assert pagination["limit"] == 2
        assert pagination["total"] >= 3
        
        orders = data["data"]["orders"]
        assert len(orders) <= 2
        
        # Проверяем структуру заказа
        if len(orders) > 0:
            order = orders[0]
            assert "id" in order
            assert "user_id" in order
            assert "status" in order
            assert "total_amount" in order
        
        print(f"Корректная пагинация - страница {pagination['page']}, всего {pagination['total']} заказов")