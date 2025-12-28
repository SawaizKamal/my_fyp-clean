# Local Setup Script
# Run this script in PowerShell: .\setup_local.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  LOCAL SETUP SCRIPT" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = Get-Location

# Step 1: Activate virtual environment and install backend dependencies
Write-Host "Step 1: Setting up Backend..." -ForegroundColor Yellow
Write-Host ""

if (Test-Path "venv\Scripts\activate.ps1") {
    Write-Host "✅ Virtual environment found" -ForegroundColor Green
    & "venv\Scripts\activate.ps1"
    Write-Host "✅ Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "❌ Virtual environment not found. Creating one..." -ForegroundColor Red
    python -m venv venv
    & "venv\Scripts\activate.ps1"
}

Write-Host ""
Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
Write-Host "⏱️  This may take 5-10 minutes..." -ForegroundColor Gray
Set-Location backend
pip install -r requirements.txt
Set-Location $projectRoot

Write-Host ""
Write-Host "Step 2: Checking for .env file..." -ForegroundColor Yellow
if (Test-Path "backend\.env") {
    Write-Host "✅ .env file exists" -ForegroundColor Green
} else {
    Write-Host "❌ .env file not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Creating .env template..." -ForegroundColor Yellow
    @"
OPENAI_API_KEY=your_openai_key_here
YOUTUBE_API_KEY=your_youtube_key_here
SECRET_KEY=your_secret_key_here
"@ | Out-File -FilePath "backend\.env" -Encoding utf8
    Write-Host "✅ Created backend\.env file" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  IMPORTANT: Edit backend\.env and add your API keys!" -ForegroundColor Yellow
    Write-Host "   - Get OpenAI key: https://platform.openai.com/api-keys" -ForegroundColor Gray
    Write-Host "   - Get YouTube key: https://console.cloud.google.com" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Step 3: Setting up Frontend..." -ForegroundColor Yellow
Set-Location frontend

if (Test-Path "node_modules") {
    Write-Host "✅ Frontend dependencies already installed" -ForegroundColor Green
} else {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
    Write-Host "⏱️  This may take 2-3 minutes..." -ForegroundColor Gray
    npm install
}

Set-Location $projectRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SETUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Edit backend\.env and add your API keys" -ForegroundColor White
Write-Host "2. Start backend: venv\Scripts\activate && cd backend && python main.py" -ForegroundColor White
Write-Host "3. Start frontend (in new terminal): cd frontend && npm run dev" -ForegroundColor White
Write-Host "4. Open browser: http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "Or use: START_LOCAL.bat (double-click)" -ForegroundColor Cyan
Write-Host ""






