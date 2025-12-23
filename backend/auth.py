# auth.py
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import database
from config import SECRET_KEY  # You might need to add this to config.py if not present

# ---------------- CONFIGURATION ----------------
# If SECRET_KEY is not in config.py, fallback to a hardcoded one (WARNING: UNSAFE FOR PRODUCTION)
if not locals().get("SECRET_KEY"):
    SECRET_KEY = "CHANGE_ME_IN_PRODUCTION_SECRET_KEY"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ---------------- HELPERS ----------------
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ---------------- AUTH FUNCTIONS ----------------
def register_user(username: str, password: str, email: Optional[str] = None):
    # Check if user exists
    if database.get_user_by_username(username):
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(password)
    user_id = database.create_user(username, email, hashed_password)
    
    # Create token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id,
        "username": username
    }

def authenticate_user(username: str, password: str):
    user = database.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # SQLAlchemy model access (dot notation)
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = database.get_user_by_username(username)
    if user is None:
        raise credentials_exception
        
    # Return a dict-like object or Pydantic model can handle the ORM object mostly, 
    # but for safety let's return a simple dict for the route to consume
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email
    }
