from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
import uuid
from enum import Enum

class OrderStatus(str, Enum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class OrderItem(BaseModel):
    product_id: str = Field(..., description="ID продукта")
    product_name: str = Field(..., description="Название продукта")
    quantity: int = Field(..., ge=1, description="Количество")
    price: float = Field(..., ge=0, description="Цена за единицу")

class Order(BaseModel):
    id: str
    user_id: str
    items: List[OrderItem]
    status: OrderStatus
    total_amount: float
    created_at: datetime
    updated_at: datetime

class OrderCreate(BaseModel):
    items: List[OrderItem] = Field(..., min_items=1, description="Список товаров")

class OrderResponse(BaseModel):
    id: str
    user_id: str
    items: List[OrderItem]
    status: OrderStatus
    total_amount: float
    created_at: datetime
    updated_at: datetime

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None

class StandardResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[dict] = None

class OrderListResponse(BaseModel):
    orders: List[OrderResponse]
    pagination: dict