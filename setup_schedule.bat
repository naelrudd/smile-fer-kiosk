@echo off
chcp 65001 >nul
setlocal

echo Setting up SMILE Kiosk daily schedule...

:: Path to executable (adjust if installed elsewhere)
set "APP_PATH=%USERPROFILE%\smile_kiosk\smile_kiosk.exe"
set "APP_DIR=%USERPROFILE%\smile_kiosk"

:: --- Morning: turn on / wake at 08:00 ---
:: Remove existing task if any
schtasks /Delete /TN "SMILE_Kiosk_Morning" /F >nul 2>&1

:: Create morning task: wake PC from sleep and run the app
schtasks /Create ^
  /TN "SMILE_Kiosk_Morning" ^
  /TR "\'%APP_PATH%\'" ^
  /SC DAILY ^
  /ST 08:00 ^
  /RL HIGHEST ^
  /F

if %errorlevel% neq 0 (
    echo Failed to create morning task.
    exit /b 1
)

:: Wake the computer from sleep for this task
powercfg /waketimers

echo Morning task created: start app at 08:00.

:: --- Evening: turn off at 17:00 ---
schtasks /Delete /TN "SMILE_Kiosk_Evening" /F >nul 2>&1

schtasks /Create ^
  /TN "SMILE_Kiosk_Evening" ^
  /TR "powershell.exe -Command \"Stop-Process -Name smile_kiosk -Force; Start-Sleep -s 5; powercfg /h off; shutdown /h\"" ^
  /SC DAILY ^
  /ST 17:00 ^
  /RL HIGHEST ^
  /F

if %errorlevel% neq 0 (
    echo Failed to create evening task.
    exit /b 1
)

echo Evening task created: stop app and hibernate at 17:00.
echo.
echo IMPORTANT: For PC to wake at 08:00, enable wake timers in BIOS / Windows.
echo To wake the TV automatically, enable HDMI-CEC on TV or set TV auto-on schedule.
pause
