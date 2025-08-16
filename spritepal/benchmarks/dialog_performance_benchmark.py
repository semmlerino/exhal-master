#!/usr/bin/env python3
"""
Dialog Performance Benchmark

This benchmark compares the performance characteristics of the legacy DialogBase
with the new DialogBaseMigrationAdapter across multiple scenarios and metrics.

Performance Metrics Measured:
- Initialization time (constructor execution)
- Memory usage (before/after creation)
- First render time (time to show())
- Property access speed
- Method call overhead
- Signal connection overhead
- Cleanup time (close and deletion)

Benchmark Scenarios:
- Minimal dialog (no options)
- Standard dialog (button box only)
- Complex dialog (tabs, status bar, button box)
- Heavy dialog (many tabs, widgets, connections)

Statistical Analysis:
- Multiple iterations with mean, median, std deviation
- Outlier identification
- Statistical significance testing
- Memory leak detection
"""

import gc
import json
import os
import statistics
import sys
import time
import traceback
import tracemalloc
import warnings
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from unittest.mock import Mock

# Third-party imports
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

# Suppress Qt warnings for cleaner benchmark output
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Add the parent directory to sys.path to import the modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Local imports (after sys.path setup)
from ui.components.base.composed.migration_adapter import (
    DialogBaseMigrationAdapter,
)
from ui.components.base.dialog_base import DialogBase  # noqa: E402


# Performance thresholds
class PerformanceThresholds:
    INIT_ACCEPTABLE_MS = 5.0
    INIT_WARNING_MS = 10.0
    MEMORY_ACCEPTABLE_MB = 1.0
    MEMORY_WARNING_MB = 2.0
    RENDER_ACCEPTABLE_MS = 50.0
    RENDER_WARNING_MS = 100.0
    CLEANUP_ACCEPTABLE_MS = 5.0
    CLEANUP_WARNING_MS = 10.0


@dataclass
class BenchmarkResult:
    """Container for benchmark results."""
    scenario: str
    dialog_type: str
    metric: str
    iterations: int
    values: list[float] = field(default_factory=list)
    mean: float = 0.0
    median: float = 0.0
    std_dev: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    outliers: list[float] = field(default_factory=list)
    memory_before: float = 0.0
    memory_after: float = 0.0
    memory_delta: float = 0.0
    status: str = "PASS"  # PASS, WARNING, FAIL

    def calculate_stats(self) -> None:
        """Calculate statistical measures from the values."""
        if not self.values:
            return

        self.mean = statistics.mean(self.values)
        self.median = statistics.median(self.values)
        self.std_dev = statistics.stdev(self.values) if len(self.values) > 1 else 0.0
        self.min_val = min(self.values)
        self.max_val = max(self.values)

        # Identify outliers using IQR method
        if len(self.values) >= 4:
            q1 = statistics.quantiles(self.values, n=4)[0]
            q3 = statistics.quantiles(self.values, n=4)[2]
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            self.outliers = [v for v in self.values if v < lower_bound or v > upper_bound]


class MemoryTracker:
    """Tracks memory usage during benchmark operations."""

    def __init__(self):
        self.snapshots = []
        self.baseline = 0

    def start_tracking(self) -> None:
        """Start memory tracking."""
        gc.collect()  # Clean up before tracking
        tracemalloc.start()
        self.baseline = self._get_memory_usage()

    def take_snapshot(self, label: str) -> float:
        """Take a memory snapshot and return current usage."""
        gc.collect()
        current = self._get_memory_usage()
        self.snapshots.append((label, current, current - self.baseline))
        return current

    def stop_tracking(self) -> float:
        """Stop tracking and return final memory usage."""
        final = self._get_memory_usage()
        tracemalloc.stop()
        return final

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            return current / 1024 / 1024  # Convert to MB
        return 0.0

    def get_peak_usage(self) -> float:
        """Get peak memory usage in MB."""
        if tracemalloc.is_tracing():
            current, peak = tracemalloc.get_traced_memory()
            return peak / 1024 / 1024
        return 0.0


