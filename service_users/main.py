from fastapi import FastAPI, Depends, HTTPException, Request, Query
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
import uuid
from datetime import datetime
from jose import jwt
from passlib.context import CryptContext
from typing import List, Optional
import logging

from schemas import UserCreate, UserLogin, UserResponse, UserUpdate, StandardResponse
from database import user_db 
from auth import verify_password, get_password_hash, create_access_token
from dependencies import verify_token

# Configure
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="User Service",
    version="1.0.0",
    description="User management and authentication service"
)

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = "your-secret-key"
ALGORITHM = "HS256"
security = HTTPBearer()


@app.post("/v1/auth/register", response_model=StandardResponse)
async def register(user_data: UserCreate, request: Request):
    logger.info(f"Registration attempt for email: {user_data.email}")
    
    existing_user = user_db.get_user_by_email(user_data.email)
    if existing_user:
        logger.warning(f"Registration failed - user exists: {user_data.email}")
        return StandardResponse(
            success=False,
            error={"code": "USER_EXISTS", "message": "User with this email already exists"}
        )
    
    user_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    user = user_db.create_user({
        "id": user_id,
        "email": user_data.email,
        "password_hash": get_password_hash(user_data.password),
        "name": user_data.name,
        "roles": ["user"],
        "created_at": now,
        "updated_at": now
    })
    
    if not user:
        return StandardResponse(
            success=False,
            error={"code": "CREATION_FAILED", "message": "Failed to create user"}
        )
    
    logger.info(f"User registered successfully: {user_id}")
    
    return StandardResponse(
        success=True,
        data={"id": user_id}
    )

@app.post("/v1/auth/login", response_model=StandardResponse)
async def login(login_data: UserLogin, request: Request):
    logger.info(f"Login attempt for email: {login_data.email}")
    
    user = user_db.get_user_by_email(login_data.email)
    if not user or not verify_password(login_data.password, user.password_hash):
        logger.warning(f"Login failed - invalid credentials: {login_data.email}")
        return StandardResponse(
            success=False,
            error={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"}
        )
    
    access_token = create_access_token(
        data={"user_id": user.id, "email": user.email, "roles": user.roles}
    )
    
    logger.info(f"User logged in successfully: {user.id}")
    
    return StandardResponse(
        success=True,
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse(**user.dict()).dict()
        }
    )

@app.get("/v1/users/me", response_model=StandardResponse)
async def get_current_user(
    request: Request, 
    current_user: dict = Depends(verify_token)
):
    user = user_db.get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return StandardResponse(
        success=True,
        data=UserResponse(**user.dict()).dict()
    )

@app.put("/v1/users/me", response_model=StandardResponse)
async def update_current_user(
    update_data: UserUpdate,
    request: Request,
    current_user: dict = Depends(verify_token)
):
    user = user_db.get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_dict = update_data.dict(exclude_unset=True)
    updated_user = user_db.update_user(user.id, update_dict)
    
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    logger.info(f"User profile updated: {user.id}")
    
    return StandardResponse(
        success=True,
        data=UserResponse(**updated_user.dict()).dict()
    )

@app.get("/v1/users", response_model=StandardResponse)
async def get_users(
    request: Request,
    current_user: dict = Depends(verify_token),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    email: Optional[str] = Query(None, description="Filter by email")
):
    if "admin" not in current_user.get("roles", []):
        logger.warning(f"Unauthorized access to users list by: {current_user['user_id']}")
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    skip = (page - 1) * limit
    
    users = user_db.get_all_users(skip, limit, email)
    total_users = user_db.get_users_count(email)
    total_pages = (total_users + limit - 1) // limit if total_users > 0 else 1
    
    logger.info(f"Users list accessed by admin: {current_user['user_id']}")
    
    return StandardResponse(
        success=True,
        data={
            "users": [UserResponse(**user.dict()).dict() for user in users],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_users,
                "pages": total_pages
            }
        }
    )