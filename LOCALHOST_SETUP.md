# Localhost Setup Guide

## ✅ Will the Code Work on Localhost?

**Yes, but you need to install ffmpeg first!**

The code will work on localhost once you install the required system dependency: **ffmpeg**.

## 📋 Prerequisites

### 1. Python Dependencies (Already in requirements.txt)
All Python packages are already listed. Just run:
```bash
cd backend
pip install -r requirements.txt
```

### 2. System Dependency: ffmpeg ⚠️ **REQUIRED**

ffmpeg is **NOT** a Python package - it's a system binary that must be installed separately.

## 🔧 Installing ffmpeg on Windows

### Option 1: Using Chocolatey (Recommended - Easiest)
```powershell
# Install Chocolatey first (if not installed)
# Visit: https://chocolatey.org/install

# Then install ffmpeg
choco install ffmpeg
```

### Option 2: Manual Installation
1. Download ffmpeg from: https://www.gyan.dev/ffmpeg/builds/
   - Choose "ffmpeg-release-essentials.zip"
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add to PATH:
   - Open "Environment Variables" (search in Windows)
   - Edit "Path" under "System variables"
   - Add: `C:\ffmpeg\bin` (or wherever you extracted it)
4. Restart your terminal/PowerShell
5. Verify: Run `ffmpeg -version` in a new terminal

### Option 3: Using winget (Windows 10/11)
```powershell
winget install ffmpeg
```

## ✅ Verify Installation

After installing, verify in a **new terminal**:
```powershell
ffmpeg -version
ffprobe -version
```

Both commands should show version information (not "command not found").

## 🚀 Running on Localhost

### Step 1: Install ffmpeg (see above)

### Step 2: Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 3: Set Environment Variables
Create `.env` file in `backend/` directory:
```
OPENAI_API_KEY=your_openai_key_here
SECRET_KEY=your_secret_key_here
```

### Step 4: Start Backend
```bash
cd backend
python main.py
# or
uvicorn main:app --reload
```

### Step 5: Start Frontend (in another terminal)
```bash
cd frontend
npm install
npm run dev
```

## 🧪 Testing Video Upload

1. Open browser: `http://localhost:5173`
2. Navigate to `/upload-video` page
3. Upload a video file (max 5 minutes, 500MB)
4. Watch live transcription happen!

## ⚠️ Common Issues

### "ffmpeg not found" Error
- **Cause**: ffmpeg not installed or not in PATH
- **Fix**: Install ffmpeg and add to PATH (see above)
- **Verify**: Run `ffmpeg -version` in terminal

### "ffprobe not found" Error
- **Cause**: ffprobe comes with ffmpeg, so if this fails, ffmpeg isn't installed correctly
- **Fix**: Reinstall ffmpeg and ensure PATH is set correctly

### Video Duration Check Fails
- **Cause**: Usually means ffmpeg/ffprobe not available
- **Fix**: Install ffmpeg (see above)

### "Permission denied" on Windows
- **Cause**: Sometimes Windows blocks subprocess calls
- **Fix**: Run terminal as Administrator, or check Windows Defender settings

## 📝 Notes

- **First run**: Whisper model will download automatically (~150MB for "base" model)
- **Processing time**: ~30 seconds per 30-second chunk
- **Memory usage**: ~200-300MB for Whisper + minimal for chunks
- **Temporary files**: Automatically cleaned up after processing

## 🔍 Troubleshooting

### Check if ffmpeg is accessible:
```powershell
# In PowerShell
where.exe ffmpeg
where.exe ffprobe
```

Should show paths like `C:\ffmpeg\bin\ffmpeg.exe`

### Test ffmpeg directly:
```powershell
ffmpeg -i "path/to/video.mp4" -t 1 -f null -
```

Should process without errors.

### If PATH doesn't work:
You can temporarily add to PATH in your current session:
```powershell
$env:Path += ";C:\ffmpeg\bin"
```

But you'll need to do this every time. Better to add permanently via System Properties.

## ✅ Quick Test

Once everything is set up, test with a short video:
1. Upload a 30-second test video
2. Should see "Chunk 1/1" processing
3. Transcript should appear within ~30-60 seconds
4. If you see "ffmpeg not found" error, ffmpeg isn't installed correctly

