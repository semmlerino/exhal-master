#!/usr/bin/env python3
"""
Test script for currently implemented Phase 1 improvements.
This version tests only the features that are already implemented.
"""

import sys
import time
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import numpy as np
from PIL import Image
import gc

from PyQt6.QtCore import Qt, QPoint, QRect, QTimer
from PyQt6.QtGui import QPainter, QColor, QPixmap
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest

# Import the modules to test
from pixel_editor_widgets import PixelCanvas, ColorPaletteWidget
from pixel_editor_workers import FileLoadWorker, FileSaveWorker, PaletteLoadWorker
from indexed_pixel_editor import IndexedPixelEditor


class TestCurrentImplementation(unittest.TestCase):
    """Test currently implemented features."""
    
    @classmethod
    def setUpClass(cls):
        """Create QApplication if needed."""
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
    
    def setUp(self):
        """Set up test environment."""
        self.palette_widget = ColorPaletteWidget()
        self.canvas = PixelCanvas(self.palette_widget)
        self.canvas.resize(800, 600)
        
        # Create test image
        self.test_image = np.zeros((256, 256), dtype=np.uint8)
        self.canvas.set_image(self.test_image)
        
        # Test directory
        self.test_dir = Path("test_current_temp")
        self.test_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        """Clean up."""
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_basic_canvas_functionality(self):
        """Test basic canvas operations."""
        # Test image setting
        self.assertIsNotNone(self.canvas.image_data)
        self.assertEqual(self.canvas.image_data.shape, (256, 256))
        
        # Test drawing
        self.canvas.current_color = 5
        self.canvas.draw_pixel(10, 20)
        self.assertEqual(self.canvas.image_data[20, 10], 5)
        
        # Test zoom
        self.canvas.set_zoom(2.0)
        self.assertEqual(self.canvas.zoom, 2.0)
    
    def test_color_palette_widget(self):
        """Test color palette functionality."""
        # Test default colors
        self.assertEqual(len(self.palette_widget.colors), 16)
        
        # Test color selection
        self.palette_widget.set_selected_color(5)
        self.assertEqual(self.palette_widget.selected_color, 5)
        
        # Test color modification
        self.palette_widget.set_color(5, (255, 128, 0))
        self.assertEqual(self.palette_widget.colors[5], (255, 128, 0))
    
    def test_file_workers(self):
        """Test async file operations."""
        # Create test image
        test_image = Image.new('P', (32, 32))
        test_image.putpalette([i % 256 for i in range(768)])
        test_path = self.test_dir / "test.png"
        test_image.save(str(test_path))
        
        # Test file loading
        load_worker = FileLoadWorker(str(test_path))
        
        results = []
        errors = []
        
        load_worker.result.connect(lambda arr, meta: results.append((arr, meta)))
        load_worker.error.connect(lambda e: errors.append(e))
        
        load_worker.start()
        load_worker.wait(2000)
        
        self.assertEqual(len(errors), 0, f"Loading should not error: {errors}")
        self.assertEqual(len(results), 1, "Should load successfully")
        
        # Test file saving
        save_array = np.ones((16, 16), dtype=np.uint8) * 3
        save_palette = [i % 256 for i in range(768)]
        save_path = self.test_dir / "saved.png"
        
        save_worker = FileSaveWorker(save_array, save_palette, str(save_path))
        
        saved_paths = []
        save_worker.saved.connect(lambda p: saved_paths.append(p))
        
        save_worker.start()
        save_worker.wait(2000)
        
        self.assertEqual(len(saved_paths), 1)
        self.assertTrue(save_path.exists())
    
    def test_editor_integration(self):
        """Test full editor functionality."""
        editor = IndexedPixelEditor()
        
        # Test initial state
        self.assertIsNotNone(editor.canvas)
        self.assertIsNotNone(editor.palette_widget)
        
        # Test creating new image
        editor.new_image()
        QApplication.processEvents()
        
        # Should have image loaded
        self.assertIsNotNone(editor.canvas.image_data)
        
        # Test tool switching
        editor.set_tool("line")
        self.assertEqual(editor.canvas.tool, "line")
        
        editor.set_tool("pencil")
        self.assertEqual(editor.canvas.tool, "pencil")
    
    def test_canvas_painting_performance(self):
        """Test current painting performance."""
        # Different image sizes
        sizes = [(64, 64), (128, 128), (256, 256)]
        
        for width, height in sizes:
            with self.subTest(size=f"{width}x{height}"):
                image = np.random.randint(0, 16, (height, width), dtype=np.uint8)
                self.canvas.set_image(image)
                
                # Show canvas
                self.canvas.show()
                QApplication.processEvents()
                
                # Time painting
                times = []
                for _ in range(5):
                    start = time.time()
                    self.canvas.repaint()
                    QApplication.processEvents()
                    times.append(time.time() - start)
                
                avg_time = sum(times) / len(times)
                print(f"\n{width}x{height} image: {avg_time*1000:.1f}ms per paint")
                
                # Basic performance check
                self.assertLess(avg_time, 0.5, 
                               f"Paint should complete in <500ms, got {avg_time*1000:.1f}ms")
    
    def test_memory_usage(self):
        """Test current memory usage patterns."""
        import psutil
        process = psutil.Process()
        
        # Get baseline memory
        gc.collect()
        baseline = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create editor with large image
        editor = IndexedPixelEditor()
        large_image = np.random.randint(0, 16, (512, 512), dtype=np.uint8)
        editor.canvas.set_image(large_image)
        
        # Perform some operations
        for i in range(20):
            editor.canvas.save_undo_state()
            editor.canvas.draw_pixel(i, i)
        
        gc.collect()
        after_ops = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_increase = after_ops - baseline
        print(f"\nMemory increase after 20 operations: {memory_increase:.1f} MB")
        
        # Current system uses full copies, so this will be high
        # Just verify it's not catastrophic
        self.assertLess(memory_increase, 100, 
                       f"Memory increase should be <100MB, got {memory_increase:.1f}MB")
    
    def test_ui_responsiveness(self):
        """Test UI responsiveness during operations."""
        editor = IndexedPixelEditor()
        editor.show()
        
        # Load a medium image
        image = np.random.randint(0, 16, (256, 256), dtype=np.uint8)
        editor.canvas.set_image(image)
        
        # Track response times
        response_times = []
        
        def measure_response():
            start = time.time()
            QApplication.processEvents()
            response_times.append(time.time() - start)
        
        # Perform rapid operations
        for i in range(50):
            editor.canvas.draw_pixel(i, i)
            measure_response()
        
        avg_response = sum(response_times) / len(response_times)
        max_response = max(response_times)
        
        print(f"\nAverage UI response time: {avg_response*1000:.1f}ms")
        print(f"Maximum UI response time: {max_response*1000:.1f}ms")
        
        # UI should remain responsive
        self.assertLess(avg_response, 0.05, 
                       f"Average response should be <50ms, got {avg_response*1000:.1f}ms")
        self.assertLess(max_response, 0.1,
                       f"Max response should be <100ms, got {max_response*1000:.1f}ms")


def main():
    """Run tests for current implementation."""
    print("="*60)
    print("TESTING CURRENT PHASE 1 IMPLEMENTATIONS")
    print("="*60)
    print("\nThis test suite checks the currently implemented features")
    print("and provides baseline performance measurements.\n")
    
    # Run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestCurrentImplementation)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    if result.wasSuccessful():
        print("\n✅ All current implementations are working correctly!")
        print("\nNext steps:")
        print("1. Implement QColor caching in PixelCanvas")
        print("2. Add viewport culling to paintEvent")
        print("3. Implement dirty rectangle tracking")
        print("4. Add tile caching for large images")
        print("5. Implement delta undo system")
    else:
        print(f"\n❌ {len(result.failures)} tests failed")
        print(f"❌ {len(result.errors)} tests had errors")
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())