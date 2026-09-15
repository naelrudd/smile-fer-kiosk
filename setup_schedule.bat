@echo off
chcp 65001 >nul
setlocal

echo Setting up SMILE Kiosk daily schedule...
echo (Run this as Administrator!)

:: App location: prefer the standalone exe, fall back to run.bat (source install)
set "APP_DIR=%USERPROFILE%\smile_kiosk"
if exist "%APP_DIR%\smile_kiosk_windows.exe" (
    set "APP_CMD=%APP_DIR%\smile_kiosk_windows.exe"
) else (
    set "APP_CMD=%APP_DIR%\run.bat"
)

if not exist "%APP_CMD%" (
    echo ERROR: %APP_CMD% not found. Install the app first with install.bat,
    echo or copy smile_kiosk_windows.exe into %APP_DIR%.
    pause
    exit /b 1
)

:: --- Morning: start app at 07:00 ---
schtasks /Delete /TN "SMILE_Kiosk_Morning" /F >nul 2>&1
schtasks /Create ^
  /TN "SMILE_Kiosk_Morning" ^
  /TR "'%APP_CMD%'" ^
  /SC DAILY ^
  /ST 07:00 ^
  /RL HIGHEST ^
  /F
if %errorlevel% neq 0 (
    echo Failed to create morning task. Run as Administrator.
    pause
    exit /b 1
)

:: Allow this task to wake the PC from sleep/hibernate
powershell -NoProfile -Command "$t = Get-ScheduledTask -TaskName 'SMILE_Kiosk_Morning'; $t.Settings.WakeToRun = $true; Set-ScheduledTask $t" >nul 2>&1

echo Morning task created: start app at 07:00 (wake enabled).

:: --- Evening: close app + hibernate at 18:00 ---
schtasks /Delete /TN "SMILE_Kiosk_Evening" /F >nul 2>&1
schtasks /Create ^
  /TN "SMILE_Kiosk_Evening" ^
  /TR "powershell.exe -NoProfile -Command \"Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*smile_kiosk*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Start-Sleep -s 3; shutdown /h\"" ^
  /SC DAILY ^
  /ST 18:00 ^
  /RL HIGHEST ^
  /F
if %errorlevel% neq 0 (
    echo Failed to create evening task. Run as Administrator.
    pause
    exit /b 1
)

echo Evening task created: close app and hibernate at 18:00.
echo.
echo IMPORTANT:
echo  1. Enable wake timers: Control Panel ^> Power Options ^> Change plan settings
echo     ^> Change advanced power settings ^> Sleep ^> Allow wake timers = Enable.
echo  2. TV auto-on: enable HDMI-CEC on the TV, or set the TV's own power timer.
pause
