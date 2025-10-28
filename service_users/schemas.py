from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional
import uuid

class User(BaseModel):
    id: str
    email: str
    password_hash: str
    name: str
    roles: List[str]
    created_at: datetime
    updated_at: datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    roles: List[str]
    created_at: datetime
    updated_at: datetime

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class StandardResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[dict] = None

class UserListResponse(BaseModel):
    users: List[UserResponse]
    pagination: dict