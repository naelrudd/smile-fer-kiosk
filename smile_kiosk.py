#!/usr/bin/env python3
"""
SMILE Kiosk - Minimal modern UI for photo booth / wahana
Run: python3 smile_kiosk.py
"""
import contextlib
import os
import sys
import threading
import time

import cv2 as cv
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from facial_fer_model import FacialExpressionRecog
from yunet import YuNet


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# --- Configuration ---
MODEL_FACE = resource_path('models/face_detection_yunet_2023mar.onnx')
MODEL_FER = resource_path(
    'models/facial_expression_recognition_mobilefacenet_2022july.onnx')

EXPRESSIONS = {
    0: {'label': 'Angry',    'emoji': '😠', 'color': (0, 0, 255)},
    1: {'label': 'Disgust',  'emoji': '😒', 'color': (0, 150, 255)},
    2: {'label': 'Fearful',  'emoji': '😨', 'color': (0, 100, 255)},
    3: {'label': 'Happy',    'emoji': '😄', 'color': (0, 255, 0)},
    4: {'label': 'Neutral',  'emoji': '😐', 'color': (200, 200, 200)},
    5: {'label': 'Sad',      'emoji': '😢', 'color': (255, 0, 0)},
    6: {'label': 'Surprised','emoji': '😲', 'color': (0, 255, 255)},
}

FONT = cv.FONT_HERSHEY_DUPLEX
EMOJI_SIZE = 28
HAPPY_IDX = 3

# Performance tuning
DETECT_SCALE = 0.5       # run detector on a downscaled frame (~4x faster)
EMA_DECAY = 0.6          # temporal smoothing on class probabilities (higher = smoother)
IOU_MATCH_THRESH = 0.3   # min IoU to keep a face's identity across frames
TRACK_MAX_AGE = 15       # frames a lost track is kept before smoothing resets
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# Gamification
LOGO_HEIGHT = 60
LOGO_MARGIN = 16
COMBO_STEP_S = 0.4       # seconds of sustained Happy per combo point
COMBO_DECAY_RATE = 2.0   # score-seconds lost per second when not happy
COMBO_MAX_DT = 0.2       # cap per-result time step to avoid jumps
FACE_LOST_TIMEOUT_S = 1.0
MILESTONE_STEP = 5
CONFETTI_COUNT = 80
CONFETTI_LIFETIME_S = 1.5
CONFETTI_GRAVITY = 900.0
COMBO_BADGE_MIN = 2      # only show the badge from this combo upward


# --- Emoji rendering (offline, from the bundled Noto Emoji font) ---
_EMOJI_FONT_CACHE = {}

_EMOJI_FONT_CANDIDATES = [
    resource_path('assets/NotoEmoji-Regular.ttf'),
    '/usr/share/fonts/google-noto-emoji-fonts/NotoEmoji-Regular.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    'C:\\Windows\\Fonts\\seguiemj.ttf',
]


def _try_load_font(path, size):
    if not os.path.exists(path):
        return None
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return None


def get_emoji_font(size):
    if size in _EMOJI_FONT_CACHE:
        return _EMOJI_FONT_CACHE[size]

    font = ImageFont.load_default()
    for path in _EMOJI_FONT_CANDIDATES:
        loaded = _try_load_font(path, size)
        if loaded is not None:
            font = loaded
            break
    _EMOJI_FONT_CACHE[size] = font
    return font


def render_emoji_rgba(char, size):
    """Pre-render an emoji glyph to an RGBA array once, for fast per-frame blitting."""
    font = get_emoji_font(size)
    try:
        left, top, right, bottom = font.getbbox(char)
    except (OSError, ValueError):
        left, top, right, bottom = (0, 0, size, size)

    w = max(1, right - left)
    h = max(1, bottom - top)
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).text((-left, -top), char, font=font, fill=255)
    alpha = np.asarray(mask, dtype=np.uint8)

    rgba = np.empty((h, w, 4), dtype=np.uint8)
    rgba[..., 0:3] = 255
    rgba[..., 3] = alpha
    return rgba


def prepare_sprite(rgba):
    """Convert an RGBA sprite to premultiplied (BGR*alpha, 1-alpha) float arrays."""
    alpha = rgba[..., 3:4].astype(np.float32) / 255.0
    bgr = rgba[..., 2::-1].astype(np.float32)
    return bgr * alpha, 1.0 - alpha


