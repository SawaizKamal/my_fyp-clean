# auth.py - Testing version with hardcoded login
from typing import Optional

# ---------------- HARD-CODED USER ----------------
HARDCODED_USER = {
    "id": 1,
    "username": "admin",
    "email": "admin@test.com",
    "hashed_password": "admin"  # plain password for testing
}

# ---------------- AUTH FUNCTIONS ----------------
def get_current_user(_=None):
    # Returns hardcoded user for testing
    return HARDCODED_USER

def register_user(username: str, password: str, email: Optional[str] = None):
    # Bypass DB, return hardcoded token structure
    return {
        "access_token": "testtoken",
        "token_type": "bearer",
        "user": HARDCODED_USER
    }

def authenticate_user(username: str, password: str):
    if username == HARDCODED_USER["username"] and password == HARDCODED_USER["hashed_password"]:
        return {
            "access_token": "testtoken",
            "token_type": "bearer",
            "user": HARDCODED_USER
        }
    raise ValueError("Invalid credentials")
