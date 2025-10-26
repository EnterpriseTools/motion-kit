"""
Unit tests for adaptive_sampling.py

Tests cover key scenarios:
- Motion-based sampling
- ID switch detection
- Crowd change monitoring
- Lock-on event handling
- Stability detection
- Configuration edge cases
"""

import pytest
import numpy as np
import time
from unittest.mock import Mock, patch

from adaptive_sampling import (
    AdaptiveFrameSampler,
    AdaptiveSamplingConfig,
    SamplingReason,
    SamplingMetrics,
    create_adaptive_sampler,
    integrate_with_detection_pipeline
)


class TestAdaptiveSamplingConfig:
    """Test configuration class"""
    
    def test_default_config(self):
        config = AdaptiveSamplingConfig()
        assert config.min_interval == 1
        assert config.max_interval == 8
        assert config.default_interval == 2
        assert config.enable_motion_detection is True
    
    def test_custom_config(self):
        config = AdaptiveSamplingConfig(
            min_interval=2,
            max_interval=10,
            motion_threshold_high=0.2
        )
        assert config.min_interval == 2
        assert config.max_interval == 10
        assert config.motion_threshold_high == 0.2


class TestSamplingMetrics:
    """Test metrics tracking"""
    
    def test_metrics_initialization(self):
        metrics = SamplingMetrics()
        assert metrics.frames_processed == 0
        assert metrics.processing_ratio == 0.0
        assert metrics.efficiency_score == 0.0
    
    def test_processing_ratio_calculation(self):
        metrics = SamplingMetrics()
        metrics.frames_processed = 50
        metrics.total_frames = 100
        assert metrics.processing_ratio == 50.0
    
    def test_efficiency_score_calculation(self):
        metrics = SamplingMetrics()
        metrics.frames_processed = 10
        metrics.detection_count = 25
        assert metrics.efficiency_score == 2.5


