"""
Manual Offset Dialog Performance Profiler

This profiler comprehensively analyzes the performance of the manual offset dialog
preview system to identify bottlenecks causing black box displays instead of sprites.

Performance measurement stages:
1. Slider signal emission timing
2. SmartPreviewCoordinator debounce/timing delays  
3. Worker pool request processing
4. Sprite data extraction performance
5. Signal delivery to preview widget
6. Widget rendering and display timing
7. Cache effectiveness analysis
8. Memory usage patterns
9. Thread contention detection

Focus areas for black box issues:
- Timing problems causing stale data display
- Memory issues during rapid updates
- CPU bottlenecks during slider movement
- Cache misses and inefficient data retrieval
- Thread synchronization delays
- Widget update failures
"""

import contextlib
import gc
import os
import statistics
import sys
import threading
import time
import traceback
import weakref
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

from utils.logging_config import get_logger

logger = get_logger(__name__)


class PerformanceStage(Enum):
    """Performance measurement stages in the preview pipeline."""
    SLIDER_SIGNAL = auto()
    COORDINATOR_DEBOUNCE = auto()
    WORKER_POOL_QUEUE = auto() 
    SPRITE_EXTRACTION = auto()
    SIGNAL_DELIVERY = auto()
    WIDGET_RENDERING = auto()
    CACHE_ACCESS = auto()
    MEMORY_ALLOCATION = auto()


class EventType(Enum):
    """Types of performance events to track."""
    START = auto()
    END = auto()
    CACHE_HIT = auto()
    CACHE_MISS = auto()
    ERROR = auto()
    WARNING = auto()
    BOTTLENECK = auto()


@dataclass
class PerformanceEvent:
    """Individual performance measurement event."""
    timestamp: float
    stage: PerformanceStage
    event_type: EventType
    offset: int
    duration_ms: Optional[float] = None
    memory_bytes: Optional[int] = None
    thread_id: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StageStatistics:
    """Statistical analysis for a performance stage."""
    stage: PerformanceStage
    total_events: int
    avg_duration_ms: float
    median_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    min_duration_ms: float
    max_duration_ms: float
    error_count: int
    cache_hit_rate: float
    memory_peak_mb: float
    thread_contention_count: int


@dataclass
class BlackBoxAnalysis:
    """Analysis of potential black box root causes."""
    timing_issues: List[str]
    memory_issues: List[str]  
    cache_issues: List[str]
    thread_issues: List[str]
    widget_issues: List[str]
    likely_root_cause: str
    confidence_score: float
    recommendations: List[str]


