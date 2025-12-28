# auth.py
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt
import hashlib
from sqlalchemy.orm import Session

import database
from config import SECRET_KEY  # You might need to add this to config.py if not present

# ---------------- CONFIGURATION ----------------
# If SECRET_KEY is not in config.py, fallback to a hardcoded one (WARNING: UNSAFE FOR PRODUCTION)
if not locals().get("SECRET_KEY"):
    SECRET_KEY = "CHANGE_ME_IN_PRODUCTION_SECRET_KEY"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ---------------- HELPERS ----------------
def _prepare_password(password: str) -> bytes:
    """Prepare password for bcrypt hashing. Bcrypt has a 72-byte limit."""
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
    else:
        password_bytes = password
    
    # If password exceeds 72 bytes, hash it with SHA-256 first
    # This is a common workaround for bcrypt's 72-byte limit
    if len(password_bytes) > 72:
        password_bytes = hashlib.sha256(password_bytes).digest()
    
    return password_bytes

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash"""
    # Ensure hashed_password is bytes
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    
    # Prepare password (hash with SHA-256 if > 72 bytes)
    password_bytes = _prepare_password(plain_password)
    
    return bcrypt.checkpw(password_bytes, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    # Prepare password (hash with SHA-256 if > 72 bytes)
    password_bytes = _prepare_password(password)
    
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string for database storage
    return hashed.decode('utf-8')

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
    # #region agent log
    import json
    import time
    import os
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_path = os.path.join(BASE_DIR, '.cursor', 'debug.log')
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"AUTH","location":"auth.py:117","message":"get_current_user called","data":{"has_token":token is not None,"token_length":len(token) if token else 0,"token_preview":token[:20] if token else None},"timestamp":int(time.time()*1000)})+'\n')
    except Exception:
        pass
    # #endregion
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"AUTH","location":"auth.py:124","message":"Token decoded successfully","data":{"username":username},"timestamp":int(time.time()*1000)})+'\n')
        except Exception:
            pass
        # #endregion
        if username is None:
            raise credentials_exception
    except JWTError as e:
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"AUTH","location":"auth.py:128","message":"JWT decode error","data":{"error_type":type(e).__name__,"error_msg":str(e)},"timestamp":int(time.time()*1000)})+'\n')
        except Exception:
            pass
        # #endregion
        raise credentials_exception
        
    user = database.get_user_by_username(username)
    if user is None:
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"AUTH","location":"auth.py:132","message":"User not found in database","data":{"username":username},"timestamp":int(time.time()*1000)})+'\n')
        except Exception:
            pass
        # #endregion
        raise credentials_exception
        
    # Return a dict-like object or Pydantic model can handle the ORM object mostly, 
    # but for safety let's return a simple dict for the route to consume
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email
    }

async def get_current_user_optional(token: Optional[str] = None):
    """Optional authentication - returns None if no valid token, user dict if authenticated"""
    # #region agent log
    import json
    import os
    import time
    log_path = os.path.join(os.path.dirname(__file__), '..', '.cursor', 'debug.log')
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"auth.py:143","message":"get_current_user_optional called","data":{"has_token":token is not None,"token_length":len(token) if token else 0},"timestamp":int(time.time()*1000)})+'\n')
    except Exception:
        pass
    # #endregion
    
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"auth.py:152","message":"JWT decode success but no username","data":{},"timestamp":int(time.time()*1000)})+'\n')
            except Exception:
                pass
            # #endregion
            return None
    except JWTError as e:
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"auth.py:160","message":"JWT decode failed","data":{"error":str(e)},"timestamp":int(time.time()*1000)})+'\n')
        except Exception:
            pass
        # #endregion
        return None
        
    user = database.get_user_by_username(username)
    if user is None:
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"auth.py:167","message":"User not found in database","data":{"username":username},"timestamp":int(time.time()*1000)})+'\n')
        except Exception:
            pass
        # #endregion
        return None
    
    # #region agent log
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"auth.py:172","message":"Authentication successful","data":{"username":user.username,"user_id":user.id},"timestamp":int(time.time()*1000)})+'\n')
    except Exception:
        pass
    # #endregion
        
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email
    }
