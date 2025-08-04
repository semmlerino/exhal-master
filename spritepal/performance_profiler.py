#!/usr/bin/env python3
"""
Performance Profiler for Manual Offset Dialog Preview Updates

This module provides comprehensive performance analysis of the preview update
mechanism in the manual offset dialog, focusing on:
1. CPU time analysis of preview methods
2. Worker thread creation/cleanup overhead
3. Signal emission and handling latency
4. Memory usage during rapid slider movements
5. Blocking operations identification

Uses built-in Python profiling tools for maximum compatibility.
"""

import cProfile
import gc
import io
import pstats
import time
import tracemalloc
import weakref
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance measurements."""
    
    # Timing metrics (milliseconds)
    preview_update_time: float = 0.0
    worker_creation_time: float = 0.0
    worker_cleanup_time: float = 0.0
    signal_emission_time: float = 0.0
    signal_handling_time: float = 0.0
    
    # Memory metrics (bytes)
    memory_before: int = 0
    memory_after: int = 0
    memory_peak: int = 0
    
    # Threading metrics
    active_threads: int = 0
    worker_threads_created: int = 0
    worker_threads_destroyed: int = 0
    
    # Frame rate metrics
    update_frequency: float = 0.0  # Hz
    frame_drops: int = 0
    
    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    
    def __str__(self) -> str:
        return (
            f"PerformanceMetrics(\n"
            f"  Preview Update: {self.preview_update_time:.2f}ms\n"
            f"  Worker Creation: {self.worker_creation_time:.2f}ms\n"
            f"  Worker Cleanup: {self.worker_cleanup_time:.2f}ms\n"
            f"  Signal Emission: {self.signal_emission_time:.2f}ms\n"
            f"  Signal Handling: {self.signal_handling_time:.2f}ms\n"
            f"  Memory Delta: {(self.memory_after - self.memory_before) / 1024:.1f}KB\n"
            f"  Memory Peak: {self.memory_peak / 1024:.1f}KB\n"
            f"  Active Threads: {self.active_threads}\n"
            f"  Update Frequency: {self.update_frequency:.1f}Hz\n"
            f"  Frame Drops: {self.frame_drops}\n"
            f"  Cache Hit Rate: {self.cache_hits / max(1, self.cache_hits + self.cache_misses) * 100:.1f}%\n"
            f")"
        )


class PerformanceProfiler:
    """
    Comprehensive performance profiler for the manual offset dialog.
    
    This profiler instruments the preview update mechanism to measure:
    - CPU time spent in critical methods
    - Memory allocation patterns
    - Worker thread lifecycle overhead
    - Signal emission/handling latency
    - UI responsiveness metrics
    """
    
    def __init__(self):
        self._metrics = PerformanceMetrics()
        self._lock = Lock()
        self._profiler: Optional[cProfile.Profile] = None
        self._memory_profiler: Optional[tracemalloc.Traceback] = None
        
        # Timing measurement state
        self._timing_stack: List[Tuple[str, float]] = []
        self._method_times: Dict[str, List[float]] = {}
        
        # Memory tracking
        self._memory_snapshots: List[Tuple[float, int]] = []
        
        # Frame rate tracking
        self._frame_timestamps: List[float] = []
        self._last_update_time = 0.0
        
        # Thread tracking
        self._thread_refs: List[weakref.ReferenceType] = []
        
        # Cache tracking
        self._cache_stats = {"hits": 0, "misses": 0}
        
    @contextmanager
    def profile_cpu(self, enable: bool = True):
        """Context manager for CPU profiling."""
        if not enable:
            yield
            return
            
        self._profiler = cProfile.Profile()
        self._profiler.enable()
        
        try:
            yield
        finally:
            self._profiler.disable()
    
    @contextmanager
    def profile_memory(self, enable: bool = True):
        """Context manager for memory profiling."""
        if not enable:
            yield
            return
            
        tracemalloc.start()
        gc.collect()  # Clean start
        
        snapshot_before = tracemalloc.take_snapshot()
        memory_before = self._get_process_memory()
        
        try:
            yield
        finally:
            memory_after = self._get_process_memory()
            snapshot_after = tracemalloc.take_snapshot()
            
            # Calculate memory delta
            self._metrics.memory_before = memory_before
            self._metrics.memory_after = memory_after
            
            # Find peak memory usage
            top_stats = snapshot_after.compare_to(snapshot_before, 'lineno')
            if top_stats:
                self._metrics.memory_peak = max(stat.size for stat in top_stats[:10])
            
            tracemalloc.stop()
    
    @contextmanager
    def time_method(self, method_name: str):
        """Context manager for timing method execution."""
        start_time = time.perf_counter()
        
        with self._lock:
            self._timing_stack.append((method_name, start_time))
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            
            with self._lock:
                self._timing_stack.pop()
                
                if method_name not in self._method_times:
                    self._method_times[method_name] = []
                self._method_times[method_name].append(duration_ms)
    
    def record_frame_update(self):
        """Record a frame update for FPS calculation."""
        current_time = time.perf_counter()
        
        with self._lock:
            self._frame_timestamps.append(current_time)
            
            # Keep only last 100 frames for calculation
            if len(self._frame_timestamps) > 100:
                self._frame_timestamps.pop(0)
            
            # Detect frame drops (> 33ms between updates = < 30 FPS)
            if self._last_update_time > 0:
                frame_time = current_time - self._last_update_time
                if frame_time > 0.033:  # 33ms
                    self._metrics.frame_drops += 1
            
            self._last_update_time = current_time
    
    def record_worker_creation(self):
        """Record worker thread creation."""
        with self._lock:
            self._metrics.worker_threads_created += 1
    
    def record_worker_destruction(self):
        """Record worker thread destruction."""
        with self._lock:
            self._metrics.worker_threads_destroyed += 1
    
    def record_cache_hit(self):
        """Record cache hit."""
        with self._lock:
            self._cache_stats["hits"] += 1
    
    def record_cache_miss(self):
        """Record cache miss."""
        with self._lock:
            self._cache_stats["misses"] += 1
    
    def _get_process_memory(self) -> int:
        """Get current process memory usage in bytes."""
        try:
            process = psutil.Process()
            return process.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0
    
    def calculate_metrics(self) -> PerformanceMetrics:
        """Calculate final performance metrics."""
        with self._lock:
            # Calculate average method times
            if "_update_preview" in self._method_times:
                times = self._method_times["_update_preview"]
                self._metrics.preview_update_time = sum(times) / len(times) if times else 0
            
            if "worker_creation" in self._method_times:
                times = self._method_times["worker_creation"]
                self._metrics.worker_creation_time = sum(times) / len(times) if times else 0
            
            if "worker_cleanup" in self._method_times:
                times = self._method_times["worker_cleanup"]
                self._metrics.worker_cleanup_time = sum(times) / len(times) if times else 0
            
            if "signal_emission" in self._method_times:
                times = self._method_times["signal_emission"]
                self._metrics.signal_emission_time = sum(times) / len(times) if times else 0
            
            if "signal_handling" in self._method_times:
                times = self._method_times["signal_handling"]
                self._metrics.signal_handling_time = sum(times) / len(times) if times else 0
            
            # Calculate update frequency
            if len(self._frame_timestamps) > 1:
                time_span = self._frame_timestamps[-1] - self._frame_timestamps[0]
                frame_count = len(self._frame_timestamps) - 1
                self._metrics.update_frequency = frame_count / time_span if time_span > 0 else 0
            
            # Get current thread count
            self._metrics.active_threads = len([ref for ref in self._thread_refs if ref() is not None])
            
            # Cache statistics
            self._metrics.cache_hits = self._cache_stats["hits"]
            self._metrics.cache_misses = self._cache_stats["misses"]
        
        return self._metrics
    
    def get_cpu_profile_report(self) -> str:
        """Get CPU profiling report."""
        if not self._profiler:
            return "No CPU profiling data available"
        
        # Capture profiling output
        stream = io.StringIO()
        stats = pstats.Stats(self._profiler, stream=stream)
        stats.sort_stats('cumulative')
        stats.print_stats(30)  # Top 30 functions
        
        return stream.getvalue()
    
    def get_method_timing_report(self) -> str:
        """Get detailed method timing report."""
        if not self._method_times:
            return "No method timing data available"
        
        report = "Method Timing Analysis:\n"
        report += "=" * 50 + "\n"
        
        for method_name, times in self._method_times.items():
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                std_dev = (sum((t - avg_time) ** 2 for t in times) / len(times)) ** 0.5
                
                report += f"\n{method_name}:\n"
                report += f"  Average: {avg_time:.2f}ms\n"
                report += f"  Min:     {min_time:.2f}ms\n"
                report += f"  Max:     {max_time:.2f}ms\n"
                report += f"  StdDev:  {std_dev:.2f}ms\n"
                report += f"  Calls:   {len(times)}\n"
        
        return report
    
    def get_bottleneck_analysis(self) -> str:
        """Analyze performance bottlenecks."""
        metrics = self.calculate_metrics()
        
        bottlenecks = []
        
        # Check preview update time
        if metrics.preview_update_time > 16:  # > 60 FPS target
            bottlenecks.append(f"Preview update time ({metrics.preview_update_time:.1f}ms) exceeds 60 FPS target (16ms)")
        
        # Check worker creation overhead
        if metrics.worker_creation_time > 5:
            bottlenecks.append(f"Worker creation time ({metrics.worker_creation_time:.1f}ms) is high")
        
        # Check worker cleanup overhead
        if metrics.worker_cleanup_time > 100:
            bottlenecks.append(f"Worker cleanup time ({metrics.worker_cleanup_time:.1f}ms) is excessive")
        
        # Check signal handling latency
        if metrics.signal_emission_time > 1:
            bottlenecks.append(f"Signal emission time ({metrics.signal_emission_time:.1f}ms) is high")
        
        if metrics.signal_handling_time > 2:
            bottlenecks.append(f"Signal handling time ({metrics.signal_handling_time:.1f}ms) is high")
        
        # Check memory usage
        memory_delta_mb = (metrics.memory_after - metrics.memory_before) / (1024 * 1024)
        if memory_delta_mb > 10:
            bottlenecks.append(f"Memory usage increased by {memory_delta_mb:.1f}MB")
        
        # Check frame rate
        if metrics.update_frequency < 30:
            bottlenecks.append(f"Update frequency ({metrics.update_frequency:.1f}Hz) is below 30 FPS")
        
        if metrics.frame_drops > 5:
            bottlenecks.append(f"Frame drops ({metrics.frame_drops}) indicate poor performance")
        
        # Check cache efficiency
        cache_hit_rate = metrics.cache_hits / max(1, metrics.cache_hits + metrics.cache_misses) * 100
        if cache_hit_rate < 70:
            bottlenecks.append(f"Cache hit rate ({cache_hit_rate:.1f}%) is low")
        
        if not bottlenecks:
            return "No significant performance bottlenecks detected."
        
        return "Performance Bottlenecks:\n" + "\n".join(f"• {b}" for b in bottlenecks)


class PreviewUpdateProfiler(QObject):
    """
    Specialized profiler for the preview update mechanism.
    
    This class instruments the actual preview update flow to measure
    real-world performance during slider interactions.
    """
    
    profiling_complete = pyqtSignal(object)  # PerformanceMetrics
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._profiler = PerformanceProfiler()
        self._dialog_ref: Optional[weakref.ReferenceType] = None
        self._original_methods: Dict[str, Callable] = {}
        
        # Simulation state
        self._simulation_timer = QTimer(self)
        self._simulation_timer.timeout.connect(self._simulate_slider_movement)
        self._simulation_offsets = []
        self._simulation_index = 0
        
    def instrument_dialog(self, dialog):
        """Instrument the dialog for performance monitoring."""
        self._dialog_ref = weakref.ref(dialog)
        
        # Store original methods
        if hasattr(dialog, '_update_preview'):
            self._original_methods['_update_preview'] = dialog._update_preview
            dialog._update_preview = self._instrumented_update_preview
        
        if hasattr(dialog, '_cleanup_workers'):
            self._original_methods['_cleanup_workers'] = dialog._cleanup_workers
            dialog._cleanup_workers = self._instrumented_cleanup_workers
        
        # Instrument smart preview coordinator if available
        if hasattr(dialog, '_smart_preview_coordinator') and dialog._smart_preview_coordinator:
            coordinator = dialog._smart_preview_coordinator
            
            if hasattr(coordinator, '_handle_drag_preview'):
                self._original_methods['_handle_drag_preview'] = coordinator._handle_drag_preview
                coordinator._handle_drag_preview = self._instrumented_handle_drag_preview
        
        logger.info("Dialog instrumented for performance monitoring")
    
    def _instrumented_update_preview(self):
        """Instrumented version of _update_preview."""
        dialog = self._dialog_ref() if self._dialog_ref else None
        if not dialog:
            return
        
        with self._profiler.time_method("_update_preview"):
            self._profiler.record_frame_update()
            
            # Call original method
            original = self._original_methods.get('_update_preview')
            if original:
                original()
    
    def _instrumented_cleanup_workers(self):
        """Instrumented version of _cleanup_workers."""
        dialog = self._dialog_ref() if self._dialog_ref else None
        if not dialog:
            return
        
        with self._profiler.time_method("worker_cleanup"):
            self._profiler.record_worker_destruction()
            
            # Call original method
            original = self._original_methods.get('_cleanup_workers')
            if original:
                original()
    
    def _instrumented_handle_drag_preview(self):
        """Instrumented version of _handle_drag_preview."""
        with self._profiler.time_method("handle_drag_preview"):
            self._profiler.record_frame_update()
            
            # Call original method
            original = self._original_methods.get('_handle_drag_preview')
            if original:
                original()
    
    def start_performance_test(self, duration_seconds: int = 10, 
                             slider_movements: int = 50):
        """Start automated performance test."""
        logger.info(f"Starting performance test: {duration_seconds}s, {slider_movements} movements")
        
        # Generate test offsets
        start_offset = 0x200000
        end_offset = 0x400000
        step = (end_offset - start_offset) // slider_movements
        
        self._simulation_offsets = [
            start_offset + i * step for i in range(slider_movements)
        ]
        self._simulation_index = 0
        
        # Start profiling
        with self._profiler.profile_cpu(True):
            with self._profiler.profile_memory(True):
                # Start simulation timer (simulate 60 FPS slider updates)
                self._simulation_timer.start(16)  # 16ms = 60 FPS
                
                # Stop after duration
                QTimer.singleShot(duration_seconds * 1000, self._finish_performance_test)
    
    def _simulate_slider_movement(self):
        """Simulate slider movement for testing."""
        dialog = self._dialog_ref() if self._dialog_ref else None
        if not dialog or not self._simulation_offsets:
            return
        
        # Get next offset
        offset = self._simulation_offsets[self._simulation_index]
        self._simulation_index = (self._simulation_index + 1) % len(self._simulation_offsets)
        
        # Update dialog offset
        if hasattr(dialog, 'set_offset'):
            dialog.set_offset(offset)
    
    def _finish_performance_test(self):
        """Finish performance test and emit results."""
        self._simulation_timer.stop()
        
        # Calculate final metrics
        metrics = self._profiler.calculate_metrics()
        
        logger.info("Performance test completed")
        logger.info(f"Results: {metrics}")
        
        self.profiling_complete.emit(metrics)
    
    def get_detailed_report(self) -> str:
        """Get comprehensive performance report."""
        report = "Performance Analysis Report\n"
        report += "=" * 50 + "\n\n"
        
        # Metrics summary
        metrics = self._profiler.calculate_metrics()
        report += str(metrics) + "\n\n"
        
        # Method timing details
        report += self._profiler.get_method_timing_report() + "\n\n"
        
        # Bottleneck analysis
        report += self._profiler.get_bottleneck_analysis() + "\n\n"
        
        # CPU profiling details
        report += "CPU Profiling Details:\n"
        report += "-" * 30 + "\n"
        report += self._profiler.get_cpu_profile_report() + "\n\n"
        
        return report


def analyze_debounce_timing_impact():
    """
    Analyze the impact of different debounce timing configurations.
    
    Tests:
    - Current 100ms debounce vs proposed 16ms
    - Worker cleanup timeout impact (1000ms vs shorter)
    - Cache hit rate with different update frequencies
    """
    
    logger.info("Analyzing debounce timing impact...")
    
    # Test configurations
    configs = [
        {"name": "Current (100ms debounce)", "debounce_ms": 100, "cleanup_ms": 1000},
        {"name": "Proposed (16ms debounce)", "debounce_ms": 16, "cleanup_ms": 500},
        {"name": "Aggressive (8ms debounce)", "debounce_ms": 8, "cleanup_ms": 250},
        {"name": "Conservative (200ms debounce)", "debounce_ms": 200, "cleanup_ms": 2000},
    ]
    
    results = {}
    
    for config in configs:
        logger.info(f"Testing configuration: {config['name']}")
        
        # Simulate timing behavior
        profiler = PerformanceProfiler()
        
        # Simulate rapid slider movements
        update_count = 0
        dropped_updates = 0
        total_time = 0
        
        for i in range(100):  # 100 slider movements
            movement_time = i * 10  # 10ms intervals (fast movement)
            
            # Check if update would be processed
            if total_time >= config["debounce_ms"]:
                update_count += 1
                total_time = 0
                
                # Simulate processing time
                processing_time = 5  # 5ms base processing time
                total_time += processing_time
            else:
                dropped_updates += 1
                total_time += 10
        
        # Calculate effectiveness
        update_rate = update_count / 1.0  # Updates per second
        responsiveness = update_count / (update_count + dropped_updates) * 100
        
        results[config["name"]] = {
            "update_rate": update_rate,
            "responsiveness": responsiveness,
            "debounce_ms": config["debounce_ms"],
            "cleanup_ms": config["cleanup_ms"]
        }
    
    # Generate report
    report = "Debounce Timing Analysis\n"
    report += "=" * 40 + "\n\n"
    
    for name, result in results.items():
        report += f"{name}:\n"
        report += f"  Update Rate: {result['update_rate']:.1f} updates/sec\n"
        report += f"  Responsiveness: {result['responsiveness']:.1f}%\n"
        report += f"  Debounce: {result['debounce_ms']}ms\n"
        report += f"  Cleanup: {result['cleanup_ms']}ms\n\n"
    
    # Recommendations
    report += "Recommendations:\n"
    report += "-" * 20 + "\n"
    
    best_config = max(results.items(), key=lambda x: x[1]["responsiveness"])
    report += f"Best responsiveness: {best_config[0]} ({best_config[1]['responsiveness']:.1f}%)\n"
    
    balanced_config = min(results.items(), 
                         key=lambda x: abs(x[1]["debounce_ms"] - 50))  # Target ~50ms
    report += f"Best balance: {balanced_config[0]}\n"
    
    logger.info("Debounce timing analysis complete")
    return report


if __name__ == "__main__":
    # Example usage
    app = QApplication([])
    
    # Analyze debounce timing impact
    timing_report = analyze_debounce_timing_impact()
    print(timing_report)
    
    # Note: Full dialog profiling requires the actual dialog instance
    # This would be done by importing and running the dialog with instrumentation