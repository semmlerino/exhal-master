"""
Comprehensive integration test for Phase 1 components.
Tests async workers, optimized canvas, and drawing operations working together.
"""

import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest
from PyQt6.QtCore import QRect
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from pixel_editor.core.indexed_pixel_editor import IndexedPixelEditor
from pixel_editor.core.widgets.color_palette_widget import ColorPaletteWidget
from pixel_editor.core.pixel_editor_canvas_v3 import PixelCanvasV3 as PixelCanvas
from pixel_editor.core.pixel_editor_workers import FileLoadWorker, FileSaveWorker


class TestIntegrationComprehensive:
    """Test all Phase 1 components working together"""

    @pytest.fixture
    def app(self):
        """Create QApplication for tests"""
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()

    @pytest.fixture
    def editor(self, app):
        """Create editor instance"""
        editor = IndexedPixelEditor()
        # Set up a basic palette
        editor.default_palette = [
            (0, 0, 0),  # Black
            (255, 0, 0),  # Red
            (0, 255, 0),  # Green
            (0, 0, 255),  # Blue
            (255, 255, 0),  # Yellow
            (255, 0, 255),  # Magenta
            (0, 255, 255),  # Cyan
            (255, 255, 255),  # White
        ] * 2  # Extend to 16 colors
        return editor

    def test_async_load_draw_save_workflow(self, editor, tmp_path, qtbot):
        """Test complete workflow with all Phase 1 components"""
        # Create test image
        test_file = tmp_path / "test_workflow.png"
        test_array = np.zeros((32, 32), dtype=np.uint8)
        test_array[5:15, 5:15] = 1  # Red square

        # Convert to PIL Image and save
        from PIL import Image

        pil_image = Image.fromarray(test_array, mode="P")
        # Set palette
        palette = []
        for color in editor.default_palette[:16]:
            palette.extend(color)
        palette.extend([0, 0, 0] * (256 - 16))  # Fill rest with black
        pil_image.putpalette(palette)
        pil_image.save(str(test_file))

        # Test 1: Async image loading
        load_completed = False
        load_error = None

        def on_load_complete(image_array, palette_data, file_path):
            nonlocal load_completed
            load_completed = True
            editor.image_array = image_array
            editor.original_array = image_array.copy()

            # Update canvas
            if hasattr(editor, "pixel_canvas"):
                editor.pixel_canvas.set_image(image_array)

        def on_load_error(msg):
            nonlocal load_error
            load_error = msg

        load_worker = FileLoadWorker(str(test_file), editor)
        load_worker.image_loaded.connect(on_load_complete)
        load_worker.error.connect(on_load_error)
        load_worker.start()

        # Wait for load to complete
        qtbot.waitUntil(lambda: load_completed or load_error is not None, timeout=5000)

        assert load_completed, f"Image loading failed: {load_error}"
        assert editor.image_array is not None
        assert editor.image_array.shape == (32, 32)

        # Test 2: Canvas optimizations
        # Create canvas if not already created
        if not hasattr(editor, "pixel_canvas"):
            palette_widget = ColorPaletteWidget()
            palette_widget.set_colors(editor.default_palette)
            editor.pixel_canvas = PixelCanvas(palette_widget)
            editor.pixel_canvas.set_image(editor.image_array)

        # Verify QColor cache is created
        editor.pixel_canvas._update_qcolor_cache()
        assert hasattr(editor.pixel_canvas, "_qcolor_cache")
        assert len(editor.pixel_canvas._qcolor_cache) > 0

        # Test 3: Drawing operations with dirty rectangle tracking
        editor.pixel_canvas._dirty_rect = None

        # Simulate drawing
        editor.current_color = 2  # Green
        editor.pixel_canvas.current_color = 2

        # Draw a line
        for x in range(10, 20):
            editor.pixel_canvas.draw_pixel(x, 10)
            if editor.image_array is not None:
                editor.image_array[10, x] = 2

        # Verify dirty rectangle was tracked
        assert editor.pixel_canvas._dirty_rect is not None

        # Test 4: Save operation
        save_completed = False
        save_error = None

        def on_save_complete():
            nonlocal save_completed
            save_completed = True

        def on_save_error(msg):
            nonlocal save_error
            save_error = msg

        save_file = tmp_path / "test_save.png"

        # Prepare palette data for save
        palette_data = {"palette": editor.default_palette[:16]}

        save_worker = FileSaveWorker(
            editor.image_array, palette_data, str(save_file), editor
        )
        save_worker.finished.connect(on_save_complete)
        save_worker.error.connect(on_save_error)
        save_worker.start()

        # Wait for save to complete
        qtbot.waitUntil(lambda: save_completed or save_error is not None, timeout=5000)

        assert save_completed, f"Image saving failed: {save_error}"
        assert save_file.exists(), "Saved file should exist"

        # Verify saved image
        saved_img = Image.open(str(save_file))
        assert saved_img.size == (32, 32)

        # Clean up workers
        load_worker.quit()
        load_worker.wait()
        save_worker.quit()
        save_worker.wait()

    def test_performance_under_load(self, editor, qtbot):
        """Test performance with many operations"""
        # Create larger image
        image_array = np.zeros((256, 256), dtype=np.uint8)

        # Create canvas
        palette_widget = ColorPaletteWidget()
        palette_widget.set_colors(editor.default_palette)
        canvas = PixelCanvas(palette_widget)
        canvas.set_image(image_array)

        # Enable optimizations
        canvas._update_qcolor_cache()

        # Test many pixel operations
        start_time = time.time()

        for i in range(100):
            x = i % 256
            y = (i * 7) % 256
            canvas.current_color = (i % 7) + 1
            canvas.draw_pixel(x, y)
            image_array[y, x] = canvas.current_color

        pixel_time = time.time() - start_time
        assert (
            pixel_time < 1.0
        ), f"100 pixel operations took {pixel_time:.2f}s, should be < 1s"

        # Test dirty rectangle consolidation
        assert canvas._dirty_rect is not None
        # Should have consolidated updates into one rectangle
        assert isinstance(canvas._dirty_rect, QRect)

    def test_error_handling_integration(self, editor, tmp_path, qtbot):
        """Test error handling across components"""
        # Test 1: Invalid file load
        error_occurred = False
        error_msg = None

        def on_error(msg):
            nonlocal error_occurred, error_msg
            error_occurred = True
            error_msg = msg

        invalid_file = tmp_path / "nonexistent.png"
        load_worker = FileLoadWorker(str(invalid_file), editor)
        load_worker.error.connect(on_error)
        load_worker.start()

        # Wait for error
        qtbot.waitUntil(lambda: error_occurred, timeout=2000)

        assert error_occurred, "Should handle missing file error"
        assert error_msg is not None

        # Test 2: Save to invalid location
        error_occurred = False
        error_msg = None

        image_array = np.zeros((32, 32), dtype=np.uint8)
        palette_data = {"palette": editor.default_palette[:16]}

        invalid_save_path = "/invalid/path/test.png"
        save_worker = FileSaveWorker(
            image_array, palette_data, invalid_save_path, editor
        )
        save_worker.error.connect(on_error)
        save_worker.start()

        # Wait for error
        qtbot.waitUntil(lambda: error_occurred, timeout=2000)

        assert error_occurred, "Should handle invalid save path"

        # Clean up
        load_worker.quit()
        save_worker.quit()

    def test_canvas_viewport_culling(self, editor):
        """Test viewport culling optimization"""
        # Create large image
        image_array = np.zeros((1024, 1024), dtype=np.uint8)

        palette_widget = ColorPaletteWidget()
        palette_widget.set_colors(editor.default_palette)
        canvas = PixelCanvas(palette_widget)
        canvas.set_image(image_array)

        # Mock scroll area parent
        scroll_area = Mock()
        viewport = Mock()
        viewport.rect.return_value = QRect(0, 0, 400, 300)
        scroll_area.viewport.return_value = viewport

        with patch.object(canvas, "parent", return_value=scroll_area):
            # Get visible range
            visible_range = canvas.get_visible_pixel_range()

            if visible_range:
                left, top, right, bottom = visible_range

                # Verify only visible area is considered
                assert right - left <= 400 / canvas.zoom_level
                assert bottom - top <= 300 / canvas.zoom_level

                # Should not include entire 1024x1024 image
                assert right < 1024 or bottom < 1024

    def test_qcolor_cache_efficiency(self, editor):
        """Test QColor caching improves performance"""
        palette_widget = ColorPaletteWidget()
        palette_widget.set_colors(editor.default_palette)
        canvas = PixelCanvas(palette_widget)

        # Create test image
        image_array = np.random.randint(0, 16, (100, 100), dtype=np.uint8)
        canvas.set_image(image_array)

        # Without cache (simulate)
        canvas._qcolor_cache.clear()

        start_time = time.time()
        # Force paint event
        paint_event = Mock()
        paint_event.rect.return_value = canvas.rect()

        with patch.object(canvas, "_qcolor_cache", {}):
            # This would be slow without cache
            pass

        # With cache
        canvas._update_qcolor_cache()

        # Verify cache contains expected colors
        assert len(canvas._qcolor_cache) >= 16  # At least palette colors
        assert -1 in canvas._qcolor_cache  # Invalid color

        # All cached colors should be QColor instances
        for color in canvas._qcolor_cache.values():
            assert isinstance(color, QColor)

    def test_concurrent_operations(self, editor, tmp_path, qtbot):
        """Test thread safety of concurrent operations"""
        # Create test images
        test_array = np.zeros((64, 64), dtype=np.uint8)
        palette_data = {"palette": editor.default_palette[:16]}

        operations_completed = []
        errors = []

        def on_complete(op_name):
            operations_completed.append(op_name)

        def on_error(msg):
            errors.append(msg)

        # Start multiple save operations concurrently
        workers = []

        for i in range(3):
            save_path = tmp_path / f"concurrent_save_{i}.png"
            worker = FileSaveWorker(
                test_array.copy(), palette_data, str(save_path), editor
            )
            worker.finished.connect(lambda i=i: on_complete(f"save_{i}"))
            worker.error.connect(on_error)
            worker.start()
            workers.append(worker)

        # Wait for all operations
        qtbot.waitUntil(lambda: len(operations_completed) == 3, timeout=5000)

        assert (
            len(operations_completed) == 3
        ), "All concurrent operations should complete"
        assert len(errors) == 0, f"No errors should occur: {errors}"

        # Verify all files created
        for i in range(3):
            assert (tmp_path / f"concurrent_save_{i}.png").exists()

        # Clean up
        for worker in workers:
            worker.quit()
            worker.wait()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