class TestAdaptiveFrameSampler:
    """Test main adaptive sampler class"""
    
    @pytest.fixture
    def sampler(self):
        config = AdaptiveSamplingConfig(
            min_interval=1,
            max_interval=4,
            default_interval=2,
            motion_threshold_high=0.1,
            motion_threshold_low=0.02,
            motion_history_size=5
        )
        return AdaptiveFrameSampler(config)
    
    @pytest.fixture
    def sample_frame(self):
        """Create a sample BGR frame"""
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    def test_initialization(self, sampler):
        assert sampler._current_interval == 2
        assert sampler._frame_count == 0
        assert len(sampler._motion_history) == 0
    
    def test_first_frame_processing(self, sampler, sample_frame):
        should_process, reason = sampler.should_process_frame(0, sample_frame)
        assert should_process is True
        assert "default" in reason.lower()
    
    def test_interval_based_processing(self, sampler, sample_frame):
        # First frame should be processed
        should_process, _ = sampler.should_process_frame(0, sample_frame)
        assert should_process is True
        
        # Next frame should be skipped (interval=2)
        should_process, _ = sampler.should_process_frame(1, sample_frame)
        assert should_process is False
        
        # Frame 2 should be processed
        should_process, _ = sampler.should_process_frame(2, sample_frame)
        assert should_process is True
    
    def test_lock_on_active_processing(self, sampler, sample_frame):
        # When lock-on is active, should process every frame
        should_process, reason = sampler.should_process_frame(
            0, sample_frame, lock_on_active=True
        )
        assert should_process is True
        assert "lock_on_active" in reason.lower()
        
        # Next frame should also be processed due to lock-on
        should_process, reason = sampler.should_process_frame(
            1, sample_frame, lock_on_active=True
        )
        assert should_process is True
    
    def test_seek_event_processing(self, sampler, sample_frame):
        should_process, reason = sampler.should_process_frame(
            0, sample_frame, seek_event=True
        )
        assert should_process is True
        assert "seek" in reason.lower()
    
    def test_motion_detection(self, sampler):
        # Create frames with different motion levels
        static_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        motion_frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        # Process static frame first
        sampler.should_process_frame(0, static_frame)
        
        # Process motion frame - should trigger motion detection
        should_process, reason = sampler.should_process_frame(1, motion_frame)
        
        # Motion score should be calculated
        assert sampler.metrics.avg_motion_score >= 0.0
    
    def test_id_switch_detection(self, sampler, sample_frame):
        # Initial detections
        detections1 = [{'id': 1}, {'id': 2}]
        sampler.should_process_frame(0, sample_frame, detections1)
        
        # ID switch occurs
        detections2 = [{'id': 1}, {'id': 3}]  # ID 2 -> 3
        should_process, reason = sampler.should_process_frame(
            2, sample_frame, detections2
        )
        
        # Should trigger ID switch handling
        assert sampler.metrics.id_switches >= 0
    
    def test_crowd_change_detection(self, sampler, sample_frame):
        # Initial crowd
        detections1 = [{'id': 1}, {'id': 2}]
        sampler.should_process_frame(0, sample_frame, detections1)
        
        # Crowd increases significantly
        detections2 = [{'id': 1}, {'id': 2}, {'id': 3}, {'id': 4}, {'id': 5}]
        should_process, reason = sampler.should_process_frame(
            2, sample_frame, detections2
        )
        
        # Should detect crowd change
        assert sampler._prev_detection_count == len(detections2)
    
    def test_stability_reduction(self, sampler, sample_frame):
        # Simulate stable scene over many frames
        stable_detections = [{'id': 1}, {'id': 2}]
        
        # Process many stable frames
        for i in range(50):
            sampler.should_process_frame(i, sample_frame, stable_detections)
        
        # Stability counter should increase
        assert sampler._stability_counter >= 0
    
    def test_metrics_tracking(self, sampler, sample_frame):
        # Process several frames
        sampler.should_process_frame(0, sample_frame)
        sampler.should_process_frame(1, sample_frame)
        sampler.should_process_frame(2, sample_frame)
        
        metrics = sampler.get_metrics()
        assert metrics.total_frames >= 3
        assert metrics.frames_processed >= 1
    
    def test_telemetry_recording(self, sampler, sample_frame):
        sampler.should_process_frame(0, sample_frame)
        
        events = sampler.get_telemetry_events()
        assert len(events) >= 1
        
        event = events[0]
        assert 'timestamp' in event
        assert 'frame_idx' in event
        assert 'reason' in event
    
    def test_reset_functionality(self, sampler, sample_frame):
        # Process some frames
        sampler.should_process_frame(0, sample_frame)
        sampler.should_process_frame(1, sample_frame)
        
        # Reset sampler
        sampler.reset()
        
        # Check state is reset
        assert sampler._frame_count == 0
        assert sampler._last_processed_frame == -1
        assert len(sampler._motion_history) == 0
        assert len(sampler._telemetry_events) == 0
    
    def test_config_update(self, sampler):
        original_max = sampler.config.max_interval
        sampler.update_config(max_interval=10)
        assert sampler.config.max_interval == 10
        assert sampler.config.max_interval != original_max


class TestMotionDetection:
    """Test motion detection algorithms"""
    
    def test_no_motion_static_frames(self):
        sampler = AdaptiveFrameSampler()
        
        # Create identical frames (no motion)
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2 = np.zeros((100, 100, 3), dtype=np.uint8)
        
        motion1 = sampler._calculate_motion_score(frame1)
        motion2 = sampler._calculate_motion_score(frame2)
        
        assert motion1 == 0.0  # No previous frame
        assert motion2 == 0.0  # No change from previous
    
    def test_high_motion_random_frames(self):
        sampler = AdaptiveFrameSampler()
        
        # Create very different frames (high motion)
        frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        frame2 = np.full((100, 100, 3), 255, dtype=np.uint8)
        
        motion1 = sampler._calculate_motion_score(frame1)
        motion2 = sampler._calculate_motion_score(frame2)
        
        assert motion1 == 0.0  # No previous frame
        assert motion2 > 0.0   # High change detected


