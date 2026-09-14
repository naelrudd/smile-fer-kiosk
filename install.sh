#!/bin/bash
# install.sh - Run once on Ubuntu Desktop after extracting smile_kiosk.zip
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOME_DIR="$HOME/smile_kiosk"

echo "Installing SMILE Kiosk to $HOME_DIR..."
mkdir -p "$HOME_DIR"

# Copy application files
cp "$SCRIPT_DIR"/*.py "$HOME_DIR/"
cp -r "$SCRIPT_DIR"/assets "$HOME_DIR/" 2>/dev/null || true
cp -r "$SCRIPT_DIR"/models "$HOME_DIR/"

# Create virtual environment
python3 -m venv "$HOME_DIR/venv"
"$HOME_DIR/venv/bin/pip" install --upgrade pip
"$HOME_DIR/venv/bin/pip" install opencv-python numpy

# Setup autostart for current user
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

# Generate desktop entry pointing to the installed location
cat > "$AUTOSTART_DIR/smile-kiosk.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=SMILE Kiosk
Exec=/bin/bash -c 'cd \"$HOME_DIR\" && export QT_QPA_PLATFORM=xcb && ./venv/bin/python3 smile_kiosk.py'
Icon=camera-web
Comment=Auto-start SMILE Facial Expression Kiosk
Terminal=false
X-GNOME-Autostart-enabled=true
EOF

chmod +x "$AUTOSTART_DIR/smile-kiosk.desktop"

cat > "$HOME_DIR/run.sh" <<'EOF'
#!/bin/bash
cd "$HOME/smile_kiosk"
export QT_QPA_PLATFORM=xcb
./venv/bin/python3 smile_kiosk.py
EOF
chmod +x "$HOME_DIR/run.sh"

echo "SMILE Kiosk installed. Reboot to start automatically."
echo "Or run manually: $HOME_DIR/run.sh"
