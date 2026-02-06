@echo off
chcp 936 >nul
title Fund Tracker - Service Monitor
cls

:LOOP
cls
echo ============================================
echo    Fund Tracker - Service Monitor
echo    Press Ctrl+C to exit
echo ============================================
echo.
echo Last updated: %date% %time%
echo.

REM Check Docker
echo [Docker]
docker ps --format "  {{.Names}}: {{.Status}}" 2>nul | findstr "redis\|postgres"
if errorlevel 1 (
    echo   No database containers running
)
echo.

REM Check Ports
echo [Port Status]
echo   Backend  (8001):
netstat -ano | findstr ":8001" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo     [Stopped]
) else (
    echo     [Running]
)

echo   Frontend (5173):
netstat -ano | findstr ":5173" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo     [Stopped]
) else (
    echo     [Running]
)

echo   Redis    (6379):
netstat -ano | findstr ":6379" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo     [Stopped]
) else (
    echo     [Running]
)

echo   PostgreSQL (5432):
netstat -ano | findstr ":5432" | findstr "LISTENING" >nul
if errorlevel 1 (
    echo     [Stopped]
) else (
    echo     [Running]
)
echo.

REM Check Backend Health
echo [Backend Health]
curl -s http://localhost:8001/health >nul 2>&1
if errorlevel 1 (
    echo   Status: Unreachable
) else (
    echo   Status: OK
    curl -s http://localhost:8001/health 2>nul
)
echo.

echo Refreshing in 5 seconds...
timeout /t 5 /nobreak >nul
goto LOOP
