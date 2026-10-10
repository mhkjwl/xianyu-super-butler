@echo off
cd /d "%~dp0"
title Xianyu Super Butler
set "PLAYWRIGHT_BROWSERS_PATH=%~dp0playwright"

echo ============================================================
echo   Xianyu Super Butler  (portable edition)
echo ------------------------------------------------------------
echo   Web UI : http://localhost:8080  (opens automatically)
echo   Data   : .\data    Logs: .\logs    Backups: .\backups
echo   Keep the server window open. Close it to stop the service.
echo ============================================================
echo.

start "Xianyu Super Butler Server" "xianyu-butler.exe"

set /a tries=0
:wait
timeout /t 2 /nobreak >nul
curl -s -o nul -m 2 http://localhost:8080/health
if %errorlevel%==0 goto :open
set /a tries+=1
if %tries% lss 60 goto :wait

echo [WARN] Server is taking longer than expected, opening browser anyway...
:open
start "" "http://localhost:8080"
exit /b 0
