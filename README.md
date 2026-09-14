# SMILE Kiosk

A fullscreen facial expression recognition kiosk for **Ubuntu Desktop** and **Windows**. Detects faces in real-time and displays the detected expression with emoji overlays.

## Features

- Real-time face detection with YuNet
- Facial expression recognition with MobileFaceNet (7 emotions)
- Mirror-flipped camera for natural selfie-style display
- Fullscreen kiosk UI with colored bounding boxes per expression
- Auto-start on login (Ubuntu and Windows)
- Single-command installer
- Pre-built executables available for Linux and Windows

## Expressions Supported

| Expression | Emoji | Color  |
|------------|-------|--------|
| Angry      | 😠   | Red    |
| Disgust    | 🤢   | Orange |
| Fearful    | 😨   | Orange |
| Happy      | 😄   | Green  |
| Neutral    | 😐   | White  |
| Sad        | 😢   | Blue   |
| Surprised  | 😲   | Cyan   |

## Download Pre-built Executables

Download the latest executables from GitHub Actions artifacts:
- `smile_kiosk_linux` — for Ubuntu/Linux
- `smile_kiosk_windows.exe` — for Windows

Or download from the [Releases](../../releases) page.

## Quick Start

### Option 1: Pre-built Executable

#### Linux

```bash
chmod +x smile_kiosk_linux
./smile_kiosk_linux
```

#### Windows

Double-click `smile_kiosk_windows.exe` or run from Command Prompt:

```batch
smile_kiosk_windows.exe
```

### Option 2: Install from Source

#### Ubuntu

1. Extract `smile_kiosk.zip`.
2. Open terminal inside the `smile_kiosk` folder.
3. Run:

```bash
chmod +x install.sh
./install.sh
```

4. Reboot.

#### Windows

1. Extract `smile_kiosk.zip`.
2. Open `smile_kiosk` folder.
3. Double-click `install.bat`.
4. Restart your PC.

## Manual Run

### Ubuntu

```bash
~/smile_kiosk/run.sh
```

### Windows

```batch
%USERPROFILE%\smile_kiosk\run.bat
```

Exit by pressing `ESC` or `Q`.

## Build Executable Yourself

### Requirements

- Python 3.12+
- `pip install opencv-python numpy pyinstaller`

### Linux

```bash
pyinstaller --onefile --name smile_kiosk_linux --add-data "models:models" --hidden-import cv2 smile_kiosk.py
```

### Windows

```batch
pyinstaller --onefile --name smile_kiosk_windows --add-data "models;models" --hidden-import cv2 smile_kiosk.py
```

## System Requirements

- Ubuntu Desktop or Windows 10/11
- Webcam
- Python 3.12+ (only for source install)
- Internet connection only during installation

## File Structure

```
smile_kiosk/
├── smile_kiosk.py       # Main application
├── yunet.py             # YuNet face detector wrapper
├── facial_fer_model.py  # FER model wrapper
├── models/              # ONNX model files
│   ├── face_detection_yunet_2023mar.onnx
│   └── facial_expression_recognition_mobilefacenet_2022july.onnx
├── install.sh           # Ubuntu installer + autostart
├── install.bat          # Windows installer + autostart
├── run.sh               # Ubuntu manual launcher
├── run.bat              # Windows manual launcher
├── .github/workflows/   # CI/CD for building executables
├── dist/                # Pre-built executables
└── README.md
```

## License

The ONNX models and wrappers are from the OpenCV Zoo project and are subject to their respective licenses. The application code is provided as-is.
