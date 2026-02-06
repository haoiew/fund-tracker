@echo off
chcp 936 >nul
title 基金跟踪器 - 停止所有服务
cls

echo ============================================
echo    基金跟踪器 - 停止所有服务
echo    Fund Tracker v2.0.0
echo ============================================
echo.

REM 检查是否为自动模式（从restart-all调用）
set "AUTO_MODE=%~1"

echo [1/4] 停止前端服务...
tasklist /fi "windowtitle eq FundTracker-Frontend" 2>nul | findstr "cmd.exe" >nul
if not errorlevel 1 (
    taskkill /fi "windowtitle eq FundTracker-Frontend" /f >nul 2>&1
    echo [OK] 前端服务已停止
) else (
    echo [OK] 前端服务未运行
)
echo.

echo [2/4] 停止后端服务...
tasklist /fi "windowtitle eq FundTracker-Backend" 2>nul | findstr "cmd.exe" >nul
if not errorlevel 1 (
    taskkill /fi "windowtitle eq FundTracker-Backend" /f >nul 2>&1
    echo [OK] 后端服务已停止
) else (
    echo [OK] 后端服务未运行
)
echo.

echo [3/4] 检查并停止基础设施服务...
echo.

REM 如果是自动模式，跳过交互，只停止应用服务
if "%AUTO_MODE%"=="auto" (
    echo [自动模式] 只停止应用服务，保留数据库运行
    goto :finish
)

echo    是否停止 Redis 和 PostgreSQL 容器？
echo    [1] 是 - 停止所有服务（包括数据库）
echo    [2] 否 - 只停止应用服务（保留数据库）
echo    [3] 取消
choice /c 123 /n /m "请选择 (1/2/3): "

if errorlevel 3 (
    echo.
    echo 操作已取消
    pause
    exit /b 0
)

if errorlevel 2 (
    echo.
    echo [OK] 保留 Redis 和 PostgreSQL 运行
    goto :finish
)

if errorlevel 1 (
    echo.
    echo [4/4] 停止 Redis 服务...
    docker ps --filter "name=redis" --format "{{.Names}}" | findstr "^redis$" >nul
    if not errorlevel 1 (
        docker stop redis >nul 2>&1
        echo [OK] Redis 已停止
    ) else (
        echo [OK] Redis 未运行
    )
    
    echo.
    echo [4/4] 停止 PostgreSQL 服务...
    docker ps --filter "name=postgres" --format "{{.Names}}" | findstr "^postgres$" >nul
    if not errorlevel 1 (
        docker stop postgres >nul 2>&1
        echo [OK] PostgreSQL 已停止
    ) else (
        echo [OK] PostgreSQL 未运行
    )
)

:finish
echo.
echo ============================================
echo    服务停止完成！
echo ============================================
echo.
echo 已停止的服务：
echo   [OK] 前端服务 (Node.js)
echo   [OK] 后端服务 (Python)

if "%AUTO_MODE%"=="auto" (
    echo   [--] Redis 缓存（保留运行）
    echo   [--] PostgreSQL 数据库（保留运行）
) else (
    if errorlevel 1 (
        echo   [OK] Redis 缓存
        echo   [OK] PostgreSQL 数据库
    )
)

echo.
echo 其他操作：
echo   - 启动所有服务: scripts\start-all.bat
echo   - 重启所有服务: scripts\restart-all.bat
echo.

if not "%AUTO_MODE%"=="auto" (
    pause
)
