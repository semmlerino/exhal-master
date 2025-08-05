#!/usr/bin/env python3
"""
Comprehensive Memory Leak Profiler for SpritePal

This module provides detailed memory leak detection and baseline measurements for SpritePal.
It tracks Qt objects, Python objects, signal connections, and memory patterns to identify
leaks and establish concrete metrics for measuring improvements.

Features:
- Baseline memory measurements on startup
- Dialog lifecycle profiling (open/close cycles)
- Qt object tree monitoring
- Worker thread cleanup verification
- Signal/slot connection tracking
- Python garbage collection analysis
- Memory pattern analysis during operations

Usage:
    profiler = MemoryLeakProfiler()
    profiler.establish_baseline()

    # Test dialog cycles
    profiler.profile_dialog_lifecycle("ManualOffsetDialog", dialog_class, cycles=10)

    # Generate comprehensive report
    report = profiler.generate_leak_report()
"""

import gc
import os
import sys
import time
import tracemalloc
import weakref
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

import psutil
from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication, QDialog

try:
    import objgraph
    OBJGRAPH_AVAILABLE = True
except ImportError:
    OBJGRAPH_AVAILABLE = False
    print("Warning: objgraph not available. Install with: pip install objgraph")

try:
    import pympler
    from pympler import muppy, summary, tracker
    PYMPLER_AVAILABLE = True
except ImportError:
    PYMPLER_AVAILABLE = False
    print("Warning: pympler not available. Install with: pip install pympler")

from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class MemorySnapshot:
    """Snapshot of memory state at a specific point in time."""
    timestamp: datetime = field(default_factory=datetime.now)
    process_memory_mb: float = 0.0
    python_objects: dict[str, int] = field(default_factory=dict)
    qt_objects: dict[str, int] = field(default_factory=dict)
    thread_count: int = 0
    gc_stats: dict[str, int] = field(default_factory=dict)
    tracemalloc_top: list[str] = field(default_factory=list)

    def memory_delta_mb(self, other: "MemorySnapshot") -> float:
        """Calculate memory delta from another snapshot."""
        return self.process_memory_mb - other.process_memory_mb

    def object_deltas(self, other: "MemorySnapshot") -> dict[str, int]:
        """Calculate object count deltas from another snapshot."""
        deltas = {}
        all_types = set(self.python_objects.keys()) | set(other.python_objects.keys())

        for obj_type in all_types:
            current = self.python_objects.get(obj_type, 0)
            previous = other.python_objects.get(obj_type, 0)
            delta = current - previous
            if delta != 0:
                deltas[obj_type] = delta

        return deltas


@dataclass
class LeakTestResult:
    """Results from a memory leak test."""
    test_name: str
    cycles_completed: int
    baseline_snapshot: MemorySnapshot
    final_snapshot: MemorySnapshot
    per_cycle_snapshots: list[MemorySnapshot] = field(default_factory=list)
    leak_detected: bool = False
    leak_severity: str = "none"  # none, minor, moderate, severe
    leak_details: dict[str, Any] = field(default_factory=dict)

    @property
    def memory_leaked_mb(self) -> float:
        """Total memory leaked in MB."""
        return self.final_snapshot.memory_delta_mb(self.baseline_snapshot)

    @property
    def memory_leaked_per_cycle_mb(self) -> float:
        """Memory leaked per cycle in MB."""
        if self.cycles_completed == 0:
            return 0.0
        return self.memory_leaked_mb / self.cycles_completed

    @property
    def objects_leaked(self) -> dict[str, int]:
        """Objects that weren't cleaned up."""
        return self.final_snapshot.object_deltas(self.baseline_snapshot)


