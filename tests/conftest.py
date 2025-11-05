import pytest
import requests
import time
import uuid

API_GATEWAY_URL = "http://localhost:8000"
USER_SERVICE_URL = "http://localhost:8001"
ORDER_SERVICE_URL = "http://localhost:8002"

def wait_for_services():
    print("⏳ Waiting for services to start...")
    
    for i in range(30):
        try:
            responses = [
                requests.get(f"{API_GATEWAY_URL}/health", timeout=2),
                requests.get(f"{USER_SERVICE_URL}/health", timeout=2),
                requests.get(f"{ORDER_SERVICE_URL}/health", timeout=2)
            ]
            
            if all(r.status_code == 200 for r in responses):
                print("All services are ready!")
                return True
        except:
            pass
        
        if i % 5 == 0:
            print(f"Attempt {i+1}/30...")
        time.sleep(2)
    
    print("Services didnt start in time")
    return False

@pytest.fixture(scope="session", autouse=True)
def check_services():
    """Проверка доступности сервисов перед запуском тестов"""
    if not wait_for_services():
        pytest.skip("Services arent available")