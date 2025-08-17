"""
Memory leak profiler utilities for SpritePal.

Provides tools for detecting memory leaks and monitoring memory usage
during dialog testing and application lifecycle.
"""

from __future__ import annotations

import gc
import os
import weakref
from typing import Any

import psutil


class MemoryMonitor:
    """Monitor memory usage for leak detection."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.initial_memory = None
        self.peak_memory = 0
        self.measurements = []

    def start(self):
        """Start monitoring memory."""
        gc.collect()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.initial_memory
        self.measurements = [self.initial_memory]

    def measure(self):
        """Take a memory measurement."""
        gc.collect()
        current = self.process.memory_info().rss / 1024 / 1024  # MB
        self.measurements.append(current)
        self.peak_memory = max(self.peak_memory, current)
        return current

    def get_increase(self) -> float:
        """Get memory increase from start."""
        if not self.initial_memory:
            return 0
        current = self.measure()
        return current - self.initial_memory

    def assert_no_leak(self, max_increase_mb: float = 10.0):
        """Assert no significant memory leak."""
        increase = self.get_increase()
        assert increase < max_increase_mb, (
            f"Memory leak detected: {increase:.2f}MB increase "
            f"(initial: {self.initial_memory:.2f}MB, current: {self.measurements[-1]:.2f}MB)"
        )


class WeakrefTracker:
    """Track object lifecycle using weakrefs."""

    def __init__(self):
        self.refs = []

    def track(self, obj: Any) -> weakref.ref:
        """Track an object with a weakref."""
        ref = weakref.ref(obj)
        self.refs.append(ref)
        return ref

    def assert_all_deleted(self):
        """Assert all tracked objects have been deleted."""
        gc.collect()
        alive = [ref for ref in self.refs if ref() is not None]
        assert not alive, f"{len(alive)} objects still alive"

    def get_alive_count(self) -> int:
        """Get count of still-alive objects."""
        gc.collect()
        return sum(1 for ref in self.refs if ref() is not None)


class MemoryLeakProfiler:
    """Combined memory profiler for dialog leak detection."""

    def __init__(self):
        self.memory_monitor = MemoryMonitor()
        self.weakref_tracker = WeakrefTracker()

    def start_profiling(self):
        """Start memory profiling session."""
        self.memory_monitor.start()

    def track_object(self, obj: Any) -> weakref.ref:
        """Track an object for lifecycle monitoring."""
        return self.weakref_tracker.track(obj)

    def measure_memory(self) -> float:
        """Take a memory measurement."""
        return self.memory_monitor.measure()

    def check_for_leaks(self, max_memory_increase_mb: float = 10.0) -> dict[str, Any]:
        """Check for memory leaks and object lifecycle issues."""
        results = {
            "memory_increase_mb": self.memory_monitor.get_increase(),
            "alive_objects": self.weakref_tracker.get_alive_count(),
            "peak_memory_mb": self.memory_monitor.peak_memory,
            "measurements": self.memory_monitor.measurements[-5:],  # Last 5 measurements
        }

        # Check for memory leaks
        if results["memory_increase_mb"] > max_memory_increase_mb:
            results["memory_leak_detected"] = True
        else:
            results["memory_leak_detected"] = False

        return results

    def assert_no_leaks(self, max_memory_increase_mb: float = 10.0):
        """Assert no memory leaks detected."""
        self.memory_monitor.assert_no_leak(max_memory_increase_mb)
        self.weakref_tracker.assert_all_deleted()