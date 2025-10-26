# api/detector_adaptive.py
import os
import logging
from typing import Dict, Any, Optional, Sequence

import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv

from adaptive_sampling import create_adaptive_sampler, integrate_with_detection_pipeline

logger = logging.getLogger(__name__)

# Cache the model across requests
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
    classes: Sequence[int] = (0,),  # 0 = person
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
        classes: Object classes to detect (0 = person)
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

    model = _get_model()
    tracker = sv.ByteTrack()

    # Initialize adaptive sampler if enabled
    adaptive_sampler = None
    if enable_adaptive_sampling:
        config_overrides = adaptive_config or {}
        adaptive_sampler = create_adaptive_sampler(
            video_fps=fps_in,
            **config_overrides
        )
        logger.info(f"Adaptive sampling enabled for video: {fps_in:.1f} FPS")
    else:
        logger.info(f"Fixed sampling enabled with stride: {sample_stride}")

    processed = 0
    tracks = []
    prev_detections = []
    raw_idx = 0
    
    # Track processing statistics
    frames_read = 0
    frames_skipped = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        
        frames_read += 1

        # Determine if we should process this frame
        should_process = False
        sampling_reason = "fixed_stride"
        
        if enable_adaptive_sampling and adaptive_sampler:
            # Use adaptive sampling
            should_process, sampling_reason, telemetry = integrate_with_detection_pipeline(
                adaptive_sampler,
                raw_idx,
                frame,
                prev_detections=prev_detections,
                lock_on_active=False,  # Could be enhanced with lock-on detection
                seek_event=False
            )
        else:
            # Use fixed stride sampling
            should_process = (raw_idx % sample_stride == 0)
            sampling_reason = f"fixed_stride_{sample_stride}"

        if not should_process:
            frames_skipped += 1
            raw_idx += 1
            continue

        # Run inference (Ultralytics handles NMS internally)
        try:
            results = model(frame, conf=conf, classes=list(classes), verbose=False)
            dets = sv.Detections.from_ultralytics(results[0])
        except Exception as e:
            logger.error(f"Detection failed on frame {raw_idx}: {e}")
            raw_idx += 1
            continue

        # Track across frames
        tracked = tracker.update_with_detections(dets)

        # Prepare detection data for next iteration
        current_detections = []
        
        # Collect normalized boxes (xyxy -> (x,y,w,h) top-left)
        for i, (x1, y1, x2, y2) in enumerate(tracked.xyxy):
            tid = tracked.tracker_id[i]
            if tid is None:
                continue

            # Clip to frame bounds
            x1 = float(max(0.0, min(x1, W)))
            y1 = float(max(0.0, min(y1, H)))
            x2 = float(max(0.0, min(x2, W)))
            y2 = float(max(0.0, min(y2, H)))
            w = max(0.0, x2 - x1)
            h = max(0.0, y2 - y1)

            # Skip invalid boxes
            if w <= 0 or h <= 0:
                continue

            # Normalize coordinates
            track_obj = {
                "frame": raw_idx,  # Use original video frame index, not processed frame index
                "id": int(tid),
                "x": x1 / W,
                "y": y1 / H,
                "w": w / W,
                "h": h / H,
                "score": float(tracked.confidence[i]) if getattr(tracked, "confidence", None) is not None else 0.0,
            }
            tracks.append(track_obj)
            
            # Store for adaptive sampling
            current_detections.append({
                "id": int(tid),
                "score": track_obj["score"],
                "box_area": track_obj["w"] * track_obj["h"]
            })

        # Update detection history for adaptive sampling
        prev_detections = current_detections

        processed += 1
        raw_idx += 1
        
        # Check exit conditions
        if max_frames and processed >= max_frames:
            logger.info(f"Reached max_frames limit: {max_frames}")
            break

    cap.release()

    # Calculate duration based on original video timeline
    # Since we're now using original frame indices, we need to use original FPS
    video_duration_s = frames_read / fps_in if fps_in > 0 else frames_read / 30.0

    # Prepare metadata
    meta = {
        "fps": round(fps_in, 2),  # Use original video FPS for frontend timing
        "width": W,
        "height": H,
        "frames": frames_read,    # Total frames in original video
        "duration_s": round(video_duration_s, 3),
        "total_frames_read": frames_read,
        "frames_skipped": frames_skipped,
        "frames_processed": processed,  # Add processed count separately
        "processing_efficiency": round((processed / frames_read) * 100, 1) if frames_read > 0 else 0.0,
    }

    # Add adaptive sampling metrics if available
    if sampling_metrics:
        meta["adaptive_sampling"] = {
            "enabled": True,
            "frames_processed": sampling_metrics.frames_processed,
            "frames_skipped": sampling_metrics.frames_skipped,
            "processing_ratio": round(sampling_metrics.processing_ratio, 2),
            "avg_motion_score": round(sampling_metrics.avg_motion_score, 4),
            "id_switches": sampling_metrics.id_switches,
            "lock_events": sampling_metrics.lock_events,
            "efficiency_score": round(sampling_metrics.efficiency_score, 2),
            "last_reason": sampling_metrics.last_reason.value
        }
    else:
        meta["adaptive_sampling"] = {
            "enabled": False,
            "fixed_stride": sample_stride
        }

    logger.info(f"Processing complete: {processed} frames processed from {frames_read} total frames")
    logger.info(f"Processing efficiency: {meta['processing_efficiency']:.1f}%")

    return {"meta": meta, "tracks": tracks}
