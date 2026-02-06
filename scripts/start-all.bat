@echo off
chcp 936 >nul
title Fund Tracker - Start All Services
cls

echo ============================================
echo    Fund Tracker - Start All Services
echo    v2.0.0
echo ============================================
echo.

REM Set project root
cd /d "%~dp0.."
echo [Debug] Current directory: %CD%
echo.

REM Check Docker
echo [1/6] Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Docker not installed or not running!
    pause
    exit /b 1
)
echo [OK] Docker is ready
echo.

REM Start Redis
echo [2/6] Starting Redis...
docker ps --filter "name=redis" --format "{{.Names}}" 2>nul | findstr /B "redis" >nul
if errorlevel 1 (
    echo    Redis not running, starting...
    docker run -d --name redis -p 6379:6379 --restart unless-stopped redis:alpine >nul 2>&1
    if errorlevel 1 (
        echo [Warning] Redis start failed, may already exist. Trying to start existing container...
        docker start redis >nul 2>&1
        if errorlevel 1 (
            echo [Error] Failed to start Redis!
            pause
            exit /b 1
        )
    )
    timeout /t 2 /nobreak >nul
    echo [OK] Redis started
) else (
    echo [OK] Redis already running
)
echo.

REM Start PostgreSQL
echo [3/6] Starting PostgreSQL...
docker ps --filter "name=postgres" --format "{{.Names}}" 2>nul | findstr /B "postgres" >nul
if errorlevel 1 (
    echo    PostgreSQL not running, starting...
    docker run -d --name postgres -p 5432:5432 -e POSTGRES_USER=fundtracker -e POSTGRES_PASSWORD=fundtracker123 -e POSTGRES_DB=fundtracker --restart unless-stopped postgres:15 >nul 2>&1
    if errorlevel 1 (
        echo [Warning] PostgreSQL start failed, may already exist. Trying to start existing container...
        docker start postgres >nul 2>&1
        if errorlevel 1 (
            echo [Error] Failed to start PostgreSQL!
            pause
            exit /b 1
        )
    )
    timeout /t 3 /nobreak >nul
    echo [OK] PostgreSQL started
) else (
    echo [OK] PostgreSQL already running
)
echo.

REM Start Backend
echo [4/6] Starting Backend...
echo    Using conda environment: Explore
echo.

REM Use full path to conda python
set "PYTHON_PATH=C:\Users\138721\AppData\Local\miniforge3\envs\Explore\python.exe"
set "CONDA_ACTIVATE=C:\Users\138721\AppData\Local\miniforge3\Scripts\activate.bat"

if exist "%CONDA_ACTIVATE%" (
    echo [OK] Found conda activate script
    start "FundTracker-Backend" cmd /k "cd fund-tracker\backend && call "%CONDA_ACTIVATE%" Explore && python -m app.main"
) else if exist "%PYTHON_PATH%" (
    echo [OK] Found Python at: %PYTHON_PATH%
    start "FundTracker-Backend" cmd /k "cd fund-tracker\backend && "%PYTHON_PATH%" -m app.main"
) else (
    echo [Warning] Conda/Python not found at expected path, trying system Python...
    start "FundTracker-Backend" cmd /k "cd fund-tracker\backend && python -m app.main"
)
echo [OK] Backend starting in new window
echo.

REM Start Frontend
echo [5/6] Starting Frontend...
start "FundTracker-Frontend" cmd /k "cd fund-tracker-desktop && npm run dev"
echo [OK] Frontend starting in new window
echo.

REM Wait for services to start
echo [6/6] Waiting for services to initialize...
echo    Waiting 15 seconds for backend and frontend to start...
timeout /t 15 /nobreak >nul
echo.

REM Check service status
echo ============================================
echo    Checking Service Status
echo ============================================
echo.

REM Check Backend
echo Checking Backend (Port 8001)...
netstat -ano | findstr ":8001" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [Warning] Backend port 8001 not listening yet
    echo          Backend may still be starting...
) else (
    echo [OK] Backend is listening on port 8001
    
    REM Try health check
    echo    Testing health endpoint...
    curl -s http://localhost:8001/health >nul 2>&1
    if errorlevel 1 (
        echo [Warning] Health check failed, service may still be initializing
    ) else (
        echo [OK] Backend health check passed
    )
)
echo.

REM Check Frontend
echo Checking Frontend (Port 5173)...
netstat -ano | findstr ":5173" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [Warning] Frontend port 5173 not listening yet
    echo          Frontend may still be starting...
) else (
    echo [OK] Frontend is listening on port 5173
)
echo.

REM Check Redis
echo Checking Redis (Port 6379)...
netstat -ano | findstr ":6379" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [Error] Redis port 6379 not listening!
) else (
    echo [OK] Redis is listening on port 6379
)
echo.

REM Check PostgreSQL
echo Checking PostgreSQL (Port 5432)...
netstat -ano | findstr ":5432" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo [Error] PostgreSQL port 5432 not listening!
) else (
    echo [OK] PostgreSQL is listening on port 5432
)
echo.

echo ============================================
echo    Service Status Summary
echo ============================================
echo.
echo Access URLs:
echo   - Frontend: http://localhost:5173
echo   - Backend:  http://localhost:8001
echo   - API Docs: http://localhost:8001/docs
echo   - Health:   http://localhost:8001/health
echo.
echo Note: If any service shows [Warning], wait a few more seconds
echo       and refresh the page, or check the service window for errors.
echo.
echo Commands:
echo   - Stop all:  scripts\stop-all.bat
echo   - Restart:   scripts\restart-all.bat
echo.
pause
