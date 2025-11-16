# api_gateway/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import uuid
import time
from typing import Dict, Tuple
import asyncio

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Получаем или создаем request_id
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        
        # Обрабатываем запрос
        response = await call_next(request)
        
        # Добавляем request_id в заголовки ответа
        response.headers['X-Request-ID'] = request_id
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Очищаем старые запросы
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if current_time - req_time < self.window_seconds
            ]
        
        # Проверяем лимит
        if client_ip in self.requests and len(self.requests[client_ip]) >= self.max_requests:
            return Response(
                content='{"success": false, "error": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json"
            )
        
        # Добавляем текущий запрос
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(current_time)
        
        # Продолжаем обработку
        response = await call_next(request)
        return response