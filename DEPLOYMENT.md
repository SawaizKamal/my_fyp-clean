# Deployment README

## Render Deployment Instructions

### Prerequisites
- Render account
- OpenAI API key
- (Optional) YouTube Data API key

### Environment Variables to Set in Render Dashboard

1. **OPENAI_API_KEY** (Required)
   - Get from: https://platform.openai.com/api-keys
   - Used for pattern detection and code analysis

2. **YOUTUBE_API_KEY** (Optional)
   - Get from: https://console.cloud.google.com
   - Used for video recommendations

3. **SECRET_KEY** (Auto-generated)
   - Used for JWT authentication
   - Render auto-generates this

4. **DATABASE_URL** (Auto-configured)
   - PostgreSQL connection string
   - Automatically set by Render database

### Deployment Steps

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Add Pattern Intelligence Layer"
   git push origin main
   ```

2. **Deploy on Render:**
   - Go to Render Dashboard
   - Connect your GitHub repository
   - Set environment variables mentioned above
   - Render will automatically run `python build.py`

3. **Verify Deployment:**
   - Check `/api/health` endpoint
   - Test pattern detection via Chat page

### New Features in This Deployment

- **Pattern Intelligence Layer**: 12 pattern categories for code error detection
- **External Knowledge Search**: GitHub, StackOverflow, Dev.to integration
- **Debugging Insights**: Root cause analysis with structured output
- **Confidence Scoring**: Transparency in pattern detection accuracy

### Dependencies Added

- `beautifulsoup4` - Web scraping for external knowledge
- `requests` - HTTP requests for API integrations

All dependencies are listed in `backend/requirements.txt` and will be automatically installed during build.
