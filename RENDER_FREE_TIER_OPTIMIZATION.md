# 🆓 Render Free Tier Optimization Guide

## ⚠️ Important: Free Tier Limitations

Render's **free tier** has significant limitations that can cause **502 errors** with video transcription:

### Free Tier Constraints:
- **RAM**: Only **512MB** (very limited!)
- **CPU**: 0.5 cores
- **Request Timeout**: **90 seconds** (requests exceeding this timeout return 502)
- **Service Spin-Down**: Services sleep after 15 minutes of inactivity (cold starts)
- **No Persistent Storage**: Files are deleted on redeploy

### Why This Causes 502 Errors:

1. **Memory Issues**:
   - Whisper "base" model requires **~1GB RAM** (exceeds free tier limit!)
   - Can cause OOM (Out Of Memory) errors → 502
   - Process gets killed by system when memory limit exceeded

2. **Timeout Issues**:
   - Video transcription can take >90 seconds
   - Free tier kills requests after 90 seconds → 502

3. **Cold Starts**:
   - Service needs to "wake up" after inactivity
   - First request can timeout → 502

## ✅ Solution: Auto-Optimization for Free Tier

The code now **automatically detects** Render free tier and optimizes accordingly:

### Automatic Model Selection:

```python
# If RENDER_SERVICE_PLAN=free or starter is detected:
# - Automatically uses Whisper "tiny" model (~39MB RAM)
# - Falls within 512MB RAM limit
# - Still provides reasonable transcription quality
```

### Manual Configuration:

Set environment variable in Render Dashboard:

```bash
# For free tier (512MB RAM) - REQUIRED
WHISPER_MODEL_SIZE=tiny

# For starter tier (512MB RAM) - Recommended  
WHISPER_MODEL_SIZE=tiny

# For standard tier (2GB RAM) - Recommended
WHISPER_MODEL_SIZE=base

# For standard-plus tier (4GB+ RAM)
WHISPER_MODEL_SIZE=small  # or medium, large
```

## 📊 Model Comparison:

| Model | RAM Usage | Speed | Accuracy | Best For |
|-------|-----------|-------|----------|----------|
| **tiny** | ~39MB | Fastest | Good | **Free/Starter tier** ✅ |
| **base** | ~1GB | Fast | Very Good | Standard tier (2GB) ✅ |
| **small** | ~2GB | Moderate | Excellent | Standard-plus (4GB+) |
| **medium** | ~5GB | Slow | Excellent | High-end servers |
| **large** | ~10GB | Slowest | Best | Enterprise servers |

## 🔧 Configuration Steps:

### Step 1: Set Environment Variable in Render

1. Go to **Render Dashboard** → Your Service → **Environment**
2. Click **"Add Environment Variable"**
3. Add:
   ```
   Key: WHISPER_MODEL_SIZE
   Value: tiny
   ```
4. Click **"Save Changes"**
5. **Redeploy** your service

### Step 2: Verify Configuration

After redeploy, check logs. You should see:
```
Loading Whisper model 'tiny' (RAM usage: tiny=39MB, base=1GB...)
Whisper model 'tiny' loaded and cached successfully
```

### Step 3: Monitor Memory Usage

In Render Dashboard → Metrics, check:
- **Memory Usage**: Should stay well below 512MB with "tiny" model
- If still hitting limits, upload shorter videos (<2 minutes)

## 🚀 Recommended: Upgrade to Standard Plan

For **production use**, consider upgrading to **Render Standard** plan:

**Benefits:**
- ✅ **2GB RAM** (enough for "base" model - better accuracy)
- ✅ **1 CPU** (faster processing)
- ✅ **Longer timeouts** (no 90-second limit)
- ✅ **No spin-down** (always available)
- ✅ **Better reliability** (fewer 502 errors)

**Cost**: ~$25/month

**To upgrade:**
1. Render Dashboard → Your Service → **Settings**
2. Click **"Change Plan"**
3. Select **"Standard"** ($25/month)
4. Set `WHISPER_MODEL_SIZE=base` in environment variables

## 🔍 Troubleshooting 502 Errors:

### If still getting 502 errors:

1. **Check Render Logs**:
   - Dashboard → Your Service → **Logs**
   - Look for "killed", "OOM", "memory", "timeout" errors

2. **Verify Model Size**:
   ```bash
   # In logs, should see:
   Loading Whisper model 'tiny' ...
   ```

3. **Try Shorter Videos**:
   - Free tier: Keep videos **<2 minutes** for best results
   - Even with "tiny" model, very long videos can cause issues

4. **Check Environment Variable**:
   - Ensure `WHISPER_MODEL_SIZE=tiny` is set
   - Redeploy after setting

5. **Monitor Memory**:
   - Dashboard → Metrics → Memory
   - Should stay below 400MB with "tiny" model

## 📝 Summary:

✅ **Free Tier**: Set `WHISPER_MODEL_SIZE=tiny` (auto-detected)
✅ **Starter Tier**: Set `WHISPER_MODEL_SIZE=tiny`  
✅ **Standard Tier**: Set `WHISPER_MODEL_SIZE=base` (recommended)
✅ **For Production**: Consider upgrading to Standard plan ($25/month)

The code now **automatically optimizes** for free tier, but you can override with the environment variable if needed!

