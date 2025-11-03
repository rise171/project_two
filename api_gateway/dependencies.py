from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
import os
from typing import Dict, Any

security = HTTPBearer()

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")
#валидация токенов
async def verify_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = None
) -> Dict[str, Any]:
    public_paths = ["/v1/auth/register", "/v1/auth/login", "/docs", "/openapi.json"]
    if any(request.url.path.endswith(path) for path in public_paths):
        return {"user_id": "anonymous", "roles": []}
    
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")