import pytest
import requests
import uuid
import time

BASE_URL = "http://localhost:8000"  # API Gateway

class TestUserService:
    """Тесты для User Service (оценка 3)"""
    
    def setup_method(self):
        self.test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        self.password = "password123"
        self.name = "Test User"
        self.user_id = None
        self.token = None
    
    def test_1_successful_registration(self):
        """Успешная регистрация с валидными полями"""
        print("\n Тест 1: Успешная регистрация")
        
        register_data = {
            "email": self.test_email,
            "password": self.password,
            "name": self.name
        }
        
        response = requests.post(f"{BASE_URL}/v1/auth/register", json=register_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["success"] == True
        assert "id" in data["data"]
        
        self.user_id = data["data"]["id"]
        print(f"Успешная регистрация - ID: {self.user_id}")
    
    def test_2_duplicate_registration_error(self):
        print("\nТест 2: Ошибка дублирования email")
        
        # Первая регистрация
        register_data = {
            "email": self.test_email,
            "password": self.password,
            "name": self.name
        }
        response1 = requests.post(f"{BASE_URL}/v1/auth/register", json=register_data)
        assert response1.status_code == 200
        
        response2 = requests.post(f"{BASE_URL}/v1/auth/register", json=register_data)
        assert response2.status_code == 400
        
        data = response2.json()
        assert data["success"] == False
        assert data["error"]["code"] == "USER_EXISTS"
        print("Корректная ошибка при дублировании email")
    
    def test_3_successful_login_with_token(self):
        print("\n Тест 3: Успешный вход с получением токена")
        
        # Регистрация
        register_data = {
            "email": self.test_email,
            "password": self.password,
            "name": self.name
        }
        requests.post(f"{BASE_URL}/v1/auth/register", json=register_data)
        
        # Вход
        login_data = {
            "email": self.test_email,
            "password": self.password
        }
        response = requests.post(f"{BASE_URL}/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "access_token" in data["data"]
        
        self.token = data["data"]["access_token"]
        print(f"Успешный вход - токен получен")
        return self.token
    
    def test_4_protected_route_without_token(self):
        print("\n=== Тест 4: Защищенный маршрут без токена ===")
        
        response = requests.get(f"{BASE_URL}/v1/users/me")
        assert response.status_code == 401
        
        data = response.json()
        assert data["success"] == False
        assert "authentication" in data["error"]["message"].lower()
        print("Корректный отказ в доступе без токена")
    
    def test_5_get_profile_with_token(self):
        print("\n Тест 5: Получение профиля с токеном")
        
        # Регистрация и вход
        self.test_3_successful_login_with_token()
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(f"{BASE_URL}/v1/users/me", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert data["data"]["email"] == self.test_email
        print("Успешное получение профиля")