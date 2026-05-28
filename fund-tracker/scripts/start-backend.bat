@echo off
chcp 65001 >nul
set "PATH=%USERPROFILE%\AppData\Local\miniforge3\condabin;%PATH%"
call conda activate fund-tracker
cd /d %~dp0\..\backend
python -m app.main
if errorlevel 1 (
    echo.
    echo [ERROR] 后端启动失败，请检查 Python 环境
    echo 确保已安装依赖: pip install -r requirements.txt
)
pause
