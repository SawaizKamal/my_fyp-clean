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

# Whisper model size configuration
# Options: "tiny" (~39MB RAM), "base" (~1GB RAM), "small" (~2GB RAM), "medium" (~5GB RAM), "large" (~10GB RAM)
# Default: "tiny" for compatibility with Render free tier (512MB RAM limit)
# For Render free/starter tier (512MB RAM): use "tiny" (default)
# For Render standard (2GB RAM): use "base" (set WHISPER_MODEL_SIZE=base in environment)
# For Render standard-plus (4GB+ RAM): use "small" or "medium"
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "tiny")  # Default to "tiny" for free tier compatibility

# Auto-detect free tier if RENDER_SERVICE_PLAN is set (optional)
RENDER_PLAN = os.getenv("RENDER_SERVICE_PLAN", "").lower()
if RENDER_PLAN in ["free", "starter"] and WHISPER_MODEL_SIZE != "tiny":
    WHISPER_MODEL_SIZE = "tiny"
    import warnings
    warnings.warn(f"Render {RENDER_PLAN} tier detected. Using Whisper 'tiny' model for compatibility (512MB RAM limit). Override with WHISPER_MODEL_SIZE env var if needed.")