#!/usr/bin/env python3
"""
Comprehensive test suite for Phase 1 improvements to the pixel editor.

Tests include:
1. Canvas optimizations (QColor caching, viewport culling, dirty rectangles, grid drawing)
2. Worker threads (async file operations, progress tracking, cancellation)
3. Delta undo system (memory usage, undo/redo operations, compression)
4. Performance benchmarks
"""

import sys
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import numpy as np
from PIL import Image
import psutil
import gc

from PyQt6.QtCore import Qt, QPoint, QRect, QTimer
from PyQt6.QtGui import QPainter, QColor, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtTest import QTest

# Import the modules to test
from pixel_editor_widgets import PixelCanvas, ColorPaletteWidget
from pixel_editor_workers import FileLoadWorker, FileSaveWorker, PaletteLoadWorker
from indexed_pixel_editor import IndexedPixelEditor


class TestCanvasOptimizations(unittest.TestCase):
    """Test canvas optimization features."""
    
    @classmethod
    def setUpClass(cls):
        """Create QApplication if needed."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up test canvas."""
        self.palette_widget = ColorPaletteWidget()
        self.canvas = PixelCanvas(self.palette_widget)
        self.canvas.resize(800, 600)
        
        # Create test image
        self.test_image = np.zeros((256, 256), dtype=np.uint8)
        self.canvas.set_image(self.test_image)
    
    def test_qcolor_caching(self):
        """Test that QColor objects are cached properly."""
        # Check if color cache exists
        self.assertTrue(hasattr(self.canvas, '_qcolor_cache'), 
                       "Canvas should have _qcolor_cache attribute")
        
        # Trigger cache update
        self.canvas._update_qcolor_cache()
        
        # Verify cache contains 16 colors + invalid color
        self.assertEqual(len(self.canvas._qcolor_cache), 17,
                        "Cache should contain 16 palette colors + 1 invalid color")
        
        # Verify colors are QColor instances
        for idx, color in self.canvas._qcolor_cache.items():
            self.assertIsInstance(color, QColor,
                                f"Cache entry {idx} should be QColor instance")
        
        # Verify invalid color is magenta
        invalid_color = self.canvas._qcolor_cache.get(-1)
        self.assertIsNotNone(invalid_color)
        self.assertEqual(invalid_color.red(), 255)
        self.assertEqual(invalid_color.green(), 0)
        self.assertEqual(invalid_color.blue(), 255)
    
    def test_viewport_culling(self):
        """Test viewport culling algorithm."""
        # Mock scroll area parent
        scroll_area = Mock()
        viewport = Mock()
        viewport.rect.return_value = QRect(0, 0, 400, 300)
        scroll_area.viewport.return_value = viewport
        
        with patch.object(self.canvas, 'parent', return_value=scroll_area):
            # Test visible range calculation
            visible_range = self.canvas.get_visible_pixel_range()
            self.assertIsNotNone(visible_range)
            
            left, top, right, bottom = visible_range
            self.assertGreaterEqual(left, 0)
            self.assertGreaterEqual(top, 0)
            self.assertLessEqual(right, 256)
            self.assertLessEqual(bottom, 256)
    
    def test_dirty_rectangle_tracking(self):
        """Test dirty rectangle tracking for partial updates."""
        # Initially no dirty rect
        self.assertIsNone(self.canvas._dirty_rect)
        
        # Mark a single pixel dirty
        self.canvas.mark_dirty(10, 20)
        self.assertIsNotNone(self.canvas._dirty_rect)
        
        # Verify dirty rect dimensions
        dirty = self.canvas._dirty_rect
        self.assertEqual(dirty.x(), 10 * self.canvas.zoom)
        self.assertEqual(dirty.y(), 20 * self.canvas.zoom)
        self.assertEqual(dirty.width(), self.canvas.zoom)
        self.assertEqual(dirty.height(), self.canvas.zoom)
        
        # Mark another pixel and verify union
        self.canvas.mark_dirty(15, 25)
        dirty = self.canvas._dirty_rect
        self.assertTrue(dirty.contains(QRect(10 * self.canvas.zoom, 
                                           20 * self.canvas.zoom,
                                           self.canvas.zoom,
                                           self.canvas.zoom)))
    
    def test_optimized_grid_drawing(self):
        """Test optimized grid drawing performance."""
        # Set zoom level where grid is visible
        self.canvas.zoom = 8
        self.canvas.grid_visible = True
        
        # Create mock painter
        painter = Mock(spec=QPainter)
        
        # Time grid drawing
        start_time = time.time()
        self.canvas._draw_grid_optimized(painter, 0, 0, 50, 50)
        draw_time = time.time() - start_time
        
        # Verify painter was called with path
        painter.drawPath.assert_called()
        
        # Should be fast even for large grid
        self.assertLess(draw_time, 0.1, "Grid drawing should be fast")
    
    def test_tile_caching(self):
        """Test tile caching system."""
        # Enable tile caching
        self.canvas.tile_cache_enabled = True
        
        # Test cache operations
        cache = self.canvas.tile_cache
        
        # Create test pixmap
        test_pixmap = QPixmap(32, 32)
        test_pixmap.fill(Qt.GlobalColor.red)
        
        # Cache a tile
        cache.set_tile(8, 0, 0, 1, test_pixmap)
        
        # Retrieve cached tile
        cached = cache.get_tile(8, 0, 0, 1)
        self.assertIsNotNone(cached)
        
        # Verify cache invalidation
        cache.invalidate_tile(0, 0)
        cached = cache.get_tile(8, 0, 0, 1)
        self.assertIsNone(cached)


