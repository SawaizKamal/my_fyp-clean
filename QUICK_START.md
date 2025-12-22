# Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Setup YouTube API Key (Required)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Enable "YouTube Data API v3"
4. Create credentials (API Key)
5. Copy your API key

### Step 2: Update API Key

Edit `backend/main.py` and update the `YOUTUBE_API_KEY` variable (around line 32):

```python
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "YOUR_API_KEY_HERE")
```

Or create a `.env` file in the `backend/` directory:

```
YOUTUBE_API_KEY=your_api_key_here
OPENAI_API_KEY=your_openai_key_if_needed
```

### Step 3: Run the Application

#### Terminal 1 - Start Backend:
```bash
cd backend
..\venv\Scripts\activate  # Windows
# or: source ../venv/bin/activate  # Mac/Linux

python main.py
```

Backend will run on `http://localhost:8000`

#### Terminal 2 - Start Frontend:
```bash
cd frontend
npm run dev
```

Frontend will run on `http://localhost:5173`

### Step 4: Use the App

1. Open browser: `http://localhost:5173`
2. Click "Get Started"
3. Search for YouTube videos
4. Select a video
5. Enter what you want to extract
6. Wait for processing
7. Download your shortened video!

## 📝 Notes

- First run may take longer (downloading AI models)
- Processing time depends on video length
- Ensure you have enough disk space for downloads

## 🐛 Troubleshooting

**Backend won't start:**
- Make sure virtual environment is activated
- Check if port 8000 is available

**Frontend won't start:**
- Run `npm install` in frontend directory
- Make sure Node.js is installed

**API errors:**
- Verify YouTube API key is correct
- Check YouTube API quota in Google Cloud Console

