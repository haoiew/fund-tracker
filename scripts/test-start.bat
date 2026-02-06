@echo off
echo ============================================
echo    基金跟踪器 - 启动测试（调试模式）
echo ============================================
echo.

REM 显示当前路径信息
echo [调试信息]
echo 脚本路径: %~dp0
echo 脚本名称: %~nx0
echo.

REM 设置项目根目录
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

echo 脚本目录: %SCRIPT_DIR%
echo 项目根目录: %PROJECT_ROOT%
echo.

REM 尝试切换目录
echo 尝试切换到项目根目录...
cd /d "%PROJECT_ROOT%"
if errorlevel 1 (
    echo [错误] 切换目录失败！
    echo 请检查脚本位置是否正确
    pause
    exit /b 1
)

echo [成功] 当前目录: %CD%
echo.

REM 检查关键目录是否存在
echo 检查项目结构...
if exist "fund-tracker\backend" (
    echo [✓] 后端目录存在
) else (
    echo [✗] 后端目录不存在: fund-tracker\backend
)

if exist "fund-tracker-desktop" (
    echo [✓] 前端目录存在
) else (
    echo [✗] 前端目录不存在: fund-tracker-desktop
)

if exist "scripts" (
    echo [✓] 脚本目录存在
) else (
    echo [✗] 脚本目录不存在: scripts
)
echo.

REM 检查虚拟环境
echo 检查虚拟环境...
if exist "fund-tracker\backend\venv\Scripts\activate.bat" (
    echo [✓] 虚拟环境存在
) else (
    echo [✗] 虚拟环境不存在: fund-tracker\backend\venv
)
echo.

REM 检查Docker
echo 检查 Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [✗] Docker 未安装或未启动
) else (
    echo [✓] Docker 已安装
    docker --version
)
echo.

echo ============================================
echo    测试完成
echo ============================================
pause
