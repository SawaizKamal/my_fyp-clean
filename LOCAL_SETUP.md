# Local Setup Guide

Follow these steps to run the application on your local machine.

## Prerequisites Check

✅ Python 3.14.0 - Installed  
✅ Node.js v25.0.0 - Installed

## Step 1: Set Up Python Virtual Environment

Open PowerShell in the project root directory and run:

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# You should see (venv) prefix in your terminal
```

## Step 2: Install Backend Dependencies

With the virtual environment activated:

```powershell
cd backend
pip install -r requirements.txt
```

**Note**: This may take a few minutes, especially for installing Whisper and other ML libraries.

## Step 3: Set Up Environment Variables

Create a `.env` file in the `backend/` directory:

```powershell
cd backend
# Create .env file
New-Item -Path .env -ItemType File -Force
```

Edit `.env` and add your API keys:

```
OPENAI_API_KEY=your_openai_api_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here
SECRET_KEY=your_secret_key_here
```

**To generate SECRET_KEY:**
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

**To get API keys:**
- **OpenAI API Key**: https://platform.openai.com/api-keys
- **YouTube API Key**: https://console.cloud.google.com (enable YouTube Data API v3)

## Step 4: Install Frontend Dependencies

Open a NEW PowerShell window:

```powershell
cd frontend
npm install
```

## Step 5: Run the Application

### Terminal 1 - Backend Server

```powershell
# Activate virtual environment
venv\Scripts\activate

# Navigate to backend
cd backend

# Run the server
python main.py
```

Backend will run on: `http://localhost:8000`

### Terminal 2 - Frontend Server

```powershell
# Navigate to frontend
cd frontend

# Run development server
npm run dev
```

Frontend will run on: `http://localhost:5173`

## Step 6: Access the Application

1. Open your browser
2. Go to: `http://localhost:5173`
3. Register a new account or login
4. Start using the app!

## Quick Commands Summary

**Backend:**
```powershell
venv\Scripts\activate
cd backend
python main.py
```

**Frontend:**
```powershell
cd frontend
npm run dev
```

## Troubleshooting

### Backend won't start
- ✅ Make sure virtual environment is activated
- ✅ Check if port 8000 is available
- ✅ Verify OPENAI_API_KEY is set in `.env` or environment
- ✅ Check if all dependencies are installed: `pip list`

### Frontend won't start
- ✅ Run `npm install` in frontend directory
- ✅ Check if port 5173 is available
- ✅ Clear node_modules and reinstall: `Remove-Item -Recurse -Force node_modules; npm install`

### Import errors in backend
- ✅ Make sure you're in the activated virtual environment
- ✅ Reinstall requirements: `pip install -r requirements.txt --force-reinstall`

### Database errors
- ✅ The app will create `users.db` automatically on first run
- ✅ If issues persist, delete `backend/users.db` and restart

### Video transcription fails
- ✅ Check OPENAI_API_KEY is correct
- ✅ Ensure you have sufficient disk space
- ✅ Check backend logs for specific error messages

## What to Expect

1. **First Run**: 
   - Backend will download Whisper model (~150MB) - takes a few minutes
   - Frontend may take 30-60 seconds to compile

2. **Video Upload/Transcription**:
   - Small videos (< 1 min): ~30-60 seconds
   - Medium videos (1-5 min): ~2-5 minutes
   - Large videos (5+ min): ~5-15 minutes

3. **Background Tasks**:
   - Upload returns immediately with task_id
   - Poll status endpoint to get progress
   - Results appear when transcription completes

## Testing the Setup

1. **Health Check**: Visit `http://localhost:8000/api/health`
   - Should return: `{"status": "ok", "database": "connected", "model": "gpt-4o"}`

2. **Frontend**: Visit `http://localhost:5173`
   - Should see the landing page

3. **Register/Login**: 
   - Create an account
   - Login should work

4. **Video Upload**:
   - Go to Chat page → Click "Upload Video"
   - Upload a small video file
   - Check if transcription starts

## Notes

- **Keep both terminals running** - Backend and Frontend must run simultaneously
- **First video transcription** takes longer (loading Whisper model)
- **Development mode** - Debug logs will appear in console
- **Hot reload** - Frontend auto-reloads on code changes






