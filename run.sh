#!/bin/bash
cd "$HOME/smile_kiosk"
export QT_QPA_PLATFORM=xcb
./venv/bin/python3 smile_kiosk.py
