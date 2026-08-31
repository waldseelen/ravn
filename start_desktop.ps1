# RAVN Desktop Launcher (PowerShell)
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

Write-Host "[RAVN] Backend servisi başlatılıyor..." -ForegroundColor Cyan
$backend = Start-Process python -ArgumentList "-m uvicorn ravn_app.api.main:app --host 127.0.0.1 --port 7842" -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 2

Write-Host "[RAVN] Native masaüstü penceresi açılıyor..." -ForegroundColor Green
$app = Start-Process "$projectDir\dist_release\RAVN.exe" -PassThru

# Pencere kapatıldığında arka plan backend servisini de kapat
$app.WaitForExit()
if ($backend -and -not $backend.HasExited) {
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
}
