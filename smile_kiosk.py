#!/usr/bin/env python3
"""
SMILE Kiosk - Fullscreen facial expression recognition for Ubuntu Desktop
Run: python3 smile_kiosk.py
"""
import os
import sys
import time
import numpy as np
import cv2 as cv

from yunet import YuNet
from facial_fer_model import FacialExpressionRecog

# --- Configuration ---
FONT = cv.FONT_HERSHEY_DUPLEX
MODEL_FACE = 'models/face_detection_yunet_2023mar.onnx'
MODEL_FER = 'models/facial_expression_recognition_mobilefacenet_2022july.onnx'

# Expression -> (label, color BGR, emoji)
EXPRESSIONS = {
    0: ('Angry',    (0, 0, 255),     '😠'),
    1: ('Disgust',  (0, 100, 255),   '🤢'),
    2: ('Fearful',  (0, 100, 255),   '😨'),
    3: ('Happy',    (0, 255, 0),     '😄'),
    4: ('Neutral',  (255, 255, 255), '😐'),
    5: ('Sad',      (255, 0, 0),     '😢'),
    6: ('Surprised', (0, 255, 255),  '😲'),
}


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


def process_frame(detect_model, fer_model, frame):
    h, w = frame.shape[:2]
    detect_model.setInputSize([w, h])
    dets = detect_model.infer(frame)
    if dets is None or len(dets) == 0:
        return []

    faces = []
    for face_points in dets:
        bbox = face_points[:4].astype(np.int32)
        landmarks = face_points[4:14].astype(np.int32).reshape((5, 2))
        fer_idx = int(fer_model.infer(frame, face_points[:-1]).item())
        faces.append((bbox, landmarks, fer_idx))
    return faces


def visualize(frame, faces, fps):
    output = frame.copy()
    h, w = output.shape[:2]

    # Dark overlay edges
    overlay = output.copy()
    cv.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
    cv.addWeighted(overlay, 0.15, output, 0.85, 0, output)

    for (x, y, bw, bh), landmarks, fer_idx in faces:
        label, color, emoji = EXPRESSIONS.get(fer_idx, ('Unknown', (128, 128, 128), '❓'))

        # Bounding box with glow effect
        cv.rectangle(output, (x-3, y-3), (x+bw+3, y+bh+3), color, 2)
        cv.rectangle(output, (x, y), (x+bw, y+bh), color, 2)

        # Landmarks
        for lx, ly in landmarks:
            cv.circle(output, (lx, ly), 4, (255, 255, 255), -1)
            cv.circle(output, (lx, ly), 3, color, -1)

        # Label with background
        text = f"{emoji} {label}"
        (tw, th), _ = cv.getTextSize(text, FONT, 0.9, 2)
        pad = 8
        cv.rectangle(output, (x, y - th - pad*2), (x + tw + pad*2, y), color, -1)
        cv.putText(output, text, (x + pad, y - pad), FONT, 0.9, (0, 0, 0), 2)

    # Header overlay
    header = f"SMILE KIOSK | FPS: {fps:.1f}"
    if not faces:
        header += " | Show your face!"
    else:
        header += f" | {len(faces)} face(s)"

    cv.rectangle(output, (0, 0), (w, 55), (0, 0, 0), -1)
    cv.rectangle(output, (0, 0), (w, 55), (0, 255, 0), 2)
    cv.putText(output, header, (20, 38), FONT, 1.0, (0, 255, 0), 2)

    return output


def main():
    detect_model, fer_model = load_models()

    cap = cv.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    cap.set(cv.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 720)

    width = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera: {width}x{height}")

    window_name = "SMILE Kiosk"
    cv.namedWindow(window_name, cv.WND_PROP_FULLSCREEN)
    cv.setWindowProperty(window_name, cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)

    prev = time.time()
    fps = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("No frame")
            break

        # Mirror left-right like a selfie
        frame = cv.flip(frame, 1)

        faces = process_frame(detect_model, fer_model, frame)

        now = time.time()
        try:
            fps = 1.0 / (now - prev)
        except ZeroDivisionError:
            fps = 0.0
        prev = now

        vis = visualize(frame, faces, fps)
        cv.imshow(window_name, vis)

        key = cv.waitKey(1) & 0xFF
        if key in (27, ord('q'), ord('Q')):
            break

    cap.release()
    cv.destroyAllWindows()


if __name__ == '__main__':
    main()
