@echo off
echo Starting Fund Tracker...
cd /d "%~dp0.."
echo Current directory: %CD%
docker run -d --name redis -p 6379:6379 redis:alpine 2>nul
docker run -d --name postgres -p 5432:5432 -e POSTGRES_USER=fundtracker -e POSTGRES_PASSWORD=fundtracker123 -e POSTGRES_DB=fundtracker postgres:15 2>nul
start cmd /k "cd fund-tracker\backend && call venv\Scripts\activate && python -m app.main"
start cmd /k "cd fund-tracker-desktop && npm run dev"
echo Services started!
echo Frontend: http://localhost:5173
echo Backend: http://localhost:8001
pause