from datetime import datetime, timedelta
from typing import Optional
import os
import bcrypt
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import database

# ✅ ENV BASED SECRET (Render safe)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer()

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_access_token(data: dict):
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    payload = verify_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("user_id")
    user = database.get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

def register_user(username: str, password: str, email: Optional[str] = None):
    if database.get_user_by_username(username):
        raise ValueError("Username already exists")

    hashed = get_password_hash(password)
    user_id = database.create_user(username, email, hashed)

    token = create_access_token({
        "user_id": user_id,
        "username": username
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user_id, "username": username, "email": email}
    }

def authenticate_user(username: str, password: str):
    user = database.get_user_by_username(username)

    if not user or not verify_password(password, user["hashed_password"]):
        raise ValueError("Invalid username or password")

    token = create_access_token({
        "user_id": user["id"],
        "username": user["username"]
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        }
    }

