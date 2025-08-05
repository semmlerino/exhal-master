#!/usr/bin/env python3
"""
Comprehensive Performance Profiler for SpritePal Application

This profiling script provides detailed analysis of:
- Memory usage and leaks
- CPU bottlenecks
- I/O efficiency
- Thread contention
- Qt object lifecycle
- Manager singleton patterns
- Worker thread performance
- ROM cache efficiency
- Large data structure handling
"""

import cProfile
import gc
import io
import json
import pstats
import sys
import threading
import time
import tracemalloc
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psutil

try:
    # LineProfiler not needed - unused
    from memory_profiler import profile as memory_profile
    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False
    def memory_profile(func):
        return func

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ProfileMetrics:
    """Container for profiling metrics"""
    cpu_stats: dict[str, Any] = field(default_factory=dict)
    memory_stats: dict[str, Any] = field(default_factory=dict)
    io_stats: dict[str, Any] = field(default_factory=dict)
    thread_stats: dict[str, Any] = field(default_factory=dict)
    qt_stats: dict[str, Any] = field(default_factory=dict)
    manager_stats: dict[str, Any] = field(default_factory=dict)
    worker_stats: dict[str, Any] = field(default_factory=dict)
    cache_stats: dict[str, Any] = field(default_factory=dict)
    timing_stats: dict[str, Any] = field(default_factory=dict)


class MemoryTracker:
    """Track memory usage patterns and detect leaks"""

    def __init__(self):
        self.snapshots = []
        self.peak_memory = 0
        self.baseline_memory = 0
        self.gc_stats = []

    def start_tracking(self):
        """Start memory tracking"""
        tracemalloc.start()
        self.baseline_memory = self._get_current_memory()
        logger.info(f"Memory tracking started. Baseline: {self.baseline_memory:.2f} MB")

    def take_snapshot(self, label: str = ""):
        """Take a memory snapshot"""
        if not tracemalloc.is_tracing():
            return None

        snapshot = tracemalloc.take_snapshot()
        current_memory = self._get_current_memory()

        self.snapshots.append({
            'label': label,
            'timestamp': time.time(),
            'memory_mb': current_memory,
            'snapshot': snapshot
        })

        self.peak_memory = max(self.peak_memory, current_memory)

        logger.debug(f"Memory snapshot '{label}': {current_memory:.2f} MB")
        return snapshot

    def _get_current_memory(self) -> float:
        """Get current memory usage in MB"""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def analyze_memory_growth(self) -> dict[str, Any]:
        """Analyze memory growth patterns"""
        if len(self.snapshots) < 2:
            return {"error": "Need at least 2 snapshots for analysis"}

        first_snapshot = self.snapshots[0]
        last_snapshot = self.snapshots[-1]

        memory_growth = last_snapshot['memory_mb'] - first_snapshot['memory_mb']

        # Analyze top memory consumers
        top_stats = last_snapshot['snapshot'].statistics('lineno')[:20]

        # Compare snapshots to find memory leaks
        leaked_objects = []
        if len(self.snapshots) >= 2:
            try:
                # Compare last two snapshots
                prev_snapshot = self.snapshots[-2]['snapshot']
                current_snapshot = last_snapshot['snapshot']

                # Find top differences
                top_stats_prev = prev_snapshot.statistics('lineno')
                top_stats_current = current_snapshot.statistics('lineno')

                # Create lookup for previous stats
                prev_stats_dict = {stat.traceback: stat for stat in top_stats_prev}

                for stat in top_stats_current[:10]:
                    prev_stat = prev_stats_dict.get(stat.traceback)
                    if prev_stat:
                        size_diff = stat.size - prev_stat.size
                        count_diff = stat.count - prev_stat.count

                        if size_diff > 0:  # Memory increase
                            leaked_objects.append({
                                'file': str(stat.traceback.format()[0]) if stat.traceback.format() else "Unknown",
                                'size_increase_mb': size_diff / 1024 / 1024,
                                'count_increase': count_diff,
                                'current_size_mb': stat.size / 1024 / 1024,
                                'current_count': stat.count
                            })
            except Exception as e:
                logger.warning(f"Error analyzing memory leaks: {e}")

        return {
            'baseline_memory_mb': self.baseline_memory,
            'peak_memory_mb': self.peak_memory,
            'current_memory_mb': last_snapshot['memory_mb'],
            'total_growth_mb': memory_growth,
            'growth_rate_mb_per_sec': memory_growth / (last_snapshot['timestamp'] - first_snapshot['timestamp']) if len(self.snapshots) > 1 else 0,
            'snapshot_count': len(self.snapshots),
            'top_memory_consumers': [
                {
                    'file': str(stat.traceback.format()[0]) if stat.traceback.format() else "Unknown",
                    'size_mb': stat.size / 1024 / 1024,
                    'count': stat.count
                }
                for stat in top_stats[:10]
            ],
            'potential_leaks': sorted(leaked_objects, key=lambda x: x['size_increase_mb'], reverse=True)[:10]
        }

    def stop_tracking(self):
        """Stop memory tracking"""
        if tracemalloc.is_tracing():
            tracemalloc.stop()


