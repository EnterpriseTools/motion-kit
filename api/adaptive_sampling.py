"""
Adaptive Frame Sampling for PROTOCAM

This module provides intelligent frame sampling that adapts to scene dynamics,
increasing processing rate during motion/changes and reducing it during stable periods.

Features:
- Motion-based sampling adjustment
- ID switch detection
- Crowd change monitoring  
- Lock-on event prioritization
- Telemetry and metrics tracking
- Configurable thresholds and parameters
"""

import time
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SamplingReason(Enum):
    """Reasons for frame sampling decisions"""
    MOTION_SPIKE = "motion_spike"
    ID_SWITCH = "id_switch" 
    CROWD_CHANGE = "crowd_change"
    LOCK_ON_ACTIVE = "lock_on_active"
    USER_SEEK = "user_seek"
    STABLE_SCENE = "stable_scene"
    INITIALIZATION = "initialization"
    DEFAULT = "default"


@dataclass
class SamplingMetrics:
    """Metrics for adaptive sampling performance"""
    frames_processed: int = 0
    frames_skipped: int = 0
    total_frames: int = 0
    current_interval: int = 2
    avg_motion_score: float = 0.0
    detection_count: int = 0
    id_switches: int = 0
    lock_events: int = 0
    processing_time_ms: float = 0.0
    last_reason: SamplingReason = SamplingReason.DEFAULT
    
    @property
    def processing_ratio(self) -> float:
        """Percentage of frames actually processed"""
        if self.total_frames == 0:
            return 0.0
        return (self.frames_processed / self.total_frames) * 100
    
    @property
    def efficiency_score(self) -> float:
        """Efficiency metric: detections per processed frame"""
        if self.frames_processed == 0:
            return 0.0
        return self.detection_count / self.frames_processed


@dataclass
class AdaptiveSamplingConfig:
    """Configuration for adaptive frame sampling"""
    
    # Base sampling intervals
    min_interval: int = 1  # Process every frame during high activity
    max_interval: int = 8  # Skip up to 7 frames during stable periods
    default_interval: int = 2  # Starting interval
    
    # Motion detection thresholds
    motion_threshold_high: float = 0.15  # High motion trigger
    motion_threshold_low: float = 0.05   # Low motion threshold
    motion_history_size: int = 10        # Frames to average motion over
    
    # Detection change thresholds
    detection_change_threshold: float = 0.3  # 30% change in detection count
    id_switch_penalty: int = 3              # Frames to process after ID switch
    
    # Lock-on parameters
    lock_on_boost_frames: int = 15  # Extra frames to process during lock-on
    
    # Timing parameters
    seek_event_window: float = 2.0    # Seconds to boost after seek
    stability_window: int = 30        # Frames of stability before reducing rate
    
    # Performance tuning
    enable_motion_detection: bool = True
    enable_id_tracking: bool = True
    enable_crowd_monitoring: bool = True