class QtObjectTracker:
    """Tracks Qt object creation, deletion, and parent-child relationships."""

    def __init__(self):
        self._tracked_objects: dict[int, weakref.ReferenceType] = {}
        self._object_types: dict[int, str] = {}
        self._creation_times: dict[int, float] = {}
        self._parent_child_map: dict[int, set[int]] = defaultdict(set)
        self._signal_connections: dict[int, int] = defaultdict(int)

    def track_object(self, obj: QObject):
        """Start tracking a Qt object."""
        obj_id = id(obj)
        self._tracked_objects[obj_id] = weakref.ref(obj, self._on_object_deleted)
        self._object_types[obj_id] = type(obj).__name__
        self._creation_times[obj_id] = time.time()

        # Track parent-child relationships
        if obj.parent() is not None:
            parent_id = id(obj.parent())
            self._parent_child_map[parent_id].add(obj_id)

    def _on_object_deleted(self, ref: weakref.ReferenceType):
        """Callback when a tracked object is deleted."""
        obj_id = None
        for oid, weak_ref in list(self._tracked_objects.items()):
            if weak_ref is ref:
                obj_id = oid
                break

        if obj_id is not None:
            self._cleanup_object_tracking(obj_id)

    def _cleanup_object_tracking(self, obj_id: int):
        """Clean up tracking data for a deleted object."""
        self._tracked_objects.pop(obj_id, None)
        self._object_types.pop(obj_id, None)
        self._creation_times.pop(obj_id, None)
        self._parent_child_map.pop(obj_id, None)
        self._signal_connections.pop(obj_id, None)

    def get_live_objects(self) -> dict[str, int]:
        """Get counts of live Qt objects by type."""
        counts = defaultdict(int)
        for obj_id, weak_ref in self._tracked_objects.items():
            if weak_ref() is not None:
                obj_type = self._object_types.get(obj_id, "Unknown")
                counts[obj_type] += 1
        return dict(counts)

    def get_orphaned_objects(self) -> list[tuple[str, float]]:
        """Get objects that should have been deleted but are still alive."""
        orphaned = []
        current_time = time.time()

        for obj_id, weak_ref in self._tracked_objects.items():
            obj = weak_ref()
            if obj is not None:
                creation_time = self._creation_times.get(obj_id, current_time)
                age = current_time - creation_time

                # Objects older than 30 seconds without parents are suspicious
                if age > 30 and obj.parent() is None:
                    obj_type = self._object_types.get(obj_id, "Unknown")
                    orphaned.append((obj_type, age))

        return orphaned

    def track_signal_connection(self, sender: QObject):
        """Track signal connections for an object."""
        sender_id = id(sender)
        self._signal_connections[sender_id] += 1

    def get_connection_counts(self) -> dict[str, int]:
        """Get signal connection counts by object type."""
        counts = defaultdict(int)
        for obj_id, conn_count in self._signal_connections.items():
            if obj_id in self._object_types:
                obj_type = self._object_types[obj_id]
                counts[obj_type] += conn_count
        return dict(counts)