class CPUProfiler:
    """Profile CPU usage and identify bottlenecks"""

    def __init__(self):
        self.profiler = None
        self.profile_data = None

    @contextmanager
    def profile_context(self):
        """Context manager for CPU profiling"""
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        try:
            yield
        finally:
            self.profiler.disable()

    def analyze_cpu_usage(self) -> dict[str, Any]:
        """Analyze CPU profiling results"""
        if not self.profiler:
            return {"error": "No profiling data available"}

        # Create string buffer to capture stats
        stats_buffer = io.StringIO()
        stats = pstats.Stats(self.profiler, stream=stats_buffer)
        stats.sort_stats('cumulative')

        # Get top functions by cumulative time
        stats.print_stats(20)
        cpu_report = stats_buffer.getvalue()

        # Get detailed stats
        stats.sort_stats('tottime')
        top_functions = []

        for func_key, (cc, _nc, tt, ct, _callers) in stats.stats.items():
            filename, line_num, func_name = func_key
            top_functions.append({
                'function': func_name,
                'file': filename,
                'line': line_num,
                'call_count': cc,
                'total_time': tt,
                'cumulative_time': ct,
                'time_per_call': tt / cc if cc > 0 else 0
            })

        # Sort by total time and take top 15
        top_functions.sort(key=lambda x: x['total_time'], reverse=True)

        return {
            'report': cpu_report,
            'top_functions': top_functions[:15],
            'total_functions': len(stats.stats),
            'total_calls': sum(cc for cc, nc, tt, ct, callers in stats.stats.values())
        }


class ThreadAnalyzer:
    """Analyze thread usage and contention"""

    def __init__(self):
        self.thread_info = {}
        self.lock_contention = defaultdict(list)

    def analyze_threads(self) -> dict[str, Any]:
        """Analyze current thread state"""
        threads = threading.enumerate()
        thread_stats = []

        for thread in threads:
            thread_info = {
                'name': thread.name,
                'daemon': thread.daemon,
                'alive': thread.is_alive(),
                'ident': thread.ident
            }

            # Check if it's a QThread
            if hasattr(thread, 'isRunning'):
                thread_info['qt_thread'] = True
                thread_info['qt_running'] = thread.isRunning()
                thread_info['qt_finished'] = thread.isFinished()

            thread_stats.append(thread_info)

        return {
            'total_threads': len(threads),
            'active_threads': len([t for t in threads if t.is_alive()]),
            'daemon_threads': len([t for t in threads if t.daemon]),
            'qt_threads': len([t for t in thread_stats if t.get('qt_thread', False)]),
            'thread_details': thread_stats
        }