def blend_sprite(frame, sprite, x, y):
    """Alpha-blend a prepared sprite onto a BGR frame at (x, y), clipped."""
    premul, inv_alpha = sprite
    fh, fw = frame.shape[:2]
    sh, sw = inv_alpha.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(fw, x + sw), min(fh, y + sh)
    if x0 >= x1 or y0 >= y1:
        return

    roi = frame[y0:y1, x0:x1]
    roi[:] = (roi * inv_alpha[y0 - y:y1 - y, x0 - x:x1 - x]
              + premul[y0 - y:y1 - y, x0 - x:x1 - x])


def load_logo(height=LOGO_HEIGHT):
    """Load the bundled innovation logo as a scaled RGBA sprite, or None."""
    path = resource_path('assets/logo-inovasi.png')
    if not os.path.exists(path):
        return None
    try:
        with Image.open(path).convert('RGBA') as img:
            bbox = img.getchannel('A').getbbox()
            if bbox is not None:
                img = img.crop(bbox)
            width = max(1, round(img.width * height / img.height))
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            return np.asarray(img, dtype=np.uint8)
    except OSError:
        return None


def _star_mask(size, points=5, inner_ratio=0.45):
    cx = cy = size / 2.0
    outer_r = size / 2.0
    inner_r = outer_r * inner_ratio
    pts = []
    for i in range(points * 2):
        r = outer_r if i % 2 == 0 else inner_r
        angle = -np.pi / 2 + i * np.pi / points
        pts.append((cx + r * np.cos(angle), cy + r * np.sin(angle)))
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    return np.asarray(mask, dtype=np.uint8)


def build_confetti_sprites(size=12):
    """Pre-render colored square/star confetti sprites (RGBA) once."""
    colors = [
        (0, 0, 255), (0, 255, 0), (255, 0, 0),
        (0, 255, 255), (255, 0, 255), (255, 255, 0),
    ]
    square = np.zeros((size, size, 4), dtype=np.uint8)
    square[..., 3] = 255
    star_alpha = _star_mask(size)

    sprites = []
    for color in colors:
        sq = square.copy()
        sq[..., 0], sq[..., 1], sq[..., 2] = color
        sprites.append(sq)

        st = np.zeros((size, size, 4), dtype=np.uint8)
        st[..., 0], st[..., 1], st[..., 2] = color
        st[..., 3] = star_alpha
        sprites.append(st)
    return sprites


def play_milestone_sound():
    """Play a short milestone chime. Windows-only; silent elsewhere."""
    if sys.platform != 'win32':
        return
    try:
        import winsound
        winsound.PlaySound(
            'SystemAsterisk', winsound.SND_ALIAS | winsound.SND_ASYNC)
    except (ImportError, RuntimeError):
        pass


