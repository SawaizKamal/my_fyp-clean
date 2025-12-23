import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_SECRET_KEY")
