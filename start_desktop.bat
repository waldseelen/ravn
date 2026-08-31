@echo off
title RAVN Desktop Launcher
cd /d "%~dp0"

echo [RAVN] Backend servisi baslatiliyor...
start /b "" python -m uvicorn ravn_app.api.main:app --host 127.0.0.1 --port 7842

echo [RAVN] Native masaustu penceresi aciliyor...
timeout /t 2 /nobreak >nul
start "" "%~dp0dist_release\RAVN.exe"
