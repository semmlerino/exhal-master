#!/usr/bin/env python3
"""
Manual Offset Dialog Preview Performance Test

This script runs comprehensive performance analysis on the preview update
mechanism, measuring real-world performance characteristics during slider
interactions.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from performance_profiler import PreviewUpdateProfiler, analyze_debounce_timing_impact
from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from core.managers.registry import ManagerRegistry
from utils.logging_config import get_logger

logger = get_logger(__name__)


class PerformanceTestRunner:
    """Runs comprehensive performance tests on the manual offset dialog."""
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication([])
        self.dialog = None
        self.profiler = None
        self.results = {}
        
    def setup_test_environment(self):
        """Set up test environment with ROM data."""
        # Create dialog instance
        self.dialog = UnifiedManualOffsetDialog()
        
        # Set up mock ROM data
        rom_path = "/mock/test.sfc"
        rom_size = 0x400000  # 4MB ROM
        
        # Get managers
        registry = ManagerRegistry()
        extraction_manager = registry.get_extraction_manager()
        
        # Set ROM data
        self.dialog.set_rom_data(rom_path, rom_size, extraction_manager)
        
        logger.info("Test environment setup complete")
        
    def run_preview_update_analysis(self) -> dict:
        """Analyze preview update performance."""
        logger.info("Starting preview update analysis...")
        
        # Create profiler
        self.profiler = PreviewUpdateProfiler()
        
        # Instrument dialog
        self.profiler.instrument_dialog(self.dialog)
        
        # Show dialog
        self.dialog.show()
        
        # Results container
        results = {}
        
        # Test 1: Single preview update timing
        logger.info("Test 1: Single preview update timing")
        start_time = time.perf_counter()
        
        # Trigger preview update
        if hasattr(self.dialog, '_update_preview'):
            self.dialog._update_preview()
        
        single_update_time = (time.perf_counter() - start_time) * 1000
        results['single_update_ms'] = single_update_time
        
        # Test 2: Rapid slider movements
        logger.info("Test 2: Rapid slider movements (10 seconds)")
        
        rapid_results = {}
        self.profiler.profiling_complete.connect(
            lambda metrics: rapid_results.update({'metrics': metrics})
        )
        
        # Start rapid movement test
        self.profiler.start_performance_test(duration_seconds=10, slider_movements=100)
        
        # Wait for completion
        timeout = 15000  # 15 seconds
        elapsed = 0
        while 'metrics' not in rapid_results and elapsed < timeout:
            self.app.processEvents()
            time.sleep(0.1)
            elapsed += 100
        
        if 'metrics' in rapid_results:
            results['rapid_movement'] = rapid_results['metrics']
        else:
            logger.warning("Rapid movement test timed out")
            results['rapid_movement'] = None
        
        # Test 3: Worker thread overhead
        logger.info("Test 3: Worker thread creation/cleanup overhead")
        worker_results = self._test_worker_overhead()
        results['worker_overhead'] = worker_results
        
        # Test 4: Signal emission latency
        logger.info("Test 4: Signal emission latency")
        signal_results = self._test_signal_latency()
        results['signal_latency'] = signal_results
        
        # Test 5: Memory usage during operations
        logger.info("Test 5: Memory usage analysis")
        memory_results = self._test_memory_usage()
        results['memory_usage'] = memory_results
        
        logger.info("Preview update analysis complete")
        return results
    
    def _test_worker_overhead(self) -> dict:
        """Test worker thread creation and cleanup overhead."""
        from ui.rom_extraction.workers import SpritePreviewWorker
        from ui.common import WorkerManager
        from core.managers.registry import ManagerRegistry
        
        results = {}
        
        # Get ROM extractor
        registry = ManagerRegistry()
        extraction_manager = registry.get_extraction_manager()
        rom_extractor = extraction_manager.get_rom_extractor()
        
        # Test worker creation time
        creation_times = []
        cleanup_times = []
        
        for i in range(10):  # Test 10 worker creations
            # Creation timing
            start_time = time.perf_counter()
            
            worker = SpritePreviewWorker(
                "/mock/test.sfc", 
                0x200000 + i * 0x1000, 
                f"test_sprite_{i}", 
                rom_extractor, 
                None
            )
            
            creation_time = (time.perf_counter() - start_time) * 1000
            creation_times.append(creation_time)
            
            # Cleanup timing
            start_time = time.perf_counter()
            WorkerManager.cleanup_worker(worker, timeout=1000)
            cleanup_time = (time.perf_counter() - start_time) * 1000
            cleanup_times.append(cleanup_time)
        
        results['avg_creation_ms'] = sum(creation_times) / len(creation_times)
        results['max_creation_ms'] = max(creation_times)
        results['avg_cleanup_ms'] = sum(cleanup_times) / len(cleanup_times)
        results['max_cleanup_ms'] = max(cleanup_times)
        
        return results
    
    def _test_signal_latency(self) -> dict:
        """Test signal emission and handling latency."""
        from PyQt6.QtCore import pyqtSignal, QObject
        
        class TestSignalEmitter(QObject):
            test_signal = pyqtSignal(int)
        
        results = {}
        emission_times = []
        handling_times = []
        
        emitter = TestSignalEmitter()
        
        # Test signal handling
        def signal_handler(value):
            nonlocal handling_times
            end_time = time.perf_counter()
            handling_time = (end_time - handler_start_time) * 1000
            handling_times.append(handling_time)
        
        emitter.test_signal.connect(signal_handler)
        
        for i in range(100):  # Test 100 signal emissions
            # Emission timing
            start_time = time.perf_counter()
            
            handler_start_time = time.perf_counter()
            emitter.test_signal.emit(i)
            
            # Process events to ensure signal is handled
            self.app.processEvents()
            
            emission_time = (time.perf_counter() - start_time) * 1000
            emission_times.append(emission_time)
        
        results['avg_emission_ms'] = sum(emission_times) / len(emission_times) if emission_times else 0
        results['max_emission_ms'] = max(emission_times) if emission_times else 0
        results['avg_handling_ms'] = sum(handling_times) / len(handling_times) if handling_times else 0
        results['max_handling_ms'] = max(handling_times) if handling_times else 0
        
        return results
    
    def _test_memory_usage(self) -> dict:
        """Test memory usage during preview operations."""
        import psutil
        import gc
        
        process = psutil.Process()
        results = {}
        
        # Baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss
        
        # Memory during single preview
        if hasattr(self.dialog, '_update_preview'):
            self.dialog._update_preview()
            self.app.processEvents()
            
            single_preview_memory = process.memory_info().rss
            results['single_preview_delta_kb'] = (single_preview_memory - baseline_memory) / 1024
        
        # Memory during rapid updates
        peak_memory = baseline_memory
        
        for i in range(50):  # 50 rapid updates
            if hasattr(self.dialog, 'set_offset'):
                self.dialog.set_offset(0x200000 + i * 0x1000)
                self.app.processEvents()
                
                current_memory = process.memory_info().rss
                peak_memory = max(peak_memory, current_memory)
        
        results['rapid_updates_peak_delta_kb'] = (peak_memory - baseline_memory) / 1024
        
        # Memory after cleanup
        gc.collect()
        final_memory = process.memory_info().rss
        results['memory_leak_kb'] = (final_memory - baseline_memory) / 1024
        
        return results
    
    def test_debounce_configurations(self) -> dict:
        """Test different debounce timing configurations."""
        logger.info("Testing debounce configurations...")
        
        # Simulate different debounce timings
        configurations = [
            {"name": "Current (100ms)", "debounce_ms": 100},
            {"name": "Proposed (16ms)", "debounce_ms": 16},
            {"name": "Ultra-fast (8ms)", "debounce_ms": 8},
            {"name": "Conservative (200ms)", "debounce_ms": 200},
        ]
        
        results = {}
        
        for config in configurations:
            logger.info(f"Testing {config['name']}")
            
            # Simulate user interaction pattern
            update_count = 0
            responsiveness_score = 0
            
            # Simulate 1 second of slider dragging
            simulation_time_ms = 1000
            mouse_move_interval_ms = 10  # Very fast mouse movements
            
            last_update_time = 0
            
            for t in range(0, simulation_time_ms, mouse_move_interval_ms):
                # Check if enough time has passed for debounced update
                if t - last_update_time >= config['debounce_ms']:
                    update_count += 1
                    last_update_time = t
                    
                    # Score responsiveness (earlier updates = better)
                    delay = t - (t // mouse_move_interval_ms * mouse_move_interval_ms)
                    responsiveness_score += max(0, 100 - delay)
            
            # Calculate metrics
            updates_per_second = update_count / (simulation_time_ms / 1000)
            avg_responsiveness = responsiveness_score / max(1, update_count)
            
            results[config['name']] = {
                'updates_per_second': updates_per_second,
                'total_updates': update_count,
                'avg_responsiveness': avg_responsiveness,
                'debounce_ms': config['debounce_ms']
            }
        
        return results
    
    def analyze_blocking_operations(self) -> dict:
        """Identify operations that could block the UI thread."""
        logger.info("Analyzing blocking operations...")
        
        blocking_operations = []
        
        # Test 1: ROM data loading
        start_time = time.perf_counter()
        
        # Simulate ROM data access
        if hasattr(self.dialog, '_has_rom_data'):
            has_data = self.dialog._has_rom_data()
        
        rom_check_time = (time.perf_counter() - start_time) * 1000
        
        if rom_check_time > 1:  # > 1ms is potentially blocking
            blocking_operations.append({
                'operation': 'ROM data check',
                'time_ms': rom_check_time,
                'severity': 'medium' if rom_check_time < 5 else 'high'
            })
        
        # Test 2: Preview widget updates
        if hasattr(self.dialog, 'preview_widget') and self.dialog.preview_widget:
            start_time = time.perf_counter()
            
            # Simulate preview update
            test_data = bytes(64 * 64 // 2)  # 32x32 4bpp sprite
            self.dialog.preview_widget.load_sprite_from_4bpp(test_data, 32, 32, "test")
            
            preview_update_time = (time.perf_counter() - start_time) * 1000
            
            if preview_update_time > 5:  # > 5ms for UI update is slow
                blocking_operations.append({
                    'operation': 'Preview widget update',
                    'time_ms': preview_update_time,
                    'severity': 'medium' if preview_update_time < 16 else 'high'
                })
        
        # Test 3: Signal emission overhead
        start_time = time.perf_counter()
        
        # Emit offset changed signal
        if hasattr(self.dialog, 'offset_changed'):
            self.dialog.offset_changed.emit(0x200000)
            self.app.processEvents()
        
        signal_time = (time.perf_counter() - start_time) * 1000
        
        if signal_time > 2:  # > 2ms for signal emission is concerning
            blocking_operations.append({
                'operation': 'Signal emission and handling',
                'time_ms': signal_time,
                'severity': 'medium' if signal_time < 10 else 'high'
            })
        
        return {
            'blocking_operations': blocking_operations,
            'total_blocking_time': sum(op['time_ms'] for op in blocking_operations),
            'high_severity_count': len([op for op in blocking_operations if op['severity'] == 'high'])
        }
    
    def cleanup(self):
        """Clean up test resources."""
        if self.dialog:
            self.dialog.hide()
            self.dialog.deleteLater()
        
        if self.profiler:
            self.profiler.deleteLater()
    
    def generate_comprehensive_report(self, results: dict) -> str:
        """Generate comprehensive performance analysis report."""
        report = "MANUAL OFFSET DIALOG PERFORMANCE ANALYSIS REPORT\n"
        report += "=" * 60 + "\n\n"
        
        # Executive Summary
        report += "EXECUTIVE SUMMARY\n"
        report += "-" * 20 + "\n"
        
        # Identify critical issues
        critical_issues = []
        
        if 'single_update_ms' in results and results['single_update_ms'] > 16:
            critical_issues.append(f"Single preview update ({results['single_update_ms']:.1f}ms) exceeds 60 FPS target")
        
        if 'worker_overhead' in results and results['worker_overhead']['avg_creation_ms'] > 10:
            critical_issues.append(f"Worker creation overhead ({results['worker_overhead']['avg_creation_ms']:.1f}ms) is high")
        
        if 'memory_usage' in results and results['memory_usage']['memory_leak_kb'] > 1000:
            critical_issues.append(f"Memory leak detected ({results['memory_usage']['memory_leak_kb']:.1f}KB)")
        
        if critical_issues:
            report += "CRITICAL PERFORMANCE ISSUES:\n"
            for issue in critical_issues:
                report += f"• {issue}\n"
        else:
            report += "No critical performance issues detected.\n"
        
        report += "\n"
        
        # Detailed Results
        report += "DETAILED PERFORMANCE ANALYSIS\n"
        report += "-" * 35 + "\n\n"
        
        # 1. Preview Update Performance
        if 'single_update_ms' in results:
            report += f"1. SINGLE PREVIEW UPDATE\n"
            report += f"   Time: {results['single_update_ms']:.2f}ms\n"
            report += f"   Target: 16.67ms (60 FPS)\n"
            if results['single_update_ms'] > 16.67:
                report += "   ⚠️  EXCEEDS 60 FPS TARGET\n"
            else:
                report += "   ✅ Within 60 FPS target\n"
            report += "\n"
        
        # 2. Rapid Movement Performance
        if 'rapid_movement' in results and results['rapid_movement']:
            metrics = results['rapid_movement']
            report += f"2. RAPID SLIDER MOVEMENT (10 seconds)\n"
            report += f"   Update Frequency: {metrics.update_frequency:.1f} Hz\n"
            report += f"   Frame Drops: {metrics.frame_drops}\n"
            report += f"   Average Preview Time: {metrics.preview_update_time:.2f}ms\n"
            report += f"   Memory Delta: {(metrics.memory_after - metrics.memory_before) / 1024:.1f}KB\n"
            
            if metrics.update_frequency < 30:
                report += "   ⚠️  UPDATE FREQUENCY BELOW 30 FPS\n"
            elif metrics.update_frequency >= 60:
                report += "   ✅ Excellent update frequency\n"
            else:
                report += "   ✅ Acceptable update frequency\n"
            report += "\n"
        
        # 3. Worker Thread Overhead
        if 'worker_overhead' in results:
            worker = results['worker_overhead']
            report += f"3. WORKER THREAD OVERHEAD\n"
            report += f"   Average Creation: {worker['avg_creation_ms']:.2f}ms\n"
            report += f"   Maximum Creation: {worker['max_creation_ms']:.2f}ms\n"
            report += f"   Average Cleanup: {worker['avg_cleanup_ms']:.2f}ms\n"
            report += f"   Maximum Cleanup: {worker['max_cleanup_ms']:.2f}ms\n"
            
            if worker['avg_creation_ms'] > 10:
                report += "   ⚠️  HIGH WORKER CREATION OVERHEAD\n"
            else:
                report += "   ✅ Acceptable worker creation overhead\n"
            report += "\n"
        
        # 4. Signal Latency
        if 'signal_latency' in results:
            signal = results['signal_latency']
            report += f"4. SIGNAL EMISSION LATENCY\n"
            report += f"   Average Emission: {signal['avg_emission_ms']:.3f}ms\n"
            report += f"   Maximum Emission: {signal['max_emission_ms']:.3f}ms\n"
            report += f"   Average Handling: {signal['avg_handling_ms']:.3f}ms\n"
            report += f"   Maximum Handling: {signal['max_handling_ms']:.3f}ms\n"
            
            if signal['avg_emission_ms'] > 1:
                report += "   ⚠️  HIGH SIGNAL EMISSION LATENCY\n"
            else:
                report += "   ✅ Low signal emission latency\n"
            report += "\n"
        
        # 5. Memory Usage
        if 'memory_usage' in results:
            memory = results['memory_usage']
            report += f"5. MEMORY USAGE ANALYSIS\n"
            report += f"   Single Preview Delta: {memory['single_preview_delta_kb']:.1f}KB\n"
            report += f"   Rapid Updates Peak: {memory['rapid_updates_peak_delta_kb']:.1f}KB\n"
            report += f"   Memory Leak: {memory['memory_leak_kb']:.1f}KB\n"
            
            if memory['memory_leak_kb'] > 1000:
                report += "   ⚠️  SIGNIFICANT MEMORY LEAK DETECTED\n"
            elif memory['memory_leak_kb'] > 100:
                report += "   ⚠️  Minor memory leak detected\n"
            else:
                report += "   ✅ No significant memory leaks\n"
            report += "\n"
        
        # 6. Debounce Configuration Analysis
        if 'debounce_test' in results:
            report += f"6. DEBOUNCE TIMING ANALYSIS\n"
            for config_name, config_data in results['debounce_test'].items():
                report += f"   {config_name}:\n"
                report += f"     Updates/sec: {config_data['updates_per_second']:.1f}\n"
                report += f"     Responsiveness: {config_data['avg_responsiveness']:.1f}\n"
            report += "\n"
        
        # 7. Blocking Operations
        if 'blocking_operations' in results:
            blocking = results['blocking_operations']
            report += f"7. BLOCKING OPERATIONS ANALYSIS\n"
            report += f"   Total Blocking Time: {blocking['total_blocking_time']:.2f}ms\n"
            report += f"   High Severity Issues: {blocking['high_severity_count']}\n"
            
            if blocking['blocking_operations']:
                report += "   Detected Issues:\n"
                for op in blocking['blocking_operations']:
                    severity_icon = "🔴" if op['severity'] == 'high' else "🟡"
                    report += f"     {severity_icon} {op['operation']}: {op['time_ms']:.2f}ms\n"
            else:
                report += "   ✅ No blocking operations detected\n"
            report += "\n"
        
        # Recommendations
        report += "PERFORMANCE OPTIMIZATION RECOMMENDATIONS\n"
        report += "-" * 40 + "\n"
        
        recommendations = []
        
        if 'single_update_ms' in results and results['single_update_ms'] > 16:
            recommendations.append("• Optimize preview generation algorithm for sub-16ms performance")
        
        if 'worker_overhead' in results and results['worker_overhead']['avg_creation_ms'] > 10:
            recommendations.append("• Implement worker thread pool to reduce creation overhead")
        
        if 'memory_usage' in results and results['memory_usage']['memory_leak_kb'] > 100:
            recommendations.append("• Investigate and fix memory leaks in preview system")
        
        if 'debounce_test' in results:
            best_config = max(results['debounce_test'].items(), 
                            key=lambda x: x[1]['avg_responsiveness'])
            recommendations.append(f"• Consider using {best_config[0]} debounce configuration")
        
        # Always recommend these optimizations
        recommendations.extend([
            "• Implement preview caching with LRU eviction policy",
            "• Use 16ms debounce timing for 60 FPS responsiveness",
            "• Implement request cancellation for stale preview updates",
            "• Consider using QOpenGLWidget for hardware-accelerated preview rendering"
        ])
        
        for rec in recommendations:
            report += f"{rec}\n"
        
        return report


def main():
    """Run comprehensive performance analysis."""
    logger.info("Starting Manual Offset Dialog Performance Analysis")
    
    # Create test runner
    runner = PerformanceTestRunner()
    
    try:
        # Setup test environment
        runner.setup_test_environment()
        
        # Run performance analysis
        results = runner.run_preview_update_analysis()
        
        # Test debounce configurations
        results['debounce_test'] = runner.test_debounce_configurations()
        
        # Analyze blocking operations
        results['blocking_operations'] = runner.analyze_blocking_operations()
        
        # Generate comprehensive report
        report = runner.generate_comprehensive_report(results)
        
        # Save report
        report_path = project_root / "PERFORMANCE_ANALYSIS_REPORT.md"
        with open(report_path, 'w') as f:
            f.write(report)
        
        # Also run standalone debounce analysis
        debounce_report = analyze_debounce_timing_impact()
        
        # Print summary
        print("Performance Analysis Complete!")
        print(f"Full report saved to: {report_path}")
        print("\n" + "="*60)
        print("SUMMARY OF KEY FINDINGS:")
        print("="*60)
        
        if 'single_update_ms' in results:
            print(f"Single Preview Update: {results['single_update_ms']:.2f}ms")
        
        if 'worker_overhead' in results:
            print(f"Worker Creation Overhead: {results['worker_overhead']['avg_creation_ms']:.2f}ms")
        
        if 'memory_usage' in results:
            print(f"Memory Leak: {results['memory_usage']['memory_leak_kb']:.1f}KB")
        
        print("\nDebounce Timing Analysis:")
        print(debounce_report)
        
    except Exception as e:
        logger.error(f"Performance analysis failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        runner.cleanup()
        
        # Keep app running briefly to ensure cleanup
        QTimer.singleShot(1000, runner.app.quit)
        runner.app.exec()


if __name__ == "__main__":
    main()