import logging
import sqlite3
from typing import List, Optional
from datetime import datetime
from schemas import User
import os

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "users.db")

class UserDB:
    def __init__(self):
        self.db_path = DATABASE_URL
        self.init_database()

    def init_database(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        name TEXT NOT NULL,
                        roles TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP NOT NULL
                    )
                ''')
                
                # index
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def _user_from_row(self, row) -> User:
        if not row:
            return None
        
        return User(
            id=row[0],
            email=row[1],
            password_hash=row[2],
            name=row[3],
            roles=row[4].split(','), 
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6])
        )

    def get_user_by_email(self, email: str) -> Optional[User]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT * FROM users WHERE email = ?', 
                    (email,)
                )
                row = cursor.fetchone()
                return self._user_from_row(row)
                
        except sqlite3.Error as e:
            logger.error(f"Error getting user by email {email}: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT * FROM users WHERE id = ?', 
                    (user_id,)
                )
                row = cursor.fetchone()
                return self._user_from_row(row)
                
        except sqlite3.Error as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None

    def create_user(self, user_data: dict) -> Optional[User]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                roles_str = ','.join(user_data['roles'])
                created_at = user_data['created_at'].isoformat()
                updated_at = user_data['updated_at'].isoformat()
                
                cursor.execute('''
                    INSERT INTO users (id, email, password_hash, name, roles, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_data['id'],
                    user_data['email'],
                    user_data['password_hash'],
                    user_data['name'],
                    roles_str,
                    created_at,
                    updated_at
                ))
                
                conn.commit()
                logger.info(f"User created: {user_data['id']}")
                
                return User(**user_data)
                
        except sqlite3.IntegrityError:
            logger.warning(f"User with email {user_data['email']} already exists")
            return None
        except sqlite3.Error as e:
            logger.error(f"Error creating user: {e}")
            return None

    def update_user(self, user_id: str, update_data: dict) -> Optional[User]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                set_clauses = []
                params = []
                
                for key, value in update_data.items():
                    if value is not None:
                        if key == 'roles' and isinstance(value, list):
                            value = ','.join(value)
                        set_clauses.append(f"{key} = ?")
                        params.append(value)
                
                if not set_clauses:
                    return self.get_user_by_id(user_id)
                
                set_clauses.append("updated_at = ?")
                params.append(datetime.utcnow().isoformat())
                
                params.append(user_id)
                
                query = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?"
                cursor.execute(query, params)
                
                conn.commit()
                logger.info(f"User updated: {user_id}")
                
                return self.get_user_by_id(user_id)
                
        except sqlite3.Error as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return None

    def get_all_users(self, skip: int = 0, limit: int = 100, email_filter: str = None) -> List[User]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM users"
                params = []
                
                if email_filter:
                    query += " WHERE email LIKE ?"
                    params.append(f"%{email_filter}%")
                
                query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, skip])
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [self._user_from_row(row) for row in rows if row]
                
        except sqlite3.Error as e:
            logger.error(f"Error getting all users: {e}")
            return []

    def get_users_count(self, email_filter: str = None) -> int:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT COUNT(*) FROM users"
                params = []
                
                if email_filter:
                    query += " WHERE email LIKE ?"
                    params.append(f"%{email_filter}%")
                
                cursor.execute(query, params)
                result = cursor.fetchone()
                
                return result[0] if result else 0
                
        except sqlite3.Error as e:
            logger.error(f"Error getting users count: {e}")
            return 0

    def delete_user(self, user_id: str) -> bool: 
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                conn.commit()
                
                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"User deleted: {user_id}")
                
                return deleted
                
        except sqlite3.Error as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return False

user_db = UserDB()