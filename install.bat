@echo off
chcp 65001 >nul
setlocal

set "HOME_DIR=%USERPROFILE%\smile_kiosk"
set "SCRIPT_DIR=%~dp0"

echo Installing SMILE Kiosk to %HOME_DIR%...
if not exist "%HOME_DIR%" mkdir "%HOME_DIR%"

xcopy /s /e /y "%SCRIPT_DIR%\*.py" "%HOME_DIR%\" >nul 2>&1
xcopy /y "%SCRIPT_DIR%\requirements.txt" "%HOME_DIR%\" >nul 2>&1
xcopy /s /e /y "%SCRIPT_DIR%\models" "%HOME_DIR%\models\" >nul 2>&1
xcopy /s /e /y "%SCRIPT_DIR%\assets" "%HOME_DIR%\assets\" >nul 2>&1

python -m venv "%HOME_DIR%\venv"
"%HOME_DIR%\venv\Scripts\pip" install --upgrade pip
"%HOME_DIR%\venv\Scripts\pip" install -r "%HOME_DIR%\requirements.txt"

:: Create startup shortcut
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateShortcut.vbs"
echo sLinkFile = "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\smile_kiosk.lnk" >> "%TEMP%\CreateShortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateShortcut.vbs"
echo oLink.TargetPath = "%HOME_DIR%\run.bat" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.WorkingDirectory = "%HOME_DIR%" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Save >> "%TEMP%\CreateShortcut.vbs"
cscript "%TEMP%\CreateShortcut.vbs" >nul 2>&1
del "%TEMP%\CreateShortcut.vbs"

copy /y "%SCRIPT_DIR%\run.bat" "%HOME_DIR%\run.bat" >nul
echo SMILE Kiosk installed. Restart to start automatically.
echo Or run manually: %HOME_DIR%\run.bat
pause
