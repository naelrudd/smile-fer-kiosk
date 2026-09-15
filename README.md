# SMILE Kiosk

A fullscreen facial expression recognition kiosk for **Ubuntu Desktop** and **Windows**. Detects faces in real-time and displays the detected expression with emoji overlays.

## Features

- Real-time face detection with YuNet
- Facial expression recognition with MobileFaceNet (7 emotions)
- Mirror-flipped camera for natural selfie-style display
- Fullscreen kiosk UI with colored bounding boxes per expression
- Threaded capture/inference pipeline for low-latency, stable tracking
- Offline emoji rendering (bundled Noto Emoji font, no internet needed)
- Innovation logo overlay (bundled `assets/logo-inovasi.png`)
- Combo game: sustained smiles build a combo, milestones fire confetti,
  screen flash, popup text, and a chime (Windows)
- Auto-start on login (Ubuntu and Windows)
- Single-command installer
- Pre-built executables available for Linux and Windows

## Expressions Supported

| Expression | Emoji | Color  |
|------------|-------|--------|
| Angry      | 😠   | Red    |
| Disgust    | 😒   | Orange |
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

## Full Windows Kiosk Installation (detailed)

Step-by-step for setting up the kiosk PC with the daily schedule
(on 07:00, hibernate 18:00).

### Step 1 — Download

1. Go to https://github.com/naelrudd/smile-fer-kiosk/releases/latest
2. Download **Source code (zip)** AND **smile_kiosk_windows.exe**.
3. Extract the Source code zip, e.g. to `Downloads\smile-fer-kiosk-master`.

### Step 2 — Install Python (only needed for source install)

1. Download Python from https://www.python.org/downloads/
2. Run the installer and **check "Add Python to PATH"** before clicking Install.
3. Verify in Command Prompt:

```batch
python --version
```

(Skip Step 2–3 if you only use `smile_kiosk_windows.exe`.)

### Step 3 — Install the app

1. Open the extracted folder.
2. Right-click **`install.bat`** → **Run as administrator**.
3. Wait until it prints "SMILE Kiosk installed."
4. (Exe alternative: copy `smile_kiosk_windows.exe` into `%USERPROFILE%\smile_kiosk\`.)

### Step 4 — Test it runs

```batch
%USERPROFILE%\smile_kiosk\run.bat
```

The camera preview must appear fullscreen. Press `ESC` or `Q` to exit.
If it fails, check the log: `%USERPROFILE%\smile_kiosk\smile_kiosk.log`.

### Step 5 — Set the daily schedule (on 07:00, off 18:00)

1. Right-click **`setup_schedule.bat`** (also copied to `%USERPROFILE%\smile_kiosk\`) → **Run as administrator**.
2. It creates two Windows Scheduled Tasks:
   - `SMILE_Kiosk_Morning` — starts the app every day at 07:00 (wakes the PC)
   - `SMILE_Kiosk_Evening` — closes the app and hibernates at 18:00

### Step 6 — Enable wake timers (required for the 07:00 auto-start)

1. Open **Control Panel → Power Options → Change plan settings → Change advanced power settings**.
2. Expand **Sleep → Allow wake timers** → set to **Enable**. Click OK.
3. Hibernate must be on. In an **admin** Command Prompt:

```batch
powercfg /hibernate on
```

### Step 7 — TV auto power (optional, done on the TV itself)

Windows cannot power the TV. Use one of:
- **HDMI-CEC**: enable it in the TV settings (e.g. "Anynet+", "BRAVIA Sync",
  "Simplink"). The TV switches on when the PC wakes and outputs video.
- **TV timer**: set the TV's own auto-on schedule (most smart TVs have it).

### Step 8 — Verify everything

1. In Task Scheduler (`taskschd.msc`) check both `SMILE_Kiosk_*` tasks exist,
   and the Morning task's conditions show "Wake the computer to run this task".
2. Temporarily move the Morning task time 2 minutes ahead (right-click →
   Properties → Triggers → Edit) and confirm the PC wakes and the app opens.
   Move it back to 07:00 afterwards.
3. Optionally test the Evening task the same way (it hibernates the PC).

### Removing the schedule

Right-click `%USERPROFILE%\smile_kiosk\remove_schedule.bat` → Run as administrator.

## Manual Run

### Ubuntu

```bash
~/smile_kiosk/run.sh
```

### Windows

```batch
%USERPROFILE%\smile_kiosk\run.bat
```

Exit by pressing `ESC` or `Q`. Press `F` to toggle the FPS/latency HUD.

## Build Executable Yourself

### Requirements

- Python 3.12+
- `pip install -r requirements.txt pyinstaller`

### Linux

```bash
pyinstaller --onefile --name smile_kiosk_linux --add-data "models:models" --add-data "assets:assets" --hidden-import cv2 smile_kiosk.py
```

### Windows

```batch
pyinstaller --onefile --name smile_kiosk_windows --add-data "models;models" --add-data "assets;assets" --hidden-import cv2 smile_kiosk.py
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
├── requirements.txt     # Python dependencies
├── models/              # ONNX model files
│   ├── face_detection_yunet_2023mar.onnx
│   └── facial_expression_recognition_mobilefacenet_2022july.onnx
├── assets/              # Bundled Noto Emoji font + innovation logo
│   ├── NotoEmoji-Regular.ttf
│   └── logo-inovasi.png
├── install.sh           # Ubuntu installer + autostart
├── install.bat          # Windows installer + autostart
├── run.sh               # Ubuntu manual launcher
├── run.bat              # Windows manual launcher
├── setup_schedule.bat   # Windows: daily on 07:00 / hibernate 18:00
├── remove_schedule.bat  # Windows: remove the scheduled tasks
├── .github/workflows/   # CI/CD for building executables
├── dist/                # Pre-built executables
└── README.md
```

## License

The ONNX models and wrappers are from the OpenCV Zoo project and are subject to their respective licenses. The application code is provided as-is.