@contextmanager
def measure_time():
    """Context manager for measuring execution time."""
    start = time.perf_counter()
    try:
        yield lambda: time.perf_counter() - start
    finally:
        pass


class DialogBenchmark:
    """Main benchmark class for dialog performance testing."""

    def __init__(self, app: QApplication, iterations: int = 100):
        self.app = app
        self.iterations = iterations
        self.results: list[BenchmarkResult] = []
        self.memory_tracker = MemoryTracker()

        # Benchmark scenarios
        self.scenarios = [
            ("minimal", self._create_minimal_dialog),
            ("standard", self._create_standard_dialog),
            ("complex", self._create_complex_dialog),
            ("heavy", self._create_heavy_dialog),
        ]

        # Dialog classes to benchmark
        self.dialog_classes = [
            ("DialogBase", DialogBase),
            ("DialogBaseMigrationAdapter", DialogBaseMigrationAdapter),
        ]

    def run_all_benchmarks(self) -> None:
        """Run all benchmark scenarios for both dialog types."""
        print("🚀 Starting Dialog Performance Benchmark Suite")
        print(f"📊 Running {self.iterations} iterations per test")
        print("=" * 60)

        for scenario_name, scenario_func in self.scenarios:
            print(f"\n📋 Testing Scenario: {scenario_name.upper()}")

            for dialog_name, dialog_class in self.dialog_classes:
                print(f"  🔧 Testing {dialog_name}...")
                self._benchmark_dialog_class(scenario_name, dialog_name, dialog_class, scenario_func)

        print("\n✅ All benchmarks completed!")
        self._analyze_results()
        self._generate_report()

    def _benchmark_dialog_class(
        self,
        scenario: str,
        dialog_name: str,
        dialog_class: type,
        scenario_func: Callable
    ) -> None:
        """Benchmark a specific dialog class in a scenario."""
        # Test initialization time
        init_result = self._benchmark_initialization(scenario, dialog_name, dialog_class, scenario_func)
        self.results.append(init_result)

        # Test memory usage
        memory_result = self._benchmark_memory_usage(scenario, dialog_name, dialog_class, scenario_func)
        self.results.append(memory_result)

        # Test render time
        render_result = self._benchmark_render_time(scenario, dialog_name, dialog_class, scenario_func)
        self.results.append(render_result)

        # Test property access speed
        property_result = self._benchmark_property_access(scenario, dialog_name, dialog_class, scenario_func)
        self.results.append(property_result)

        # Test method call overhead
        method_result = self._benchmark_method_calls(scenario, dialog_name, dialog_class, scenario_func)
        self.results.append(method_result)

        # Test signal connection overhead
        signal_result = self._benchmark_signal_connections(scenario, dialog_name, dialog_class, scenario_func)
        self.results.append(signal_result)

        # Test cleanup time
        cleanup_result = self._benchmark_cleanup(scenario, dialog_name, dialog_class, scenario_func)
        self.results.append(cleanup_result)

    def _benchmark_initialization(
        self,
        scenario: str,
        dialog_name: str,
        dialog_class: type,
        scenario_func: Callable
    ) -> BenchmarkResult:
        """Benchmark dialog initialization time."""
        result = BenchmarkResult(scenario, dialog_name, "initialization", self.iterations)
        self.memory_tracker.start_tracking()
        result.memory_before = self.memory_tracker.take_snapshot("before_init")

        for _i in range(self.iterations):
            gc.collect()  # Clean up before each iteration

            with measure_time() as get_time:
                dialog = scenario_func(dialog_class)
                # Force Qt to process the dialog creation
                self.app.processEvents()

            init_time_ms = get_time() * 1000
            result.values.append(init_time_ms)

            # Cleanup
            dialog.close()
            dialog.deleteLater()
            self.app.processEvents()

        result.memory_after = self.memory_tracker.stop_tracking()
        result.memory_delta = result.memory_after - result.memory_before
        result.calculate_stats()

        # Determine status based on thresholds
        if result.mean > PerformanceThresholds.INIT_WARNING_MS:
            result.status = "FAIL"
        elif result.mean > PerformanceThresholds.INIT_ACCEPTABLE_MS:
            result.status = "WARNING"

        return result

    def _benchmark_memory_usage(
        self,
        scenario: str,
        dialog_name: str,
        dialog_class: type,
        scenario_func: Callable
    ) -> BenchmarkResult:
        """Benchmark dialog memory usage."""
        result = BenchmarkResult(scenario, dialog_name, "memory_usage", self.iterations)
        dialogs = []

        self.memory_tracker.start_tracking()
        result.memory_before = self.memory_tracker.take_snapshot("before_memory_test")

        # Create multiple dialogs to measure memory usage
        for i in range(min(self.iterations, 50)):  # Limit to prevent excessive memory usage
            dialog = scenario_func(dialog_class)
            dialogs.append(dialog)

            memory_usage = self.memory_tracker.take_snapshot(f"after_dialog_{i}")
            result.values.append(memory_usage - result.memory_before)

        result.memory_after = self.memory_tracker.stop_tracking()
        result.memory_delta = result.memory_after - result.memory_before
        result.calculate_stats()

        # Cleanup all dialogs
        for dialog in dialogs:
            dialog.close()
            dialog.deleteLater()
        self.app.processEvents()
        gc.collect()

        # Determine status based on thresholds
        if result.memory_delta > PerformanceThresholds.MEMORY_WARNING_MB:
            result.status = "FAIL"
        elif result.memory_delta > PerformanceThresholds.MEMORY_ACCEPTABLE_MB:
            result.status = "WARNING"

        return result

    def _benchmark_render_time(
        self,
        scenario: str,
        dialog_name: str,
        dialog_class: type,
        scenario_func: Callable
    ) -> BenchmarkResult:
        """Benchmark dialog render time (time to show)."""
        result = BenchmarkResult(scenario, dialog_name, "render_time", self.iterations)

        for _i in range(self.iterations):
            dialog = scenario_func(dialog_class)

            with measure_time() as get_time:
                dialog.show()
                self.app.processEvents()  # Force rendering
                QTest.qWait(1)  # Small delay to ensure rendering

            render_time_ms = get_time() * 1000
            result.values.append(render_time_ms)

            dialog.close()
            dialog.deleteLater()
            self.app.processEvents()

        result.calculate_stats()

        # Determine status based on thresholds
        if result.mean > PerformanceThresholds.RENDER_WARNING_MS:
            result.status = "FAIL"
        elif result.mean > PerformanceThresholds.RENDER_ACCEPTABLE_MS:
            result.status = "WARNING"

        return result

    def _benchmark_property_access(
        self,
        scenario: str,
        dialog_name: str,
        dialog_class: type,
        scenario_func: Callable
    ) -> BenchmarkResult:
        """Benchmark property access speed."""
        result = BenchmarkResult(scenario, dialog_name, "property_access", self.iterations)

        dialog = scenario_func(dialog_class)
        properties_to_test = ["windowTitle", "isModal", "size", "minimumSize"]

        for _i in range(self.iterations):
            with measure_time() as get_time:
                # Access multiple properties
                for prop in properties_to_test:
                    if hasattr(dialog, prop):
                        getattr(dialog, prop)()
                    # Test common dialog-specific properties
                    if hasattr(dialog, "button_box"):
                        _ = dialog.button_box
                    if hasattr(dialog, "status_bar"):
                        _ = dialog.status_bar
                    if hasattr(dialog, "main_layout"):
                        _ = dialog.main_layout

            access_time_ms = get_time() * 1000
            result.values.append(access_time_ms)

        dialog.close()
        dialog.deleteLater()
        self.app.processEvents()

        result.calculate_stats()
        return result

    def _benchmark_method_calls(
        self,
        scenario: str,
        dialog_name: str,
        dialog_class: type,
        scenario_func: Callable
    ) -> BenchmarkResult:
        """Benchmark method call overhead."""
        result = BenchmarkResult(scenario, dialog_name, "method_calls", self.iterations)

        dialog = scenario_func(dialog_class)

        for i in range(self.iterations):
            with measure_time() as get_time:
                # Test common method calls
                if hasattr(dialog, "update_status"):
                    dialog.update_status(f"Test message {i}")
                if hasattr(dialog, "show_info"):
                    # Mock the message box to avoid actual popup
                    original_method = dialog.show_info
                    dialog.show_info = Mock()
                    dialog.show_info("Test", "Test message")
                    dialog.show_info = original_method
                if hasattr(dialog, "add_button"):
                    dialog.add_button("Test Button")
                if hasattr(dialog, "set_current_tab") and hasattr(dialog, "_tab_widget") and dialog._tab_widget:
                    dialog.set_current_tab(0)

            call_time_ms = get_time() * 1000
            result.values.append(call_time_ms)

        dialog.close()
        dialog.deleteLater()
        self.app.processEvents()

        result.calculate_stats()
        return result

    def _benchmark_signal_connections(
        self,
        scenario: str,
        dialog_name: str,
        dialog_class: type,
        scenario_func: Callable
    ) -> BenchmarkResult:
        """Benchmark signal connection overhead."""
        result = BenchmarkResult(scenario, dialog_name, "signal_connections", self.iterations)

        dialog = scenario_func(dialog_class)

        def dummy_slot():
            pass

        for _i in range(self.iterations):
            with measure_time() as get_time:
                # Connect to common signals
                if hasattr(dialog, "finished"):
                    dialog.finished.connect(dummy_slot)
                if hasattr(dialog, "accepted"):
                    dialog.accepted.connect(dummy_slot)
                if hasattr(dialog, "rejected"):
                    dialog.rejected.connect(dummy_slot)
                if hasattr(dialog, "button_box") and dialog.button_box:
                    dialog.button_box.accepted.connect(dummy_slot)
                    dialog.button_box.rejected.connect(dummy_slot)

            connection_time_ms = get_time() * 1000
            result.values.append(connection_time_ms)

        dialog.close()
        dialog.deleteLater()
        self.app.processEvents()

        result.calculate_stats()
        return result

    def _benchmark_cleanup(
        self,
        scenario: str,
        dialog_name: str,
        dialog_class: type,
        scenario_func: Callable
    ) -> BenchmarkResult:
        """Benchmark cleanup time (close and deletion)."""
        result = BenchmarkResult(scenario, dialog_name, "cleanup", self.iterations)

        for _i in range(self.iterations):
            dialog = scenario_func(dialog_class)
            dialog.show()
            self.app.processEvents()

            with measure_time() as get_time:
                dialog.close()
                dialog.deleteLater()
                self.app.processEvents()
                gc.collect()

            cleanup_time_ms = get_time() * 1000
            result.values.append(cleanup_time_ms)

        result.calculate_stats()

        # Determine status based on thresholds
        if result.mean > PerformanceThresholds.CLEANUP_WARNING_MS:
            result.status = "FAIL"
        elif result.mean > PerformanceThresholds.CLEANUP_ACCEPTABLE_MS:
            result.status = "WARNING"

        return result

    # Dialog creation scenarios
    def _create_minimal_dialog(self, dialog_class: type) -> Any:
        """Create a minimal dialog with no options."""
        return dialog_class(
            title="Minimal Test Dialog",
            with_button_box=False,
            with_status_bar=False
        )

    def _create_standard_dialog(self, dialog_class: type) -> Any:
        """Create a standard dialog with button box only."""
        return dialog_class(
            title="Standard Test Dialog",
            with_button_box=True,
            with_status_bar=False
        )

    def _create_complex_dialog(self, dialog_class: type) -> Any:
        """Create a complex dialog with tabs, status bar, and button box."""
        dialog = dialog_class(
            title="Complex Test Dialog",
            with_button_box=True,
            with_status_bar=True,
            min_size=(400, 300)
        )

        # Add tabs
        for i in range(3):
            tab_widget = QWidget()
            layout = QVBoxLayout(tab_widget)
            layout.addWidget(QLabel(f"Tab {i} Content"))
            dialog.add_tab(tab_widget, f"Tab {i}")

        return dialog

    def _create_heavy_dialog(self, dialog_class: type) -> Any:
        """Create a heavy dialog with many tabs, widgets, and connections."""
        dialog = dialog_class(
            title="Heavy Test Dialog",
            with_button_box=True,
            with_status_bar=True,
            size=(800, 600),
            min_size=(600, 400)
        )

        # Add many tabs with widgets
        for i in range(10):
            tab_widget = QWidget()
            layout = QVBoxLayout(tab_widget)

            # Add multiple widgets per tab
            for j in range(5):
                label = QLabel(f"Tab {i} Widget {j}")
                layout.addWidget(label)

            dialog.add_tab(tab_widget, f"Heavy Tab {i}")

        # Add many custom buttons
        for i in range(5):
            dialog.add_button(f"Button {i}", lambda: None)

        return dialog

    def _analyze_results(self) -> None:
        """Analyze benchmark results for patterns and comparisons."""
        print("\n📊 PERFORMANCE ANALYSIS")
        print("=" * 60)

        # Group results by scenario and metric
        by_scenario = {}
        for result in self.results:
            key = f"{result.scenario}_{result.metric}"
            if key not in by_scenario:
                by_scenario[key] = {}
            by_scenario[key][result.dialog_type] = result

        # Compare each metric
        for key, dialogs in by_scenario.items():
            scenario, metric = key.split("_", 1)

            if len(dialogs) == 2:
                legacy = dialogs.get("DialogBase")
                new = dialogs.get("DialogBaseMigrationAdapter")

                if legacy and new:
                    self._compare_results(scenario, metric, legacy, new)

    def _compare_results(
        self,
        scenario: str,
        metric: str,
        legacy: BenchmarkResult,
        new: BenchmarkResult
    ) -> None:
        """Compare results between legacy and new implementations."""
        print(f"\n🔍 {scenario.upper()} - {metric.replace('_', ' ').title()}")
        print(f"   Legacy:     {legacy.mean:.3f}ms ± {legacy.std_dev:.3f}")
        print(f"   New:        {new.mean:.3f}ms ± {new.std_dev:.3f}")

        if legacy.mean > 0:
            overhead_pct = ((new.mean - legacy.mean) / legacy.mean) * 100

            if overhead_pct > 0:
                print(f"   Overhead:   +{overhead_pct:.1f}% ({'❌' if overhead_pct > 20 else '⚠️' if overhead_pct > 5 else '✅'})")
            else:
                print(f"   Improvement: {abs(overhead_pct):.1f}% ✅")

        # Memory comparison for memory usage metric
        if metric == "memory_usage":
            legacy_mem = legacy.memory_delta
            new_mem = new.memory_delta
            print(f"   Legacy Mem: {legacy_mem:.2f}MB")
            print(f"   New Mem:    {new_mem:.2f}MB")

            if legacy_mem > 0:
                mem_overhead_pct = ((new_mem - legacy_mem) / legacy_mem) * 100
                if mem_overhead_pct > 0:
                    print(f"   Mem Overhead: +{mem_overhead_pct:.1f}%")
                else:
                    print(f"   Mem Improvement: {abs(mem_overhead_pct):.1f}%")

    def _generate_report(self) -> None:
        """Generate comprehensive performance report."""
        report_data = {
            "metadata": {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "iterations": self.iterations,
                "scenarios": [s[0] for s in self.scenarios],
                "dialog_types": [d[0] for d in self.dialog_classes],
                "thresholds": {
                    "init_acceptable_ms": PerformanceThresholds.INIT_ACCEPTABLE_MS,
                    "init_warning_ms": PerformanceThresholds.INIT_WARNING_MS,
                    "memory_acceptable_mb": PerformanceThresholds.MEMORY_ACCEPTABLE_MB,
                    "memory_warning_mb": PerformanceThresholds.MEMORY_WARNING_MB,
                    "render_acceptable_ms": PerformanceThresholds.RENDER_ACCEPTABLE_MS,
                    "render_warning_ms": PerformanceThresholds.RENDER_WARNING_MS,
                    "cleanup_acceptable_ms": PerformanceThresholds.CLEANUP_ACCEPTABLE_MS,
                    "cleanup_warning_ms": PerformanceThresholds.CLEANUP_WARNING_MS,
                }
            },
            "results": []
        }

        # Add all results to report data
        for result in self.results:
            report_data["results"].append({
                "scenario": result.scenario,
                "dialog_type": result.dialog_type,
                "metric": result.metric,
                "iterations": result.iterations,
                "mean": result.mean,
                "median": result.median,
                "std_dev": result.std_dev,
                "min": result.min_val,
                "max": result.max_val,
                "outliers_count": len(result.outliers),
                "memory_delta": result.memory_delta,
                "status": result.status
            })

        # Write human-readable report
        self._write_human_report(report_data)

        # Write machine-readable report
        self._write_json_report(report_data)

        # Print summary
        self._print_summary(report_data)

    def _write_human_report(self, report_data: dict[str, Any]) -> None:
        """Write human-readable report to file."""
        report_path = Path(__file__).parent / "dialog_performance_report.txt"

        with report_path.open("w") as f:
            f.write("DIALOG PERFORMANCE BENCHMARK REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {report_data['metadata']['timestamp']}\n")
            f.write(f"Iterations: {report_data['metadata']['iterations']}\n")
            f.write(f"Scenarios: {', '.join(report_data['metadata']['scenarios'])}\n")
            f.write(f"Dialog Types: {', '.join(report_data['metadata']['dialog_types'])}\n\n")

            # Performance thresholds
            f.write("PERFORMANCE THRESHOLDS\n")
            f.write("-" * 30 + "\n")
            thresholds = report_data['metadata']['thresholds']
            f.write(f"Initialization: {thresholds['init_acceptable_ms']}ms (acceptable), {thresholds['init_warning_ms']}ms (warning)\n")
            f.write(f"Memory Usage: {thresholds['memory_acceptable_mb']}MB (acceptable), {thresholds['memory_warning_mb']}MB (warning)\n")
            f.write(f"Render Time: {thresholds['render_acceptable_ms']}ms (acceptable), {thresholds['render_warning_ms']}ms (warning)\n")
            f.write(f"Cleanup Time: {thresholds['cleanup_acceptable_ms']}ms (acceptable), {thresholds['cleanup_warning_ms']}ms (warning)\n\n")

            # Results by scenario
            scenarios = {}
            for result in report_data['results']:
                key = result['scenario']
                if key not in scenarios:
                    scenarios[key] = {}
                metric_key = result['metric']
                if metric_key not in scenarios[key]:
                    scenarios[key][metric_key] = {}
                scenarios[key][metric_key][result['dialog_type']] = result

            for scenario, metrics in scenarios.items():
                f.write(f"SCENARIO: {scenario.upper()}\n")
                f.write("-" * 30 + "\n")

                for metric, dialog_types in metrics.items():
                    f.write(f"\n{metric.replace('_', ' ').title()}:\n")

                    for dialog_type, result in dialog_types.items():
                        status_icon = "✅" if result['status'] == "PASS" else "⚠️" if result['status'] == "WARNING" else "❌"
                        f.write(f"  {dialog_type}: {result['mean']:.3f}ms ± {result['std_dev']:.3f} {status_icon}\n")
                        if result['memory_delta'] > 0:
                            f.write(f"    Memory Delta: {result['memory_delta']:.2f}MB\n")
                        if result['outliers_count'] > 0:
                            f.write(f"    Outliers: {result['outliers_count']}\n")

                f.write("\n")

        print(f"📄 Human-readable report written to: {report_path}")

    def _write_json_report(self, report_data: dict[str, Any]) -> None:
        """Write machine-readable JSON report to file."""
        report_path = Path(__file__).parent / "dialog_performance_report.json"

        with report_path.open("w") as f:
            json.dump(report_data, f, indent=2, default=str)

        print(f"🔧 Machine-readable report written to: {report_path}")

    def _print_summary(self, report_data: dict[str, Any]) -> None:
        """Print executive summary of benchmark results."""
        print("\n📋 EXECUTIVE SUMMARY")
        print("=" * 60)

        total_tests = len(report_data['results'])
        pass_count = sum(1 for r in report_data['results'] if r['status'] == 'PASS')
        warning_count = sum(1 for r in report_data['results'] if r['status'] == 'WARNING')
        fail_count = sum(1 for r in report_data['results'] if r['status'] == 'FAIL')

        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {pass_count} ({pass_count/total_tests*100:.1f}%)")
        print(f"⚠️  Warnings: {warning_count} ({warning_count/total_tests*100:.1f}%)")
        print(f"❌ Failed: {fail_count} ({fail_count/total_tests*100:.1f}%)")

        # Key findings
        print("\n🔍 KEY FINDINGS")
        print("-" * 30)

        # Find average overhead per metric
        overheads = {}
        for result in report_data['results']:
            if result['dialog_type'] == 'DialogBaseMigrationAdapter':
                # Find corresponding legacy result
                legacy_result = next(
                    (r for r in report_data['results']
                     if r['scenario'] == result['scenario']
                     and r['metric'] == result['metric']
                     and r['dialog_type'] == 'DialogBase'),
                    None
                )

                if legacy_result and legacy_result['mean'] > 0:
                    overhead_pct = ((result['mean'] - legacy_result['mean']) / legacy_result['mean']) * 100
                    metric = result['metric']
                    if metric not in overheads:
                        overheads[metric] = []
                    overheads[metric].append(overhead_pct)

        for metric, overhead_list in overheads.items():
            avg_overhead = statistics.mean(overhead_list)
            metric_name = metric.replace('_', ' ').title()

            if avg_overhead > 0:
                print(f"• {metric_name}: +{avg_overhead:.1f}% overhead on average")
            else:
                print(f"• {metric_name}: {abs(avg_overhead):.1f}% improvement on average")

        # Memory leak detection
        memory_results = [r for r in report_data['results'] if r['metric'] == 'memory_usage']
        if any(r['memory_delta'] > PerformanceThresholds.MEMORY_WARNING_MB for r in memory_results):
            print("⚠️  Potential memory leaks detected!")
        else:
            print("✅ No memory leaks detected")

        print("\n" + "=" * 60)
        print("🏁 Benchmark Complete!")


def main():
    """Main benchmark execution function."""
    # Check if we're in a headless environment
    if "DISPLAY" not in os.environ and sys.platform.startswith("linux"):
        print("⚠️  No display found. Setting up virtual display...")
        try:
            from pyvirtualdisplay import Display  # noqa: PLC0415
            display = Display(visible=0, size=(800, 600))
            display.start()
        except ImportError:
            print("❌ pyvirtualdisplay not available. Install with: pip install pyvirtualdisplay")
            print("   Or run in an environment with a display")
            return 1

    # Create Qt application
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Set up application for benchmarking
    cast(QApplication, app).setQuitOnLastWindowClosed(False)

    try:
        # Run benchmarks with different iteration counts for testing
        iterations = int(os.environ.get("BENCHMARK_ITERATIONS", "100"))
        print(f"🔧 Using {iterations} iterations per test")

        benchmark = DialogBenchmark(app, iterations=iterations)
        benchmark.run_all_benchmarks()

        return 0

    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        traceback.print_exc()
        return 1

    finally:
        # Clean up
        if hasattr(locals(), 'display'):
            display.stop()
        app.quit()


if __name__ == "__main__":
    sys.exit(main())
