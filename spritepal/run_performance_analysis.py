#!/usr/bin/env python3
"""
Run comprehensive performance analysis on SpritePal components.

This script exercises the major performance-critical paths in SpritePal:
1. Manager initialization and singleton access
2. Worker thread lifecycle and cleanup
3. ROM cache operations and efficiency
4. Qt widget creation and destruction
5. Memory usage patterns during sprite operations
6. I/O patterns and disk access efficiency
"""

import sys
import time
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from performance_profiler import PerformanceProfiler, save_report, format_report
from utils.logging_config import get_logger

logger = get_logger(__name__)


def profile_manager_initialization():
    """Profile manager system initialization performance"""
    logger.info("Profiling manager initialization...")
    
    profiler = PerformanceProfiler()
    profiler.start_profiling()
    
    def initialize_managers():
        """Initialize manager system"""
        try:
            from core.managers.registry import initialize_managers, cleanup_managers, get_registry
            
            # Clean start
            cleanup_managers()
            
            # Profile initialization
            initialize_managers("PerformanceTest")
            
            # Test manager access patterns
            registry = get_registry()
            
            # Test repeated access (singleton performance)
            for _ in range(100):
                try:
                    registry.get_session_manager()
                    registry.get_extraction_manager()
                    registry.get_injection_manager()
                except Exception:
                    pass  # Expected if not fully initialized
                    
            # Cleanup
            cleanup_managers()
            
        except ImportError as e:
            logger.warning(f"Manager initialization test skipped: {e}")
            
    result = profiler.profile_operation("manager_initialization", initialize_managers)
    metrics = profiler.generate_comprehensive_report()
    profiler.stop_profiling()
    
    return metrics, result


def profile_rom_cache_operations():
    """Profile ROM cache system performance"""
    logger.info("Profiling ROM cache operations...")
    
    profiler = PerformanceProfiler()
    profiler.start_profiling()
    
    def test_cache_operations():
        """Test ROM cache operations with realistic data"""
        try:
            from utils.rom_cache import get_rom_cache
            
            cache = get_rom_cache()
            
            # Create test ROM file
            with tempfile.NamedTemporaryFile(suffix='.sfc', delete=False) as test_rom:
                test_rom_path = test_rom.name
                test_rom.write(b'ROM_DATA' * 10000)  # 70KB test ROM
            
            try:
                # Test 1: Cache sprite locations (typical data structure)
                sprite_locations = {
                    'kirby_walk_1': {'offset': 0x200000, 'size': 512},
                    'kirby_walk_2': {'offset': 0x200200, 'size': 512},
                    'kirby_jump': {'offset': 0x200400, 'size': 768},
                    'enemy_goomba': {'offset': 0x201000, 'size': 256},
                }
                
                for i in range(10):  # Multiple operations
                    cache.save_sprite_locations(test_rom_path, sprite_locations)
                    loaded_locations = cache.get_sprite_locations(test_rom_path)
                
                # Test 2: Cache preview data (heavy I/O operations)
                test_tile_data = b'\x00\x01\x02\x03' * 2048  # 8KB tile data
                
                for offset in range(0x200000, 0x200500, 0x100):  # 5 operations
                    cache.save_preview_data(test_rom_path, offset, test_tile_data, 32, 32)
                    cached_preview = cache.get_preview_data(test_rom_path, offset)
                
                # Test 3: Batch operations (efficiency test)
                batch_data = {}
                for i in range(50):
                    offset = 0x300000 + (i * 0x100)
                    batch_data[offset] = {
                        'tile_data': test_tile_data,
                        'width': 32,
                        'height': 32
                    }
                
                cache.save_preview_batch(test_rom_path, batch_data)
                
                # Test 4: Cache statistics and cleanup
                stats = cache.get_cache_stats()
                logger.debug(f"Cache stats: {stats}")
                
                cache.clear_preview_cache(test_rom_path)
                
            finally:
                # Cleanup test ROM
                try:
                    os.unlink(test_rom_path)
                except OSError:
                    pass
                    
        except ImportError as e:
            logger.warning(f"ROM cache test skipped: {e}")
            
    result = profiler.profile_operation("rom_cache_operations", test_cache_operations)
    metrics = profiler.generate_comprehensive_report()
    profiler.stop_profiling()
    
    return metrics, result


