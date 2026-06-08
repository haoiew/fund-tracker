@echo off
setlocal

set BACKEND_DIR=%~dp0..\backend
set FRONTEND_DIR=%~dp0..\frontend
set CONDA_BAT=%USERPROFILE%\AppData\Local\miniforge3\condabin\conda.bat

echo ========================================
echo   Fund Tracker v3.0
echo ========================================
echo.

echo [0/2] Closing existing Fund Tracker ports...
call :KILL_PORT 8001
call :KILL_PORT 3000
call :KILL_PORT 5173

echo [1/2] Starting backend on port 8001...
start "Fund Tracker Backend" cmd /k cd /d "%BACKEND_DIR%" ^&^& "%CONDA_BAT%" activate fund-tracker ^&^& set "HOST=127.0.0.1" ^&^& set "PORT=8001" ^&^& python -m app.main
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
goto :EOF

:KILL_PORT
set "TARGET_PORT=%~1"
for /f %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -State Listen -LocalPort %TARGET_PORT% -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique"') do (
  echo   Closing process %%P on port %TARGET_PORT%
  taskkill /F /PID %%P >nul 2>nul
)
goto :EOF
