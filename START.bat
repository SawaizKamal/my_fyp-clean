@echo off
echo ========================================
echo   VideoShortener AI - Backend Server
echo ========================================
echo.
echo Starting backend server...
echo.

cd backend
call ..\venv\Scripts\activate
python main.py

pause