def profile_worker_thread_lifecycle():
    """Profile worker thread creation, execution, and cleanup"""
    logger.info("Profiling worker thread lifecycle...")
    
    profiler = PerformanceProfiler()
    profiler.start_profiling()
    
    def test_worker_lifecycle():
        """Test worker thread patterns"""
        try:
            from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer
            from PyQt6.QtWidgets import QApplication
            from core.workers.base import BaseWorker
            
            app = QApplication.instance()
            if not app:
                app = QApplication([])
            
            class TestWorker(BaseWorker):
                """Test worker for profiling"""
                result_ready = pyqtSignal(str)
                
                def run(self):
                    """Simulate work"""
                    try:
                        for i in range(100):
                            if self.is_cancelled:
                                break
                            self.emit_progress(i, f"Processing {i}")
                            time.sleep(0.001)  # Simulate work
                        
                        self.result_ready.emit("Work completed")
                        self.operation_finished.emit(True, "Success")
                    except Exception as e:
                        self.emit_error(str(e), e)
                        self.operation_finished.emit(False, str(e))
            
            # Test multiple worker creation/destruction cycles
            workers = []
            
            for cycle in range(5):
                # Create workers
                cycle_workers = []
                for i in range(3):
                    worker = TestWorker()
                    worker.setObjectName(f"TestWorker-{cycle}-{i}")
                    cycle_workers.append(worker)
                    workers.append(worker)
                
                # Start workers
                for worker in cycle_workers:
                    worker.start()
                
                # Wait for completion
                for worker in cycle_workers:
                    worker.wait(1000)  # 1 second timeout
                
                # Cleanup
                for worker in cycle_workers:
                    if worker.isRunning():
                        worker.requestInterruption()
                        worker.wait(500)
                    worker.deleteLater()
                
                # Process events to ensure cleanup
                if app:
                    app.processEvents()
            
            # Final cleanup
            for worker in workers:
                if worker.isRunning():
                    worker.requestInterruption()
                    worker.wait(100)
                        
        except ImportError as e:
            logger.warning(f"Worker lifecycle test skipped: {e}")
            
    result = profiler.profile_operation("worker_lifecycle", test_worker_lifecycle)
    metrics = profiler.generate_comprehensive_report()
    profiler.stop_profiling()
    
    return metrics, result


def profile_qt_widget_patterns():
    """Profile Qt widget creation and lifecycle patterns"""
    logger.info("Profiling Qt widget patterns...")
    
    profiler = PerformanceProfiler()
    profiler.start_profiling()
    
    def test_widget_patterns():
        """Test Qt widget creation/destruction patterns"""
        try:
            from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, 
                                       QHBoxLayout, QLabel, QPushButton, 
                                       QSlider, QSpinBox, QGroupBox)
            from PyQt6.QtCore import Qt
            
            app = QApplication.instance()
            if not app:
                app = QApplication([])
            
            widgets_created = []
            
            # Test 1: Typical dialog creation pattern (like manual offset dialog)
            for i in range(10):
                main_widget = QWidget()
                main_layout = QVBoxLayout(main_widget)
                
                # Create complex widget hierarchy
                for group_idx in range(5):
                    group = QGroupBox(f"Group {group_idx}")
                    group_layout = QVBoxLayout(group)
                    
                    for row_idx in range(3):
                        row_widget = QWidget()
                        row_layout = QHBoxLayout(row_widget)
                        
                        row_layout.addWidget(QLabel(f"Label {row_idx}"))
                        row_layout.addWidget(QSlider(Qt.Orientation.Horizontal))
                        row_layout.addWidget(QSpinBox())
                        row_layout.addWidget(QPushButton(f"Button {row_idx}"))
                        
                        group_layout.addWidget(row_widget)
                    
                    main_layout.addWidget(group)
                
                widgets_created.append(main_widget)
                
                # Process events (simulates real usage)
                app.processEvents()
            
            # Test 2: Rapid widget creation/destruction (slider updates)
            for i in range(50):
                temp_widget = QWidget()
                temp_layout = QVBoxLayout(temp_widget)
                temp_layout.addWidget(QLabel(f"Temporary {i}"))
                temp_layout.addWidget(QSlider(Qt.Orientation.Horizontal))
                
                app.processEvents()
                
                # Immediate cleanup (simulates preview updates)
                temp_widget.deleteLater()
            
            # Cleanup all widgets
            for widget in widgets_created:
                widget.deleteLater()
            
            # Final event processing
            app.processEvents()
            
        except ImportError as e:
            logger.warning(f"Qt widget test skipped: {e}")
            
    result = profiler.profile_operation("qt_widget_patterns", test_widget_patterns)
    metrics = profiler.generate_comprehensive_report()
    profiler.stop_profiling()
    
    return metrics, result


