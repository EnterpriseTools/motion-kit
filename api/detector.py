# api/detector.py
import os
import logging
from typing import Dict, Any, Optional, Sequence

import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv

from adaptive_sampling import create_adaptive_sampler, integrate_with_detection_pipeline

logger = logging.getLogger(__name__)

# COCO class ID to object type mapping
COCO_CLASS_MAPPING = {
    0: "person",
    2: "car", 
    3: "motorcycle",
    5: "bus",
    7: "truck"
}

def get_object_type(class_id: int) -> str:
    """Get object type from COCO class ID"""
    return COCO_CLASS_MAPPING.get(class_id, "unknown")

def is_vehicle(class_id: int) -> bool:
    """Check if class ID represents a vehicle"""
    return class_id in (2, 3, 5, 7)  # car, motorcycle, bus, truck

# Cache the models across requests
_MODEL: Optional[YOLO] = None


def _get_model() -> YOLO:
    """
    Lazy-load YOLOv8 model. Uses YOLO_WEIGHTS env var if set, else yolov8n.pt.
    Optionally honor YOLO_DEVICE (e.g., 'cpu', 'mps', 'cuda').
    """
    global _MODEL
    if _MODEL is None:
        weights = os.getenv("YOLO_WEIGHTS", "yolov8n.pt")  # nano for speed
        _MODEL = YOLO(weights)  # downloads weights on first run

        device = os.getenv("YOLO_DEVICE")
        if device:
            try:
                _MODEL.to(device)
            except Exception:
                # If device move fails, keep default device
                pass
    return _MODEL


def _video_meta(cap: cv2.VideoCapture) -> Dict[str, Any]:
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    frames_est = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    return {"width": w, "height": h, "fps_in": fps, "frames_est": frames_est}


def run_detection(
    video_path: str,
    conf: float = 0.25,
    sample_stride: int = 1,
    classes: Sequence[int] = (0, 2, 3, 5, 7),  # person, car, motorcycle, bus, truck
    max_frames: Optional[int] = None,
    enable_adaptive_sampling: bool = True,
    adaptive_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process video with adaptive frame sampling and return compact results for the player.

    Args:
        video_path: Path to input video file
        conf: YOLOv8 confidence threshold
        sample_stride: Fixed stride (used when adaptive sampling disabled)
        classes: Object classes to detect (0=person, 2=car, 3=motorcycle, 5=bus, 7=truck)
        max_frames: Maximum frames to process
        enable_adaptive_sampling: Whether to use adaptive frame sampling
        adaptive_config: Configuration overrides for adaptive sampler

    Returns:
      {
        "meta": {"fps": <processed_fps>, "width": W, "height": H, "frames": N, "duration_s": ..., "adaptive_metrics": {...}},
        "tracks": [{"frame":i, "id":tid, "x":..., "y":..., "w":..., "h":..., "score":...}, ...]
      }

    Notes:
      - Frame indices are sequential for processed frames: 0..N-1
      - x,y,w,h are normalized to original video size; x,y are *top-left*
      - When adaptive sampling is enabled, sample_stride is used as fallback only
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    meta_in = _video_meta(cap)
    W, H, fps_in = meta_in["width"], meta_in["height"], meta_in["fps_in"]
    fps_in = fps_in if fps_in and fps_in > 0 else 30.0
    fps_out = fps_in / max(1, sample_stride)

    model = _get_model()
    tracker = sv.ByteTrack()

    processed = 0
    tracks = []

    raw_idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        if raw_idx % sample_stride != 0:
            raw_idx += 1
            continue

        # Inference (Ultralytics handles NMS internally)
        # Detect people and vehicles
        results = model(frame, conf=conf, classes=list(classes), verbose=False)
        dets = sv.Detections.from_ultralytics(results[0])

        # Track across frames
        tracked = tracker.update_with_detections(dets)

        # Collect normalized boxes (xyxy -> (x,y,w,h) top-left)
        for i, (x1, y1, x2, y2) in enumerate(tracked.xyxy):
            tid = tracked.tracker_id[i]
            if tid is None:
                continue

            # Get object class information
            class_id = int(tracked.class_id[i]) if hasattr(tracked, 'class_id') and tracked.class_id is not None else 0
            object_type = get_object_type(class_id)
            confidence = float(tracked.confidence[i]) if hasattr(tracked, 'confidence') and tracked.confidence is not None else 0.0

            # clip to frame
            x1 = float(max(0.0, min(x1, W)))
            y1 = float(max(0.0, min(y1, H)))
            x2 = float(max(0.0, min(x2, W)))
            y2 = float(max(0.0, min(y2, H)))
            w = max(0.0, x2 - x1)
            h = max(0.0, y2 - y1)

            # normalize
            track_obj = {
                "frame": processed,
                "id": int(tid),
                "x": x1 / W,
                "y": y1 / H,
                "w": w / W,
                "h": h / H,
                "score": confidence,
                "class_id": class_id,
                "object_type": object_type,
                "is_vehicle": is_vehicle(class_id),
            }
            tracks.append(track_obj)

        processed += 1
        raw_idx += 1
        if max_frames and processed >= max_frames:
            break

    cap.release()

    duration_s = round(processed / fps_out, 3) if fps_out > 0 else round(processed / 30.0, 3)
    meta = {
        "fps": round(fps_out, 2),
        "width": W,
        "height": H,
        "frames": processed,
        "duration_s": duration_s,
    }
    return {"meta": meta, "tracks": tracks}
