import logging
from typing import List, Optional
from datetime import datetime
from .models import Order, OrderItem, OrderStatus
import uuid

logger = logging.getLogger(__name__)

orders_db: List[Order] = []

class OrderDB:
    @staticmethod
    def create_order(order_data: dict) -> Order:
        order = Order(**order_data)
        orders_db.append(order)
        logger.info(f"Order created: {order.id} for user: {order.user_id}")
        return order
    
    @staticmethod
    def get_order_by_id(order_id: str) -> Optional[Order]:
        return next((order for order in orders_db if order.id == order_id), None)
    
    @staticmethod
    def get_orders_by_user(user_id: str, skip: int = 0, limit: int = 100, status_filter: str = None) -> List[Order]:
        user_orders = [order for order in orders_db if order.user_id == user_id]
        
        if status_filter:
            user_orders = [order for order in user_orders if order.status == status_filter]
        
        user_orders.sort(key=lambda x: x.created_at, reverse=True)
        
        return user_orders[skip:skip + limit]
    
    @staticmethod
    def get_user_orders_count(user_id: str, status_filter: str = None) -> int:
        user_orders = [order for order in orders_db if order.user_id == user_id]
        
        if status_filter:
            user_orders = [order for order in user_orders if order.status == status_filter]
        
        return len(user_orders)
    
    @staticmethod
    def update_order_status(order_id: str, new_status: OrderStatus) -> Optional[Order]:
        order = OrderDB.get_order_by_id(order_id)
        if order:
            order.status = new_status
            order.updated_at = datetime.utcnow()
            logger.info(f"Order status updated: {order_id} -> {new_status}")
        return order
    
    @staticmethod
    def can_user_access_order(order: Order, user: dict) -> bool:
        return order.user_id == user.get("user_id") or "admin" in user.get("roles", [])
    
    @staticmethod
    def calculate_total_amount(items: List[OrderItem]) -> float:
        return sum(item.quantity * item.price for item in items)
    
    @staticmethod
    def get_all_orders(skip: int = 0, limit: int = 100) -> List[Order]:
        return orders_db[skip:skip + limit]
    
    @staticmethod
    def get_total_orders_count() -> int:
        return len(orders_db)