def profile_sprite_data_operations():
    """Profile sprite data processing operations"""
    logger.info("Profiling sprite data operations...")
    
    profiler = PerformanceProfiler()
    profiler.start_profiling()
    
    def test_sprite_operations():
        """Test sprite data processing patterns"""
        try:
            # Test 1: Large data structure creation (ROM data simulation)
            rom_data_chunks = []
            for i in range(100):
                # Simulate 64KB ROM chunks
                chunk = bytearray(65536)
                # Fill with pattern data
                for j in range(0, 65536, 4):
                    chunk[j:j+4] = (i * 4 + j).to_bytes(4, 'little')
                rom_data_chunks.append(chunk)
            
            # Test 2: Sprite extraction simulation
            extracted_sprites = []
            for chunk_idx, chunk in enumerate(rom_data_chunks[:10]):  # Process subset
                for offset in range(0, len(chunk), 512):  # 512-byte sprites
                    sprite_data = chunk[offset:offset+512]
                    
                    # Simulate processing (pattern detection)
                    if sprite_data[0] != 0:  # Simple pattern check
                        extracted_sprites.append({
                            'chunk': chunk_idx,
                            'offset': offset,
                            'data': sprite_data,
                            'size': len(sprite_data)
                        })
            
            # Test 3: Memory-intensive operations (palette generation)
            palettes = []
            for sprite in extracted_sprites[:50]:  # Process subset
                # Generate color palette (simulate intensive computation)
                palette = []
                sprite_data = sprite['data']
                for i in range(0, min(len(sprite_data), 32), 2):  # 16 colors max
                    # Simulate SNES color conversion
                    color_word = int.from_bytes(sprite_data[i:i+2], 'little')
                    r = (color_word & 0x1F) * 8
                    g = ((color_word >> 5) & 0x1F) * 8
                    b = ((color_word >> 10) & 0x1F) * 8
                    palette.append((r, g, b))
                palettes.append(palette)
            
            # Test 4: Cleanup and garbage collection stress test
            del rom_data_chunks
            del extracted_sprites
            del palettes
            
            import gc
            gc.collect()
            
        except Exception as e:
            logger.warning(f"Sprite operations test error: {e}")
            
    result = profiler.profile_operation("sprite_data_operations", test_sprite_operations)
    metrics = profiler.generate_comprehensive_report()
    profiler.stop_profiling()
    
    return metrics, result


def run_comprehensive_analysis():
    """Run all performance analyses and generate reports"""
    logger.info("Starting comprehensive SpritePal performance analysis...")
    
    test_results = {}
    
    # Run all profiling tests
    tests = [
        ("Manager Initialization", profile_manager_initialization),
        ("ROM Cache Operations", profile_rom_cache_operations), 
        ("Worker Lifecycle", profile_worker_thread_lifecycle),
        ("Qt Widget Patterns", profile_qt_widget_patterns),
        ("Sprite Data Operations", profile_sprite_data_operations)
    ]
    
    for test_name, test_func in tests:
        logger.info(f"Running {test_name} test...")
        try:
            metrics, result = test_func()
            test_results[test_name] = {
                'metrics': metrics,
                'result': result,
                'success': True
            }
            logger.info(f"{test_name} test completed successfully")
        except Exception as e:
            logger.error(f"{test_name} test failed: {e}")
            test_results[test_name] = {
                'error': str(e),
                'success': False
            }
    
    # Generate comprehensive report
    logger.info("Generating comprehensive analysis report...")
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    # Individual test reports
    for test_name, test_data in test_results.items():
        if test_data['success']:
            metrics = test_data['metrics']
            filename = f"spritepal_{test_name.lower().replace(' ', '_')}_profile_{timestamp}.txt"
            report_file, json_file = save_report(metrics, filename)
            logger.info(f"{test_name} report saved to: {report_file}")
    
    # Combined summary report
    summary_filename = f"spritepal_performance_summary_{timestamp}.txt"
    generate_summary_report(test_results, summary_filename)
    
    logger.info(f"Comprehensive analysis complete. Summary: {summary_filename}")
    return test_results


