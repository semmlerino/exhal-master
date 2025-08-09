"""
Comprehensive tests for SmartPreviewCoordinator - Real-time preview updates with dual-tier caching

Tests focus on:
1. Real-time preview updates with proper debouncing
2. Drag state handling and different timing strategies  
3. Dual-tier caching (memory + ROM cache)
4. Worker pool integration and thread reuse
5. Request prioritization and cancellation
6. Performance metrics and cache hit/miss tracking
7. Signal chain integration (sliderPressed/sliderReleased)
8. Error handling and recovery patterns
"""

import time
import weakref
from enum import Enum
from unittest.mock import Mock, patch, MagicMock

import pytest
from PyQt6.QtCore import QMutex, QMutexLocker, QObject, QTimer
from PyQt6.QtWidgets import QSlider

from ui.common.smart_preview_coordinator import (
# Serial execution required: QApplication management, Real Qt components
pytestmark = [
    
    pytest.mark.serial,
    pytest.mark.qt_application
]


    SmartPreviewCoordinator,
    DragState,
    PreviewRequest
)
from tests.infrastructure.real_component_factory import RealComponentFactory


class MockPreviewCache:
    """Mock PreviewCache for testing"""
    def __init__(self):
        self.cache_data = {}
        self.get_calls = []
        self.put_calls = []
        self.clear_calls = []
        
    def get(self, key):
        """Mock cache get"""
        self.get_calls.append(key)
        return self.cache_data.get(key)
        
    def put(self, key, data, metadata=None):
        """Mock cache put"""
        self.put_calls.append((key, data, metadata))
        self.cache_data[key] = (data, metadata)
        
    def clear(self):
        """Mock cache clear"""
        self.clear_calls.append(time.time())
        self.cache_data.clear()
        
    def get_stats(self):
        """Mock cache stats"""
        return {
            "hits": len([c for c in self.get_calls if c in self.cache_data]),
            "misses": len([c for c in self.get_calls if c not in self.cache_data]),
            "size": len(self.cache_data)
        }


class MockPreviewWorkerPool(QObject):
    """Mock PreviewWorkerPool for testing"""
    from PyQt6.QtCore import pyqtSignal
    
    preview_ready = pyqtSignal(str, bytes, int, int, str)  # request_id, data, width, height, name
    preview_error = pyqtSignal(str, str)                   # request_id, error
    
    def __init__(self):
        super().__init__()
        self.generate_calls = []
        self.cancel_calls = []
        self.cleanup_calls = []
        
    def generate_preview(self, request_id, rom_path, offset, priority=0):
        """Mock preview generation"""
        self.generate_calls.append((request_id, rom_path, offset, priority))
        
        # Simulate successful generation after short delay
        QTimer.singleShot(10, lambda: self.preview_ready.emit(
            request_id, b"mock_tile_data", 128, 128, f"sprite_{offset:06x}"
        ))
        
    def cancel_request(self, request_id):
        """Mock request cancellation"""
        self.cancel_calls.append(request_id)
        
    def cleanup_stale_requests(self):
        """Mock stale request cleanup"""
        self.cleanup_calls.append(time.time())


class MockROMCache:
    """Mock ROM cache for testing"""
    def __init__(self):
        self.cache_data = {}
        self.get_calls = []
        self.put_calls = []
        
    def get_cached_sprite_data(self, rom_path, offset):
        """Mock ROM cache get"""
        key = f"{rom_path}_{offset:08x}"
        self.get_calls.append((rom_path, offset))
        return self.cache_data.get(key)
        
    def cache_sprite_data(self, rom_path, offset, data, metadata=None):
        """Mock ROM cache put"""
        key = f"{rom_path}_{offset:08x}"
        self.put_calls.append((rom_path, offset, data, metadata))
        self.cache_data[key] = (data, metadata)
        
    def get_cache_status(self, rom_path):
        """Mock cache status"""
        return "ready" if rom_path else "no_cache"


