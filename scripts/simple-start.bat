@echo off
echo ============================================
echo    Fund Tracker - Simple Start
echo ============================================
echo.

REM Change to project root
cd /d "%~dp0.."
echo Current directory: %CD%
echo.

REM Start Redis
echo Starting Redis...
docker run -d --name redis -p 6379:6379 redis:alpine 2>nul
if errorlevel 1 (
    echo Redis already running or error occurred
) else (
    echo Redis started
)

REM Start PostgreSQL
echo Starting PostgreSQL...
docker run -d --name postgres -p 5432:5432 -e POSTGRES_USER=fundtracker -e POSTGRES_PASSWORD=fundtracker123 -e POSTGRES_DB=fundtracker postgres:15 2>nul
if errorlevel 1 (
    echo PostgreSQL already running or error occurred
) else (
    echo PostgreSQL started
)

echo.
echo Starting Backend...
start cmd /k "cd fund-tracker\backend && call venv\Scripts\activate && python -m app.main"

echo Starting Frontend...
start cmd /k "cd fund-tracker-desktop && npm run dev"

echo.
echo All services started!
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8001
pause
