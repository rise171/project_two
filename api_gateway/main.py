from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import uuid
import time
import logging
from middleware import RateLimitMiddleware, RequestIDMiddleware
from dependencies import verify_token

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API Gateway",
    version="1.0.0",
    description="Gateway for microservices task management system"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(RateLimitMiddleware, calls=100, period=60)

security = HTTPBearer()

USER_SERVICE_URL = "http://users-service:8001"
ORDER_SERVICE_URL = "http://orders-service:8002"

DEV_USER_SERVICE_URL = "http://localhost:8001"
DEV_ORDER_SERVICE_URL = "http://localhost:8002"

def get_service_urls():
    import os
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "development":
        return DEV_USER_SERVICE_URL, DEV_ORDER_SERVICE_URL
    else:
        return USER_SERVICE_URL, ORDER_SERVICE_URL

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = getattr(request.state, 'request_id', 'unknown')
    logger.info(f"Request: {request.method} {request.url.path} - ID: {request_id}")
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(f"Response: {response.status_code} - Time: {process_time:.3f}s - ID: {request_id}")
    
    return response

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api-gateway"}

@app.api_route("/v1/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_users(
    request: Request, 
    path: str, 
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(verify_token)
):
    user_service_url, _ = get_service_urls()
    return await proxy_request(request, user_service_url, path)

@app.api_route("/v1/auth/{path:path}", methods=["POST"])
async def proxy_auth(request: Request, path: str):
    user_service_url, _ = get_service_urls()
    return await proxy_request(request, user_service_url, f"auth/{path}")

@app.api_route("/v1/orders/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_orders(
    request: Request, 
    path: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(verify_token)
):
    _, order_service_url = get_service_urls()
    return await proxy_request(request, order_service_url, path)

async def proxy_request(request: Request, base_url: str, path: str):
    # Формируем URL целевого сервиса
    url = f"{base_url}/v1/{path}" if path else f"{base_url}/v1/{request.url.path.split('/')[-1]}"
    # Подготавливаем заголовки
    headers = dict(request.headers)
    headers.pop("host", None) # Удаляем host оригинального запроса
    
    request_id = getattr(request.state, 'request_id', None)
    if request_id:
        headers["X-Request-ID"] = request_id
    
    try:
        #Отправляем запрос в целевой сервис
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=await request.body(),
                params=dict(request.query_params)
            )
        #Возвращаем ответ от сервиса
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    
    except httpx.ConnectError:
        logger.error(f"Cannot connect to service: {base_url}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": {
                    "code": "SERVICE_UNAVAILABLE",
                    "message": "Service temporarily unavailable"
                }
            }
        )
    except Exception as e:
        logger.error(f"Proxy error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error"
                }
            }
        )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, 'request_id', 'unknown')
    logger.warning(f"HTTPException: {exc.status_code} - {exc.detail} - ID: {request_id}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail
            }
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")