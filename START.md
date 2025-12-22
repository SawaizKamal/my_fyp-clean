# Start the App

## Quick Start

### Option 1: Use Batch Files (Windows)
- Double-click `START.bat` to start backend
- Double-click `START_FRONTEND.bat` to start frontend

### Option 2: Manual Commands

#### Start Backend (Terminal 1)
```bash
cd backend
..\venv\Scripts\activate
python main.py
```
Backend runs on: `http://localhost:8000`

#### Start Frontend (Terminal 2)
```bash
cd frontend
npm run dev
```
Frontend runs on: `http://localhost:5173`

## Access the App
Open browser: **http://localhost:5173**

## Prerequisites
- Virtual environment activated (venv)
- Node.js and npm installed
- Dependencies installed:
  - Backend: `pip install -r backend/requirements.txt`
  - Frontend: `npm install` (in frontend directory)