class AdaptiveFrameSampler:
    """
    Adaptive frame sampler that adjusts processing rate based on scene dynamics.
    
    The sampler uses multiple signals to determine when to increase or decrease
    the frame processing rate:
    - Motion detection using frame differences
    - Detection count changes (crowd monitoring)
    - ID switches in tracking
    - Lock-on events from targeting system
    - User seek events
    """
    
    def __init__(self, config: Optional[AdaptiveSamplingConfig] = None):
        self.config = config or AdaptiveSamplingConfig()
        self.metrics = SamplingMetrics()
        
        # State tracking
        self._current_interval = self.config.default_interval
        self._frame_count = 0
        self._last_processed_frame = -1
        
        # Motion detection state
        self._prev_frame_gray: Optional[np.ndarray] = None
        self._motion_history: List[float] = []
        
        # Detection tracking state
        self._prev_detection_count = 0
        self._prev_track_ids: set = set()
        self._stability_counter = 0
        
        # Event state
        self._lock_on_boost_remaining = 0
        self._id_switch_boost_remaining = 0
        self._last_seek_time = 0.0
        
        # Telemetry buffer
        self._telemetry_events: List[Dict[str, Any]] = []
        self._max_telemetry_events = 1000
        
        logger.info(f"AdaptiveFrameSampler initialized with config: {self.config}")
    
    def should_process_frame(
        self,
        frame_idx: int,
        frame: np.ndarray,
        detections: Optional[List[Dict]] = None,
        lock_on_active: bool = False,
        seek_event: bool = False
    ) -> Tuple[bool, str]:
        """
        Determine if a frame should be processed based on adaptive criteria.
        
        Args:
            frame_idx: Current frame index
            frame: Current frame (BGR format)
            detections: Previous frame detections for comparison
            lock_on_active: Whether targeting lock-on is active
            seek_event: Whether user just seeked in video
            
        Returns:
            Tuple of (should_process, reason_string)
        """
        start_time = time.perf_counter()
        
        self._frame_count = frame_idx
        self.metrics.total_frames = max(self.metrics.total_frames, frame_idx + 1)
        
        # Handle seek events
        if seek_event:
            self._last_seek_time = time.time()
            self._record_telemetry(frame_idx, SamplingReason.USER_SEEK, 1)
            self.metrics.last_reason = SamplingReason.USER_SEEK
            return True, "User seek event"
        
        # Check if we're in a seek boost window
        if time.time() - self._last_seek_time < self.config.seek_event_window:
            interval = 1
            reason = SamplingReason.USER_SEEK
        # Check lock-on boost
        elif lock_on_active:
            self._lock_on_boost_remaining = self.config.lock_on_boost_frames
            interval = 1
            reason = SamplingReason.LOCK_ON_ACTIVE
            self.metrics.lock_events += 1
        # Check ID switch boost
        elif self._id_switch_boost_remaining > 0:
            interval = 1
            reason = SamplingReason.ID_SWITCH
            self._id_switch_boost_remaining -= 1
        else:
            # Normal adaptive logic
            interval, reason = self._calculate_adaptive_interval(frame, detections)
        
        # Update current interval
        self._current_interval = interval
        self.metrics.current_interval = interval
        self.metrics.last_reason = reason
        
        # Determine if we should process this frame
        should_process = (frame_idx - self._last_processed_frame) >= interval
        
        if should_process:
            self._last_processed_frame = frame_idx
            self.metrics.frames_processed += 1
            
            # Update detection metrics if provided
            if detections is not None:
                self.metrics.detection_count += len(detections)
        else:
            self.metrics.frames_skipped += 1
        
        # Record processing time
        processing_time = (time.perf_counter() - start_time) * 1000
        self.metrics.processing_time_ms = processing_time
        
        # Record telemetry
        self._record_telemetry(frame_idx, reason, interval, should_process)
        
        reason_str = f"{reason.value} (interval={interval})"
        return should_process, reason_str
    
    def _calculate_adaptive_interval(
        self,
        frame: np.ndarray,
        detections: Optional[List[Dict]] = None
    ) -> Tuple[int, SamplingReason]:
        """Calculate adaptive sampling interval based on scene analysis"""
        
        # Start with default interval
        interval = self.config.default_interval
        reason = SamplingReason.DEFAULT
        
        # Motion detection
        if self.config.enable_motion_detection:
            motion_score = self._calculate_motion_score(frame)
            self._motion_history.append(motion_score)
            
            # Keep motion history bounded
            if len(self._motion_history) > self.config.motion_history_size:
                self._motion_history.pop(0)
            
            # Calculate average motion
            avg_motion = np.mean(self._motion_history)
            self.metrics.avg_motion_score = avg_motion
            
            # Adjust interval based on motion
            if avg_motion > self.config.motion_threshold_high:
                interval = self.config.min_interval
                reason = SamplingReason.MOTION_SPIKE
                self._stability_counter = 0
            elif avg_motion < self.config.motion_threshold_low:
                self._stability_counter += 1
            else:
                self._stability_counter = 0
        
        # Detection count changes (crowd monitoring)
        if self.config.enable_crowd_monitoring and detections is not None:
            current_count = len(detections)
            
            if self._prev_detection_count > 0:
                count_change = abs(current_count - self._prev_detection_count) / self._prev_detection_count
                
                if count_change > self.config.detection_change_threshold:
                    interval = min(interval, self.config.min_interval + 1)
                    reason = SamplingReason.CROWD_CHANGE
                    self._stability_counter = 0
            
            self._prev_detection_count = current_count
        
        # ID switch detection
        if self.config.enable_id_tracking and detections is not None:
            current_ids = {det.get('id', -1) for det in detections if 'id' in det}
            
            if self._prev_track_ids and current_ids != self._prev_track_ids:
                # Detect new IDs or lost IDs
                new_ids = current_ids - self._prev_track_ids
                lost_ids = self._prev_track_ids - current_ids
                
                if new_ids or lost_ids:
                    self._id_switch_boost_remaining = self.config.id_switch_penalty
                    interval = self.config.min_interval
                    reason = SamplingReason.ID_SWITCH
                    self.metrics.id_switches += 1
                    self._stability_counter = 0
            
            self._prev_track_ids = current_ids.copy()
        
        # Apply stability reduction
        if self._stability_counter >= self.config.stability_window:
            if reason == SamplingReason.DEFAULT:
                interval = min(self.config.max_interval, interval + 1)
                reason = SamplingReason.STABLE_SCENE
        
        # Ensure interval is within bounds
        interval = max(self.config.min_interval, min(self.config.max_interval, interval))
        
        return interval, reason
    
    def _calculate_motion_score(self, frame: np.ndarray) -> float:
        """Calculate motion score using frame difference"""
        
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # Calculate motion score
        if self._prev_frame_gray is not None:
            # Frame difference
            diff = cv2.absdiff(self._prev_frame_gray, gray)
            
            # Threshold to get binary motion map
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            
            # Calculate percentage of changed pixels
            motion_score = np.sum(thresh > 0) / (thresh.shape[0] * thresh.shape[1])
        else:
            motion_score = 0.0
        
        self._prev_frame_gray = gray.copy()
        return motion_score
    
    def _record_telemetry(
        self,
        frame_idx: int,
        reason: SamplingReason,
        interval: int,
        processed: bool = True
    ):
        """Record telemetry event for monitoring and debugging"""
        
        event = {
            'timestamp': time.time(),
            'frame_idx': frame_idx,
            'reason': reason.value,
            'interval': interval,
            'processed': processed,
            'motion_score': self.metrics.avg_motion_score,
            'detection_count': self.metrics.detection_count,
            'processing_ratio': self.metrics.processing_ratio
        }
        
        self._telemetry_events.append(event)
        
        # Keep telemetry buffer bounded
        if len(self._telemetry_events) > self._max_telemetry_events:
            self._telemetry_events.pop(0)
    
    def get_metrics(self) -> SamplingMetrics:
        """Get current sampling metrics"""
        return self.metrics
    
    def get_telemetry_events(self, since_timestamp: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get telemetry events, optionally filtered by timestamp"""
        
        if since_timestamp is None:
            return self._telemetry_events.copy()
        
        return [
            event for event in self._telemetry_events
            if event['timestamp'] >= since_timestamp
        ]
    
    def reset(self):
        """Reset sampler state for new video processing"""
        
        logger.info("Resetting AdaptiveFrameSampler state")
        
        self.metrics = SamplingMetrics()
        self._current_interval = self.config.default_interval
        self._frame_count = 0
        self._last_processed_frame = -1
        
        self._prev_frame_gray = None
        self._motion_history.clear()
        
        self._prev_detection_count = 0
        self._prev_track_ids.clear()
        self._stability_counter = 0
        
        self._lock_on_boost_remaining = 0
        self._id_switch_boost_remaining = 0
        self._last_seek_time = 0.0
        
        self._telemetry_events.clear()
    
    def update_config(self, **kwargs):
        """Update configuration parameters"""
        
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Updated config: {key} = {value}")
            else:
                logger.warning(f"Unknown config parameter: {key}")


# Integration helper functions

def create_adaptive_sampler(
    video_fps: Optional[float] = None,
    **config_overrides
) -> AdaptiveFrameSampler:
    """
    Create an adaptive sampler with sensible defaults for given video FPS.
    
    Args:
        video_fps: Target video FPS (defaults to 30 if unknown)
        **config_overrides: Override default config parameters
        
    Returns:
        Configured AdaptiveFrameSampler instance
    """
    
    # Default FPS assumption
    fps = video_fps or 30.0
    
    # Adjust config based on FPS
    config = AdaptiveSamplingConfig()
    
    # Higher FPS videos can afford larger intervals
    if fps >= 60:
        config.default_interval = 3
        config.max_interval = 12
    elif fps >= 30:
        config.default_interval = 2
        config.max_interval = 8
    else:
        config.default_interval = 1
        config.max_interval = 4
    
    # Apply overrides
    for key, value in config_overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return AdaptiveFrameSampler(config)


def integrate_with_detection_pipeline(
    sampler: AdaptiveFrameSampler,
    frame_idx: int,
    frame: np.ndarray,
    prev_detections: Optional[List[Dict]] = None,
    lock_on_active: bool = False,
    seek_event: bool = False
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Integration helper for existing detection pipeline.
    
    Args:
        sampler: AdaptiveFrameSampler instance
        frame_idx: Current frame index
        frame: Current frame
        prev_detections: Previous frame detections
        lock_on_active: Whether lock-on is active
        seek_event: Whether user seeked
        
    Returns:
        Tuple of (should_process, reason, telemetry_data)
    """
    
    should_process, reason = sampler.should_process_frame(
        frame_idx, frame, prev_detections, lock_on_active, seek_event
    )
    
    # Prepare telemetry data for frontend
    metrics = sampler.get_metrics()
    telemetry_data = {
        'adaptive_sampling': {
            'should_process': should_process,
            'reason': reason,
            'current_interval': metrics.current_interval,
            'processing_ratio': round(metrics.processing_ratio, 2),
            'frames_processed': metrics.frames_processed,
            'frames_skipped': metrics.frames_skipped,
            'avg_motion_score': round(metrics.avg_motion_score, 4),
            'efficiency_score': round(metrics.efficiency_score, 2)
        }
    }
    
    return should_process, reason, telemetry_data
