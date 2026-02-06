@echo off
chcp 936 >nul
title 基金跟踪器 - 服务状态检查
cls

echo ============================================
echo    基金跟踪器 - 服务状态检查
echo    Fund Tracker v2.0.0
echo ============================================
echo.

REM 设置项目根目录
set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

echo [1/5] 检查 Docker 环境...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [X] Docker 未安装或未启动
) else (
    echo [OK] Docker 环境正常
)
echo.

echo [2/5] 检查 Redis 服务...
docker ps --filter "name=redis" --format "{{.Names}}" | findstr "^redis$" >nul
if errorlevel 1 (
    echo [X] Redis 未运行
) else (
    echo [OK] Redis 正在运行
    docker ps --filter "name=redis" --format "  状态: {{.Status}} | 端口: {{.Ports}}"
)
echo.

echo [3/5] 检查 PostgreSQL 服务...
docker ps --filter "name=postgres" --format "{{.Names}}" | findstr "^postgres$" >nul
if errorlevel 1 (
    echo [X] PostgreSQL 未运行
) else (
    echo [OK] PostgreSQL 正在运行
    docker ps --filter "name=postgres" --format "  状态: {{.Status}} | 端口: {{.Ports}}"
)
echo.

echo [4/5] 检查后端服务...
tasklist /fi "windowtitle eq FundTracker-Backend" 2>nul | findstr "cmd.exe" >nul
if not errorlevel 1 (
    echo [OK] 后端服务正在运行
    REM 检查端口
    netstat -ano | findstr ":8001" | findstr "LISTENING" >nul
    if not errorlevel 1 (
        echo   端口 8001: 正在监听
    ) else (
        echo   端口 8001: 未监听（可能正在启动中）
    )
) else (
    echo [X] 后端服务未运行
)
echo.

echo [5/5] 检查前端服务...
tasklist /fi "windowtitle eq FundTracker-Frontend" 2>nul | findstr "cmd.exe" >nul
if not errorlevel 1 (
    echo [OK] 前端服务正在运行
    REM 检查端口
    netstat -ano | findstr ":5173" | findstr "LISTENING" >nul
    if not errorlevel 1 (
        echo   端口 5173: 正在监听
    ) else (
        echo   端口 5173: 未监听（可能正在启动中）
    )
) else (
    echo [X] 前端服务未运行
)
echo.

echo ============================================
echo    状态检查完成
echo ============================================
echo.
echo 访问地址：
echo   - 前端界面: http://localhost:5173
echo   - 后端API:  http://localhost:8001
echo   - API文档:  http://localhost:8001/docs
echo.
echo 操作命令：
echo   - 启动服务: scripts\start-all.bat
echo   - 停止服务: scripts\stop-all.bat
echo   - 重启服务: scripts\restart-all.bat
echo.
pause
