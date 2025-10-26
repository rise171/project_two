from fastapi import FastAPI, Depends, HTTPException, status, Query, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
import uuid
from datetime import datetime
import jwt
from passlib.context import CryptContext
from typing import List, Optional
import logging
from dependencies import verify_token 
from models import UserCreate, StandardResponse, User, UserLogin, UserResponse
from auth import verify_password, get_password_hash, create_access_token
from database import users_db, UserDB as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="User Service", version="1.0.0")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = "your-secret-key"
ALGORITHM = "HS256"


@app.post("/v1/auth/register", response_model=StandardResponse)
async def register(user_data: UserCreate, request: Request):
    logger.info(f"Registration attempt for email: {user_data.email}")
    
    if db.get_user_by_email(user_data.email):
        return StandardResponse(
            success=False,
            error={"code": "USER_EXISTS", "message": "User already exists"}
        )
    
    user_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    user = User(
        id=user_id,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        name=user_data.name,
        roles=["user"],
        created_at=now,
        updated_at=now
    )
    
    users_db.append(user)
    
    logger.info(f"User registered successfully: {user_id}")
    
    return StandardResponse(
        success=True,
        data={"id": user_id}
    )

@app.post("/v1/auth/login", response_model=StandardResponse)
async def login(login_data: UserLogin, request: Request):
    logger.info(f"Login attempt for email: {login_data.email}")
    
    user = db.get_user_by_email(login_data.email)
    if not user or not verify_password(login_data.password, user.password_hash):
        return StandardResponse(
            success=False,
            error={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"}
        )
    
    access_token = create_access_token({"user_id": user.id, "email": user.email, "roles": user.roles})
    
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
async def get_current_user(request: Request, current_user: dict = Depends(verify_token)):
    user = db.get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return StandardResponse(
        success=True,
        data=UserResponse(**user.dict()).dict()
    )

@app.put("/v1/users/me", response_model=StandardResponse)
async def update_current_user(update_data: dict, request: Request, current_user: dict = Depends(verify_token)):
    user = db.get_user_by_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if "name" in update_data:
        user.name = update_data["name"]
    user.updated_at = datetime.utcnow()
    
    return StandardResponse(
        success=True,
        data=UserResponse(**user.dict()).dict()
    )

@app.get("/v1/users", response_model=StandardResponse)
async def get_users(
    request: Request,
    current_user: dict = Depends(verify_token),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    email: Optional[str] = None
):
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    filtered_users = users_db
    if email:
        filtered_users = [u for u in filtered_users if email in u.email]
    
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_users = filtered_users[start_idx:end_idx]
    
    return StandardResponse(
        success=True,
        data={
            "users": [UserResponse(**user.dict()).dict() for user in paginated_users],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(filtered_users),
                "pages": (len(filtered_users) + limit - 1) // limit
            }
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)