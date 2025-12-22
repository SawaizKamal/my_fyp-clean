from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import database

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# HTTP Bearer token
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    try:
        # Ensure password is bytes for bcrypt
        if isinstance(plain_password, str):
            password_bytes = plain_password.encode('utf-8')
        else:
            password_bytes = plain_password
        
        # Ensure hashed_password is bytes
        if isinstance(hashed_password, str):
            hashed_bytes = hashed_password.encode('utf-8')
        else:
            hashed_bytes = hashed_password
        
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def get_password_hash(password: str) -> str:
    """Hash a password."""
    try:
        # Ensure password is a string
        if not isinstance(password, str):
            password = str(password)
        
        # Convert to bytes for bcrypt
        password_bytes = password.encode('utf-8')
        
        # Bcrypt limit is 72 bytes - truncate if necessary
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]
        
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        
        # Return as string
        return hashed.decode('utf-8')
    except Exception as e:
        print(f"Password hashing error: {e}")
        print(f"Password type: {type(password)}, length: {len(password) if isinstance(password, str) else 'N/A'}")
        if isinstance(password, str):
            print(f"Password bytes length: {len(password.encode('utf-8'))}")
        raise ValueError(f"Failed to hash password: {str(e)}")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: int = payload.get("user_id")
    username: str = payload.get("username")
    
    if user_id is None or username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = database.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

def register_user(username: str, password: str, email: Optional[str] = None):
    """Register a new user."""
    # Ensure password is a string
    if not isinstance(password, str):
        password = str(password)
    
    # Validate password length
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters long")
    
    # Check password byte length (bcrypt limit is 72 bytes)
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        raise ValueError("Password is too long (maximum 72 bytes)")
    
    # Check if user exists
    if database.get_user_by_username(username):
        raise ValueError("Username already exists")
    
    # Hash password
    try:
        hashed_password = get_password_hash(password)
    except Exception as e:
        raise ValueError(f"Failed to process password: {str(e)}")
    
    # Create user
    user_id = database.create_user(username, email, hashed_password)
    
    # Create access token
    access_token = create_access_token(
        data={"user_id": user_id, "username": username}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "username": username,
            "email": email
        }
    }

def authenticate_user(username: str, password: str):
    """Authenticate a user and return token."""
    # Ensure password is a string
    if not isinstance(password, str):
        password = str(password)
    
    user = database.get_user_by_username(username)
    if not user:
        raise ValueError("Invalid username or password")
    
    if not verify_password(password, user["hashed_password"]):
        raise ValueError("Invalid username or password")
    
    # Create access token
    access_token = create_access_token(
        data={"user_id": user["id"], "username": user["username"]}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"]
        }
    }
