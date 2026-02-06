@echo off
chcp 936 >nul
title 基金跟踪器 - 重启所有服务
cls

echo ============================================
echo    基金跟踪器 - 重启所有服务
echo    Fund Tracker v2.0.0
echo ============================================
echo.

echo 正在执行重启操作...
echo.

REM 获取脚本所在目录
set "SCRIPT_DIR=%~dp0"

REM 第一步：停止所有服务
echo [步骤 1/2] 正在停止所有服务...
call "%SCRIPT_DIR%stop-all.bat" auto
if errorlevel 1 (
    echo [警告] 停止服务时出现问题，继续重启...
)
echo.

REM 等待几秒确保服务完全停止
echo 等待服务完全停止...
timeout /t 3 /nobreak >nul
echo.

REM 第二步：启动所有服务
echo [步骤 2/2] 正在启动所有服务...
call "%SCRIPT_DIR%start-all.bat"
if errorlevel 1 (
    echo [错误] 启动服务失败！
    pause
    exit /b 1
)

echo.
echo ============================================
echo    服务重启完成！
echo ============================================
echo.
pause