class PerformanceProfiler(QObject):
    """
    Comprehensive performance profiler for manual offset dialog preview system.
    
    This profiler instruments the entire preview pipeline from slider movement
    to final widget display, measuring timing, memory usage, and identifying
    bottlenecks that could cause black box issues.
    """
    
    # Signals for real-time monitoring
    performance_alert = pyqtSignal(str, float)  # message, severity
    bottleneck_detected = pyqtSignal(PerformanceStage, float)  # stage, duration_ms
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        # Event storage
        self._events: deque[PerformanceEvent] = deque(maxlen=10000)
        self._stage_timers: Dict[Tuple[PerformanceStage, int], float] = {}
        
        # Performance thresholds (ms)
        self._thresholds = {
            PerformanceStage.SLIDER_SIGNAL: 5.0,      # Slider should be very fast
            PerformanceStage.COORDINATOR_DEBOUNCE: 20.0,  # 60fps = 16ms
            PerformanceStage.WORKER_POOL_QUEUE: 10.0,   # Queue operations should be fast
            PerformanceStage.SPRITE_EXTRACTION: 100.0,  # Data extraction
            PerformanceStage.SIGNAL_DELIVERY: 5.0,     # Qt signals should be fast
            PerformanceStage.WIDGET_RENDERING: 16.0,   # 60fps rendering
            PerformanceStage.CACHE_ACCESS: 2.0,       # Memory cache should be instant
            PerformanceStage.MEMORY_ALLOCATION: 10.0,  # Memory ops
        }
        
        # Memory tracking
        self._memory_baseline = 0
        self._peak_memory = 0
        self._gc_count_start = 0
        
        # Thread monitoring
        self._thread_contentions = defaultdict(int)
        self._active_threads = set()
        
        # Cache analysis
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'memory_cache_hits': 0,
            'rom_cache_hits': 0
        }
        
        # Real-time analysis
        self._analysis_timer = QTimer(self)
        self._analysis_timer.timeout.connect(self._analyze_real_time_performance)
        self._analysis_timer.start(1000)  # Analyze every second
        
        # Instrumented objects
        self._instrumented_objects: List[Any] = []
        
        logger.info("PerformanceProfiler initialized with comprehensive monitoring")
    
    def start_profiling(self) -> None:
        """Start comprehensive performance profiling."""
        logger.info("Starting manual offset dialog performance profiling")
        
        # Reset all metrics
        self._events.clear()
        self._stage_timers.clear()
        self._thread_contentions.clear()
        self._active_threads.clear()
        
        # Establish memory baseline
        gc.collect()  # Force garbage collection for clean baseline
        self._memory_baseline = self._get_memory_usage()
        self._peak_memory = self._memory_baseline
        self._gc_count_start = len(gc.get_objects())
        
        logger.info(f"Profiling baseline: {self._memory_baseline:.1f}MB memory, {self._gc_count_start} objects")
    
    def stop_profiling(self) -> Tuple[Dict[PerformanceStage, StageStatistics], BlackBoxAnalysis]:
        """Stop profiling and return comprehensive analysis."""
        self._analysis_timer.stop()
        
        # Final memory check
        gc.collect()
        final_memory = self._get_memory_usage()
        final_gc_count = len(gc.get_objects())
        
        logger.info(f"Profiling complete: {final_memory:.1f}MB memory (+{final_memory-self._memory_baseline:.1f}MB), "
                   f"{final_gc_count} objects (+{final_gc_count-self._gc_count_start})")
        
        # Generate comprehensive analysis
        stage_stats = self._calculate_stage_statistics()
        black_box_analysis = self._analyze_black_box_issues()
        
        return stage_stats, black_box_analysis
    
    def instrument_dialog(self, dialog) -> None:
        """Instrument manual offset dialog for performance monitoring."""
        logger.info(f"Instrumenting manual offset dialog: {type(dialog).__name__}")
        
        try:
            # Instrument slider signals
            if hasattr(dialog, 'browse_tab') and dialog.browse_tab:
                self._instrument_slider(dialog.browse_tab.position_slider)
            
            # Instrument SmartPreviewCoordinator
            if hasattr(dialog, '_smart_preview_coordinator') and dialog._smart_preview_coordinator:
                self._instrument_coordinator(dialog._smart_preview_coordinator)
            
            # Instrument preview widget
            if hasattr(dialog, 'preview_widget') and dialog.preview_widget:
                self._instrument_preview_widget(dialog.preview_widget)
                
            self._instrumented_objects.append(weakref.ref(dialog))
            
        except Exception as e:
            logger.error(f"Error instrumenting dialog: {e}")
    
    def _instrument_slider(self, slider) -> None:
        """Instrument slider for signal timing measurement."""
        logger.debug("Instrumenting slider signals")
        
        # Wrap slider signals with timing measurement
        original_value_changed = slider.valueChanged
        original_slider_moved = slider.sliderMoved
        original_slider_pressed = slider.sliderPressed
        original_slider_released = slider.sliderReleased
        
        def timed_value_changed(value):
            self.start_stage(PerformanceStage.SLIDER_SIGNAL, value)
            try:
                original_value_changed.emit(value)
            finally:
                self.end_stage(PerformanceStage.SLIDER_SIGNAL, value)
        
        def timed_slider_moved(value):
            self.start_stage(PerformanceStage.SLIDER_SIGNAL, value, {'event': 'sliderMoved'})
            try:
                original_slider_moved.emit(value)
            finally:
                self.end_stage(PerformanceStage.SLIDER_SIGNAL, value)
        
        def timed_slider_pressed():
            self.start_stage(PerformanceStage.SLIDER_SIGNAL, 0, {'event': 'sliderPressed'})
            try:
                original_slider_pressed.emit()
            finally:
                self.end_stage(PerformanceStage.SLIDER_SIGNAL, 0)
        
        def timed_slider_released():
            self.start_stage(PerformanceStage.SLIDER_SIGNAL, 0, {'event': 'sliderReleased'})
            try:
                original_slider_released.emit()
            finally:
                self.end_stage(PerformanceStage.SLIDER_SIGNAL, 0)
        
        # Replace the signal emission methods
        slider.valueChanged = type(original_value_changed)(timed_value_changed)
        slider.sliderMoved = type(original_slider_moved)(timed_slider_moved)
        slider.sliderPressed = type(original_slider_pressed)(timed_slider_pressed)  
        slider.sliderReleased = type(original_slider_released)(timed_slider_released)
    
    def _instrument_coordinator(self, coordinator) -> None:
        """Instrument SmartPreviewCoordinator for timing analysis."""
        logger.debug("Instrumenting SmartPreviewCoordinator")
        
        # Wrap key methods with performance measurement
        original_request_preview = coordinator.request_preview
        original_handle_drag_preview = coordinator._handle_drag_preview
        original_handle_release_preview = coordinator._handle_release_preview
        original_try_show_cached = coordinator._try_show_cached_preview_dual_tier
        
        def timed_request_preview(offset: int, priority: int = 0):
            self.start_stage(PerformanceStage.COORDINATOR_DEBOUNCE, offset, {'priority': priority})
            try:
                return original_request_preview(offset, priority)
            finally:
                self.end_stage(PerformanceStage.COORDINATOR_DEBOUNCE, offset)
        
        def timed_handle_drag_preview():
            current_offset = getattr(coordinator, '_current_offset', 0)
            self.start_stage(PerformanceStage.COORDINATOR_DEBOUNCE, current_offset, {'type': 'drag'})
            try:
                return original_handle_drag_preview()
            finally:
                self.end_stage(PerformanceStage.COORDINATOR_DEBOUNCE, current_offset)
        
        def timed_handle_release_preview():
            current_offset = getattr(coordinator, '_current_offset', 0)
            self.start_stage(PerformanceStage.COORDINATOR_DEBOUNCE, current_offset, {'type': 'release'})
            try:
                return original_handle_release_preview()
            finally:
                self.end_stage(PerformanceStage.COORDINATOR_DEBOUNCE, current_offset)
        
        def timed_try_show_cached():
            current_offset = getattr(coordinator, '_current_offset', 0)
            self.start_stage(PerformanceStage.CACHE_ACCESS, current_offset)
            try:
                result = original_try_show_cached()
                if result:
                    self._record_event(PerformanceStage.CACHE_ACCESS, EventType.CACHE_HIT, current_offset)
                else:
                    self._record_event(PerformanceStage.CACHE_ACCESS, EventType.CACHE_MISS, current_offset)
                return result
            finally:
                self.end_stage(PerformanceStage.CACHE_ACCESS, current_offset)
        
        # Replace methods with instrumented versions
        coordinator.request_preview = timed_request_preview
        coordinator._handle_drag_preview = timed_handle_drag_preview
        coordinator._handle_release_preview = timed_handle_release_preview
        coordinator._try_show_cached_preview_dual_tier = timed_try_show_cached
        
        # Also instrument worker pool if available
        if hasattr(coordinator, '_worker_pool') and coordinator._worker_pool:
            self._instrument_worker_pool(coordinator._worker_pool)
    
    def _instrument_worker_pool(self, worker_pool) -> None:
        """Instrument PreviewWorkerPool for request processing analysis."""
        logger.debug("Instrumenting PreviewWorkerPool")
        
        original_submit_request = worker_pool.submit_request
        
        def timed_submit_request(request, extractor, rom_cache=None):
            self.start_stage(PerformanceStage.WORKER_POOL_QUEUE, request.offset, 
                           {'request_id': request.request_id, 'priority': request.priority})
            try:
                # Also track sprite extraction timing
                self._track_sprite_extraction(request, extractor)
                return original_submit_request(request, extractor, rom_cache)
            finally:
                self.end_stage(PerformanceStage.WORKER_POOL_QUEUE, request.offset)
        
        worker_pool.submit_request = timed_submit_request
    
    def _track_sprite_extraction(self, request, extractor) -> None:
        """Track sprite data extraction performance."""
        if not extractor:
            return
            
        # We'll instrument the worker's run method to track extraction time
        # This is more complex since it happens in a separate thread
        def track_extraction_start():
            self.start_stage(PerformanceStage.SPRITE_EXTRACTION, request.offset, 
                           {'request_id': request.request_id})
        
        def track_extraction_end():
            self.end_stage(PerformanceStage.SPRITE_EXTRACTION, request.offset)
        
        # Store callbacks for the worker to use
        request._profiler_start = track_extraction_start
        request._profiler_end = track_extraction_end
    
    def _instrument_preview_widget(self, widget) -> None:
        """Instrument SpritePreviewWidget for rendering performance."""
        logger.debug("Instrumenting SpritePreviewWidget")
        
        original_load_sprite = widget.load_sprite_from_4bpp
        original_set_pixmap = widget.preview_label.setPixmap if widget.preview_label else None
        
        def timed_load_sprite(tile_data: bytes, width: int = 128, height: int = 128, 
                            sprite_name: Optional[str] = None):
            offset = getattr(widget, 'current_offset', 0)
            self.start_stage(PerformanceStage.WIDGET_RENDERING, offset,
                           {'data_size': len(tile_data) if tile_data else 0,
                            'dimensions': f'{width}x{height}',
                            'sprite_name': sprite_name})
            try:
                return original_load_sprite(tile_data, width, height, sprite_name)
            finally:
                self.end_stage(PerformanceStage.WIDGET_RENDERING, offset)
        
        if original_set_pixmap:
            def timed_set_pixmap(pixmap):
                self.start_stage(PerformanceStage.WIDGET_RENDERING, 0, {'operation': 'setPixmap'})
                try:
                    return original_set_pixmap(pixmap)
                finally:
                    self.end_stage(PerformanceStage.WIDGET_RENDERING, 0)
            
            widget.preview_label.setPixmap = timed_set_pixmap
        
        widget.load_sprite_from_4bpp = timed_load_sprite
    
    def start_stage(self, stage: PerformanceStage, offset: int, details: Optional[Dict[str, Any]] = None) -> None:
        """Start timing a performance stage."""
        key = (stage, offset)
        current_time = time.perf_counter()
        
        # Check if we already have a timer running for this stage/offset
        if key in self._stage_timers:
            # Log potential timing issue
            previous_start = self._stage_timers[key]
            logger.warning(f"Stage {stage.name} for offset 0x{offset:06X} started again before ending "
                         f"(previous start: {current_time - previous_start:.1f}ms ago)")
        
        self._stage_timers[key] = current_time
        
        # Record start event
        self._record_event(stage, EventType.START, offset, details=details or {})
        
        # Track memory usage
        current_memory = self._get_memory_usage()
        if current_memory > self._peak_memory:
            self._peak_memory = current_memory
        
        # Track thread activity
        thread_id = threading.get_ident()
        self._active_threads.add(thread_id)
    
    def end_stage(self, stage: PerformanceStage, offset: int, details: Optional[Dict[str, Any]] = None) -> None:
        """End timing a performance stage."""
        key = (stage, offset)
        end_time = time.perf_counter()
        
        if key in self._stage_timers:
            start_time = self._stage_timers.pop(key)
            duration_ms = (end_time - start_time) * 1000
            
            # Check for bottlenecks
            threshold = self._thresholds.get(stage, 50.0)
            if duration_ms > threshold:
                self._record_event(stage, EventType.BOTTLENECK, offset, duration_ms, 
                                 details={**(details or {}), 'threshold_ms': threshold})
                self.bottleneck_detected.emit(stage, duration_ms)
                logger.warning(f"Performance bottleneck: {stage.name} took {duration_ms:.1f}ms "
                             f"(threshold: {threshold:.1f}ms) for offset 0x{offset:06X}")
            
            # Record end event
            self._record_event(stage, EventType.END, offset, duration_ms, details=details or {})
        else:
            logger.warning(f"End stage called for {stage.name} offset 0x{offset:06X} without matching start")
    
    def _record_event(self, stage: PerformanceStage, event_type: EventType, offset: int, 
                     duration_ms: Optional[float] = None, details: Optional[Dict[str, Any]] = None) -> None:
        """Record a performance event."""
        event = PerformanceEvent(
            timestamp=time.perf_counter(),
            stage=stage,
            event_type=event_type,
            offset=offset,
            duration_ms=duration_ms,
            memory_bytes=self._get_memory_usage_bytes(),
            thread_id=threading.get_ident(),
            details=details or {}
        )
        
        self._events.append(event)
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            # Fallback to gc object count as memory proxy
            return len(gc.get_objects()) / 1000.0
    
    def _get_memory_usage_bytes(self) -> int:
        """Get current memory usage in bytes."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except ImportError:
            return len(gc.get_objects()) * 100  # Rough approximation
    
    def _analyze_real_time_performance(self) -> None:
        """Analyze performance in real-time and emit alerts."""
        if len(self._events) < 10:
            return
        
        # Analyze recent events (last 5 seconds)
        recent_time = time.perf_counter() - 5.0
        recent_events = [e for e in self._events if e.timestamp > recent_time]
        
        if not recent_events:
            return
        
        # Check for excessive bottlenecks
        bottlenecks = [e for e in recent_events if e.event_type == EventType.BOTTLENECK]
        if len(bottlenecks) > 5:  # More than 5 bottlenecks in 5 seconds
            severity = len(bottlenecks) / 10.0  # Scale 0-1
            self.performance_alert.emit(
                f"High bottleneck frequency: {len(bottlenecks)} in 5s", severity)
        
        # Check for memory growth
        if len(recent_events) > 5:
            memory_trend = [e.memory_bytes for e in recent_events[-5:] if e.memory_bytes]
            if len(memory_trend) >= 5 and memory_trend[-1] > memory_trend[0] * 1.1:
                growth_mb = (memory_trend[-1] - memory_trend[0]) / 1024 / 1024
                self.performance_alert.emit(
                    f"Memory growth detected: +{growth_mb:.1f}MB", 0.7)
        
        # Check for cache miss patterns
        cache_events = [e for e in recent_events if e.stage == PerformanceStage.CACHE_ACCESS]
        if len(cache_events) > 10:
            cache_misses = len([e for e in cache_events if e.event_type == EventType.CACHE_MISS])
            miss_rate = cache_misses / len(cache_events)
            if miss_rate > 0.8:  # >80% cache miss rate
                self.performance_alert.emit(
                    f"High cache miss rate: {miss_rate*100:.1f}%", 0.8)
    
    def _calculate_stage_statistics(self) -> Dict[PerformanceStage, StageStatistics]:
        """Calculate comprehensive statistics for each performance stage."""
        stage_stats = {}
        
        for stage in PerformanceStage:
            stage_events = [e for e in self._events if e.stage == stage]
            if not stage_events:
                continue
            
            # Calculate timing statistics
            durations = [e.duration_ms for e in stage_events 
                        if e.duration_ms is not None and e.event_type == EventType.END]
            
            if durations:
                avg_duration = statistics.mean(durations)
                median_duration = statistics.median(durations)
                p95_duration = self._percentile(durations, 95)
                p99_duration = self._percentile(durations, 99)
                min_duration = min(durations)
                max_duration = max(durations)
            else:
                avg_duration = median_duration = p95_duration = p99_duration = 0
                min_duration = max_duration = 0
            
            # Calculate error and cache statistics
            error_count = len([e for e in stage_events if e.event_type == EventType.ERROR])
            cache_hits = len([e for e in stage_events if e.event_type == EventType.CACHE_HIT])
            cache_misses = len([e for e in stage_events if e.event_type == EventType.CACHE_MISS])
            total_cache_attempts = cache_hits + cache_misses
            cache_hit_rate = cache_hits / total_cache_attempts if total_cache_attempts > 0 else 0
            
            # Calculate memory statistics
            memory_values = [e.memory_bytes for e in stage_events if e.memory_bytes is not None]
            memory_peak_mb = max(memory_values) / 1024 / 1024 if memory_values else 0
            
            # Calculate thread contention
            thread_contention_count = sum(self._thread_contentions.values())
            
            stage_stats[stage] = StageStatistics(
                stage=stage,
                total_events=len(stage_events),
                avg_duration_ms=avg_duration,
                median_duration_ms=median_duration,
                p95_duration_ms=p95_duration,
                p99_duration_ms=p99_duration,
                min_duration_ms=min_duration,
                max_duration_ms=max_duration,
                error_count=error_count,
                cache_hit_rate=cache_hit_rate,
                memory_peak_mb=memory_peak_mb,
                thread_contention_count=thread_contention_count
            )
        
        return stage_stats
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value from data."""
        if not data:
            return 0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = k - f
        if f == len(sorted_data) - 1:
            return sorted_data[f]
        return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c
    
    def _analyze_black_box_issues(self) -> BlackBoxAnalysis:
        """Analyze potential root causes of black box display issues."""
        timing_issues = []
        memory_issues = []
        cache_issues = []
        thread_issues = []
        widget_issues = []
        
        # Analyze timing patterns
        widget_events = [e for e in self._events if e.stage == PerformanceStage.WIDGET_RENDERING]
        if widget_events:
            slow_renders = [e for e in widget_events if e.duration_ms and e.duration_ms > 50]
            if slow_renders:
                timing_issues.append(f"Slow widget rendering detected: {len(slow_renders)} events >50ms")
        
        # Check for excessive debounce delays
        coordinator_events = [e for e in self._events if e.stage == PerformanceStage.COORDINATOR_DEBOUNCE]
        if coordinator_events:
            long_delays = [e for e in coordinator_events if e.duration_ms and e.duration_ms > 200]
            if long_delays:
                timing_issues.append(f"Excessive coordinator delays: {len(long_delays)} events >200ms")
        
        # Analyze memory patterns
        memory_events = [e for e in self._events if e.memory_bytes is not None]
        if len(memory_events) > 10:
            memory_growth = memory_events[-1].memory_bytes - memory_events[0].memory_bytes
            if memory_growth > 50 * 1024 * 1024:  # >50MB growth
                memory_issues.append(f"Significant memory growth: +{memory_growth/1024/1024:.1f}MB")
        
        # Analyze cache effectiveness
        cache_events = [e for e in self._events if e.stage == PerformanceStage.CACHE_ACCESS]
        if cache_events:
            cache_misses = len([e for e in cache_events if e.event_type == EventType.CACHE_MISS])
            cache_hits = len([e for e in cache_events if e.event_type == EventType.CACHE_HIT])
            if cache_misses > cache_hits * 2:  # More than 2x misses vs hits
                cache_issues.append(f"Poor cache performance: {cache_misses} misses vs {cache_hits} hits")
        
        # Analyze thread contention
        if self._thread_contentions:
            max_contention = max(self._thread_contentions.values())
            if max_contention > 5:
                thread_issues.append(f"High thread contention detected: {max_contention} conflicts")
        
        # Analyze widget update failures
        widget_errors = [e for e in widget_events if e.event_type == EventType.ERROR]
        if widget_errors:
            widget_issues.append(f"Widget update errors: {len(widget_errors)} failures")
        
        # Determine likely root cause and confidence
        all_issues = timing_issues + memory_issues + cache_issues + thread_issues + widget_issues
        
        # Confidence scoring based on issue patterns
        confidence_factors = []
        likely_root_cause = "Unknown - insufficient data"
        
        if timing_issues and widget_issues:
            confidence_factors.append(0.9)
            likely_root_cause = "Widget rendering performance bottlenecks causing display failures"
        elif cache_issues and timing_issues:
            confidence_factors.append(0.8)
            likely_root_cause = "Cache inefficiency causing stale data display (black boxes)"
        elif memory_issues and timing_issues:
            confidence_factors.append(0.7)
            likely_root_cause = "Memory pressure causing garbage collection pauses and display lag"
        elif thread_issues:
            confidence_factors.append(0.6)
            likely_root_cause = "Thread synchronization issues causing preview update delays"
        elif timing_issues:
            confidence_factors.append(0.5)
            likely_root_cause = "General performance bottlenecks in preview pipeline"
        
        confidence_score = max(confidence_factors) if confidence_factors else 0.0
        
        # Generate recommendations
        recommendations = []
        if timing_issues:
            recommendations.append("Optimize slow operations identified in timing analysis")
        if cache_issues:
            recommendations.append("Improve cache hit rate and reduce redundant data retrieval")
        if memory_issues:
            recommendations.append("Investigate memory leaks and optimize memory usage patterns")
        if widget_issues:
            recommendations.append("Add better error handling and retry logic for widget updates")
        if thread_issues:
            recommendations.append("Review thread synchronization and reduce contention points")
        
        # Always recommend comprehensive monitoring
        recommendations.append("Continue performance monitoring during user interaction testing")
        
        return BlackBoxAnalysis(
            timing_issues=timing_issues,
            memory_issues=memory_issues,
            cache_issues=cache_issues,
            thread_issues=thread_issues,
            widget_issues=widget_issues,
            likely_root_cause=likely_root_cause,
            confidence_score=confidence_score,
            recommendations=recommendations
        )
    
    def generate_report(self, stage_stats: Dict[PerformanceStage, StageStatistics], 
                       black_box_analysis: BlackBoxAnalysis) -> str:
        """Generate comprehensive performance report."""
        report_lines = [
            "=" * 80,
            "MANUAL OFFSET DIALOG PERFORMANCE ANALYSIS REPORT",
            "=" * 80,
            "",
            f"Analysis Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Events Recorded: {len(self._events)}",
            f"Memory Baseline: {self._memory_baseline:.1f}MB",
            f"Peak Memory: {self._peak_memory:.1f}MB",
            f"Memory Growth: +{self._peak_memory - self._memory_baseline:.1f}MB",
            f"Active Threads: {len(self._active_threads)}",
            "",
            "STAGE PERFORMANCE ANALYSIS",
            "-" * 40,
        ]
        
        for stage, stats in stage_stats.items():
            report_lines.extend([
                f"",
                f"{stage.name}:",
                f"  Total Events: {stats.total_events}",
                f"  Average Duration: {stats.avg_duration_ms:.2f}ms",
                f"  Median Duration: {stats.median_duration_ms:.2f}ms", 
                f"  95th Percentile: {stats.p95_duration_ms:.2f}ms",
                f"  99th Percentile: {stats.p99_duration_ms:.2f}ms",
                f"  Min/Max Duration: {stats.min_duration_ms:.2f}ms / {stats.max_duration_ms:.2f}ms",
                f"  Error Count: {stats.error_count}",
                f"  Cache Hit Rate: {stats.cache_hit_rate*100:.1f}%",
                f"  Peak Memory: {stats.memory_peak_mb:.1f}MB",
                f"  Thread Contention: {stats.thread_contention_count}",
            ])
        
        report_lines.extend([
            "",
            "BLACK BOX ISSUE ANALYSIS",
            "-" * 40,
            f"Root Cause (Confidence: {black_box_analysis.confidence_score*100:.1f}%): {black_box_analysis.likely_root_cause}",
            "",
        ])
        
        if black_box_analysis.timing_issues:
            report_lines.extend(["TIMING ISSUES:"] + [f"  • {issue}" for issue in black_box_analysis.timing_issues] + [""])
        
        if black_box_analysis.memory_issues:
            report_lines.extend(["MEMORY ISSUES:"] + [f"  • {issue}" for issue in black_box_analysis.memory_issues] + [""])
        
        if black_box_analysis.cache_issues:
            report_lines.extend(["CACHE ISSUES:"] + [f"  • {issue}" for issue in black_box_analysis.cache_issues] + [""])
        
        if black_box_analysis.thread_issues:
            report_lines.extend(["THREAD ISSUES:"] + [f"  • {issue}" for issue in black_box_analysis.thread_issues] + [""])
        
        if black_box_analysis.widget_issues:
            report_lines.extend(["WIDGET ISSUES:"] + [f"  • {issue}" for issue in black_box_analysis.widget_issues] + [""])
        
        report_lines.extend([
            "RECOMMENDATIONS:",
        ] + [f"  • {rec}" for rec in black_box_analysis.recommendations] + [
            "",
            "=" * 80
        ])
        
        return "\n".join(report_lines)
    
    def export_detailed_data(self, filepath: str) -> None:
        """Export detailed performance data for further analysis."""
        import json
        
        export_data = {
            'metadata': {
                'export_time': time.time(),
                'total_events': len(self._events),
                'memory_baseline_mb': self._memory_baseline,
                'peak_memory_mb': self._peak_memory,
                'active_threads': len(self._active_threads),
            },
            'events': []
        }
        
        for event in self._events:
            export_data['events'].append({
                'timestamp': event.timestamp,
                'stage': event.stage.name,
                'event_type': event.event_type.name,
                'offset': f"0x{event.offset:06X}",
                'duration_ms': event.duration_ms,
                'memory_bytes': event.memory_bytes,
                'thread_id': event.thread_id,
                'details': event.details
            })
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Detailed performance data exported to {filepath}")
    
    def cleanup(self) -> None:
        """Clean up profiler resources."""
        if self._analysis_timer.isActive():
            self._analysis_timer.stop()
        
        # Clear instrumented object references
        self._instrumented_objects.clear()
        
        logger.info("PerformanceProfiler cleaned up")