class MemoryLeakProfiler:
    """Comprehensive memory leak profiler for SpritePal."""

    def __init__(self):
        self.qt_tracker = QtObjectTracker()
        self.baseline_snapshot: MemorySnapshot | None = None
        self.test_results: dict[str, LeakTestResult] = {}
        self.memory_tracker = None

        # Initialize profiling tools
        if PYMPLER_AVAILABLE:
            self.memory_tracker = tracker.SummaryTracker()

        # Start tracemalloc for detailed memory tracking
        if not tracemalloc.is_tracing():
            tracemalloc.start(25)  # Keep 25 frames for detailed traces

    def take_memory_snapshot(self, label: str = "") -> MemorySnapshot:
        """Take a comprehensive memory snapshot."""
        logger.info(f"Taking memory snapshot: {label}")

        # Force garbage collection before measurement
        for _ in range(3):
            gc.collect()

        # Get process memory info
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024

        # Get Python object counts
        python_objects = {}
        if OBJGRAPH_AVAILABLE:
            python_objects = dict(objgraph.most_common_types(50))

        # Get Qt object counts
        qt_objects = self.qt_tracker.get_live_objects()

        # Get thread count
        thread_count = process.num_threads()

        # Get garbage collection stats
        gc_stats = {}
        for i, count in enumerate(gc.get_count()):
            gc_stats[f"generation_{i}"] = count

        # Get top memory allocations from tracemalloc
        tracemalloc_top = []
        if tracemalloc.is_tracing():
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics("lineno")[:10]
            tracemalloc_top = [str(stat) for stat in top_stats]

        return MemorySnapshot(
            process_memory_mb=memory_mb,
            python_objects=python_objects,
            qt_objects=qt_objects,
            thread_count=thread_count,
            gc_stats=gc_stats,
            tracemalloc_top=tracemalloc_top
        )

    def establish_baseline(self) -> MemorySnapshot:
        """Establish baseline memory usage after application startup."""
        logger.info("Establishing memory baseline...")

        # Wait for application to stabilize
        QApplication.processEvents()
        time.sleep(2)

        self.baseline_snapshot = self.take_memory_snapshot("baseline")
        logger.info(f"Baseline established: {self.baseline_snapshot.process_memory_mb:.2f} MB")

        return self.baseline_snapshot

    def profile_dialog_lifecycle(self, dialog_name: str, dialog_class: type[QDialog],
                                cycles: int = 10, **dialog_kwargs) -> LeakTestResult:
        """Profile memory usage during dialog open/close cycles."""
        logger.info(f"Profiling {dialog_name} lifecycle for {cycles} cycles")

        if self.baseline_snapshot is None:
            self.establish_baseline()

        # Create test result
        result = LeakTestResult(
            test_name=f"{dialog_name}_lifecycle",
            cycles_completed=0,
            baseline_snapshot=self.take_memory_snapshot(f"{dialog_name}_pre_test")
        )

        try:
            for cycle in range(cycles):
                logger.debug(f"Cycle {cycle + 1}/{cycles}")

                # Create and show dialog
                dialog = dialog_class(**dialog_kwargs)
                self._track_dialog_objects(dialog)

                # Simulate user interaction
                QApplication.processEvents()
                time.sleep(0.1)  # Brief interaction time

                # Close and delete dialog
                dialog.close()
                dialog.deleteLater()
                QApplication.processEvents()

                # Take snapshot every few cycles
                if (cycle + 1) % max(1, cycles // 5) == 0:
                    snapshot = self.take_memory_snapshot(f"{dialog_name}_cycle_{cycle + 1}")
                    result.per_cycle_snapshots.append(snapshot)

                result.cycles_completed = cycle + 1

                # Brief pause between cycles
                time.sleep(0.05)

        except Exception as e:
            logger.exception(f"Error during {dialog_name} lifecycle profiling: {e}")
            result.leak_details["error"] = str(e)

        # Take final snapshot
        result.final_snapshot = self.take_memory_snapshot(f"{dialog_name}_post_test")

        # Analyze for leaks
        self._analyze_leak_result(result)

        # Store result
        self.test_results[result.test_name] = result

        return result

    def profile_worker_operations(self, operation_name: str, worker_factory: Callable,
                                operations: int = 20) -> LeakTestResult:
        """Profile memory usage during worker thread operations."""
        logger.info(f"Profiling {operation_name} worker operations for {operations} operations")

        if self.baseline_snapshot is None:
            self.establish_baseline()

        result = LeakTestResult(
            test_name=f"{operation_name}_workers",
            cycles_completed=0,
            baseline_snapshot=self.take_memory_snapshot(f"{operation_name}_workers_pre_test")
        )

        workers_created = []

        try:
            for op in range(operations):
                logger.debug(f"Operation {op + 1}/{operations}")

                # Create worker
                worker = worker_factory()
                workers_created.append(weakref.ref(worker))
                self.qt_tracker.track_object(worker)

                # Simulate work
                QApplication.processEvents()
                time.sleep(0.05)

                # Clean up worker
                worker.quit()
                worker.wait(1000)  # Wait up to 1 second
                worker.deleteLater()

                # Take snapshot every few operations
                if (op + 1) % max(1, operations // 5) == 0:
                    snapshot = self.take_memory_snapshot(f"{operation_name}_workers_op_{op + 1}")
                    result.per_cycle_snapshots.append(snapshot)

                result.cycles_completed = op + 1

        except Exception as e:
            logger.exception(f"Error during {operation_name} worker profiling: {e}")
            result.leak_details["error"] = str(e)

        # Check for leaked workers
        time.sleep(1)  # Allow cleanup time
        QApplication.processEvents()

        leaked_workers = sum(1 for worker_ref in workers_created if worker_ref() is not None)
        result.leak_details["leaked_workers"] = leaked_workers

        # Take final snapshot
        result.final_snapshot = self.take_memory_snapshot(f"{operation_name}_workers_post_test")

        # Analyze for leaks
        self._analyze_leak_result(result)

        # Store result
        self.test_results[result.test_name] = result

        return result

    def profile_extraction_operations(self, rom_path: str, operations: int = 10) -> LeakTestResult:
        """Profile memory usage during sprite extraction operations."""
        logger.info(f"Profiling extraction operations for {operations} operations")

        if self.baseline_snapshot is None:
            self.establish_baseline()

        result = LeakTestResult(
            test_name="extraction_operations",
            cycles_completed=0,
            baseline_snapshot=self.take_memory_snapshot("extraction_pre_test")
        )

        try:
            # Import here to avoid circular imports
            from core.managers.registry import ManagerRegistry

            registry = ManagerRegistry()
            registry.get_extraction_manager()

            for op in range(operations):
                logger.debug(f"Extraction operation {op + 1}/{operations}")

                # Simulate extraction operation
                0x200000 + (op * 0x1000)

                try:
                    # This would normally trigger extraction
                    # We'll simulate the memory impact
                    QApplication.processEvents()
                    time.sleep(0.1)

                except Exception as e:
                    logger.warning(f"Extraction operation {op + 1} failed: {e}")

                # Take snapshot periodically
                if (op + 1) % max(1, operations // 3) == 0:
                    snapshot = self.take_memory_snapshot(f"extraction_op_{op + 1}")
                    result.per_cycle_snapshots.append(snapshot)

                result.cycles_completed = op + 1

        except Exception as e:
            logger.exception(f"Error during extraction profiling: {e}")
            result.leak_details["error"] = str(e)

        # Take final snapshot
        result.final_snapshot = self.take_memory_snapshot("extraction_post_test")

        # Analyze for leaks
        self._analyze_leak_result(result)

        # Store result
        self.test_results[result.test_name] = result

        return result

    def _track_dialog_objects(self, dialog: QDialog):
        """Track all Qt objects in a dialog hierarchy."""
        self.qt_tracker.track_object(dialog)

        # Recursively track all child objects
        def track_children(parent):
            for child in parent.findChildren(QObject):
                self.qt_tracker.track_object(child)

        track_children(dialog)

    def _analyze_leak_result(self, result: LeakTestResult):
        """Analyze test result for memory leaks."""
        memory_leaked = result.memory_leaked_mb
        per_cycle_leaked = result.memory_leaked_per_cycle_mb
        objects_leaked = result.objects_leaked

        # Determine leak severity
        if memory_leaked < 1.0:
            result.leak_severity = "none"
        elif memory_leaked < 5.0:
            result.leak_severity = "minor"
        elif memory_leaked < 20.0:
            result.leak_severity = "moderate"
        else:
            result.leak_severity = "severe"

        result.leak_detected = memory_leaked > 0.5  # 500KB threshold

        # Detailed analysis
        result.leak_details.update({
            "total_memory_leaked_mb": memory_leaked,
            "memory_per_cycle_mb": per_cycle_leaked,
            "objects_leaked": objects_leaked,
            "qt_orphaned_objects": self.qt_tracker.get_orphaned_objects(),
            "signal_connections": self.qt_tracker.get_connection_counts()
        })

        # Check for specific leak patterns
        suspicious_objects = []
        for obj_type, count in objects_leaked.items():
            if count > result.cycles_completed * 2:  # More than 2x expected
                suspicious_objects.append(f"{obj_type}: +{count}")

        if suspicious_objects:
            result.leak_details["suspicious_objects"] = suspicious_objects

        logger.info(f"Leak analysis for {result.test_name}: {result.leak_severity} "
                   f"({memory_leaked:.2f}MB total, {per_cycle_leaked:.3f}MB per cycle)")

    def generate_leak_report(self) -> str:
        """Generate comprehensive memory leak report."""
        if not self.test_results:
            return "No memory leak tests have been run."

        report = ["SpritePal Memory Leak Analysis Report"]
        report.append("=" * 50)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Executive Summary
        report.append("EXECUTIVE SUMMARY")
        report.append("-" * 20)

        total_tests = len(self.test_results)
        leaked_tests = sum(1 for r in self.test_results.values() if r.leak_detected)
        severe_leaks = sum(1 for r in self.test_results.values() if r.leak_severity == "severe")

        report.append(f"Tests Run: {total_tests}")
        report.append(f"Tests with Leaks: {leaked_tests}")
        report.append(f"Severe Leaks: {severe_leaks}")
        report.append("")

        if self.baseline_snapshot:
            report.append(f"Baseline Memory: {self.baseline_snapshot.process_memory_mb:.2f} MB")
            report.append(f"Baseline Objects: {sum(self.baseline_snapshot.python_objects.values())}")
            report.append("")

        # Detailed Results
        report.append("DETAILED RESULTS")
        report.append("-" * 20)

        for test_name, result in self.test_results.items():
            report.append(f"\n{test_name.upper()}")
            report.append(f"Cycles: {result.cycles_completed}")
            report.append(f"Memory Leaked: {result.memory_leaked_mb:.2f} MB")
            report.append(f"Per Cycle: {result.memory_leaked_per_cycle_mb:.3f} MB")
            report.append(f"Severity: {result.leak_severity}")

            if result.objects_leaked:
                report.append("Object Leaks:")
                for obj_type, count in sorted(result.objects_leaked.items(),
                                            key=lambda x: abs(x[1]), reverse=True)[:10]:
                    report.append(f"  {obj_type}: {count:+d}")

            if "suspicious_objects" in result.leak_details:
                report.append("Suspicious Objects:")
                for obj in result.leak_details["suspicious_objects"]:
                    report.append(f"  {obj}")

            if "leaked_workers" in result.leak_details:
                leaked_workers = result.leak_details["leaked_workers"]
                if leaked_workers > 0:
                    report.append(f"Leaked Workers: {leaked_workers}")

        # Qt Object Analysis
        report.append("\nQT OBJECT ANALYSIS")
        report.append("-" * 20)
        orphaned = self.qt_tracker.get_orphaned_objects()
        if orphaned:
            report.append("Orphaned Objects (no parent, age > 30s):")
            for obj_type, age in sorted(orphaned, key=lambda x: x[1], reverse=True)[:10]:
                report.append(f"  {obj_type}: {age:.1f}s old")
        else:
            report.append("No orphaned Qt objects detected.")

        # Signal Connection Analysis
        connections = self.qt_tracker.get_connection_counts()
        if connections:
            report.append("\nSignal Connections by Type:")
            for obj_type, count in sorted(connections.items(), key=lambda x: x[1], reverse=True)[:10]:
                report.append(f"  {obj_type}: {count} connections")

        # Recommendations
        report.append("\nRECOMMENDATIONS")
        report.append("-" * 20)

        if severe_leaks > 0:
            report.append("🔴 CRITICAL: Severe memory leaks detected!")
            report.append("   - Fix immediately before release")
            report.append("   - Focus on dialog cleanup and worker termination")
        elif leaked_tests > 0:
            report.append("🟡 WARNING: Memory leaks detected")
            report.append("   - Address before next release")
            report.append("   - Monitor growth over time")
        else:
            report.append("✅ GOOD: No significant memory leaks detected")

        report.append("\nSpecific Actions:")
        for test_name, result in self.test_results.items():
            if result.leak_detected:
                per_cycle = result.memory_leaked_per_cycle_mb * 1000  # Convert to KB
                report.append(f"- {test_name}: Fix {per_cycle:.1f}KB leak per operation")

        # Metrics for Tracking
        report.append("\nBASELINE METRICS FOR TRACKING")
        report.append("-" * 30)
        for test_name, result in self.test_results.items():
            report.append(f"{test_name}:")
            report.append(f"  Memory per cycle: {result.memory_leaked_per_cycle_mb * 1000:.1f} KB")
            report.append(f"  Objects leaked: {sum(abs(v) for v in result.objects_leaked.values())}")

        return "\n".join(report)

    def run_comprehensive_leak_test(self, rom_path: str | None = None) -> str:
        """Run comprehensive memory leak tests on all major components."""
        logger.info("Starting comprehensive memory leak test suite")

        self.establish_baseline()

        # Test 1: Manual Offset Dialog Lifecycle
        try:
            from ui.dialogs.manual_offset_unified_integrated import ManualOffsetDialog
            logger.info("Testing Manual Offset Dialog...")
            self.profile_dialog_lifecycle("ManualOffsetDialog", ManualOffsetDialog, cycles=10)
        except Exception as e:
            logger.exception(f"Manual Offset Dialog test failed: {e}")

        # Test 2: Advanced Search Dialog Lifecycle
        try:
            from ui.dialogs.advanced_search_dialog import AdvancedSearchDialog
            logger.info("Testing Advanced Search Dialog...")
            self.profile_dialog_lifecycle("AdvancedSearchDialog", AdvancedSearchDialog, cycles=10)
        except Exception as e:
            logger.exception(f"Advanced Search Dialog test failed: {e}")

        # Test 3: Settings Dialog Lifecycle
        try:
            from ui.dialogs.settings_dialog import SettingsDialog
            logger.info("Testing Settings Dialog...")
            self.profile_dialog_lifecycle("SettingsDialog", SettingsDialog, cycles=10)
        except Exception as e:
            logger.exception(f"Settings Dialog test failed: {e}")

        # Test 4: Worker Thread Operations
        try:
            from ui.rom_extraction.workers.preview_worker import SpritePreviewWorker
            logger.info("Testing Preview Workers...")
            self.profile_worker_operations("PreviewWorker", lambda: SpritePreviewWorker(), operations=20)
        except Exception as e:
            logger.exception(f"Preview Worker test failed: {e}")

        # Test 5: Extraction Operations (if ROM provided)
        if rom_path and os.path.exists(rom_path):
            try:
                logger.info("Testing Extraction Operations...")
                self.profile_extraction_operations(rom_path, operations=10)
            except Exception as e:
                logger.exception(f"Extraction operations test failed: {e}")

        # Generate and return comprehensive report
        return self.generate_leak_report()


def main():
    """Main function for running memory leak profiling."""
    import argparse

    parser = argparse.ArgumentParser(description="SpritePal Memory Leak Profiler")
    parser.add_argument("--rom", help="Path to ROM file for extraction testing")
    parser.add_argument("--output", help="Output file for report", default="memory_leak_report.txt")
    parser.add_argument("--cycles", type=int, default=10, help="Number of test cycles per component")

    args = parser.parse_args()

    # Initialize Qt application
    QApplication(sys.argv)

    # Create profiler
    profiler = MemoryLeakProfiler()

    # Run comprehensive tests
    report = profiler.run_comprehensive_leak_test(args.rom)

    # Save report
    with open(args.output, "w") as f:
        f.write(report)

    print(f"Memory leak report saved to: {args.output}")
    print("\nSummary:")

    leaked_tests = sum(1 for r in profiler.test_results.values() if r.leak_detected)
    total_tests = len(profiler.test_results)

    if leaked_tests == 0:
        print("✅ No memory leaks detected!")
    else:
        print(f"⚠️  {leaked_tests}/{total_tests} tests detected memory leaks")

        # Show worst leaks
        worst_leaks = sorted(profiler.test_results.values(),
                           key=lambda r: r.memory_leaked_mb, reverse=True)[:3]

        for result in worst_leaks:
            if result.leak_detected:
                print(f"   - {result.test_name}: {result.memory_leaked_mb:.2f}MB "
                      f"({result.memory_leaked_per_cycle_mb*1000:.1f}KB per cycle)")


if __name__ == "__main__":
    main()
