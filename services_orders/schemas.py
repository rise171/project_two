from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .models import OrderStatus

class OrderItemSchema(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    price: float

    class Config:
        from_attributes = True

class OrderSchema(BaseModel):
    id: str
    user_id: str
    items: List[OrderItemSchema]
    status: OrderStatus
    total_amount: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OrderCreateSchema(BaseModel):
    items: List[OrderItemSchema]

class OrderUpdateSchema(BaseModel):
    status: Optional[OrderStatus] = None

class PaginationSchema(BaseModel):
    page: int
    limit: int
    total: int
    pages: int

class OrderListSchema(BaseModel):
    orders: List[OrderSchema]
    pagination: PaginationSchema