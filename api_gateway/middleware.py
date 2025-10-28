import uuid
import time
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from collections import defaultdict
from typing import Dict, List

# идентификацию запросов и ограничение частоты запросов

class RequestIDMiddleware:
    async def __call__(self, request: Request, call_next):
        # Получаем X-Request-ID из заголовков или генерируем новый UUID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

class RateLimitMiddleware:
    def __init__(self, calls: int = 100, period: int = 60):
        self.calls = calls
        self.period = period
        self.requests: Dict[str, List[float]] = defaultdict(list)
    
    async def __call__(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()
        
        #Очищаем старые запросы (старше period секунд)
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if now - req_time < self.period
        ]
        #не превышен ли лимит
        if len(self.requests[client_ip]) >= self.calls:
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests"
                    }
                }
            )
        #текущий запрос в историю
        self.requests[client_ip].append(now)
        return await call_next(request)