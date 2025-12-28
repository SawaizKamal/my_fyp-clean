import os
from dotenv import load_dotenv

# Load environment variables from .env file
# Get the directory where config.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Load .env file from the same directory as config.py
load_dotenv(os.path.join(BASE_DIR, ".env"))

# OpenAI API Key - Set via environment variable OPENAI_API_KEY
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

# YouTube Data API Key - Get this from https://console.cloud.google.com
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Server configuration
HOST = "0.0.0.0"
PORT = 8000

# Auth configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # In production, fail if SECRET_KEY is not set
    if os.getenv("ENVIRONMENT") == "production":
        raise ValueError("SECRET_KEY environment variable is required in production")
    # Development fallback (not secure, but allows local development)
    SECRET_KEY = "DEV_SECRET_KEY_CHANGE_IN_PRODUCTION"
    import warnings
    warnings.warn("Using default SECRET_KEY. Set SECRET_KEY environment variable in production!")

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
# In production, restrict CORS to specific origins
if os.getenv("ENVIRONMENT") == "production" and "*" in ALLOWED_ORIGINS:
    import warnings
    warnings.warn("CORS allows all origins in production. Set ALLOWED_ORIGINS environment variable!")
