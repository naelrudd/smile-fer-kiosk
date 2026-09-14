#!/usr/bin/env python3
"""
SMILE Kiosk - Minimal modern UI for photo booth / wahana
Run: python3 smile_kiosk.py
"""
import os
import sys
import collections
import numpy as np
import cv2 as cv

from PIL import Image, ImageFont

from pilmoji import Pilmoji

from yunet import YuNet
from facial_fer_model import FacialExpressionRecog

# --- Configuration ---
MODEL_FACE = 'models/face_detection_yunet_2023mar.onnx'
MODEL_FER = 'models/facial_expression_recognition_mobilefacenet_2022july.onnx'

EXPRESSIONS = {
    0: {'label': 'Angry',    'emoji': '😠', 'color': (0, 0, 255)},
    1: {'label': 'Disgust',  'emoji': '😒', 'color': (0, 150, 255)},
    2: {'label': 'Fearful',  'emoji': '😨', 'color': (0, 100, 255)},
    3: {'label': 'Happy',    'emoji': '😄', 'color': (0, 255, 0)},
    4: {'label': 'Neutral',  'emoji': '😐', 'color': (200, 200, 200)},
    5: {'label': 'Sad',      'emoji': '😢', 'color': (255, 0, 0)},
    6: {'label': 'Surprised','emoji': '😲', 'color': (0, 255, 255)},
}

SMOOTH_FRAMES = 5
FONT = cv.FONT_HERSHEY_DUPLEX
FER_INTERVAL = 3  # ponytail: run FER every N frames; face detection runs every frame


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def get_emoji_font(size):
    candidates = [
        resource_path('assets/NotoEmoji-Regular.ttf'),
        '/usr/share/fonts/google-noto-emoji-fonts/NotoEmoji-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        'C:\\Windows\\Fonts\\seguiemj.ttf',
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_emoji_bgr(frame, emoji, position, size):
    """Draw emoji onto a BGR frame using Pilmoji, returns modified frame."""
    img = Image.fromarray(cv.cvtColor(frame, cv.COLOR_BGR2RGB))
    font = get_emoji_font(size)
    with Pilmoji(img) as pilmoji:
        pilmoji.text(position, emoji, font=font, fill=(255, 255, 255))
    return cv.cvtColor(np.array(img), cv.COLOR_RGB2BGR)


def load_models():
    detect_model = YuNet(
        modelPath=MODEL_FACE,
        inputSize=[320, 320],
        confThreshold=0.6,
        nmsThreshold=0.3,
        topK=5000,
        backendId=cv.dnn.DNN_BACKEND_OPENCV,
        targetId=cv.dnn.DNN_TARGET_CPU,
    )
    fer_model = FacialExpressionRecog(
        modelPath=MODEL_FER,
        backendId=cv.dnn.DNN_BACKEND_OPENCV,
        targetId=cv.dnn.DNN_TARGET_CPU,
    )
    return detect_model, fer_model


def detect_faces(detect_model, frame):
    h, w = frame.shape[:2]
    detect_model.setInputSize([w, h])
    dets = detect_model.infer(frame)
    if dets is None or len(dets) == 0:
        return []

    faces = []
    for face_points in dets:
        bbox = face_points[:4].astype(np.int32)
        landmarks = face_points[4:14].astype(np.int32).reshape((5, 2))
        faces.append((bbox, landmarks, face_points[:-1]))
    return faces


def smooth_expression(idx, history):
    history.append(idx)
    if len(history) > SMOOTH_FRAMES:
        history.pop(0)
    counter = collections.Counter(history)
    return counter.most_common(1)[0][0], history


def draw_pill(img, x1, y1, x2, y2, color, alpha=0.8):
    overlay = img.copy()
    cv.rectangle(overlay, (x1, y1), (x2, y2), color, -1, cv.LINE_AA)
    cv.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)


def visualize(frame, faces, history):
    output = frame.copy()

    if not faces:
        return output, history

    for (x, y, bw, bh), landmarks, fer_idx in faces:
        smooth_idx, history = smooth_expression(fer_idx, history)
        info = EXPRESSIONS.get(smooth_idx, EXPRESSIONS[4])
        color = info['color']

        # Thin rounded-ish rectangle
        pad = 6
        cv.rectangle(output, (x - pad, y - pad), (x + bw + pad, y + bh + pad), color, 3, cv.LINE_AA)

        # Small landmark dots
        for lx, ly in landmarks:
            cv.circle(output, (lx, ly), 4, (255, 255, 255), -1, cv.LINE_AA)
            cv.circle(output, (lx, ly), 2, color, -1, cv.LINE_AA)

        # Label without emoji for pill size calculation
        label_text = info['label']
        (tw, th), _ = cv.getTextSize(label_text, FONT, 0.75, 2)

        pill_h = th + 22
        pill_w = tw + 80  # extra space for emoji
        px1 = x + (bw - pill_w) // 2
        py1 = y + bh + 16
        px2 = px1 + pill_w
        py2 = py1 + pill_h

        draw_pill(output, px1, py1, px2, py2, color)

        # Draw label text
        text_y = py1 + pill_h - 14
        cv.putText(output, label_text, (px1 + 60, text_y), FONT, 0.75, (255, 255, 255), 2, cv.LINE_AA)

        # Draw emoji on the left of pill, vertically centered inside pill
        emoji_size = 28
        emoji_x = px1 + 12
        emoji_y = py1 + (pill_h - emoji_size) // 2 - 8
        output = draw_emoji_bgr(output, info['emoji'], (emoji_x, emoji_y), size=emoji_size)

    return output, history


def main():
    detect_model, fer_model = load_models()

    cap = cv.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    cap.set(cv.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 480)

    window_name = "SMILE Kiosk"
    cv.namedWindow(window_name, cv.WND_PROP_FULLSCREEN)
    cv.setWindowProperty(window_name, cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)

    history = []
    last_fer = {}  # face index -> expression
    frame_counter = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("No frame")
            break

        frame = cv.flip(frame, 1)
        faces = detect_faces(detect_model, frame)

        if frame_counter % FER_INTERVAL == 0:
            current_fer = {}
            for i, (bbox, landmarks, face_points) in enumerate(faces):
                fer_idx = int(fer_model.infer(frame, face_points).item())
                current_fer[i] = fer_idx
            last_fer = current_fer

        # Merge detection with last known expressions
        merged_faces = []
        for i, (bbox, landmarks, _) in enumerate(faces):
            fer_idx = last_fer.get(i, 4)
            merged_faces.append((bbox, landmarks, fer_idx))

        vis, history = visualize(frame, merged_faces, history)

        cv.imshow(window_name, vis)
        frame_counter += 1

        key = cv.waitKey(1) & 0xFF
        if key in (27, ord('q'), ord('Q')):
            break

    cap.release()
    cv.destroyAllWindows()


if __name__ == '__main__':
    main()
