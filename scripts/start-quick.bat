@echo off
chcp 936 >nul
title Fund Tracker - Quick Start
cls

echo ============================================
echo    Fund Tracker - Quick Start
echo    v2.0.0
echo ============================================
echo.

cd /d "%~dp0.."
echo Current directory: %CD%
echo.

echo Starting Redis...
docker run -d --name redis -p 6379:6379 redis:alpine 2>nul || docker start redis 2>nul
echo Starting PostgreSQL...
docker run -d --name postgres -p 5432:5432 -e POSTGRES_USER=fundtracker -e POSTGRES_PASSWORD=fundtracker123 -e POSTGRES_DB=fundtracker postgres:15 2>nul || docker start postgres 2>nul

echo.
echo Starting Backend with conda (Explore)...

REM Use full path to conda
set "CONDA_ACTIVATE=C:\Users\138721\AppData\Local\miniforge3\Scripts\activate.bat"

if exist "%CONDA_ACTIVATE%" (
    start "FundTracker-Backend" cmd /k "cd fund-tracker\backend && call "%CONDA_ACTIVATE%" Explore && python -m app.main"
) else (
    echo [Error] Conda not found!
    pause
    exit /b 1
)

echo Starting Frontend...
start "FundTracker-Frontend" cmd /k "cd fund-tracker-desktop && npm run dev"

echo.
echo ============================================
echo    All services started!
echo ============================================
echo.
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8001
echo.
pause
