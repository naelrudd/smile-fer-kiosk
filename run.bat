@echo off
chcp 65001 >nul
cd /d "%USERPROFILE%\smile_kiosk"
"%USERPROFILE%\smile_kiosk\venv\Scripts\python" smile_kiosk.py