class TestWorkerThreads(unittest.TestCase):
    """Test async worker thread functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Create QApplication if needed."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path("test_phase1_temp")
        self.test_dir.mkdir(exist_ok=True)
        
        # Create test image
        self.test_image = Image.new('P', (64, 64))
        self.test_image.putpalette([i % 256 for i in range(768)])
        self.test_image_path = self.test_dir / "test_image.png"
        self.test_image.save(str(self.test_image_path))
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_file_load_worker(self):
        """Test async file loading."""
        worker = FileLoadWorker(str(self.test_image_path))
        
        # Track signals
        progress_values = []
        result_data = []
        errors = []
        finished_count = [0]
        
        worker.progress.connect(lambda v: progress_values.append(v))
        worker.result.connect(lambda arr, meta: result_data.append((arr, meta)))
        worker.error.connect(lambda e: errors.append(e))
        worker.finished.connect(lambda: finished_count[0].__add__(1))
        
        # Run worker
        worker.start()
        worker.wait(5000)  # Wait up to 5 seconds
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Should have no errors: {errors}")
        self.assertEqual(finished_count[0], 1, "Should finish once")
        self.assertEqual(len(result_data), 1, "Should emit result once")
        
        # Verify progress updates
        self.assertGreater(len(progress_values), 0, "Should emit progress")
        self.assertEqual(progress_values[-1], 100, "Should reach 100%")
        
        # Verify loaded data
        image_array, metadata = result_data[0]
        self.assertEqual(image_array.shape, (64, 64))
        self.assertEqual(metadata['width'], 64)
        self.assertEqual(metadata['height'], 64)
    
    def test_file_save_worker(self):
        """Test async file saving."""
        # Create test data
        test_array = np.ones((32, 32), dtype=np.uint8) * 5
        test_palette = [i % 256 for i in range(768)]
        save_path = self.test_dir / "saved_image.png"
        
        worker = FileSaveWorker(test_array, test_palette, str(save_path))
        
        # Track signals
        progress_values = []
        saved_paths = []
        errors = []
        
        worker.progress.connect(lambda v: progress_values.append(v))
        worker.saved.connect(lambda p: saved_paths.append(p))
        worker.error.connect(lambda e: errors.append(e))
        
        # Run worker
        worker.start()
        worker.wait(5000)
        
        # Verify results
        self.assertEqual(len(errors), 0, f"Should have no errors: {errors}")
        self.assertEqual(len(saved_paths), 1, "Should save once")
        self.assertTrue(save_path.exists(), "File should be created")
        
        # Verify saved image
        loaded = Image.open(str(save_path))
        self.assertEqual(loaded.size, (32, 32))
        self.assertEqual(loaded.mode, 'P')
    
    def test_worker_cancellation(self):
        """Test worker cancellation functionality."""
        worker = FileLoadWorker(str(self.test_image_path))
        
        # Cancel immediately
        worker.cancel()
        self.assertTrue(worker.is_cancelled())
        
        # Signals should not be emitted after cancellation
        signals_emitted = []
        worker.progress.connect(lambda v: signals_emitted.append('progress'))
        worker.result.connect(lambda a, m: signals_emitted.append('result'))
        worker.finished.connect(lambda: signals_emitted.append('finished'))
        
        worker.start()
        worker.wait(1000)
        
        # Should emit minimal or no signals
        self.assertEqual(len(signals_emitted), 0, 
                        "Cancelled worker should not emit signals")
    
    def test_palette_load_worker(self):
        """Test palette loading worker."""
        # Create test palette file
        palette_data = {
            "name": "Test Palette",
            "colors": [[255, 0, 0], [0, 255, 0], [0, 0, 255]]
        }
        palette_path = self.test_dir / "test_palette.json"
        
        import json
        with open(palette_path, 'w') as f:
            json.dump(palette_data, f)
        
        worker = PaletteLoadWorker(str(palette_path))
        
        # Track results
        results = []
        worker.result.connect(lambda d: results.append(d))
        
        # Run worker
        worker.start()
        worker.wait(2000)
        
        # Verify results
        self.assertEqual(len(results), 1)
        loaded_data = results[0]
        self.assertEqual(loaded_data['name'], "Test Palette")
        self.assertEqual(len(loaded_data['colors']), 3)


class TestDeltaUndoSystem(unittest.TestCase):
    """Test delta-based undo system."""
    
    def setUp(self):
        """Create test components."""
        # Import delta undo system (if implemented)
        try:
            from delta_undo_system import (
                UndoManager, DrawPixelCommand, DrawLineCommand, 
                FloodFillCommand, BatchCommand
            )
            self.undo_available = True
            self.UndoManager = UndoManager
            self.DrawPixelCommand = DrawPixelCommand
            self.DrawLineCommand = DrawLineCommand
            self.FloodFillCommand = FloodFillCommand
            self.BatchCommand = BatchCommand
        except ImportError:
            self.undo_available = False
            
        if self.undo_available:
            self.manager = self.UndoManager()
            self.test_canvas = Mock()
            self.test_canvas.image_data = np.zeros((100, 100), dtype=np.uint8)
    
    def test_draw_pixel_command(self):
        """Test single pixel draw command."""
        if not self.undo_available:
            self.skipTest("Delta undo system not implemented yet")
            
        # Create command
        cmd = self.DrawPixelCommand(x=10, y=20, old_color=0, new_color=5)
        
        # Execute
        self.manager.execute_command(cmd, self.test_canvas)
        self.assertEqual(self.test_canvas.image_data[20, 10], 5)
        
        # Undo
        self.manager.undo(self.test_canvas)
        self.assertEqual(self.test_canvas.image_data[20, 10], 0)
        
        # Redo
        self.manager.redo(self.test_canvas)
        self.assertEqual(self.test_canvas.image_data[20, 10], 5)
    
    def test_memory_usage_comparison(self):
        """Compare memory usage: delta vs full copy system."""
        if not self.undo_available:
            self.skipTest("Delta undo system not implemented yet")
            
        # Measure delta system
        gc.collect()
        process = psutil.Process()
        
        # Delta system memory
        delta_start = process.memory_info().rss
        
        for i in range(50):
            cmd = self.DrawPixelCommand(x=i, y=i, old_color=0, new_color=1)
            self.manager.execute_command(cmd, self.test_canvas)
        
        gc.collect()
        delta_end = process.memory_info().rss
        delta_usage = delta_end - delta_start
        
        # Full copy system memory
        from collections import deque
        undo_stack = deque(maxlen=50)
        
        gc.collect()
        full_start = process.memory_info().rss
        
        for i in range(50):
            undo_stack.append(self.test_canvas.image_data.copy())
        
        gc.collect()
        full_end = process.memory_info().rss
        full_usage = full_end - full_start
        
        # Delta should use much less memory
        self.assertLess(delta_usage, full_usage / 10,
                       f"Delta system should use <10% of full copy memory. "
                       f"Delta: {delta_usage/1024:.1f}KB, Full: {full_usage/1024:.1f}KB")
    
    def test_command_compression(self):
        """Test command compression functionality."""
        if not self.undo_available:
            self.skipTest("Delta undo system not implemented yet")
            
        # Create flood fill command with large affected area
        affected_data = np.random.randint(0, 16, (50, 50), dtype=np.uint8)
        cmd = self.FloodFillCommand(
            affected_region=(10, 10, 50, 50),
            old_data=affected_data,
            new_color=7
        )
        
        # Check uncompressed size
        uncompressed_size = cmd.get_memory_size()
        
        # Compress
        cmd.compress()
        self.assertTrue(cmd.compressed)
        
        # Check compressed size
        compressed_size = cmd.get_memory_size()
        self.assertLess(compressed_size, uncompressed_size,
                       "Compressed command should use less memory")
        
        # Decompress and verify functionality
        cmd.decompress()
        self.assertFalse(cmd.compressed)
        self.assertTrue(np.array_equal(cmd.old_data, affected_data))
    
    def test_batch_command(self):
        """Test batch command for continuous operations."""
        if not self.undo_available:
            self.skipTest("Delta undo system not implemented yet")
            
        # Create batch of pixel commands
        commands = []
        for i in range(10):
            cmd = self.DrawPixelCommand(x=i, y=0, old_color=0, new_color=i)
            commands.append(cmd)
        
        batch = self.BatchCommand(commands)
        
        # Execute batch
        self.manager.execute_command(batch, self.test_canvas)
        
        # Verify all pixels changed
        for i in range(10):
            self.assertEqual(self.test_canvas.image_data[0, i], i)
        
        # Undo batch
        self.manager.undo(self.test_canvas)
        
        # Verify all pixels reverted
        for i in range(10):
            self.assertEqual(self.test_canvas.image_data[0, i], 0)


class TestPerformanceBenchmarks(unittest.TestCase):
    """Performance benchmarks for improvements."""
    
    @classmethod
    def setUpClass(cls):
        """Create QApplication if needed."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up benchmark environment."""
        self.palette_widget = ColorPaletteWidget()
        self.canvas = PixelCanvas(self.palette_widget)
        
    def test_paintEvent_performance(self):
        """Benchmark paintEvent with optimizations."""
        # Test with different image sizes
        sizes = [(64, 64), (256, 256), (512, 512)]
        
        for width, height in sizes:
            with self.subTest(size=f"{width}x{height}"):
                # Create test image
                image = np.random.randint(0, 16, (height, width), dtype=np.uint8)
                self.canvas.set_image(image)
                self.canvas.resize(800, 600)
                
                # Force show to ensure proper setup
                self.canvas.show()
                QApplication.processEvents()
                
                # Measure paint time
                paint_times = []
                
                for _ in range(10):
                    start = time.time()
                    self.canvas.repaint()
                    QApplication.processEvents()
                    paint_times.append(time.time() - start)
                
                avg_time = sum(paint_times) / len(paint_times)
                
                # Performance targets
                if width <= 256:
                    self.assertLess(avg_time, 0.05, 
                                   f"Small images should paint in <50ms, got {avg_time*1000:.1f}ms")
                else:
                    self.assertLess(avg_time, 0.1,
                                   f"Large images should paint in <100ms, got {avg_time*1000:.1f}ms")
    
    def test_color_cache_performance(self):
        """Benchmark QColor caching performance."""
        # Time color lookup with caching
        self.canvas._update_qcolor_cache()
        
        iterations = 100000
        
        # Benchmark cached lookup
        start = time.time()
        for _ in range(iterations):
            color = self.canvas._qcolor_cache.get(5, self.canvas._qcolor_cache[-1])
        cached_time = time.time() - start
        
        # Benchmark QColor creation
        start = time.time()
        for _ in range(iterations):
            color = QColor(85, 85, 85)  # RGB for color index 5
        creation_time = time.time() - start
        
        # Caching should be significantly faster
        speedup = creation_time / cached_time
        self.assertGreater(speedup, 5,
                          f"Color caching should be >5x faster. Got {speedup:.1f}x speedup")
    
    def test_viewport_culling_performance(self):
        """Test performance improvement from viewport culling."""
        # Create large image
        large_image = np.random.randint(0, 16, (1024, 1024), dtype=np.uint8)
        self.canvas.set_image(large_image)
        
        # Set small viewport
        self.canvas.resize(200, 200)
        self.canvas.show()
        QApplication.processEvents()
        
        # Mock viewport culling
        with patch.object(self.canvas, 'get_visible_pixel_range', 
                         return_value=(0, 0, 50, 50)):
            # Time paint with culling
            start = time.time()
            for _ in range(10):
                self.canvas.repaint()
                QApplication.processEvents()
            culled_time = time.time() - start
        
        # Time paint without culling (full image)
        with patch.object(self.canvas, 'get_visible_pixel_range',
                         return_value=(0, 0, 1024, 1024)):
            start = time.time()
            for _ in range(10):
                self.canvas.repaint()
                QApplication.processEvents()
            full_time = time.time() - start
        
        # Culling should provide significant speedup
        speedup = full_time / culled_time
        self.assertGreater(speedup, 10,
                          f"Viewport culling should provide >10x speedup for small viewport. "
                          f"Got {speedup:.1f}x")
    
    def test_dirty_rect_performance(self):
        """Test performance of dirty rectangle updates."""
        # Create medium image
        image = np.zeros((256, 256), dtype=np.uint8)
        self.canvas.set_image(image)
        self.canvas.show()
        QApplication.processEvents()
        
        # Time full update
        start = time.time()
        for _ in range(100):
            self.canvas.update()
            QApplication.processEvents()
        full_update_time = time.time() - start
        
        # Time dirty rect update (single pixel)
        start = time.time()
        for _ in range(100):
            self.canvas.mark_dirty(10, 10)
            QApplication.processEvents()
        dirty_update_time = time.time() - start
        
        # Dirty rect should be much faster
        speedup = full_update_time / dirty_update_time
        self.assertGreater(speedup, 5,
                          f"Dirty rect updates should be >5x faster. Got {speedup:.1f}x")


