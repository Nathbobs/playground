import asyncio
import time
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from .tracker import Tracker
from .scorer import compute_score

VEHICLE_CLASSES = [2, 3, 5, 7]  # car, motorcycle, bus, truck (COCO indices)
CONF_THRESHOLD = 0.4

# Resolved relative to this file so the path is correct regardless of cwd
_MODELS_DIR = Path(__file__).parent / "models"
MODEL_PATH = _MODELS_DIR / "yolov8n.pt"


def _load_model(model_path: Path) -> YOLO:
    # ultralytics downloads "yolov8n.pt" by name, then we move it into place
    if not model_path.exists():
        model_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = YOLO("yolov8n.pt")          # downloads to cwd / ultralytics cache
        src = Path(tmp.ckpt_path).resolve()
        if src != model_path.resolve():
            src.rename(model_path)
        return tmp
    return YOLO(str(model_path))


class PipelineState:
    def __init__(self):
        self.running = False
        self.total_vehicles = 0
        self.stationary = 0
        self.moving = 0
        self.congestion_score = 0.0
        self.status = "FREE"
        self.fps = 0.0
        self.latest_frame: bytes | None = None


state = PipelineState()


async def run_pipeline(video_path: str, model_path: Path = MODEL_PATH) -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"

    model = await asyncio.to_thread(_load_model, model_path)
    model.to(device)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    tracker = Tracker()
    frame_idx = 0
    last_detections: list[list[float]] = []
    fps_counter = 0
    fps_ts = time.monotonic()

    state.running = True

    try:
        while state.running:
            ok, frame = await asyncio.to_thread(cap.read)
            if not ok:
                # Loop the video rather than stopping
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = await asyncio.to_thread(cap.read)
                if not ok:
                    break

            frame_idx += 1
            fps_counter += 1

            # Inference every other frame — halves GPU load without much accuracy loss
            if frame_idx % 2 == 0:
                results = await asyncio.to_thread(
                    model, frame,
                    conf=CONF_THRESHOLD,
                    classes=VEHICLE_CLASSES,
                    verbose=False,
                )
                boxes = results[0].boxes
                last_detections = [
                    b.xyxy[0].tolist()
                    for b in boxes
                    if int(b.cls[0]) in set(VEHICLE_CLASSES)
                ] if boxes is not None else []

            active = tracker.update(last_detections)

            total = len(active)
            stationary = sum(1 for t in active if t.stationary)
            score, status = compute_score(total, stationary)

            now = time.monotonic()
            if now - fps_ts >= 1.0:
                state.fps = fps_counter / (now - fps_ts)
                fps_counter = 0
                fps_ts = now

            state.total_vehicles = total
            state.stationary = stationary
            state.moving = total - stationary
            state.congestion_score = score
            state.status = status

            annotated = _draw_tracks(frame, active)
            state.latest_frame = await asyncio.to_thread(
                lambda f: cv2.imencode(".jpg", f)[1].tobytes(), annotated
            )

            await asyncio.sleep(0)  # yield so FastAPI can serve requests between frames
    finally:
        cap.release()
        state.running = False


def _draw_tracks(frame: np.ndarray, tracks) -> np.ndarray:
    out = frame.copy()
    for t in tracks:
        x1, y1, x2, y2 = (int(v) for v in t.bbox)
        color = (0, 0, 220) if t.stationary else (0, 200, 0)
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        cv2.putText(out, f"ID:{t.id}", (x1, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
    return out
