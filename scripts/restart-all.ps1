# 基金跟踪器 - 重启所有服务
# Fund Tracker v2.0.0

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   基金跟踪器 - 重启所有服务" -ForegroundColor Cyan
Write-Host "   Fund Tracker v2.0.0" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "正在执行重启操作..." -ForegroundColor Yellow
Write-Host ""

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 第一步：停止所有服务
Write-Host "[步骤 1/2] 正在停止所有服务..." -ForegroundColor Yellow
& "$ScriptDir\stop-all.ps1" -Auto
if ($LASTEXITCODE -ne 0) {
    Write-Host "[警告] 停止服务时出现问题，继续重启..." -ForegroundColor Yellow
}
Write-Host ""

# 等待几秒确保服务完全停止
Write-Host "等待服务完全停止..." -ForegroundColor Gray
Start-Sleep -Seconds 3
Write-Host ""

# 第二步：启动所有服务
Write-Host "[步骤 2/2] 正在启动所有服务..." -ForegroundColor Yellow
& "$ScriptDir\start-all.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 启动服务失败！" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   服务重启完成！" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "按回车键关闭此窗口"
