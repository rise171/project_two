import logging
from typing import List, Optional
from models import User
from datetime import datetime

logger = logging.getLogger(__name__)

# Mock database (in production use real database)
users_db: List[User] = []

class UserDB:
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Find user by email"""
        return next((user for user in users_db if user.email == email), None)
    
    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[User]:
        """Find user by ID"""
        return next((user for user in users_db if user.id == user_id), None)
    
    @staticmethod
    def create_user(user_data: dict) -> User:
        """Create new user"""
        user = User(**user_data)
        users_db.append(user)
        logger.info(f"User created: {user.id}")
        return user
    
    @staticmethod
    def update_user(user_id: str, update_data: dict) -> Optional[User]:
        """Update user data"""
        user = UserDB.get_user_by_id(user_id)
        if user:
            for key, value in update_data.items():
                if value is not None and hasattr(user, key):
                    setattr(user, key, value)
            user.updated_at = datetime.utcnow()
            logger.info(f"User updated: {user_id}")
        return user
    
    @staticmethod
    def get_all_users(skip: int = 0, limit: int = 100, email_filter: str = None) -> List[User]:
        """Get all users with pagination and filtering"""
        users = users_db
        
        if email_filter:
            users = [user for user in users if email_filter.lower() in user.email.lower()]
        
        return users[skip:skip + limit]
    
    @staticmethod
    def get_users_count(email_filter: str = None) -> int:
        """Get total users count"""
        if email_filter:
            return len([user for user in users_db if email_filter.lower() in user.email.lower()])
        return len(users_db)