class IntegrationTests(unittest.TestCase):
    """Integration tests for all improvements working together."""
    
    @classmethod
    def setUpClass(cls):
        """Create QApplication if needed."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def test_editor_with_optimizations(self):
        """Test full editor with all optimizations enabled."""
        editor = IndexedPixelEditor()
        
        # Create test image
        test_image = np.random.randint(0, 16, (128, 128), dtype=np.uint8)
        editor.canvas.set_image(test_image)
        
        # Verify optimizations are enabled
        self.assertTrue(hasattr(editor.canvas, '_qcolor_cache'),
                       "Color caching should be available")
        self.assertTrue(hasattr(editor.canvas, 'get_visible_pixel_range'),
                       "Viewport culling should be available")
        self.assertTrue(hasattr(editor.canvas, 'mark_dirty'),
                       "Dirty rect tracking should be available")
        
        # Test drawing performance
        editor.show()
        QApplication.processEvents()
        
        # Simulate user drawing
        start = time.time()
        for i in range(50):
            editor.canvas.draw_pixel(i, i)
            QApplication.processEvents()
        draw_time = time.time() - start
        
        # Should handle rapid drawing smoothly
        self.assertLess(draw_time, 1.0,
                       f"50 pixel draws should complete in <1s. Got {draw_time:.2f}s")
    
    def test_async_file_operations_integration(self):
        """Test async file operations in full editor context."""
        editor = IndexedPixelEditor()
        
        # Create temp file
        temp_dir = Path("test_integration_temp")
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # Create test image
            test_image = Image.new('P', (64, 64))
            test_image.putpalette([i % 256 for i in range(768)])
            test_path = temp_dir / "test.png"
            test_image.save(str(test_path))
            
            # Track if UI remains responsive
            ui_responsive = True
            response_times = []
            
            def check_responsiveness():
                start = time.time()
                QApplication.processEvents()
                response_time = time.time() - start
                response_times.append(response_time)
                if response_time > 0.1:  # More than 100ms is unresponsive
                    nonlocal ui_responsive
                    ui_responsive = False
            
            # Set up timer to check responsiveness
            timer = QTimer()
            timer.timeout.connect(check_responsiveness)
            timer.start(50)  # Check every 50ms
            
            # Load file async
            editor.load_image(str(test_path))
            
            # Wait for load to complete
            timeout = 5.0
            start = time.time()
            while time.time() - start < timeout:
                QApplication.processEvents()
                if editor.canvas.image_data is not None:
                    break
            
            timer.stop()
            
            # Verify UI remained responsive
            self.assertTrue(ui_responsive,
                           f"UI should remain responsive during file load. "
                           f"Max response time: {max(response_times)*1000:.1f}ms")
            
        finally:
            # Cleanup
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)


def run_benchmarks():
    """Run performance benchmarks and print results."""
    print("\n" + "="*60)
    print("PHASE 1 IMPROVEMENTS - PERFORMANCE BENCHMARKS")
    print("="*60 + "\n")
    
    # Run specific benchmark tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPerformanceBenchmarks)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "-"*60)
    print("BENCHMARK SUMMARY")
    print("-"*60)
    
    if result.wasSuccessful():
        print("✅ All performance benchmarks passed!")
    else:
        print(f"❌ {len(result.failures)} benchmarks failed")
        print(f"❌ {len(result.errors)} benchmarks had errors")
    
    return result.wasSuccessful()


def main():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestCanvasOptimizations))
    suite.addTests(loader.loadTestsFromTestCase(TestWorkerThreads))
    suite.addTests(loader.loadTestsFromTestCase(TestDeltaUndoSystem))
    suite.addTests(loader.loadTestsFromTestCase(IntegrationTests))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Run benchmarks separately
    print("\n" + "="*60)
    input("Press Enter to run performance benchmarks...")
    benchmark_success = run_benchmarks()
    
    # Print final summary
    print("\n" + "="*60)
    print("FINAL TEST SUMMARY")
    print("="*60)
    
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    
    print(f"\nTotal tests run: {total_tests}")
    print(f"Failures: {failures}")
    print(f"Errors: {errors}")
    
    if result.wasSuccessful() and benchmark_success:
        print("\n✅ All Phase 1 improvements are working correctly!")
    else:
        print("\n❌ Some tests failed. Please review the output above.")
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())