def create_performance_test_suite(dialog) -> Tuple[PerformanceProfiler, Callable[[], Tuple[Dict, BlackBoxAnalysis]]]:
    """
    Create a complete performance test suite for the manual offset dialog.
    
    Returns:
        - Configured performance profiler
        - Function to run tests and get results
    """
    profiler = PerformanceProfiler()
    
    def run_performance_tests() -> Tuple[Dict, BlackBoxAnalysis]:
        """Run comprehensive performance tests."""
        logger.info("Starting comprehensive manual offset dialog performance tests")
        
        profiler.start_profiling()
        profiler.instrument_dialog(dialog)
        
        # Simulate user interactions for testing
        test_offsets = [0x200000, 0x250000, 0x300000, 0x350000, 0x400000]
        
        try:
            # Test rapid slider movements (simulates dragging)
            logger.info("Testing rapid slider movements...")
            for offset in test_offsets:
                if hasattr(dialog, 'set_offset'):
                    dialog.set_offset(offset)
                    time.sleep(0.05)  # 50ms between updates (20fps)
            
            # Test slower movements (simulates careful navigation)
            logger.info("Testing careful navigation...")
            for offset in test_offsets:
                if hasattr(dialog, 'set_offset'):
                    dialog.set_offset(offset)
                    time.sleep(0.2)  # 200ms between updates
            
            # Allow time for final operations to complete
            time.sleep(1.0)
            
        except Exception as e:
            logger.error(f"Error during performance testing: {e}")
        
        # Stop profiling and get analysis
        stage_stats, black_box_analysis = profiler.stop_profiling()
        
        return stage_stats, black_box_analysis
    
    return profiler, run_performance_tests


if __name__ == "__main__":
    # Example usage for testing the profiler itself
    app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
    
    # Create a mock profiler for testing
    profiler = PerformanceProfiler()
    
    # Simulate some performance events
    for i in range(10):
        profiler.start_stage(PerformanceStage.SLIDER_SIGNAL, 0x200000 + i * 0x1000)
        time.sleep(0.001 * i)  # Variable delays
        profiler.end_stage(PerformanceStage.SLIDER_SIGNAL, 0x200000 + i * 0x1000)
    
    # Generate test analysis
    stage_stats, analysis = profiler.stop_profiling()
    report = profiler.generate_report(stage_stats, analysis)
    
    print(report)
    print(f"\nDetailed data would be exported to: performance_data_{int(time.time())}.json")
    
    profiler.cleanup()