class QtObjectTracker:
    """Track Qt object creation and lifecycle"""

    def __init__(self):
        self.qt_objects = {}
        self.widget_counts = defaultdict(int)

    def analyze_qt_objects(self) -> dict[str, Any]:
        """Analyze Qt object usage"""
        try:
            from PyQt6.QtCore import QObject
            from PyQt6.QtWidgets import QApplication, QWidget

            # Get application instance
            app = QApplication.instance()
            if not app:
                return {"error": "No QApplication instance found"}

            # Count widgets
            all_widgets = app.allWidgets()
            widget_types = defaultdict(int)

            for widget in all_widgets:
                widget_type = type(widget).__name__
                widget_types[widget_type] += 1

            # Get top-level widgets
            top_level_widgets = app.topLevelWidgets()

            return {
                'total_widgets': len(all_widgets),
                'top_level_widgets': len(top_level_widgets),
                'widget_types': dict(widget_types),
                'top_widget_types': sorted(widget_types.items(), key=lambda x: x[1], reverse=True)[:10]
            }

        except ImportError:
            return {"error": "PyQt6 not available"}
        except Exception as e:
            return {"error": f"Qt analysis failed: {e}"}


class ManagerProfiler:
    """Profile manager singleton usage and lifecycle"""

    def analyze_managers(self) -> dict[str, Any]:
        """Analyze manager instances"""
        try:
            from core.managers.registry import are_managers_initialized, get_registry

            registry = get_registry()
            manager_stats = {
                'managers_initialized': are_managers_initialized(),
                'available_managers': {},
                'manager_memory': {}
            }

            if are_managers_initialized():
                try:
                    # Try to get each manager and analyze it
                    managers_to_check = [
                        ('session', 'get_session_manager'),
                        ('extraction', 'get_extraction_manager'),
                        ('injection', 'get_injection_manager')
                    ]

                    for manager_name, getter_name in managers_to_check:
                        try:
                            getter = getattr(registry, getter_name)
                            manager = getter()

                            manager_info = {
                                'initialized': manager.is_initialized() if hasattr(manager, 'is_initialized') else True,
                                'type': type(manager).__name__,
                                'memory_size': sys.getsizeof(manager)
                            }

                            # Check for common performance-relevant attributes
                            if hasattr(manager, '_cache'):
                                cache_size = len(manager._cache) if hasattr(manager._cache, '__len__') else 'unknown'
                                manager_info['cache_size'] = cache_size

                            manager_stats['available_managers'][manager_name] = manager_info

                        except Exception as e:
                            manager_stats['available_managers'][manager_name] = {'error': str(e)}

                except Exception as e:
                    manager_stats['registry_error'] = str(e)

            return manager_stats

        except ImportError as e:
            return {"error": f"Cannot import manager registry: {e}"}


class WorkerProfiler:
    """Profile worker thread performance"""

    def analyze_workers(self) -> dict[str, Any]:
        """Analyze worker thread patterns"""
        threads = threading.enumerate()
        worker_threads = []

        for thread in threads:
            # Check if it looks like a worker thread
            if (hasattr(thread, 'is_cancelled') or
                'worker' in thread.name.lower() or
                'Worker' in type(thread).__name__):

                worker_info = {
                    'name': thread.name,
                    'type': type(thread).__name__,
                    'alive': thread.is_alive(),
                    'daemon': thread.daemon
                }

                # Check for worker-specific attributes
                if hasattr(thread, 'is_cancelled'):
                    worker_info['cancelled'] = thread.is_cancelled
                if hasattr(thread, 'is_paused'):
                    worker_info['paused'] = thread.is_paused
                if hasattr(thread, 'isRunning'):
                    worker_info['qt_running'] = thread.isRunning()

                worker_threads.append(worker_info)

        return {
            'total_worker_threads': len(worker_threads),
            'active_workers': len([w for w in worker_threads if w['alive']]),
            'worker_details': worker_threads
        }