# --- Gamification ---
class ComboTracker:
    """Per-face combo counter: grows while Happy, decays otherwise.

    Combo is time-based: each COMBO_STEP_S of sustained Happy adds one point,
    so a fast result rate does not inflate the score.
    """

    def __init__(self, step=COMBO_STEP_S, decay=COMBO_DECAY_RATE,
                 timeout=FACE_LOST_TIMEOUT_S):
        self._step = step
        self._decay = decay
        self._timeout = timeout
        self._score = {}
        self._combo = {}
        self._last_t = {}
        self._last_seen = {}

    def update(self, faces, now):
        """Advance combo for each face; return milestone (tid, combo, bbox)."""
        milestones = []
        seen = set()
        for bbox, _landmarks, idx, tid in faces:
            seen.add(tid)
            last = self._last_t.get(tid, now)
            dt = min(max(0.0, now - last), COMBO_MAX_DT)
            self._last_t[tid] = now

            score = self._score.get(tid, 0.0)
            if idx == HAPPY_IDX:
                score += dt
            else:
                score = max(0.0, score - dt * self._decay)
            self._score[tid] = score

            prev_combo = self._combo.get(tid, 0)
            combo = int(score / self._step)
            self._combo[tid] = combo
            self._last_seen[tid] = now

            if combo > prev_combo:
                highest = (combo // MILESTONE_STEP) * MILESTONE_STEP
                if highest > (prev_combo // MILESTONE_STEP) * MILESTONE_STEP:
                    milestones.append((tid, highest, bbox))

        for tid in list(self._combo):
            if tid not in seen and now - self._last_seen.get(tid, now) > self._timeout:
                del self._combo[tid]
                del self._score[tid]
                del self._last_t[tid]
                del self._last_seen[tid]
        return milestones

    def get(self, tid):
        return self._combo.get(tid, 0)


class ConfettiField:
    """Pooled confetti particles with simple gravity, drawn as RGBA sprites."""

    def __init__(self, sprites):
        self._sprites = [prepare_sprite(s) for s in sprites]
        self._particles = []
        self._rng = np.random.default_rng()

    def burst(self, x, y, count=CONFETTI_COUNT):
        for _ in range(count):
            angle = self._rng.uniform(0.0, 2.0 * np.pi)
            speed = self._rng.uniform(120.0, 380.0)
            self._particles.append({
                'x': float(x),
                'y': float(y),
                'vx': float(np.cos(angle) * speed),
                'vy': float(np.sin(angle) * speed) - 120.0,
                'life': float(CONFETTI_LIFETIME_S * self._rng.uniform(0.7, 1.2)),
                'sprite': int(self._rng.integers(0, len(self._sprites))),
            })

    def update(self, dt):
        alive = []
        for p in self._particles:
            p['life'] -= dt
            if p['life'] <= 0.0:
                continue
            p['vy'] += CONFETTI_GRAVITY * dt
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            alive.append(p)
        self._particles = alive

    def draw(self, frame):
        for p in self._particles:
            blend_sprite(frame, self._sprites[p['sprite']], int(p['x']), int(p['y']))


class GameState:
    """Combo tracking plus milestone effects (confetti, flash, popup, sound)."""

    def __init__(self, confetti_sprites):
        self.combo = ComboTracker()
        self.confetti = ConfettiField(confetti_sprites)
        self.flash = 0.0
        self.flash_color = (0, 255, 0)
        self.popup = None

    def on_results(self, faces, now):
        for _tid, combo, bbox in self.combo.update(faces, now):
            x, y, w, h = bbox
            cx, cy = x + w // 2, y + h // 2
            self.confetti.burst(cx, cy)
            self.flash = 0.35
            self.flash_color = (0, 255, 255) if combo >= 10 else (0, 255, 0)
            self.popup = {
                'text': 'AWESOME!' if combo >= 10 else 'GREAT!',
                'x': cx,
                'y': y - 20,
                'life': 1.0,
            }
            play_milestone_sound()

    def update(self, dt):
        self.confetti.update(dt)
        if self.flash > 0.0:
            self.flash = max(0.0, self.flash - dt * 2.5)
        if self.popup is not None:
            self.popup['life'] -= dt
            self.popup['y'] -= dt * 30.0
            if self.popup['life'] <= 0.0:
                self.popup = None

    def draw(self, frame):
        self.confetti.draw(frame)
        if self.flash > 0.0:
            overlay = np.empty_like(frame)
            overlay[:] = self.flash_color
            cv.addWeighted(overlay, self.flash, frame, 1.0 - self.flash, 0, frame)
        if self.popup is not None:
            alpha = max(0.0, min(1.0, self.popup['life']))
            color = tuple(int(c * alpha) for c in self.flash_color)
            text = self.popup['text']
            (tw, _th), _ = cv.getTextSize(text, FONT, 1.2, 3)
            pos = (self.popup['x'] - tw // 2, int(self.popup['y']))
            cv.putText(frame, text, pos, FONT, 1.2, (0, 0, 0), 6, cv.LINE_AA)
            cv.putText(frame, text, pos, FONT, 1.2, color, 3, cv.LINE_AA)


# --- Face tracking (IoU) so identities stay stable across frames ---
def iou(a, b):
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


class IouTracker:
    def __init__(self, thresh=IOU_MATCH_THRESH, max_age=TRACK_MAX_AGE):
        self._thresh = thresh
        self._max_age = max_age
        self._tracks = {}
        self._next_id = 0

    def update(self, boxes):
        """Match current boxes to existing tracks, returning an id per box."""
        pairs = []
        for tid, (tb, _age) in self._tracks.items():
            for bi, box in enumerate(boxes):
                pairs.append((iou(tb, box), tid, bi))
        pairs.sort(reverse=True)

        assigned = {}
        used_tracks = set()
        used_boxes = set()
        for score, tid, bi in pairs:
            if score < self._thresh:
                break
            if tid in used_tracks or bi in used_boxes:
                continue
            used_tracks.add(tid)
            used_boxes.add(bi)
            assigned[bi] = tid

        ids = []
        new_tracks = {}
        for bi, box in enumerate(boxes):
            if bi in assigned:
                tid = assigned[bi]
            else:
                tid = self._next_id
                self._next_id += 1
            new_tracks[tid] = (box, 0)
            ids.append(tid)

        for tid, (tb, age) in self._tracks.items():
            if tid not in new_tracks and age + 1 < self._max_age:
                new_tracks[tid] = (tb, age + 1)

        self._tracks = new_tracks
        return ids


# --- Shared latest-value slot between threads ---
class SharedFrame:
    def __init__(self):
        self._lock = threading.Lock()
        self.frame = None
        self.ts = 0.0
        self.seq = 0
        self.extra = None

    def set(self, frame, ts, extra=None):
        with self._lock:
            self.frame = frame
            self.ts = ts
            self.seq += 1
            self.extra = extra

    def get(self):
        with self._lock:
            return self.frame, self.ts, self.seq, self.extra


# --- Models ---
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
    sw = max(1, int(w * DETECT_SCALE))
    sh = max(1, int(h * DETECT_SCALE))
    small = cv.resize(frame, (sw, sh), interpolation=cv.INTER_LINEAR)
    detect_model.setInputSize([sw, sh])
    dets = detect_model.infer(small)
    if dets is None or len(dets) == 0:
        return []

    inv = 1.0 / DETECT_SCALE
    faces = []
    for face_points in dets:
        scaled = face_points[:14].astype(np.float32) * inv
        bbox = scaled[:4].astype(np.int32)
        landmarks = scaled[4:14].astype(np.int32).reshape((5, 2))
        faces.append((bbox, landmarks, scaled))
    return faces


# --- Camera ---
def open_camera():
    if sys.platform == 'win32':
        backends = [cv.CAP_DSHOW, cv.CAP_ANY]
    else:
        backends = [cv.CAP_V4L2, cv.CAP_ANY]
    for backend in backends:
        cap = cv.VideoCapture(0, backend)
        if cap.isOpened():
            cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc(*'MJPG'))
            cap.set(cv.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            cap.set(cv.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            cap.set(cv.CAP_PROP_FPS, 30)
            with contextlib.suppress(cv.error):
                cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
            return cap
        cap.release()
    return None


def capture_worker(cap, slot, stop):
    while not stop.is_set():
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.01)
            continue
        frame = cv.flip(frame, 1)
        slot.set(frame, time.perf_counter())


def inference_worker(detect_model, fer_model, capture_slot, result_slot, stop):
    tracker = IouTracker()
    ema = {}
    last_seq = -1

    while not stop.is_set():
        frame, ts, seq, _ = capture_slot.get()
        if frame is None or seq == last_seq:
            time.sleep(0.002)
            continue
        last_seq = seq

        faces = detect_faces(detect_model, frame)
        ids = tracker.update([bbox for bbox, _landmarks, _pts in faces])

        active = set()
        results = []
        for (bbox, landmarks, face_points), tid in zip(faces, ids):
            active.add(tid)
            probs = fer_model.infer_probs(frame, face_points)
            prev = ema.get(tid)
            if prev is None:
                ema[tid] = probs
            else:
                ema[tid] = EMA_DECAY * prev + (1.0 - EMA_DECAY) * probs
            results.append((bbox, landmarks, int(np.argmax(ema[tid])), tid))

        for tid in list(ema):
            if tid not in active:
                del ema[tid]

        result_slot.set(frame, ts, results)


# --- Drawing ---
def draw_pill(img, x1, y1, x2, y2, color, alpha=0.8):
    h, w = img.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x1 >= x2 or y1 >= y2:
        return
    roi = img[y1:y2, x1:x2]
    overlay = np.empty_like(roi)
    overlay[:] = color
    cv.addWeighted(overlay, alpha, roi, 1 - alpha, 0, roi)


def combo_color(combo):
    if combo >= 10:
        return (0, 165, 255)   # orange
    if combo >= 5:
        return (0, 255, 255)   # yellow
    return (255, 255, 255)     # white


def draw_logo(frame, logo):
    if logo is None:
        return
    x = frame.shape[1] - logo[1].shape[1] - LOGO_MARGIN
    blend_sprite(frame, logo, x, LOGO_MARGIN)


def draw_combo_badge(frame, x, y, combo):
    text = f"x{combo}"
    (tw, th), _ = cv.getTextSize(text, FONT, 0.9, 2)
    bx1 = x
    by1 = y
    bx2 = bx1 + tw + 24
    by2 = by1 + th + 16
    draw_pill(frame, bx1, by1, bx2, by2, (20, 20, 20), alpha=0.7)
    cv.putText(frame, text, (bx1 + 12, by2 - 9), FONT, 0.9,
               (0, 0, 0), 4, cv.LINE_AA)
    cv.putText(frame, text, (bx1 + 12, by2 - 9), FONT, 0.9,
               combo_color(combo), 2, cv.LINE_AA)


def render(frame, faces, emoji_sprites, game):
    output = frame

    for (x, y, bw, bh), _landmarks, idx, tid in faces:
        info = EXPRESSIONS.get(idx, EXPRESSIONS[4])
        color = info['color']

        label_text = info['label']
        (tw, th), _ = cv.getTextSize(label_text, FONT, 0.75, 2)

        pill_h = th + 22
        pill_w = tw + 80
        px1 = x + (bw - pill_w) // 2
        py1 = y + bh + 16

        draw_pill(output, px1, py1, px1 + pill_w, py1 + pill_h, color)

        text_y = py1 + pill_h - 14
        cv.putText(output, label_text, (px1 + 60, text_y), FONT, 0.75,
                   (255, 255, 255), 2, cv.LINE_AA)

        sprite = emoji_sprites.get(idx)
        if sprite is None:
            sprite = emoji_sprites.get(4)
        if sprite is not None:
            emoji_x = px1 + 12
            emoji_y = py1 + (pill_h - sprite[1].shape[0]) // 2
            blend_sprite(output, sprite, emoji_x, emoji_y)

        combo = game.combo.get(tid)
        if combo >= COMBO_BADGE_MIN:
            draw_combo_badge(output, px1 + pill_w + 10, py1, combo)

    return output


def draw_hud(frame, fps, latency_ms):
    cv.putText(frame, f"{fps:4.1f} FPS  {latency_ms:4.0f} ms", (16, 34),
               FONT, 0.8, (0, 0, 0), 4, cv.LINE_AA)
    cv.putText(frame, f"{fps:4.1f} FPS  {latency_ms:4.0f} ms", (16, 34),
               FONT, 0.8, (0, 255, 0), 2, cv.LINE_AA)


def main():
    cv.setNumThreads(max(1, (os.cpu_count() or 4) // 2))

    detect_model, fer_model = load_models()

    cap = open_camera()
    if cap is None:
        print("Cannot open camera")
        return

    emoji_sprites = {idx: prepare_sprite(render_emoji_rgba(info['emoji'], EMOJI_SIZE))
                     for idx, info in EXPRESSIONS.items()}
    logo = load_logo()
    logo = prepare_sprite(logo) if logo is not None else None
    game = GameState(build_confetti_sprites())

    capture_slot = SharedFrame()
    result_slot = SharedFrame()
    stop = threading.Event()

    inference_args = (detect_model, fer_model, capture_slot, result_slot, stop)
    threads = [
        threading.Thread(target=capture_worker,
                         args=(cap, capture_slot, stop), daemon=True),
        threading.Thread(target=inference_worker,
                         args=inference_args, daemon=True),
    ]
    for t in threads:
        t.start()

    window_name = "SMILE Kiosk"
    cv.namedWindow(window_name, cv.WND_PROP_FULLSCREEN)
    cv.setWindowProperty(window_name, cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)

    frame_times = []
    show_hud = False
    last_seq = -1
    last_time = time.perf_counter()

    while True:
        key = cv.waitKey(1) & 0xFF
        if key in (27, ord('q'), ord('Q')):
            break
        if key in (ord('f'), ord('F')):
            show_hud = not show_hud

        frame, ts, seq, faces = result_slot.get()
        if frame is None or seq == last_seq:
            time.sleep(0.003)
            continue
        last_seq = seq

        now = time.perf_counter()
        dt = min(now - last_time, 0.1)
        last_time = now

        game.on_results(faces or [], now)
        game.update(dt)

        vis = render(frame, faces or [], emoji_sprites, game)
        game.draw(vis)
        draw_logo(vis, logo)

        frame_times.append(now)
        if len(frame_times) > 30:
            frame_times.pop(0)
        if show_hud:
            fps = 0.0
            if len(frame_times) > 1:
                span = frame_times[-1] - frame_times[0]
                if span > 0:
                    fps = (len(frame_times) - 1) / span
            draw_hud(vis, fps, (now - ts) * 1000.0)

        cv.imshow(window_name, vis)

    stop.set()
    for t in threads:
        t.join(timeout=1.0)
    cap.release()
    cv.destroyAllWindows()


if __name__ == '__main__':
    main()