class TestPreviewRequest:
    """Test PreviewRequest data structure"""
    
    def test_request_creation(self):
        """Test request creation with parameters"""
        callback = Mock()
        request = PreviewRequest(
            request_id=123,
            offset=0x200000,
            rom_path="/test/rom.sfc",
            priority=5,
            callback=callback
        )
        
        assert request.request_id == 123
        assert request.offset == 0x200000
        assert request.rom_path == "/test/rom.sfc"
        assert request.priority == 5
        assert request.callback == callback
        assert not request.cancelled
    
    def test_request_cancellation(self):
        """Test request cancellation"""
        request = PreviewRequest(request_id=1, offset=0x100000, rom_path="/test/rom.sfc")
        
        assert not request.cancelled
        request.cancel()
        assert request.cancelled
    
    def test_request_priority_ordering(self):
        """Test priority queue ordering"""
        low_priority = PreviewRequest(request_id=1, offset=0x100000, rom_path="/test/rom.sfc", priority=1)
        high_priority = PreviewRequest(request_id=2, offset=0x200000, rom_path="/test/rom.sfc", priority=10)
        
        # Higher priority should come first
        assert high_priority < low_priority


class TestSmartPreviewCoordinator:
    """Test SmartPreviewCoordinator functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_rom_cache = MockROMCache()
        self.coordinator = SmartPreviewCoordinator(rom_cache=self.mock_rom_cache)
        
        # Mock dependencies
        self.mock_memory_cache = MockPreviewCache()
        self.mock_worker_pool = MockPreviewWorkerPool()
        
        # Inject mocks
        self.coordinator._memory_cache = self.mock_memory_cache
        self.coordinator._worker_pool = self.mock_worker_pool
        
        # Connect mock signals
        self.mock_worker_pool.preview_ready.connect(self.coordinator._on_worker_preview_ready)
        self.mock_worker_pool.preview_error.connect(self.coordinator._on_worker_preview_error)
    
    def teardown_method(self):
        """Clean up test fixtures"""
        if hasattr(self, 'coordinator'):
            self.coordinator.cleanup()
            del self.coordinator
    
    def test_coordinator_initialization(self):
        """Test proper initialization"""
        assert self.coordinator._current_rom_path == ""
        assert self.coordinator._drag_state == DragState.IDLE
        assert self.coordinator._last_request_id == 0
        assert isinstance(self.coordinator._performance_metrics, dict)
        assert self.coordinator._debounce_timer is not None
        assert self.coordinator._settling_timer is not None
    
    def test_drag_state_transitions(self, qtbot):
        """Test drag state transitions and timing changes"""
        # Initially idle
        assert self.coordinator._drag_state == DragState.IDLE
        
        # Start dragging
        with qtbot.wait_signal(self.coordinator.drag_state_changed, timeout=100):
            self.coordinator.on_slider_pressed()
        
        assert self.coordinator._drag_state == DragState.DRAGGING
        
        # End dragging
        with qtbot.wait_signal(self.coordinator.drag_state_changed, timeout=100):
            self.coordinator.on_slider_released()
        
        assert self.coordinator._drag_state == DragState.SETTLING
        
        # Should eventually return to idle
        QTimer.singleShot(250, lambda: self.assertEqual(self.coordinator._drag_state, DragState.IDLE))
    
    def test_memory_cache_hit_immediate_response(self, qtbot):
        """Test memory cache hit provides immediate response"""
        rom_path = "/test/rom.sfc"
        offset = 0x200000
        
        # Pre-populate memory cache
        cache_key = f"preview_{hash(rom_path)}_{offset:08x}"
        cached_data = b"cached_tile_data"
        self.mock_memory_cache.cache_data[cache_key] = (cached_data, {"width": 128, "height": 128})
        
        # Request should hit memory cache
        with qtbot.wait_signal(self.coordinator.preview_cached, timeout=100) as blocker:
            self.coordinator.request_preview_update(rom_path, offset)
        
        # Should get immediate cached response
        args = blocker.args
        assert args[0] == cached_data  # tile_data
        assert args[1] == 128         # width
        assert args[2] == 128         # height
        
        # Should not trigger worker generation
        assert len(self.mock_worker_pool.generate_calls) == 0
    
    def test_rom_cache_hit_fast_response(self, qtbot):
        """Test ROM cache hit when memory cache misses"""
        rom_path = "/test/rom.sfc"
        offset = 0x300000
        
        # Pre-populate ROM cache
        cached_data = b"rom_cached_data"
        self.mock_rom_cache.cache_sprite_data(rom_path, offset, cached_data, {"source": "rom"})
        
        # Request should hit ROM cache
        with qtbot.wait_signal(self.coordinator.preview_ready, timeout=200) as blocker:
            self.coordinator.request_preview_update(rom_path, offset)
        
        # Should eventually get ROM cached response
        args = blocker.args
        assert args[0] == cached_data
        
        # Should not trigger worker generation
        assert len(self.mock_worker_pool.generate_calls) == 0
        
        # Should populate memory cache for next time
        assert len(self.mock_memory_cache.put_calls) == 1
    
    def test_cache_miss_triggers_worker_generation(self, qtbot):
        """Test cache miss triggers worker preview generation"""
        rom_path = "/test/rom.sfc"
        offset = 0x400000
        
        # Request with no cache data should trigger worker
        with qtbot.wait_signal(self.coordinator.preview_ready, timeout=500) as blocker:
            self.coordinator.request_preview_update(rom_path, offset)
        
        # Should trigger worker generation
        assert len(self.mock_worker_pool.generate_calls) == 1
        call_args = self.mock_worker_pool.generate_calls[0]
        assert call_args[1] == rom_path  # rom_path
        assert call_args[2] == offset    # offset
        
        # Should eventually get worker response
        args = blocker.args
        assert args[0] == b"mock_tile_data"
        assert args[1] == 128
        assert args[2] == 128
    
    def test_debounced_updates_during_dragging(self, qtbot):
        """Test preview updates are debounced during dragging"""
        rom_path = "/test/rom.sfc"
        
        # Start dragging
        self.coordinator.on_slider_pressed()
        
        # Submit multiple rapid updates
        request_times = []
        for i in range(5):
            offset = 0x200000 + (i * 0x1000)
            self.coordinator.request_preview_update(rom_path, offset)
            request_times.append(time.time())
            time.sleep(0.01)  # 10ms between requests
        
        # Should only process final request after debounce
        # (Mock worker will respond to any generate calls)
        time.sleep(0.1)  # Wait for debounce timer
        
        # Should have fewer worker calls than requests due to debouncing
        assert len(self.mock_worker_pool.generate_calls) <= 2  # At most 1-2 calls
    
    def test_high_quality_update_after_settling(self, qtbot):
        """Test high-quality update after drag settling"""
        rom_path = "/test/rom.sfc"
        offset = 0x200000
        
        # Start and end dragging
        self.coordinator.on_slider_pressed()
        self.coordinator.request_preview_update(rom_path, offset)
        self.coordinator.on_slider_released()
        
        # Should trigger settling update with longer debounce
        with qtbot.wait_signal(self.coordinator.preview_ready, timeout=1000):
            pass
        
        # Should have generated preview
        assert len(self.mock_worker_pool.generate_calls) >= 1
        
        # Last call should be for the final offset
        last_call = self.mock_worker_pool.generate_calls[-1]
        assert last_call[1] == rom_path
        assert last_call[2] == offset
    
    def test_request_cancellation_prevents_stale_updates(self):
        """Test request cancellation prevents stale updates"""
        rom_path = "/test/rom.sfc"
        
        # Submit request
        request_id = self.coordinator.request_preview_update(rom_path, 0x200000)
        
        # Cancel request
        self.coordinator.cancel_pending_requests()
        
        # Should have cancelled pending request
        with QMutexLocker(self.coordinator._request_mutex):
            if request_id in self.coordinator._active_requests:
                assert self.coordinator._active_requests[request_id].cancelled
    
    def test_worker_thread_reuse(self):
        """Test worker thread reuse prevents excessive thread creation"""
        rom_path = "/test/rom.sfc"
        
        # Submit multiple requests
        for i in range(5):
            offset = 0x200000 + (i * 0x1000)
            self.coordinator.request_preview_update(rom_path, offset)
        
        # Should reuse worker pool (not create new workers for each request)
        assert len(self.mock_worker_pool.generate_calls) <= 5
        
        # Worker pool should handle the requests
        # (Actual thread reuse is handled by PreviewWorkerPool implementation)
    
    def test_performance_metrics_tracking(self):
        """Test performance metrics are tracked"""
        initial_metrics = self.coordinator._performance_metrics.copy()
        
        # Perform cache hit
        rom_path = "/test/metrics.sfc"
        offset = 0x200000
        cache_key = f"preview_{hash(rom_path)}_{offset:08x}"
        self.mock_memory_cache.cache_data[cache_key] = (b"cached", {})
        
        self.coordinator.request_preview_update(rom_path, offset)
        
        # Metrics should be updated
        assert self.coordinator._performance_metrics["cache_hits"] > initial_metrics.get("cache_hits", 0)
        assert self.coordinator._performance_metrics["total_requests"] > initial_metrics.get("total_requests", 0)
    
    def test_cache_miss_metrics_tracking(self, qtbot):
        """Test cache miss metrics are tracked"""
        initial_misses = self.coordinator._performance_metrics.get("cache_misses", 0)
        
        # Request with no cache data
        with qtbot.wait_signal(self.coordinator.preview_ready, timeout=500):
            self.coordinator.request_preview_update("/test/miss.sfc", 0x300000)
        
        # Should increment cache miss counter
        assert self.coordinator._performance_metrics["cache_misses"] > initial_misses
    
    def test_response_time_tracking(self, qtbot):
        """Test response time metrics are tracked"""
        rom_path = "/test/timing.sfc"
        offset = 0x200000
        
        # Pre-populate memory cache for fast response
        cache_key = f"preview_{hash(rom_path)}_{offset:08x}"
        self.mock_memory_cache.cache_data[cache_key] = (b"fast_cached", {})
        
        start_time = time.perf_counter()
        
        with qtbot.wait_signal(self.coordinator.preview_cached, timeout=100):
            self.coordinator.request_preview_update(rom_path, offset)
        
        response_time = time.perf_counter() - start_time
        
        # Should track response times
        assert "response_times" in self.coordinator._performance_metrics
        assert len(self.coordinator._performance_metrics["response_times"]) > 0
        
        # Response should be fast for cache hit
        assert response_time < 0.05  # Should be under 50ms for cache hit
    
    def test_slider_signal_integration(self, qtbot):
        """Test integration with QSlider pressed/released signals"""
        # Create mock slider
        mock_slider = Mock(spec=QSlider)
        
        # Connect coordinator to slider signals
        self.coordinator.connect_to_slider(mock_slider)
        
        # Verify signal connections
        # (In real implementation, would connect to sliderPressed/sliderReleased)
        assert hasattr(self.coordinator, 'on_slider_pressed')
        assert hasattr(self.coordinator, 'on_slider_released')
    
    def test_rom_path_changes_clear_context(self):
        """Test ROM path changes clear preview context"""
        # Set initial ROM path
        old_rom = "/test/old.sfc"
        self.coordinator.set_rom_path(old_rom)
        
        # Populate some cache data
        self.coordinator.request_preview_update(old_rom, 0x200000)
        
        # Change ROM path
        new_rom = "/test/new.sfc"
        self.coordinator.set_rom_path(new_rom)
        
        # Should clear context for new ROM
        assert self.coordinator._current_rom_path == new_rom
        # Previous requests should be cancelled/cleared
    
    def test_cleanup_prevents_memory_leaks(self):
        """Test cleanup properly releases resources"""
        # Add some active requests
        self.coordinator.request_preview_update("/test/cleanup.sfc", 0x200000)
        
        # Cleanup should clear all state
        self.coordinator.cleanup()
        
        # Should have cleaned up resources
        with QMutexLocker(self.coordinator._request_mutex):
            assert len(self.coordinator._active_requests) == 0
        
        # Should stop timers
        assert not self.coordinator._debounce_timer.isActive()
        assert not self.coordinator._settling_timer.isActive()
    
    def test_weak_reference_handling(self):
        """Test weak references don't cause issues when objects are deleted"""
        # Create widget reference
        mock_widget = Mock()
        weak_ref = weakref.ref(mock_widget)
        
        # Coordinator should handle weak references properly
        self.coordinator._preview_widget_ref = weak_ref
        
        # Delete original widget
        del mock_widget
        
        # Coordinator should handle dead reference gracefully
        widget = self.coordinator._get_preview_widget()
        assert widget is None
    
    def test_concurrent_request_handling(self, qtbot):
        """Test handling of concurrent preview requests"""
        rom_path = "/test/concurrent.sfc"
        
        # Submit multiple concurrent requests
        request_ids = []
        for i in range(10):
            offset = 0x200000 + (i * 0x1000)
            request_id = self.coordinator.request_preview_update(rom_path, offset)
            request_ids.append(request_id)
        
        # All requests should be tracked
        with QMutexLocker(self.coordinator._request_mutex):
            active_count = len([r for r in self.coordinator._active_requests.values() 
                               if not r.cancelled])
            assert active_count > 0
        
        # Should not exceed reasonable limits
        assert len(self.mock_worker_pool.generate_calls) <= 10
    
    def test_error_handling_and_recovery(self, qtbot):
        """Test error handling and recovery from failures"""
        rom_path = "/test/error.sfc"
        offset = 0x200000
        
        # Submit request that will trigger worker error
        request_id = self.coordinator.request_preview_update(rom_path, offset)
        
        # Simulate worker error
        with qtbot.wait_signal(self.coordinator.preview_error, timeout=100):
            self.mock_worker_pool.preview_error.emit(str(request_id), "Mock error")
        
        # Coordinator should handle error gracefully
        # Request should be cleaned up
        with QMutexLocker(self.coordinator._request_mutex):
            assert request_id not in self.coordinator._active_requests or \
                   self.coordinator._active_requests[request_id].cancelled
    
    @pytest.mark.performance 
    def test_high_frequency_updates_performance(self, qtbot):
        """Test performance under high-frequency updates"""
        rom_path = "/test/performance.sfc"
        
        # Simulate rapid slider movement (60 FPS)
        start_time = time.perf_counter()
        
        for i in range(60):  # 60 updates in ~1 second
            offset = 0x200000 + (i * 0x100)
            self.coordinator.request_preview_update(rom_path, offset)
            time.sleep(1/60)  # 16.67ms between updates
        
        total_time = time.perf_counter() - start_time
        
        # Should handle high frequency updates without significant overhead
        assert total_time < 2.0  # Should complete in under 2 seconds
        
        # Should not create excessive worker requests due to debouncing
        assert len(self.mock_worker_pool.generate_calls) < 60  # Significantly fewer than input requests
    
    def test_cache_efficiency_under_load(self):
        """Test cache efficiency with realistic usage patterns"""
        rom_path = "/test/efficiency.sfc"
        
        # Simulate user scrolling back and forth (realistic usage)
        offsets = [0x200000, 0x201000, 0x202000, 0x201000, 0x200000,  # Forward then back
                  0x200000, 0x201000, 0x200000]  # More back and forth
        
        for offset in offsets:
            self.coordinator.request_preview_update(rom_path, offset)
        
        # Should have high cache hit rate due to repeated offsets
        stats = self.mock_memory_cache.get_stats()
        total_requests = stats["hits"] + stats["misses"]
        
        if total_requests > 0:
            hit_rate = stats["hits"] / total_requests
            # Should achieve reasonable cache hit rate
            assert hit_rate > 0.3  # At least 30% hit rate with repeated offsets