class IOAnalyzer:
    """Analyze I/O patterns and efficiency"""

    def __init__(self):
        self.io_operations = []

    def analyze_cache_efficiency(self) -> dict[str, Any]:
        """Analyze ROM cache efficiency"""
        try:
            from utils.rom_cache import get_rom_cache

            cache = get_rom_cache()
            cache_stats = cache.get_cache_stats()

            # Add efficiency metrics
            if cache_stats.get('total_files', 0) > 0:
                avg_file_size = cache_stats['total_size_bytes'] / cache_stats['total_files']
                cache_stats['avg_file_size_bytes'] = avg_file_size
                cache_stats['total_size_mb'] = cache_stats['total_size_bytes'] / 1024 / 1024

            return cache_stats

        except Exception as e:
            return {"error": f"Cannot analyze cache: {e}"}

    def analyze_file_operations(self) -> dict[str, Any]:
        """Analyze file I/O patterns"""
        process = psutil.Process()

        try:
            io_counters = process.io_counters()
            return {
                'read_count': io_counters.read_count,
                'write_count': io_counters.write_count,
                'read_bytes': io_counters.read_bytes,
                'write_bytes': io_counters.write_bytes,
                'read_mb': io_counters.read_bytes / 1024 / 1024,
                'write_mb': io_counters.write_bytes / 1024 / 1024
            }
        except AttributeError:
            return {"error": "I/O counters not available on this platform"}


