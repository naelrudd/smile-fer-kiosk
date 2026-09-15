@echo off
chcp 65001 >nul
setlocal

echo Removing SMILE Kiosk daily schedule...
schtasks /Delete /TN "SMILE_Kiosk_Morning" /F >nul 2>&1
schtasks /Delete /TN "SMILE_Kiosk_Evening" /F >nul 2>&1
echo Done.
pause