def generate_summary_report(test_results, filename):
    """Generate a summary report combining all test results"""
    report = []
    report.append("=" * 80)
    report.append("SPRITEPAL COMPREHENSIVE PERFORMANCE ANALYSIS SUMMARY")
    report.append("=" * 80)
    report.append("")
    report.append(f"Analysis completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Test execution summary
    report.append("TEST EXECUTION SUMMARY")
    report.append("-" * 40)
    
    successful_tests = 0
    total_tests = len(test_results)
    
    for test_name, test_data in test_results.items():
        status = "✓ PASSED" if test_data['success'] else "✗ FAILED"
        report.append(f"{test_name}: {status}")
        if test_data['success']:
            successful_tests += 1
            if 'result' in test_data and 'execution_time' in test_data['result']:
                exec_time = test_data['result']['execution_time']
                report.append(f"  Execution time: {exec_time:.2f}s")
        else:
            report.append(f"  Error: {test_data.get('error', 'Unknown error')}")
    
    report.append("")
    report.append(f"Overall: {successful_tests}/{total_tests} tests passed")
    report.append("")
    
    # Performance highlights from successful tests
    if successful_tests > 0:
        report.append("PERFORMANCE HIGHLIGHTS")
        report.append("-" * 40)
        
        for test_name, test_data in test_results.items():
            if not test_data['success']:
                continue
                
            metrics = test_data['metrics']
            
            report.append(f"\n{test_name}:")
            
            # Memory stats
            mem_stats = metrics.memory_stats
            if 'error' not in mem_stats:
                growth = mem_stats.get('total_growth_mb', 0)
                peak = mem_stats.get('peak_memory_mb', 0)
                report.append(f"  Memory growth: {growth:.2f} MB, Peak: {peak:.2f} MB")
                
                growth_rate = mem_stats.get('growth_rate_mb_per_sec', 0)
                if growth_rate > 0.1:
                    report.append(f"  WARNING: High memory growth rate: {growth_rate:.3f} MB/s")
            
            # Thread stats
            thread_stats = metrics.thread_stats
            thread_count = thread_stats.get('total_threads', 0)
            worker_count = metrics.worker_stats.get('total_worker_threads', 0)
            report.append(f"  Threads: {thread_count} total, {worker_count} workers")
            
            # Qt stats
            qt_stats = metrics.qt_stats
            if 'error' not in qt_stats:
                widget_count = qt_stats.get('total_widgets', 0)
                report.append(f"  Qt widgets: {widget_count}")
        
        report.append("")
        
        # Combined recommendations
        report.append("COMBINED PERFORMANCE RECOMMENDATIONS")
        report.append("-" * 40)
        
        all_recommendations = set()
        
        for test_name, test_data in test_results.items():
            if not test_data['success']:
                continue
            
            from performance_profiler import generate_recommendations
            recommendations = generate_recommendations(test_data['metrics'])
            
            for rec in recommendations:
                if "No critical performance issues" not in rec:
                    all_recommendations.add(rec)
        
        if all_recommendations:
            for rec in sorted(all_recommendations):
                report.append(f"• {rec}")
        else:
            report.append("• No critical performance issues detected across all tests")
    
    report.append("")
    report.append("=" * 80)
    
    # Write report
    filename_path = Path(filename)  
    with filename_path.open('w') as f:
        f.write('\n'.join(report))
    
    # Also print summary to console
    print('\n'.join(report))


if __name__ == "__main__":
    # Run the comprehensive analysis
    try:
        results = run_comprehensive_analysis()
        print("\nSpritePal performance analysis completed successfully!")
        print(f"Results summary: {len([r for r in results.values() if r['success']])}/{len(results)} tests passed")
        
    except KeyboardInterrupt:
        print("\nPerformance analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nPerformance analysis failed: {e}")
        logger.exception("Analysis failed with exception")
        sys.exit(1)