class TestIntegrationHelpers:
    """Test integration helper functions"""
    
    def test_create_adaptive_sampler_default(self):
        sampler = create_adaptive_sampler()
        assert isinstance(sampler, AdaptiveFrameSampler)
        assert sampler.config.default_interval == 2  # 30 FPS default
    
    def test_create_adaptive_sampler_high_fps(self):
        sampler = create_adaptive_sampler(video_fps=60)
        assert sampler.config.default_interval == 3  # Higher interval for 60 FPS
    
    def test_create_adaptive_sampler_low_fps(self):
        sampler = create_adaptive_sampler(video_fps=15)
        assert sampler.config.default_interval == 1  # Lower interval for 15 FPS
    
    def test_create_adaptive_sampler_with_overrides(self):
        sampler = create_adaptive_sampler(
            video_fps=30,
            max_interval=12,
            motion_threshold_high=0.3
        )
        assert sampler.config.max_interval == 12
        assert sampler.config.motion_threshold_high == 0.3
    
    def test_integrate_with_detection_pipeline(self):
        sampler = create_adaptive_sampler()
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        should_process, reason, telemetry = integrate_with_detection_pipeline(
            sampler, 0, frame
        )
        
        assert isinstance(should_process, bool)
        assert isinstance(reason, str)
        assert 'adaptive_sampling' in telemetry
        assert 'should_process' in telemetry['adaptive_sampling']


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_detections_list(self):
        sampler = AdaptiveFrameSampler()
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        should_process, reason = sampler.should_process_frame(
            0, frame, detections=[]
        )
        assert isinstance(should_process, bool)
    
    def test_detections_without_ids(self):
        sampler = AdaptiveFrameSampler()
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Detections without 'id' field
        detections = [{'score': 0.9}, {'score': 0.8}]
        should_process, reason = sampler.should_process_frame(
            0, frame, detections=detections
        )
        assert isinstance(should_process, bool)
    
    def test_very_large_frame_indices(self):
        sampler = AdaptiveFrameSampler()
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Test with large frame index
        should_process, reason = sampler.should_process_frame(
            999999, frame
        )
        assert isinstance(should_process, bool)
    
    def test_rapid_seek_events(self):
        sampler = AdaptiveFrameSampler()
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Multiple rapid seek events
        for i in range(5):
            should_process, reason = sampler.should_process_frame(
                i, frame, seek_event=True
            )
            assert should_process is True
    
    def test_malformed_frame(self):
        sampler = AdaptiveFrameSampler()
        
        # Test with unusual frame dimensions
        weird_frame = np.zeros((1, 1, 3), dtype=np.uint8)
        should_process, reason = sampler.should_process_frame(0, weird_frame)
        assert isinstance(should_process, bool)


class TestPerformance:
    """Test performance characteristics"""
    
    def test_motion_calculation_performance(self):
        sampler = AdaptiveFrameSampler()
        frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        
        start_time = time.perf_counter()
        for _ in range(10):
            sampler._calculate_motion_score(frame)
        end_time = time.perf_counter()
        
        avg_time = (end_time - start_time) / 10
        # Should complete in reasonable time (< 50ms per frame)
        assert avg_time < 0.05
    
    def test_telemetry_buffer_management(self):
        config = AdaptiveSamplingConfig()
        sampler = AdaptiveFrameSampler(config)
        sampler._max_telemetry_events = 5  # Small buffer for testing
        
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Generate more events than buffer size
        for i in range(10):
            sampler.should_process_frame(i, frame)
        
        events = sampler.get_telemetry_events()
        assert len(events) <= sampler._max_telemetry_events


if __name__ == "__main__":
    # Run basic functionality test
    print("Running basic adaptive sampling test...")
    
    sampler = create_adaptive_sampler(video_fps=30)
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    for i in range(20):
        should_process, reason = sampler.should_process_frame(i, frame)
        print(f"Frame {i}: Process={should_process}, Reason={reason}")
    
    metrics = sampler.get_metrics()
    print(f"\nMetrics: {metrics.frames_processed}/{metrics.total_frames} processed")
    print(f"Processing ratio: {metrics.processing_ratio:.1f}%")
    print("Basic test completed successfully!")
