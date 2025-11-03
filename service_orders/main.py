from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
import uuid
import logging
from datetime import datetime
from typing import Optional

from models import OrderCreate, OrderResponse, StandardResponse, OrderStatus, OrderUpdate
from database import order_db


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Order Service",
    version="1.0.0",
    description="Order management service"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JWT_SECRET = "your-secret-key"
ALGORITHM = "HS256"
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    class RequestIDFilter(logging.Filter):
        def filter(self, record):
            record.request_id = request_id
            return True
    
    logger.addFilter(RequestIDFilter())
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "order-service"}

@app.post("/v1/orders", response_model=StandardResponse)
async def create_order(
    order_data: OrderCreate,
    request: Request,
    current_user: dict = Depends(verify_token)
):
    logger.info(f"Creating order for user: {current_user['user_id']}")
    
    if not order_data.items:
        return StandardResponse(
            success=False,
            error={"code": "INVALID_ORDER", "message": "Order must contain at least one item"}
        )
    
    total_amount = order_db.calculate_total_amount(order_data.items)
    
    order_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    order = order_db.create_order({
        "id": order_id,
        "user_id": current_user["user_id"],
        "items": order_data.items,
        "status": OrderStatus.CREATED,
        "total_amount": total_amount,
        "created_at": now,
        "updated_at": now
    })
    
    if not order:
        return StandardResponse(
            success=False,
            error={"code": "CREATION_FAILED", "message": "Failed to create order"}
        )
    
    logger.info(f"Order created successfully: {order_id} - Total: {total_amount}")
    
    return StandardResponse(
        success=True,
        data=OrderResponse(**order.dict()).dict()
    )

@app.get("/v1/orders/{order_id}", response_model=StandardResponse)
async def get_order(
    order_id: str,
    request: Request,
    current_user: dict = Depends(verify_token)
):
    order = order_db.get_order_by_id(order_id)
    if not order:
        return StandardResponse(
            success=False,
            error={"code": "ORDER_NOT_FOUND", "message": "Order not found"}
        )
    
    if not order_db.can_user_access_order(order, current_user):
        logger.warning(f"Unauthorized access attempt to order {order_id} by user {current_user['user_id']}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    return StandardResponse(
        success=True,
        data=OrderResponse(**order.dict()).dict()
    )

@app.get("/v1/orders", response_model=StandardResponse)
async def get_orders(
    request: Request,
    current_user: dict = Depends(verify_token),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[OrderStatus] = Query(None, description="Filter by status")
):
    skip = (page - 1) * limit
    
    user_orders = order_db.get_orders_by_user(
        current_user["user_id"], 
        skip, 
        limit, 
        status.value if status else None
    )
    
    total_orders = order_db.get_user_orders_count(
        current_user["user_id"], 
        status.value if status else None
    )
    
    total_pages = (total_orders + limit - 1) // limit if total_orders > 0 else 1
    
    logger.info(f"Orders list accessed by user: {current_user['user_id']} - Total: {total_orders}")
    
    return StandardResponse(
        success=True,
        data={
            "orders": [OrderResponse(**order.dict()).dict() for order in user_orders],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_orders,
                "pages": total_pages
            }
        }
    )

@app.put("/v1/orders/{order_id}/status", response_model=StandardResponse)
async def update_order_status(
    order_id: str,
    status_update: OrderUpdate,
    request: Request,
    current_user: dict = Depends(verify_token)
):
    order = order_db.get_order_by_id(order_id)
    if not order:
        return StandardResponse(
            success=False,
            error={"code": "ORDER_NOT_FOUND", "message": "Order not found"}
        )
    
    if not order_db.can_user_access_order(order, current_user):
        logger.warning(f"Unauthorized status update attempt for order {order_id} by user {current_user['user_id']}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not status_update.status:
        return StandardResponse(
            success=False,
            error={"code": "INVALID_STATUS", "message": "Status is required"}
        )
    
    updated_order = order_db.update_order_status(order_id, status_update.status)
    
    if not updated_order:
        return StandardResponse(
            success=False,
            error={"code": "UPDATE_FAILED", "message": "Failed to update order status"}
        )
    
    logger.info(f"Order status updated: {order_id} -> {status_update.status} by user: {current_user['user_id']}")
    
    return StandardResponse(
        success=True,
        data=OrderResponse(**updated_order.dict()).dict()
    )

@app.delete("/v1/orders/{order_id}", response_model=StandardResponse)
async def cancel_order(
    order_id: str,
    request: Request,
    current_user: dict = Depends(verify_token)
):
    order = order_db.get_order_by_id(order_id)
    if not order:
        return StandardResponse(
            success=False,
            error={"code": "ORDER_NOT_FOUND", "message": "Order not found"}
        )
    
    if order.user_id != current_user["user_id"]:
        logger.warning(f"Unauthorized cancel attempt for order {order_id} by user {current_user['user_id']}")
        raise HTTPException(status_code=403, detail="Can only cancel your own orders")
    
    if order.status == OrderStatus.CANCELLED:
        return StandardResponse(
            success=False,
            error={"code": "ALREADY_CANCELLED", "message": "Order already cancelled"}
        )
    
    updated_order = order_db.update_order_status(order_id, OrderStatus.CANCELLED)
    
    if not updated_order:
        return StandardResponse(
            success=False,
            error={"code": "CANCEL_FAILED", "message": "Failed to cancel order"}
        )
    
    logger.info(f"Order cancelled: {order_id} by user: {current_user['user_id']}")
    
    return StandardResponse(
        success=True,
        data=OrderResponse(**updated_order.dict()).dict()
    )

@app.get("/v1/admin/orders", response_model=StandardResponse)
async def get_all_orders(
    request: Request,
    current_user: dict = Depends(verify_token),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page")
):
    if "admin" not in current_user.get("roles", []):
        logger.warning(f"Unauthorized access to admin orders by: {current_user['user_id']}")
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    skip = (page - 1) * limit
    
    all_orders = order_db.get_all_orders(skip, limit)
    total_orders = order_db.get_total_orders_count()
    total_pages = (total_orders + limit - 1) // limit if total_orders > 0 else 1
    
    logger.info(f"All orders accessed by admin: {current_user['user_id']} - Total: {total_orders}")
    
    return StandardResponse(
        success=True,
        data={
            "orders": [OrderResponse(**order.dict()).dict() for order in all_orders],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_orders,
                "pages": total_pages
            }
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.error(f"HTTPException: {exc.status_code} - {exc.detail} - ID: {request_id}")
    
    return StandardResponse(
        success=False,
        error={
            "code": "HTTP_ERROR",
            "message": exc.detail
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.error(f"Unhandled exception: {str(exc)} - ID: {request_id}")
    
    return StandardResponse(
        success=False,
        error={
            "code": "INTERNAL_ERROR",
            "message": "Internal server error"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")