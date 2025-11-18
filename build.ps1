# RAVN Build Script
# Proje yapısını kontrol et ve gerekli dosyaları kur

param(
    [string]$Action = "check"
)

Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   RAVN - Media Downloader Builder     ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

function Check-Environment {
    Write-Host "🔍 Ortam kontrolü yapılıyor..." -ForegroundColor Yellow

    # Python kontrolü
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonVersion = python --version
        Write-Host "✓ Python: $pythonVersion" -ForegroundColor Green
    }
    else {
        Write-Host "✗ Python bulunamadı!" -ForegroundColor Red
        return $false
    }

    # FFmpeg kontrolü
    if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
        Write-Host "✓ FFmpeg: Kurulu" -ForegroundColor Green
    }
    else {
        Write-Host "⚠ FFmpeg bulunamadı. Uygulama başlatıldığında indirilecek." -ForegroundColor Yellow
    }

    # Bağımlılıklar kontrolü
    if (Test-Path "requirements.txt") {
        Write-Host "✓ requirements.txt: Bulundu" -ForegroundColor Green
    }
    else {
        Write-Host "✗ requirements.txt bulunamadı!" -ForegroundColor Red
        return $false
    }

    return $true
}

function Install-ProjectDependencies {
    Write-Host "`n📦 Bağımlılıklar kuruluyor..." -ForegroundColor Yellow

    if (-not (Test-Path "venv")) {
        Write-Host "Sanal ortam oluşturuluyor..." -ForegroundColor Cyan
        python -m venv venv
    }

    & ".\venv\Scripts\Activate.ps1"
    pip install -r requirements.txt

    Write-Host "✓ Bağımlılıklar kuruldu" -ForegroundColor Green
}

function Invoke-Tests {
    Write-Host "`n🧪 Testler çalıştırılıyor..." -ForegroundColor Yellow

    if (Get-Command pytest -ErrorAction SilentlyContinue) {
        pytest tests/ -v
        Write-Host "✓ Testler tamamlandı" -ForegroundColor Green
    }
    else {
        Write-Host "⚠ pytest bulunamadı. Testler atlanıyor." -ForegroundColor Yellow
    }
}

function Start-RavnApp {
    Write-Host "`n🚀 Uygulama başlatılıyor..." -ForegroundColor Yellow
    python -m ravn_app.ui.main_window
}

function Clear-ProjectFiles {
    Write-Host "`n🧹 Proje temizleniyor..." -ForegroundColor Yellow

    Get-ChildItem -Path . -Include __pycache__ -Recurse -Directory | Remove-Item -Recurse -Force
    Get-ChildItem -Path . -Include *.pyc -Recurse | Remove-Item -Force
    Get-ChildItem -Path . -Include .pytest_cache -Recurse -Directory | Remove-Item -Recurse -Force

    Write-Host "✓ Proje temizlendi" -ForegroundColor Green
}

# Ana akış
switch ($Action.ToLower()) {
    "check" {
        Check-Environment
    }
    "install" {
        Check-Environment
        Install-ProjectDependencies
    }
    "test" {
        Invoke-Tests
    }
    "run" {
        Start-RavnApp
    }
    "clean" {
        Clear-ProjectFiles
    }
    "all" {
        Check-Environment
        Install-ProjectDependencies
        Clear-ProjectFiles
        Invoke-Tests
        Start-RavnApp
    }
    default {
        Write-Host "Kullanım: .\build.ps1 [check|install|test|run|clean|all]" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Seçenekler:" -ForegroundColor Cyan
        Write-Host "  check    - Ortam kontrolü yap" -ForegroundColor Gray
        Write-Host "  install  - Bağımlılıkları kur" -ForegroundColor Gray
        Write-Host "  test     - Testleri çalıştır" -ForegroundColor Gray
        Write-Host "  run      - Uygulamayı başlat" -ForegroundColor Gray
        Write-Host "  clean    - Projeden cache'leri temizle" -ForegroundColor Gray
        Write-Host "  all      - Hepsi (install→clean→test→run)" -ForegroundColor Gray
    }
}
