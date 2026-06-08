@echo off
chcp 65001 >nul
set "PATH=%USERPROFILE%\AppData\Local\miniforge3\condabin;%PATH%"
call conda activate fund-tracker
cd /d %~dp0\..\backend
set "HOST=127.0.0.1"
set "PORT=8001"
python -m app.main
if errorlevel 1 (
    echo.
    echo [ERROR] 后端启动失败，请检查 Python 环境
    echo 请检查 backend\requirements.txt 中的依赖是否已安装
)
pause
