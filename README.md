# SMILE Kiosk

A fullscreen facial expression recognition kiosk for Ubuntu Desktop. Detects faces in real-time and displays the detected expression with emoji overlays.

## Features

- Real-time face detection with YuNet
- Facial expression recognition with MobileFaceNet (7 emotions)
- Mirror-flipped camera for natural selfie-style display
- Fullscreen kiosk UI with colored bounding boxes per expression
- Auto-start on Ubuntu Desktop login
- Single-command installer

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

## Quick Start

1. Download and extract `smile_kiosk.zip`.
2. Open a terminal inside the extracted `smile_kiosk` folder.
3. Run the installer:

```bash
chmod +x install.sh
./install.sh
```

4. Reboot the machine.

The kiosk will start automatically after login.

## Manual Run

```bash
~/smile_kiosk/run.sh
```

Exit by pressing `ESC` or `Q`.

## System Requirements

- Ubuntu Desktop (tested on Ubuntu with GNOME)
- Webcam
- Python 3.12+
- Internet connection only during installation (for pip packages)

## File Structure

```
smile_kiosk/
├── smile_kiosk.py       # Main application
├── yunet.py             # YuNet face detector wrapper
├── facial_fer_model.py  # FER model wrapper
├── models/              # ONNX model files
│   ├── face_detection_yunet_2023mar.onnx
│   └── facial_expression_recognition_mobilefacenet_2022july.onnx
├── install.sh           # One-time installer with autostart setup
├── run.sh               # Manual launcher
└── README.md
```

## License

The ONNX models and wrappers are from the OpenCV Zoo project and are subject to their respective licenses. The application code is provided as-is.
