import logging
import sqlite3
import json
from typing import List, Optional
from datetime import datetime
from .models import Order, OrderItem, OrderStatus
import os

logger = logging.getLogger(__name__)

#configuration
DATABASE_URL = os.getenv("DATABASE_URL", "orders.db")

class OrderDB:
    def __init__(self):
        self.db_path = DATABASE_URL
        self.init_database()

    def init_database(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create orders table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS orders (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        items TEXT NOT NULL,
                        status TEXT NOT NULL,
                        total_amount REAL NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')
                
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)')
                
                conn.commit()
                logger.info("Orders database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def _order_from_row(self, row) -> Order:
        if not row:
            return None
        
        items_data = json.loads(row[2])
        items = [OrderItem(**item) for item in items_data]
        
        return Order(
            id=row[0],
            user_id=row[1],
            items=items,
            status=OrderStatus(row[3]),
            total_amount=row[4],
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6])
        )

    def create_order(self, order_data: dict) -> Optional[Order]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Convert items to JSON string
                items_json = json.dumps([item.dict() for item in order_data['items']])
                created_at = order_data['created_at'].isoformat()
                updated_at = order_data['updated_at'].isoformat()
                
                cursor.execute('''
                    INSERT INTO orders (id, user_id, items, status, total_amount, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    order_data['id'],
                    order_data['user_id'],
                    items_json,
                    order_data['status'].value,
                    order_data['total_amount'],
                    created_at,
                    updated_at
                ))
                
                conn.commit()
                logger.info(f"Order created: {order_data['id']} for user: {order_data['user_id']}")
                
                return Order(**order_data)
                
        except sqlite3.Error as e:
            logger.error(f"Error creating order: {e}")
            return None

    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT * FROM orders WHERE id = ?', 
                    (order_id,)
                )
                row = cursor.fetchone()
                return self._order_from_row(row)
                
        except sqlite3.Error as e:
            logger.error(f"Error getting order by ID {order_id}: {e}")
            return None

    def get_orders_by_user(self, user_id: str, skip: int = 0, limit: int = 100, status_filter: str = None) -> List[Order]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM orders WHERE user_id = ?"
                params = [user_id]
                
                if status_filter:
                    query += " AND status = ?"
                    params.append(status_filter)
                
                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, skip])
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [self._order_from_row(row) for row in rows if row]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting orders for user {user_id}: {e}")
            return []

    def get_user_orders_count(self, user_id: str, status_filter: str = None) -> int:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT COUNT(*) FROM orders WHERE user_id = ?"
                params = [user_id]
                
                if status_filter:
                    query += " AND status = ?"
                    params.append(status_filter)
                
                cursor.execute(query, params)
                result = cursor.fetchone()
                
                return result[0] if result else 0
                
        except sqlite3.Error as e:
            logger.error(f"Error getting orders count for user {user_id}: {e}")
            return 0

    def update_order_status(self, order_id: str, new_status: OrderStatus) -> Optional[Order]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                updated_at = datetime.utcnow().isoformat()
                
                cursor.execute('''
                    UPDATE orders 
                    SET status = ?, updated_at = ? 
                    WHERE id = ?
                ''', (new_status.value, updated_at, order_id))
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Order status updated: {order_id} -> {new_status}")
                    return self.get_order_by_id(order_id)
                else:
                    return None
                    
        except sqlite3.Error as e:
            logger.error(f"Error updating order status {order_id}: {e}")
            return None

    def can_user_access_order(self, order: Order, user: dict) -> bool:
        return order.user_id == user.get("user_id") or "admin" in user.get("roles", [])

    def calculate_total_amount(self, items: List[OrderItem]) -> float:
        return sum(item.quantity * item.price for item in items)

    def get_all_orders(self, skip: int = 0, limit: int = 100) -> List[Order]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    'SELECT * FROM orders ORDER BY created_at DESC LIMIT ? OFFSET ?',
                    (limit, skip)
                )
                rows = cursor.fetchall()
                
                return [self._order_from_row(row) for row in rows if row]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting all orders: {e}")
            return []

    def get_total_orders_count(self) -> int:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM orders')
                result = cursor.fetchone()
                
                return result[0] if result else 0
                
        except sqlite3.Error as e:
            logger.error(f"Error getting total orders count: {e}")
            return 0

    def delete_order(self, order_id: str) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM orders WHERE id = ?', (order_id,))
                conn.commit()
                
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"Order deleted: {order_id}")
                
                return deleted
                
        except sqlite3.Error as e:
            logger.error(f"Error deleting order {order_id}: {e}")
            return False

order_db = OrderDB()