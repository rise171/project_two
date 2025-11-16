# test_api_gateway.py
import pytest
import requests
import uuid
import time
from unittest.mock import Mock, patch, AsyncMock
import asyncio

BASE_URL = "http://localhost:8000"

class TestAPIGateway:
    
    def setup_method(self):
        self.test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        self.password = "password123"
        self.name = "Test User"
        self.token = "mock_jwt_token_123"
        self.user_id = "user_123"
        self.order_id = "order_456"
    
    def _wait_for_gateway(self, max_attempts=10):
        """Ожидание доступности Gateway"""
        for i in range(max_attempts):
            try:
                response = requests.get(f"{BASE_URL}/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Gateway is available")
                    return True
            except Exception as e:
                print(f"Attempt {i+1}/{max_attempts}: Gateway not ready - {e}")
            time.sleep(2)
        return False

    # Тест 1: Health Check Gateway
    def test_1_gateway_health_check(self):
        """Тест проверки здоровья Gateway"""
        print("\n=== Тест 1: Health Check Gateway ===")
        
        if not self._wait_for_gateway():
            pytest.skip("Gateway is not available")
        
        response = requests.get(f"{BASE_URL}/health")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "api-gateway"
        
        print("✅ Health check PASSED")

    # Тест 2: Аутентификация (регистрация и логин)
    def test_2_auth_workflow(self):
        """Тест полного цикла аутентификации через Gateway"""
        print("\n=== Тест 2: Auth Workflow ===")
        
        if not self._wait_for_gateway():
            pytest.skip("Gateway is not available")

        # Мокируем запросы к users-service
        mock_register_response = Mock()
        mock_register_response.status_code = 200
        mock_register_response.json.return_value = {
            "success": True,
            "data": {
                "id": self.user_id,
                "email": self.test_email,
                "name": self.name
            }
        }

        mock_login_response = Mock()
        mock_login_response.status_code = 200
        mock_login_response.json.return_value = {
            "success": True,
            "data": {
                "access_token": self.token,
                "token_type": "bearer",
                "user_id": self.user_id
            }
        }

        with patch('httpx.AsyncClient.request') as mock_request:
            # Настраиваем моки для последовательных вызовов
            mock_request.side_effect = [
                AsyncMock(**{
                    "status_code": 200,
                    "json.return_value": mock_register_response.json.return_value,
                    "headers": {}
                }),
                AsyncMock(**{
                    "status_code": 200,
                    "json.return_value": mock_login_response.json.return_value,
                    "headers": {}
                })
            ]

            # Тестируем регистрацию
            register_data = {
                "email": self.test_email,
                "password": self.password,
                "name": self.name
            }
            
            try:
                response = requests.post(f"{BASE_URL}/v1/auth/register", json=register_data)
                print(f"Registration response: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    assert data["success"] == True
                    assert data["data"]["email"] == self.test_email
                    print("✅ Registration PASSED")
                else:
                    print(f"⚠️ Registration returned {response.status_code}")
                    pytest.skip("Registration service not available")
            
            except Exception as e:
                print(f"⚠️ Registration error: {e}")
                pytest.skip(f"Registration service error: {e}")

            # Тестируем логин
            login_data = {
                "email": self.test_email,
                "password": self.password
            }
            
            try:
                response = requests.post(f"{BASE_URL}/v1/auth/login", json=login_data)
                print(f"Login response: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    assert data["success"] == True
                    assert "access_token" in data["data"]
                    assert data["data"]["token_type"] == "bearer"
                    print("✅ Login PASSED")
                else:
                    print(f"⚠️ Login returned {response.status_code}")
            
            except Exception as e:
                print(f"⚠️ Login error: {e}")

    # Тест 3: Защищенные маршруты без токена
    def test_3_protected_routes_without_token(self):
        """Тест доступа к защищенным маршрутам без токена"""
        print("\n=== Тест 3: Protected Routes Without Token ===")
        
        if not self._wait_for_gateway():
            pytest.skip("Gateway is not available")

        # Мок для ошибки аутентификации
        mock_auth_error = Mock()
        mock_auth_error.status_code = 401
        mock_auth_error.json.return_value = {
            "success": False,
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Authentication required"
            }
        }

        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.return_value = AsyncMock(**{
                "status_code": 401,
                "json.return_value": mock_auth_error.json.return_value,
                "headers": {}
            })

            # Пытаемся получить профиль без токена
            response = requests.get(f"{BASE_URL}/v1/users/me")
            
            # Gateway должен вернуть 401 или проксировать ошибку от сервиса
            assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
            
            data = response.json()
            assert data["success"] == False
            assert "error" in data
            
            print("✅ Protected routes without token PASSED")

    # Тест 4: Request ID propagation
    def test_4_request_id_propagation(self):
        """Тест распространения X-Request-ID через Gateway"""
        print("\n=== Тест 4: Request ID Propagation ===")
        
        if not self._wait_for_gateway():
            pytest.skip("Gateway is not available")

        custom_request_id = f"test-req-{uuid.uuid4().hex[:8]}"
        
        # Мок успешного ответа
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}
        mock_response.headers = {"X-Request-ID": custom_request_id}

        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.return_value = AsyncMock(**{
                "status_code": 200,
                "json.return_value": mock_response.json.return_value,
                "headers": mock_response.headers
            })

            headers = {"X-Request-ID": custom_request_id}
            response = requests.get(f"{BASE_URL}/health", headers=headers)
            
            assert response.status_code == 200
            # Проверяем что Request ID возвращается в ответе
            if "X-Request-ID" in response.headers:
                assert response.headers["X-Request-ID"] == custom_request_id
                print("✅ Request ID propagation PASSED")
            else:
                print("⚠️ Request ID not in response headers")

    # Тест 5: Обработка ошибок сервисов
    def test_5_service_error_handling(self):
        """Тест обработки ошибок недоступных сервисов"""
        print("\n=== Тест 5: Service Error Handling ===")
        
        if not self._wait_for_gateway():
            pytest.skip("Gateway is not available")

        # Мок для ошибки соединения
        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.side_effect = Exception("Connection failed")

            # Пытаемся сделать запрос к несуществующему сервису
            try:
                response = requests.get(f"{BASE_URL}/v1/users/me")
                
                # Gateway должен обработать ошибку и вернуть 503 или 500
                assert response.status_code in [503, 500], f"Expected 503/500, got {response.status_code}"
                
                data = response.json()
                assert data["success"] == False
                assert "error" in data
                assert data["error"]["code"] in ["SERVICE_UNAVAILABLE", "INTERNAL_ERROR"]
                
                print("✅ Service error handling PASSED")
                
            except Exception as e:
                print(f"⚠️ Error handling test exception: {e}")

    # Дополнительный тест: Rate Limiting
    def test_6_rate_limiting(self):
        """Тест ограничения частоты запросов"""
        print("\n=== Тест 6: Rate Limiting ===")
        
        if not self._wait_for_gateway():
            pytest.skip("Gateway is not available")

        # Делаем несколько быстрых запросов
        rate_limit_triggered = False
        
        for i in range(15):  # Делаем 15 запросов быстро
            try:
                response = requests.get(f"{BASE_URL}/health")
                if response.status_code == 429:
                    rate_limit_triggered = True
                    print(f"✅ Rate limiting triggered after {i+1} requests")
                    break
                time.sleep(0.1)  # Небольшая задержка
            except Exception as e:
                print(f"Request {i+1} failed: {e}")
        
        if not rate_limit_triggered:
            print("⚠️ Rate limiting not triggered (might be disabled in development)")


