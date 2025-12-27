# Dockerfile for Render deployment with ffmpeg support
# Alternative to native service if apt-get doesn't work

FROM python:3.10-slim

# Install system dependencies including ffmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY backend/requirements.txt /app/backend/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy frontend and build it
COPY frontend/package*.json /app/frontend/
WORKDIR /app/frontend
RUN npm install && npm run build

# Copy backend code
WORKDIR /app
COPY backend/ /app/backend/
COPY frontend/dist/ /app/backend/dist_build/

# Set working directory to backend
WORKDIR /app/backend

# Expose port (Render will set PORT env var)
EXPOSE $PORT

# Start command
CMD python -m uvicorn main:app --host 0.0.0.0 --port $PORT

