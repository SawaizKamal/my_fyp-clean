# Installing ffmpeg on Render

## ⚠️ Yes, Render Requires ffmpeg!

Render does **NOT** come with ffmpeg pre-installed. You **MUST** install it during the build process.

## ✅ Solution 1: Updated render.yaml (Recommended)

The `render.yaml` has been updated to install ffmpeg automatically:

```yaml
buildCommand: sudo apt-get update && sudo apt-get install -y ffmpeg && python build.py
```

This will:
1. Update package lists
2. Install ffmpeg (and ffprobe)
3. Run the normal build process

**Status**: ✅ Already configured in `render.yaml`

## ✅ Solution 2: Using Dockerfile (Alternative)

If the native service approach doesn't work (some Render plans don't allow sudo), use the provided `Dockerfile`:

1. In Render Dashboard → Your Service → Settings
2. Change **Runtime** from "Native" to "Docker"
3. Render will automatically use the `Dockerfile`
4. The Dockerfile already includes ffmpeg installation

**Status**: ✅ `Dockerfile` is ready to use

## 🔍 Verify ffmpeg Installation

After deployment, check the health endpoint:
```bash
curl https://yourapp.onrender.com/api/health
```

Should return:
```json
{
  "status": "ok",
  "database": "connected",
  "model": "gpt-4o",
  "ffmpeg_available": true
}
```

If `ffmpeg_available: false`, check build logs for installation errors.

## 🐛 Troubleshooting

### Build Fails with "sudo: command not found"
- **Cause**: Some Render plans don't allow sudo
- **Solution**: Use the Dockerfile approach (Solution 2)

### Build Fails with "apt-get: command not found"
- **Cause**: Not using Ubuntu-based image
- **Solution**: Use the Dockerfile which uses `python:3.10-slim` (Ubuntu-based)

### ffmpeg Still Not Found After Build
- **Check**: Build logs should show ffmpeg installation
- **Verify**: Check `/api/health` endpoint
- **Fix**: Ensure build command runs successfully (check logs)

### Video Upload Still Fails
- **Check**: Server logs for specific error
- **Verify**: `ffmpeg -version` in build logs
- **Test**: Upload a small test video (30 seconds)

## 📝 Build Logs to Check

When deploying, look for these in build logs:
```
--- Installing ffmpeg ---
Reading package lists...
Installing ffmpeg...
Setting up ffmpeg...
```

If you see errors, the installation failed.

## 🚀 Quick Test

After deployment:
1. Go to: `https://yourapp.onrender.com/upload-video`
2. Upload a short test video (30 seconds, < 10MB)
3. Should see "Chunk 1/1" processing
4. Transcript should appear

If you get "ffmpeg not found" error, the installation didn't work.

## 💡 Alternative: Use Dockerfile

If native service doesn't work, switch to Docker:

1. **In Render Dashboard**:
   - Go to your service
   - Settings → Runtime
   - Change from "Native" to "Docker"
   - Save

2. **Render will automatically**:
   - Use the `Dockerfile` in your repo
   - Build with ffmpeg included
   - Deploy the container

3. **Verify**:
   - Check `/api/health` endpoint
   - Should show `ffmpeg_available: true`

## 📋 Current Configuration

✅ **render.yaml**: Updated with ffmpeg installation
✅ **Dockerfile**: Available as backup option
✅ **Health endpoint**: Reports ffmpeg status
✅ **Error handling**: Provides helpful messages if ffmpeg missing

## 🎯 Summary

- **Render needs ffmpeg**: ✅ Yes, must be installed
- **Current setup**: ✅ Already configured in render.yaml
- **Backup option**: ✅ Dockerfile available
- **Verification**: ✅ Check `/api/health` endpoint

