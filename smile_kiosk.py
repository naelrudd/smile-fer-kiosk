#!/usr/bin/env python3
"""
SMILE Kiosk - Minimal modern UI for photo booth / wahana
Optimized for low-latency on modest hardware.
Run: python3 smile_kiosk.py
"""
import os
import sys
import collections
import logging
import traceback
import numpy as np
import cv2 as cv

from yunet import YuNet
from facial_fer_model import FacialExpressionRecog

# --- Logging ---
LOG_DIR = os.path.join(os.path.expanduser('~'), 'smile_kiosk')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'smile_kiosk.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)

# --- Configuration ---
MODEL_FACE = 'models/face_detection_yunet_2023mar.onnx'
MODEL_FER = 'models/facial_expression_recognition_mobilefacenet_2022july.onnx'

EXPRESSIONS = {
    0: {'label': 'Angry',    'color': (0, 0, 255)},
    1: {'label': 'Disgust',  'color': (0, 150, 255)},
    2: {'label': 'Fearful',  'color': (0, 100, 255)},
    3: {'label': 'Happy',    'color': (0, 255, 0)},
    4: {'label': 'Neutral',  'color': (200, 200, 200)},
    5: {'label': 'Sad',      'color': (255, 0, 0)},
    6: {'label': 'Surprised','color': (0, 255, 255)},
}

SMOOTH_FRAMES = 5
FONT = cv.FONT_HERSHEY_DUPLEX
FER_INTERVAL = 5
FACE_INPUT_SIZE = (320, 240)
BRIGHTNESS_FACTOR = 0.7  # ponytail: fixed value, add slider if user wants manual control


def apply_brightness_filter(frame, brightness_factor=BRIGHTNESS_FACTOR, contrast=1.0):
    """Reduce brightness and optionally adjust contrast."""
    frame = frame.astype(np.float32) * contrast
    frame = frame - 127.0 * (contrast - 1.0)
    frame = frame * brightness_factor
    return np.clip(frame, 0, 255).astype(np.uint8)


def load_models():
    logging.info('Loading models...')
    try:
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
        logging.info('Models loaded successfully.')
        return detect_model, fer_model
    except Exception as e:
        logging.error('Failed to load models: %s', e)
        logging.error(traceback.format_exc())
        raise


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

        pad = 6
        cv.rectangle(output, (x - pad, y - pad), (x + bw + pad, y + bh + pad), color, 3, cv.LINE_AA)

        for lx, ly in landmarks:
            cv.circle(output, (lx, ly), 4, (255, 255, 255), -1, cv.LINE_AA)
            cv.circle(output, (lx, ly), 2, color, -1, cv.LINE_AA)

        label_text = info['label']
        (tw, th), _ = cv.getTextSize(label_text, FONT, 0.75, 2)

        pill_h = th + 18
        pill_w = tw + 24
        px1 = x + (bw - pill_w) // 2
        py1 = y + bh + 12
        px2 = px1 + pill_w
        py2 = py1 + pill_h

        draw_pill(output, px1, py1, px2, py2, color)

        text_x = px1 + (pill_w - tw) // 2
        text_y = py1 + pill_h - 10
        cv.putText(output, label_text, (text_x, text_y), FONT, 0.75, (255, 255, 255), 2, cv.LINE_AA)

    return output, history


def open_camera(max_index=5):
    """Try camera indices 0..max_index, return first working capture."""
    logging.info('Searching for camera...')
    for idx in range(max_index):
        cap = cv.VideoCapture(idx)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                logging.info('Camera index %d opened successfully.', idx)
                return cap
            else:
                logging.warning('Camera index %d opened but cannot read frame.', idx)
        cap.release()
    logging.error('No working camera found on indices 0..%d.', max_index)
    return None


def main():
    logging.info('=== SMILE Kiosk started ===')
    try:
        detect_model, fer_model = load_models()
    except Exception:
        logging.error('Exiting due to model load failure.')
        input('Press Enter to exit...')
        return

    cap = open_camera()
    if cap is None:
        print('ERROR: No camera detected. Check device and permissions.')
        print(f'Log file: {LOG_FILE}')
        input('Press Enter to exit...')
        return

    # Lower default resolution for performance
    cap.set(cv.CAP_PROP_FRAME_WIDTH, 480)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 360)

    window_name = "SMILE Kiosk"
    cv.namedWindow(window_name, cv.WND_PROP_FULLSCREEN)
    cv.setWindowProperty(window_name, cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)

    history = []
    last_fer = {}
    frame_counter = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logging.error('Failed to read frame from camera.')
                break

            frame = cv.flip(frame, 1)
            frame = apply_brightness_filter(frame)

            # Resize for faster face detection, then scale coords back
            orig_h, orig_w = frame.shape[:2]
            small_frame = cv.resize(frame, FACE_INPUT_SIZE)
            scale_x = orig_w / FACE_INPUT_SIZE[0]
            scale_y = orig_h / FACE_INPUT_SIZE[1]

            try:
                small_faces = detect_faces(detect_model, small_frame)
            except Exception as e:
                logging.error('Face detection error: %s', e)
                logging.error(traceback.format_exc())
                small_faces = []

            # Scale bounding boxes and landmarks back to original frame size
            scaled_faces = []
            for (x, y, bw, bh), landmarks, face_points in small_faces:
                x, y, bw, bh = int(x * scale_x), int(y * scale_y), int(bw * scale_x), int(bh * scale_y)
                scaled_landmarks = [(int(lx * scale_x), int(ly * scale_y)) for lx, ly in landmarks]
                scaled_faces.append(((x, y, bw, bh), scaled_landmarks, face_points))

            if frame_counter % FER_INTERVAL == 0:
                current_fer = {}
                for i, (bbox, landmarks, face_points) in enumerate(scaled_faces):
                    try:
                        fer_idx = int(fer_model.infer(frame, face_points).item())
                        current_fer[i] = fer_idx
                    except Exception as e:
                        logging.error('FER inference error for face %d: %s', i, e)
                        current_fer[i] = 4
                last_fer = current_fer

            merged_faces = []
            for i, (bbox, landmarks, _) in enumerate(scaled_faces):
                fer_idx = last_fer.get(i, 4)
                merged_faces.append((bbox, landmarks, fer_idx))

            vis, history = visualize(frame, merged_faces, history)

            cv.imshow(window_name, vis)
            frame_counter += 1

            key = cv.waitKey(1) & 0xFF
            if key in (27, ord('q'), ord('Q')):
                logging.info('Exit requested by user.')
                break
    except Exception as e:
        logging.error('Runtime error: %s', e)
        logging.error(traceback.format_exc())
    finally:
        cap.release()
        cv.destroyAllWindows()
        logging.info('=== SMILE Kiosk stopped ===')


if __name__ == '__main__':
    main()
