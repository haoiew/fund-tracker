# 基金跟踪器 - 停止所有服务
# Fund Tracker v2.0.0

param(
    [switch]$Auto = $false
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   基金跟踪器 - 停止所有服务" -ForegroundColor Cyan
Write-Host "   Fund Tracker v2.0.0" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 停止前端
Write-Host "[1/4] 停止前端服务..." -ForegroundColor Yellow
$frontendProcess = Get-Process -Name "cmd" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*FundTracker-Frontend*" }
if ($frontendProcess) {
    Stop-Process -Id $frontendProcess.Id -Force
    Write-Host "[OK] 前端服务已停止" -ForegroundColor Green
} else {
    Write-Host "[OK] 前端服务未运行" -ForegroundColor Green
}
Write-Host ""

# 停止后端
Write-Host "[2/4] 停止后端服务..." -ForegroundColor Yellow
$backendProcess = Get-Process -Name "cmd" -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*FundTracker-Backend*" }
if ($backendProcess) {
    Stop-Process -Id $backendProcess.Id -Force
    Write-Host "[OK] 后端服务已停止" -ForegroundColor Green
} else {
    Write-Host "[OK] 后端服务未运行" -ForegroundColor Green
}
Write-Host ""

# 停止基础设施
Write-Host "[3/4] 检查并停止基础设施服务..." -ForegroundColor Yellow
Write-Host ""

if (-not $Auto) {
    Write-Host "   是否停止 Redis 和 PostgreSQL 容器？" -ForegroundColor White
    Write-Host "   [1] 是 - 停止所有服务（包括数据库）" -ForegroundColor Gray
    Write-Host "   [2] 否 - 只停止应用服务（保留数据库）" -ForegroundColor Gray
    Write-Host "   [3] 取消" -ForegroundColor Gray
    $choice = Read-Host "   请选择 (1/2/3)"
    
    if ($choice -eq "3") {
        Write-Host ""
        Write-Host "操作已取消" -ForegroundColor Yellow
        Read-Host "按回车键退出"
        exit 0
    }
    
    if ($choice -eq "2") {
        Write-Host ""
        Write-Host "[OK] 保留 Redis 和 PostgreSQL 运行" -ForegroundColor Green
        goto Finish
    }
}

# 停止 Redis
Write-Host ""
Write-Host "[4/4] 停止 Redis 服务..." -ForegroundColor Yellow
$redisRunning = docker ps --filter "name=redis" --format "{{.Names}}" | Select-String "^redis$"
if ($redisRunning) {
    docker stop redis 2>$null | Out-Null
    Write-Host "[OK] Redis 已停止" -ForegroundColor Green
} else {
    Write-Host "[OK] Redis 未运行" -ForegroundColor Green
}

# 停止 PostgreSQL
Write-Host ""
Write-Host "[4/4] 停止 PostgreSQL 服务..." -ForegroundColor Yellow
$postgresRunning = docker ps --filter "name=postgres" --format "{{.Names}}" | Select-String "^postgres$"
if ($postgresRunning) {
    docker stop postgres 2>$null | Out-Null
    Write-Host "[OK] PostgreSQL 已停止" -ForegroundColor Green
} else {
    Write-Host "[OK] PostgreSQL 未运行" -ForegroundColor Green
}

:Finish
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   服务停止完成！" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "已停止的服务：" -ForegroundColor White
Write-Host "  [OK] 前端服务 (Node.js)" -ForegroundColor Green
Write-Host "  [OK] 后端服务 (Python)" -ForegroundColor Green

if ($Auto -or $choice -eq "2") {
    Write-Host "  [--] Redis 缓存（保留运行）" -ForegroundColor Gray
    Write-Host "  [--] PostgreSQL 数据库（保留运行）" -ForegroundColor Gray
} else {
    Write-Host "  [OK] Redis 缓存" -ForegroundColor Green
    Write-Host "  [OK] PostgreSQL 数据库" -ForegroundColor Green
}

Write-Host ""
Write-Host "其他操作：" -ForegroundColor White
Write-Host "  - 启动所有服务: scripts\start.bat" -ForegroundColor Gray
Write-Host "  - 重启所有服务: scripts\restart.bat" -ForegroundColor Gray
Write-Host ""

if (-not $Auto) {
    Read-Host "按回车键关闭此窗口"
}