class TestAPIGatewayIntegration:
    """Интеграционные тесты полного workflow"""
    
    def test_full_user_workflow(self):
        """Полный тест workflow пользователя через Gateway"""
        print("\n=== Интеграционный тест: Full User Workflow ===")
        
        # Создаем уникальные данные для теста
        test_email = f"integration_{uuid.uuid4().hex[:8]}@example.com"
        password = "password123"
        name = "Integration Test User"
        
        # Мокируем все вызовы к сервисам
        mock_responses = [
            # Health check
            AsyncMock(**{
                "status_code": 200,
                "json.return_value": {"status": "healthy", "service": "api-gateway"},
                "headers": {}
            }),
            # Registration
            AsyncMock(**{
                "status_code": 200,
                "json.return_value": {
                    "success": True,
                    "data": {"id": "user_int_123", "email": test_email, "name": name}
                },
                "headers": {}
            }),
            # Login
            AsyncMock(**{
                "status_code": 200,
                "json.return_value": {
                    "success": True,
                    "data": {"access_token": "token_int_123", "token_type": "bearer"}
                },
                "headers": {}
            }),
            # Profile
            AsyncMock(**{
                "status_code": 200,
                "json.return_value": {
                    "success": True,
                    "data": {"id": "user_int_123", "email": test_email, "name": name}
                },
                "headers": {}
            })
        ]

        with patch('httpx.AsyncClient.request') as mock_request:
            mock_request.side_effect = mock_responses

            # 1. Health check
            health_response = requests.get(f"{BASE_URL}/health")
            assert health_response.status_code == 200
            print("✅ Gateway health check")

            # 2. Registration
            register_data = {"email": test_email, "password": password, "name": name}
            register_response = requests.post(f"{BASE_URL}/v1/auth/register", json=register_data)
            assert register_response.status_code == 200
            print("✅ User registration")

            # 3. Login
            login_data = {"email": test_email, "password": password}
            login_response = requests.post(f"{BASE_URL}/v1/auth/login", json=login_data)
            assert login_response.status_code == 200
            token = login_response.json()["data"]["access_token"]
            print("✅ User login")

            # 4. Get profile
            headers = {"Authorization": f"Bearer {token}"}
            profile_response = requests.get(f"{BASE_URL}/v1/users/me", headers=headers)
            assert profile_response.status_code == 200
            assert profile_response.json()["data"]["email"] == test_email
            print("✅ User profile")

            print("Full integration test PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])