# Quick Fix for Video Recommendations

## Problem
YouTube videos were not appearing because `YOUTUBE_API_KEY` was not set, causing the search to return empty results.

## Solution Applied
✅ Added fallback video recommendations when API key is missing
✅ System now shows placeholder videos instead of nothing

## To Get Real YouTube Videos:

### Option 1: Set YOUTUBE_API_KEY (Recommended)

1. **Get YouTube API Key:**
   - Go to https://console.cloud.google.com
   - Create a project
   - Enable "YouTube Data API v3"
   - Create credentials → API Key
   - Copy the API key

2. **Set the key locally:**
   ```bash
   # Windows (PowerShell)
   $env:YOUTUBE_API_KEY="your_key_here"
   
   # Or create .env file in project root:
   echo "YOUTUBE_API_KEY=your_key_here" >> .env
   echo "OPENAI_API_KEY=your_openai_key" >> .env
   ```

3. **Restart backend:**
   ```bash
   cd backend
   python main.py
   ```

### Option 2: Use Fallback (Current)
- System will show placeholder videos
- Videos will still attempt transcript analysis
- Most will be skipped with reason "Transcript unavailable"

## Expected Behavior Now:

**Without YOUTUBE_API_KEY:**
- Shows 3 placeholder videos with pattern-based titles
- Console shows: ⚠️ YOUTUBE_API_KEY not set - using fallback video recommendations

**With YOUTUBE_API_KEY:**
- Searches real YouTube videos based on pattern
- Extracts timestamps from transcripts
- Skips videos without transcripts (with transparency)

## Test It:

1. Submit code with an error in Chat page
2. Check for "Recommended Videos" section
3. Should see either:
   - Real videos (if API key set)
   - Fallback videos (if no API key)

## For Render Deployment:
Add `YOUTUBE_API_KEY` to environment variables in Render dashboard (optional but recommended).
