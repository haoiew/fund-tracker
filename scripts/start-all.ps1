# 基金跟踪器 - 一键启动服务
# Fund Tracker v2.0.0

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   基金跟踪器 - 一键启动服务" -ForegroundColor Cyan
Write-Host "   Fund Tracker v2.0.0" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 设置项目根目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "[调试] 当前目录: $PWD" -ForegroundColor Gray
Write-Host ""

# 检查 Docker
Write-Host "[1/5] 检查 Docker 环境..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Docker 环境正常" -ForegroundColor Green
    } else {
        throw "Docker not found"
    }
} catch {
    Write-Host "[错误] Docker 未安装或未启动！" -ForegroundColor Red
    Write-Host "请先安装 Docker Desktop 并启动服务。" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}
Write-Host ""

# 启动 Redis
Write-Host "[2/5] 启动 Redis 服务..." -ForegroundColor Yellow
$redisRunning = docker ps --filter "name=redis" --format "{{.Names}}" | Select-String "^redis$"
if (-not $redisRunning) {
    Write-Host "   Redis 未运行，正在启动..." -ForegroundColor Gray
    docker run -d --name redis -p 6379:6379 --restart unless-stopped redis:alpine 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[警告] Redis 启动失败，尝试重启..." -ForegroundColor Yellow
        docker rm -f redis 2>$null
        docker run -d --name redis -p 6379:6379 --restart unless-stopped redis:alpine 2>$null
    }
    Start-Sleep -Seconds 2
    Write-Host "[OK] Redis 已启动" -ForegroundColor Green
} else {
    Write-Host "[OK] Redis 已在运行" -ForegroundColor Green
}
Write-Host ""

# 启动 PostgreSQL
Write-Host "[3/5] 启动 PostgreSQL 服务..." -ForegroundColor Yellow
$postgresRunning = docker ps --filter "name=postgres" --format "{{.Names}}" | Select-String "^postgres$"
if (-not $postgresRunning) {
    Write-Host "   PostgreSQL 未运行，正在启动..." -ForegroundColor Gray
    docker run -d --name postgres -p 5432:5432 `
        -e POSTGRES_USER=fundtracker `
        -e POSTGRES_PASSWORD=fundtracker123 `
        -e POSTGRES_DB=fundtracker `
        --restart unless-stopped postgres:15 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[警告] PostgreSQL 启动失败，尝试重启..." -ForegroundColor Yellow
        docker rm -f postgres 2>$null
        docker run -d --name postgres -p 5432:5432 `
            -e POSTGRES_USER=fundtracker `
            -e POSTGRES_PASSWORD=fundtracker123 `
            -e POSTGRES_DB=fundtracker `
            --restart unless-stopped postgres:15 2>$null
    }
    Start-Sleep -Seconds 3
    Write-Host "[OK] PostgreSQL 已启动" -ForegroundColor Green
} else {
    Write-Host "[OK] PostgreSQL 已在运行" -ForegroundColor Green
}
Write-Host ""

# 启动后端
Write-Host "[4/5] 启动后端服务..." -ForegroundColor Yellow
$backendPath = Join-Path $PWD "fund-tracker\backend"
$venvPath = Join-Path $backendPath "venv\Scripts\activate.bat"

if (-not (Test-Path $venvPath)) {
    Write-Host "[错误] 虚拟环境不存在！" -ForegroundColor Red
    Write-Host "请先创建虚拟环境并安装依赖：" -ForegroundColor Yellow
    Write-Host "  cd fund-tracker\backend" -ForegroundColor Gray
    Write-Host "  python -m venv venv" -ForegroundColor Gray
    Write-Host "  venv\Scripts\activate" -ForegroundColor Gray
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Gray
    Read-Host "按回车键退出"
    exit 1
}

Write-Host "   正在启动 Python 后端服务..." -ForegroundColor Gray
$backendCmd = "cd /d `"$backendPath`" && echo 正在激活虚拟环境... && call venv\Scripts\activate && echo 正在启动后端服务... && python -m app.main"
Start-Process cmd -ArgumentList "/k", $backendCmd -WindowStyle Normal
Write-Host "[OK] 后端服务启动中（新窗口）" -ForegroundColor Green
Write-Host ""

# 启动前端
Write-Host "[5/5] 启动前端服务..." -ForegroundColor Yellow
$frontendPath = Join-Path $PWD "fund-tracker-desktop"
$nodeModulesPath = Join-Path $frontendPath "node_modules"

if (-not (Test-Path $nodeModulesPath)) {
    Write-Host "[警告] 前端依赖未安装！" -ForegroundColor Yellow
    $install = Read-Host "是否现在安装依赖？(Y/N)"
    if ($install -eq "Y" -or $install -eq "y") {
        Write-Host "正在安装依赖..." -ForegroundColor Gray
        Set-Location $frontendPath
        & npm install
        Set-Location $ProjectRoot
    } else {
        Write-Host "跳过安装，前端服务可能无法启动" -ForegroundColor Yellow
    }
}

Write-Host "   正在启动 Node.js 前端服务..." -ForegroundColor Gray
$frontendCmd = "cd /d `"$frontendPath`" && echo 正在启动前端服务... && npm run dev"
Start-Process cmd -ArgumentList "/k", $frontendCmd -WindowStyle Normal
Write-Host "[OK] 前端服务启动中（新窗口）" -ForegroundColor Green
Write-Host ""

# 完成
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   所有服务启动完成！" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "服务访问地址：" -ForegroundColor White
Write-Host "  - 前端界面: http://localhost:5173" -ForegroundColor Yellow
Write-Host "  - 后端API:  http://localhost:8001" -ForegroundColor Yellow
Write-Host "  - API文档:  http://localhost:8001/docs" -ForegroundColor Yellow
Write-Host "  - 健康检查: http://localhost:8001/health" -ForegroundColor Yellow
Write-Host ""
Write-Host "其他操作：" -ForegroundColor White
Write-Host "  - 停止所有服务: scripts\stop-all.ps1" -ForegroundColor Gray
Write-Host "  - 重启所有服务: scripts\restart-all.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "注意：请等待后端和前端窗口显示启动成功后再访问界面" -ForegroundColor Magenta
Write-Host ""
Read-Host "按回车键关闭此窗口"