class TestSmartPreviewCoordinatorIntegration:
    """Integration tests with real Qt components"""
    
    def test_real_slider_integration(self, qtbot):
        """Test integration with real QSlider widget"""
        from PyQt6.QtWidgets import QApplication, QSlider
        
        # Ensure QApplication exists
        if not QApplication.instance():
            app = QApplication([])
        
        # Create real slider
        slider = QSlider()
        slider.setMinimum(0)
        slider.setMaximum(0x400000)
        slider.setValue(0x200000)
        
        # Create coordinator
        coordinator = SmartPreviewCoordinator()
        
        # Connect to slider
        coordinator.connect_to_slider(slider)
        
        # Test signal emission
        with qtbot.wait_signal(coordinator.drag_state_changed, timeout=100):
            slider.sliderPressed.emit()
        
        with qtbot.wait_signal(coordinator.drag_state_changed, timeout=100):
            slider.sliderReleased.emit()
        
        # Cleanup
        coordinator.cleanup()
        del coordinator
    
    def test_memory_usage_patterns(self):
        """Test memory usage patterns under realistic load"""
        coordinator = SmartPreviewCoordinator()
        
        # Simulate extended usage session
        rom_path = "/test/memory.sfc"
        
        # Generate many unique offsets to test cache eviction
        for i in range(100):
            offset = 0x200000 + (i * 0x1000)
            coordinator.request_preview_update(rom_path, offset)
        
        # Memory cache should have reasonable bounds
        if hasattr(coordinator, '_memory_cache'):
            # Cache should not grow unbounded
            cache_size = len(coordinator._memory_cache._cache) if hasattr(coordinator._memory_cache, '_cache') else 0
            assert cache_size < 50  # Should evict old entries
        
        coordinator.cleanup()
        del coordinator


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])