class PerformanceProfiler:
    """Main profiler orchestrating all analysis"""

    def __init__(self):
        self.memory_tracker = MemoryTracker()
        self.cpu_profiler = CPUProfiler()
        self.thread_analyzer = ThreadAnalyzer()
        self.qt_tracker = QtObjectTracker()
        self.manager_profiler = ManagerProfiler()
        self.worker_profiler = WorkerProfiler()
        self.io_analyzer = IOAnalyzer()
        self.start_time = None

    def start_profiling(self):
        """Start comprehensive profiling"""
        self.start_time = time.time()
        self.memory_tracker.start_tracking()
        self.memory_tracker.take_snapshot("profiling_start")
        logger.info("Performance profiling started")

    def profile_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Profile a specific operation"""
        logger.info(f"Profiling operation: {operation_name}")

        # Take pre-operation snapshot
        self.memory_tracker.take_snapshot(f"before_{operation_name}")

        # Profile CPU usage
        with self.cpu_profiler.profile_context():
            start_time = time.time()
            try:
                result = operation_func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                result = None
                success = False
                error = str(e)
                logger.error(f"Operation {operation_name} failed: {e}")

        end_time = time.time()
        operation_time = end_time - start_time

        # Take post-operation snapshot
        self.memory_tracker.take_snapshot(f"after_{operation_name}")

        logger.info(f"Operation {operation_name} completed in {operation_time:.2f}s")

        return {
            'result': result,
            'success': success,
            'error': error,
            'execution_time': operation_time
        }

    def generate_comprehensive_report(self) -> ProfileMetrics:
        """Generate comprehensive performance report"""
        end_time = time.time()
        total_time = end_time - self.start_time if self.start_time else 0

        self.memory_tracker.take_snapshot("profiling_end")

        metrics = ProfileMetrics()

        # CPU Analysis
        metrics.cpu_stats = self.cpu_profiler.analyze_cpu_usage()

        # Memory Analysis
        metrics.memory_stats = self.memory_tracker.analyze_memory_growth()

        # Thread Analysis
        metrics.thread_stats = self.thread_analyzer.analyze_threads()

        # Qt Object Analysis
        metrics.qt_stats = self.qt_tracker.analyze_qt_objects()

        # Manager Analysis
        metrics.manager_stats = self.manager_profiler.analyze_managers()

        # Worker Analysis
        metrics.worker_stats = self.worker_profiler.analyze_workers()

        # I/O Analysis
        metrics.io_stats = {
            'cache_efficiency': self.io_analyzer.analyze_cache_efficiency(),
            'file_operations': self.io_analyzer.analyze_file_operations()
        }

        # Cache-specific analysis
        metrics.cache_stats = self.io_analyzer.analyze_cache_efficiency()

        # Timing statistics
        metrics.timing_stats = {
            'total_profiling_time': total_time,
            'profiling_start': self.start_time,
            'profiling_end': end_time
        }

        return metrics

    def stop_profiling(self):
        """Stop profiling and cleanup"""
        self.memory_tracker.stop_tracking()
        logger.info("Performance profiling stopped")


def format_report(metrics: ProfileMetrics) -> str:
    """Format profiling results into readable report"""
    report = []
    report.append("=" * 80)
    report.append("SPRITEPAL PERFORMANCE PROFILING REPORT")
    report.append("=" * 80)
    report.append("")

    # Timing Summary
    report.append("PROFILING SUMMARY")
    report.append("-" * 40)
    total_time = metrics.timing_stats.get('total_profiling_time', 0)
    report.append(f"Total profiling time: {total_time:.2f} seconds")
    report.append("")

    # Memory Analysis
    report.append("MEMORY ANALYSIS")
    report.append("-" * 40)
    mem_stats = metrics.memory_stats
    if 'error' not in mem_stats:
        report.append(f"Baseline memory: {mem_stats.get('baseline_memory_mb', 0):.2f} MB")
        report.append(f"Peak memory: {mem_stats.get('peak_memory_mb', 0):.2f} MB")
        report.append(f"Current memory: {mem_stats.get('current_memory_mb', 0):.2f} MB")
        report.append(f"Total growth: {mem_stats.get('total_growth_mb', 0):.2f} MB")

        growth_rate = mem_stats.get('growth_rate_mb_per_sec', 0)
        if growth_rate > 0.1:
            report.append(f"WARNING: MEMORY LEAK - Growth rate {growth_rate:.3f} MB/sec")

        # Top memory consumers
        report.append("\nTop Memory Consumers:")
        for consumer in mem_stats.get('top_memory_consumers', [])[:5]:
            report.append(f"  • {consumer['file']}: {consumer['size_mb']:.2f} MB ({consumer['count']} objects)")

        # Potential leaks
        leaks = mem_stats.get('potential_leaks', [])
        if leaks:
            report.append("\nPOTENTIAL MEMORY LEAKS:")
            for leak in leaks[:3]:
                report.append(f"  • {leak['file']}: +{leak['size_increase_mb']:.2f} MB")
    else:
        report.append(f"Memory analysis error: {mem_stats['error']}")
    report.append("")

    # CPU Analysis
    report.append("CPU PERFORMANCE ANALYSIS")
    report.append("-" * 40)
    cpu_stats = metrics.cpu_stats
    if 'error' not in cpu_stats:
        report.append(f"Total functions analyzed: {cpu_stats.get('total_functions', 0)}")
        report.append(f"Total function calls: {cpu_stats.get('total_calls', 0)}")

        report.append("\nTop CPU Bottlenecks:")
        for func in cpu_stats.get('top_functions', [])[:5]:
            if func['total_time'] > 0.01:  # Only show functions taking >10ms
                report.append(f"  • {func['function']} ({func['file']}:{func['line']})")
                report.append(f"    Time: {func['total_time']:.3f}s, Calls: {func['call_count']}")
    else:
        report.append(f"CPU analysis error: {cpu_stats['error']}")
    report.append("")

    # Thread Analysis
    report.append("THREAD ANALYSIS")
    report.append("-" * 40)
    thread_stats = metrics.thread_stats
    report.append(f"Total threads: {thread_stats.get('total_threads', 0)}")
    report.append(f"Active threads: {thread_stats.get('active_threads', 0)}")
    report.append(f"Qt threads: {thread_stats.get('qt_threads', 0)}")
    report.append(f"Worker threads: {metrics.worker_stats.get('total_worker_threads', 0)}")

    if thread_stats.get('total_threads', 0) > 20:
        report.append("WARNING: HIGH THREAD COUNT - Consider thread pooling")
    report.append("")

    # Qt Objects Analysis
    report.append("QT OBJECTS ANALYSIS")
    report.append("-" * 40)
    qt_stats = metrics.qt_stats
    if 'error' not in qt_stats:
        report.append(f"Total widgets: {qt_stats.get('total_widgets', 0)}")
        report.append(f"Top-level widgets: {qt_stats.get('top_level_widgets', 0)}")

        if qt_stats.get('total_widgets', 0) > 1000:
            report.append("WARNING: HIGH WIDGET COUNT - Potential memory usage issue")

        report.append("\nTop Widget Types:")
        for widget_type, count in qt_stats.get('top_widget_types', [])[:5]:
            report.append(f"  • {widget_type}: {count}")
    else:
        report.append(f"Qt analysis error: {qt_stats['error']}")
    report.append("")

    # Manager Analysis
    report.append("MANAGER ANALYSIS")
    report.append("-" * 40)
    manager_stats = metrics.manager_stats
    report.append(f"Managers initialized: {manager_stats.get('managers_initialized', False)}")

    available_managers = manager_stats.get('available_managers', {})
    for name, info in available_managers.items():
        if 'error' in info:
            report.append(f"  • {name}: ERROR - {info['error']}")
        else:
            status = "✓" if info.get('initialized', True) else "✗"
            memory_kb = info.get('memory_size', 0) / 1024
            report.append(f"  • {name} {status}: {info.get('type', 'Unknown')} ({memory_kb:.1f} KB)")
            if 'cache_size' in info:
                report.append(f"    Cache size: {info['cache_size']}")
    report.append("")

    # Cache Analysis
    report.append("ROM CACHE ANALYSIS")
    report.append("-" * 40)
    cache_stats = metrics.cache_stats
    if 'error' not in cache_stats:
        if cache_stats.get('cache_enabled', False):
            report.append("Cache enabled: ✓")
            report.append(f"Cache directory: {cache_stats.get('cache_dir', 'Unknown')}")
            report.append(f"Total cache files: {cache_stats.get('total_files', 0)}")
            report.append(f"Total cache size: {cache_stats.get('total_size_mb', 0):.1f} MB")
            report.append(f"Sprite location caches: {cache_stats.get('sprite_location_caches', 0)}")
            report.append(f"Scan progress caches: {cache_stats.get('scan_progress_caches', 0)}")
            report.append(f"Preview caches: {cache_stats.get('preview_caches', 0)}")

            # Cache efficiency warning
            if cache_stats.get('total_size_mb', 0) > 500:
                report.append("WARNING: LARGE CACHE - Consider cleanup")
        else:
            report.append("Cache disabled")
    else:
        report.append(f"Cache analysis error: {cache_stats['error']}")
    report.append("")

    # I/O Analysis
    report.append("I/O PERFORMANCE ANALYSIS")
    report.append("-" * 40)
    io_stats = metrics.io_stats.get('file_operations', {})
    if 'error' not in io_stats:
        report.append(f"Read operations: {io_stats.get('read_count', 0)}")
        report.append(f"Write operations: {io_stats.get('write_count', 0)}")
        report.append(f"Data read: {io_stats.get('read_mb', 0):.1f} MB")
        report.append(f"Data written: {io_stats.get('write_mb', 0):.1f} MB")
    else:
        report.append(f"I/O analysis error: {io_stats['error']}")
    report.append("")

    # Performance Recommendations
    report.append("PERFORMANCE RECOMMENDATIONS")
    report.append("-" * 40)
    recommendations = generate_recommendations(metrics)
    for recommendation in recommendations:
        report.append(f"• {recommendation}")

    report.append("")
    report.append("=" * 80)

    return "\n".join(report)


def generate_recommendations(metrics: ProfileMetrics) -> list[str]:
    """Generate performance optimization recommendations"""
    recommendations = []

    # Memory recommendations
    mem_stats = metrics.memory_stats
    if 'error' not in mem_stats:
        growth_rate = mem_stats.get('growth_rate_mb_per_sec', 0)
        if growth_rate > 0.1:
            recommendations.append("CRITICAL: Investigate memory leaks - growth rate exceeds 0.1 MB/sec")

        if mem_stats.get('peak_memory_mb', 0) > 1000:
            recommendations.append("HIGH: Consider memory optimization - peak usage over 1GB")

        leaks = mem_stats.get('potential_leaks', [])
        if leaks:
            recommendations.append(f"MEDIUM: Investigate {len(leaks)} potential memory leak sources")

    # Thread recommendations
    thread_count = metrics.thread_stats.get('total_threads', 0)
    if thread_count > 20:
        recommendations.append("MEDIUM: High thread count - consider thread pooling")

    worker_count = metrics.worker_stats.get('total_worker_threads', 0)
    if worker_count > 10:
        recommendations.append("LOW: Many worker threads active - ensure proper cleanup")

    # Qt recommendations
    qt_stats = metrics.qt_stats
    if 'error' not in qt_stats:
        widget_count = qt_stats.get('total_widgets', 0)
        if widget_count > 1000:
            recommendations.append("HIGH: Excessive widget count - review widget lifecycle")

    # Cache recommendations
    cache_stats = metrics.cache_stats
    if 'error' not in cache_stats and cache_stats.get('cache_enabled', False):
        cache_size_mb = cache_stats.get('total_size_mb', 0)
        if cache_size_mb > 500:
            recommendations.append("LOW: Large cache size - schedule periodic cleanup")

        if cache_stats.get('total_files', 0) > 1000:
            recommendations.append("LOW: Many cache files - consider cache consolidation")

    # CPU recommendations
    cpu_stats = metrics.cpu_stats
    if 'error' not in cpu_stats:
        top_functions = cpu_stats.get('top_functions', [])
        if top_functions:
            slowest = top_functions[0]
            if slowest.get('total_time', 0) > 1.0:
                recommendations.append(f"HIGH: Optimize {slowest['function']} - consumes {slowest['total_time']:.2f}s")

    # Manager recommendations
    manager_stats = metrics.manager_stats
    available_managers = manager_stats.get('available_managers', {})
    for name, info in available_managers.items():
        if 'error' in info:
            recommendations.append(f"MEDIUM: Fix manager initialization issue for {name}")

    if not recommendations:
        recommendations.append("No critical performance issues detected")

    return recommendations


def save_report(metrics: ProfileMetrics, filename: str | None = None):
    """Save profiling report to file"""
    if filename is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"spritepal_performance_report_{timestamp}.txt"

    report_text = format_report(metrics)

    with Path(filename).open('w') as f:
        f.write(report_text)

    # Also save raw metrics as JSON for further analysis
    json_filename = filename.replace('.txt', '_raw_data.json')

    # Convert metrics to JSON-serializable format
    json_data = {
        'cpu_stats': metrics.cpu_stats,
        'memory_stats': metrics.memory_stats,
        'io_stats': metrics.io_stats,
        'thread_stats': metrics.thread_stats,
        'qt_stats': metrics.qt_stats,
        'manager_stats': metrics.manager_stats,
        'worker_stats': metrics.worker_stats,
        'cache_stats': metrics.cache_stats,
        'timing_stats': metrics.timing_stats
    }

    with Path(json_filename).open('w') as f:
        json.dump(json_data, f, indent=2, default=str)

    logger.info(f"Performance report saved to {filename}")
    logger.info(f"Raw data saved to {json_filename}")

    return filename, json_filename


# Specialized profiling functions for SpritePal components

def profile_worker_lifecycle():
    """Profile worker thread creation and cleanup patterns"""
    profiler = PerformanceProfiler()
    profiler.start_profiling()

    def simulate_worker_operations():
        """Simulate typical worker operations"""
        # Simulate ROM extraction operations
        time.sleep(0.1)  # Simulate work
        gc.collect()  # Force collection to see cleanup patterns

    # Profile multiple worker cycles
    for i in range(5):
        profiler.profile_operation(f"worker_cycle_{i}", simulate_worker_operations)

    metrics = profiler.generate_comprehensive_report()
    profiler.stop_profiling()

    return metrics


def profile_manager_singleton_access():
    """Profile manager singleton access patterns"""
    profiler = PerformanceProfiler()
    profiler.start_profiling()

    def simulate_manager_access():
        """Simulate manager access patterns"""
        try:
            from core.managers.registry import get_registry
            registry = get_registry()
            # Simulate multiple manager accesses
            for _ in range(10):
                if hasattr(registry, 'get_session_manager'):
                    try:
                        registry.get_session_manager()
                    except:
                        pass  # Expected if not initialized
        except ImportError:
            pass

    profiler.profile_operation("manager_access", simulate_manager_access)

    metrics = profiler.generate_comprehensive_report()
    profiler.stop_profiling()

    return metrics


def profile_rom_cache_operations():
    """Profile ROM cache efficiency"""
    profiler = PerformanceProfiler()
    profiler.start_profiling()

    def simulate_cache_operations():
        """Simulate ROM cache operations"""
        try:
            from utils.rom_cache import get_rom_cache
            cache = get_rom_cache()

            # Simulate cache operations
            test_rom_path = "test_rom.sfc"
            test_data = b"test_data" * 1000  # 9KB test data

            # Test save operations
            cache.save_preview_data(test_rom_path, 0x200000, test_data, 32, 32)

            # Test load operations
            cache.get_preview_data(test_rom_path, 0x200000)

            # Test cache stats
            cache.get_cache_stats()

        except Exception as e:
            logger.debug(f"Cache simulation error: {e}")

    profiler.profile_operation("cache_operations", simulate_cache_operations)

    metrics = profiler.generate_comprehensive_report()
    profiler.stop_profiling()

    return metrics


if __name__ == "__main__":
    # Comprehensive profiling example
    print("Starting SpritePal Performance Analysis...")

    profiler = PerformanceProfiler()
    profiler.start_profiling()

    # Simulate some operations (replace with actual SpritePal operations)
    time.sleep(2)  # Simulate work

    # Generate and save comprehensive report
    metrics = profiler.generate_comprehensive_report()
    profiler.stop_profiling()

    # Save reports
    report_file, json_file = save_report(metrics)
    print(f"Performance analysis complete. Report saved to: {report_file}")

    # Quick summary
    print("\nQuick Summary:")
    print(format_report(metrics)[:2000] + "..." if len(format_report(metrics)) > 2000 else format_report(metrics))

    # Run specialized profiling
    print("\nRunning specialized profiling...")

    # Profile worker lifecycle
    print("Profiling worker lifecycle...")
    worker_metrics = profile_worker_lifecycle()
    worker_report, _ = save_report(worker_metrics, "worker_lifecycle_profile.txt")
    print(f"Worker lifecycle profile saved to: {worker_report}")

    # Profile manager access
    print("Profiling manager singleton access...")
    manager_metrics = profile_manager_singleton_access()
    manager_report, _ = save_report(manager_metrics, "manager_access_profile.txt")
    print(f"Manager access profile saved to: {manager_report}")

    # Profile ROM cache
    print("Profiling ROM cache operations...")
    cache_metrics = profile_rom_cache_operations()
    cache_report, _ = save_report(cache_metrics, "rom_cache_profile.txt")
    print(f"ROM cache profile saved to: {cache_report}")

    print("\nSpritePal performance analysis complete!")
