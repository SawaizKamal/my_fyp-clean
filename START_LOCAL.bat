@echo off
echo ========================================
echo   Starting Full-Stack Application
echo ========================================
echo.
echo This will start both backend and frontend.
echo Make sure you have:
echo  1. Virtual environment activated
echo  2. Backend dependencies installed
echo  3. Frontend dependencies installed
echo  4. .env file with API keys in backend/
echo.
echo Press any key to continue...
pause > nul

echo.
echo Starting Backend Server (Terminal 1)...
start "Backend Server" cmd /k "venv\Scripts\activate && cd backend && python main.py"

timeout /t 3 /nobreak > nul

echo.
echo Starting Frontend Server (Terminal 2)...
start "Frontend Server" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo   Both servers are starting...
echo ========================================
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Press any key to exit this window...
pause > nul






