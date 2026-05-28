@echo off

set BACKEND_DIR=%~dp0..\backend
set FRONTEND_DIR=%~dp0..\frontend
set CONDA_BAT=%USERPROFILE%\AppData\Local\miniforge3\condabin\conda.bat

echo ========================================
echo   Fund Tracker v3.0
echo ========================================
echo.
echo [1/2] Starting backend on port 8001...
start "Fund Tracker Backend" cmd /k cd /d "%BACKEND_DIR%" ^&^& "%CONDA_BAT%" activate fund-tracker ^&^& python -m app.main
timeout /t 3 /nobreak >nul
echo [2/2] Starting frontend on port 3000...
start "Fund Tracker Frontend" cmd /k cd /d "%FRONTEND_DIR%" ^&^& npm run dev
echo.
echo Fund Tracker started!
echo   Backend:  http://127.0.0.1:8001
echo   Frontend: http://localhost:3000
echo   API Docs: http://127.0.0.1:8001/docs
echo.
pause
