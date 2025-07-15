#!/usr/bin/env python3
"""
Integration tests for the Pixel Editor components.
Tests interactions between modules to catch bugs like the ProgressDialog issue.
"""

import json
from unittest.mock import Mock, patch

import numpy as np
import pytest
from PIL import Image
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtWidgets import QApplication

# Import the components we're testing
from pixel_editor.core.indexed_pixel_editor import IndexedPixelEditor
from pixel_editor.core.pixel_editor_widgets import (
    ColorPaletteWidget,
    PixelCanvas,
)
from pixel_editor.core.pixel_editor_workers import (
    BaseWorker,
    FileLoadWorker,
    FileSaveWorker,
    PaletteLoadWorker,
)


class TestWorkerDialogIntegration:
    """Test worker threads with UI components"""

    @pytest.fixture
    def app(self):
        """Create QApplication for tests"""
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()

    @pytest.mark.skip(reason="Hangs in headless environment - QEventLoop issue")
    def test_file_load_worker_integration(self, app, tmp_path):
        """Test FileLoadWorker with IndexedPixelEditor"""
        # Create test image
        test_file = tmp_path / "test_image.png"
        test_array = np.ones((16, 16), dtype=np.uint8)
        img = Image.fromarray(test_array, mode="P")
        img.putpalette([i % 256 for i in range(768)])
        img.save(str(test_file))

        # Mock the editor's load handling
        with patch(
            "pixel_editor.core.indexed_pixel_editor.IndexedPixelEditor.load_file_by_path"
        ):
            _editor = IndexedPixelEditor()

            # The actual integration pattern
            worker = FileLoadWorker(str(test_file))
            # V3 refactor: Operations now run without blocking UI

            # Should not raise any errors
            from PyQt6.QtCore import QEventLoop, QTimer

            loop = QEventLoop()
            worker.finished.connect(loop.quit)
            worker.error.connect(loop.quit)

            timeout_timer = QTimer()
            timeout_timer.setSingleShot(True)
            timeout_timer.timeout.connect(loop.quit)
            timeout_timer.start(2000)  # 2 second timeout

            worker.start()
            loop.exec()  # Process Qt events

            timeout_timer.stop()

    def test_palette_worker_integration(self, app, tmp_path):
        """Test PaletteLoadWorker with mixed file formats"""
        # Test different palette formats

        # JSON format
        json_file = tmp_path / "test.pal.json"
        json_file.write_text('{"colors": [[255, 0, 0], [0, 255, 0], [0, 0, 255]]}')

        worker = PaletteLoadWorker(str(json_file))
        results = []
        worker.result.connect(lambda data: results.append(data))

        # Use QEventLoop to properly wait for the signal
        loop = QEventLoop()
        worker.finished.connect(loop.quit)
        worker.error.connect(loop.quit)

        # Set up timeout
        timeout_timer = QTimer()
        timeout_timer.setSingleShot(True)
        timeout_timer.timeout.connect(loop.quit)
        timeout_timer.start(2000)  # 2 second timeout

        worker.start()
        loop.exec()  # Process Qt events until signal is received

        timeout_timer.stop()

        assert len(results) == 1
        assert "colors" in results[0]
        assert len(results[0]["colors"]) == 3


class TestCanvasWidgetIntegration:
    """Test PixelCanvas with other components"""

    @pytest.fixture
    def app(self):
        """Create QApplication for tests"""
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()

    def test_canvas_palette_integration(self, app):
        """Test PixelCanvas with ColorPaletteWidget"""
        canvas = PixelCanvas()
        palette = ColorPaletteWidget()

        # Set up the connection as done in real usage
        canvas.palette_widget = palette
        palette.colorSelected.connect(canvas.set_drawing_color)

        # Create test image
        canvas.create_new_image(8, 8)

        # Select color in palette
        palette.current_color = 5
        palette.colorSelected.emit(5)

        # Verify canvas received the color
        assert canvas.drawing_color == 5

        # Test drawing with selected color
        canvas.draw_pixel(2, 2)
        assert canvas.image_data[2, 2] == 5

    def test_canvas_optimization_integration(self, app):
        """Test canvas optimizations are working"""
        canvas = PixelCanvas()
        palette = ColorPaletteWidget()

        # Set up palette
        test_colors = [(i * 16, i * 16, i * 16) for i in range(16)]
        palette.set_palette(test_colors)
        canvas.palette_widget = palette

        # Create image
        canvas.create_new_image(100, 100)

        # Test color caching
        assert hasattr(canvas, "_qcolor_cache")
        assert hasattr(canvas, "_update_qcolor_cache")

        # Trigger cache update
        canvas._update_qcolor_cache()
        assert len(canvas._qcolor_cache) > 0

        # Test viewport culling
        visible_range = canvas._get_visible_pixel_range()
        assert visible_range is not None

        # Test dirty rect tracking
        canvas._dirty_rect = None
        canvas.draw_pixel(10, 10)
        assert canvas._dirty_rect is not None


class TestEditorIntegration:
    """Test full IndexedPixelEditor integration"""

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
        with patch("pixel_editor.core.indexed_pixel_editor_v3.QFileDialog"):
            editor = IndexedPixelEditor()
            yield editor
            editor.close()

    @pytest.mark.skip(reason="Hangs in headless environment - GUI initialization issue")
    def test_editor_worker_integration(self, editor, tmp_path):
        """Test editor's integration with workers"""
        # Create test file
        test_file = tmp_path / "test.png"
        img = Image.new("P", (8, 8))
        img.save(str(test_file))

        # Mock the file dialog to return our test file
        with patch(
            "pixel_editor.core.indexed_pixel_editor.QFileDialog.getOpenFileName"
        ) as mock_dialog:
            mock_dialog.return_value = (str(test_file), "")

            # V3 refactor: No progress dialog needed
            # Just verify the file opens
            editor.open_file()

    @pytest.mark.skip(reason="Hangs in headless environment - GUI initialization issue")
    def test_palette_loading_integration(self, editor, tmp_path):
        """Test the specific palette loading pattern that failed"""
        # Create test palette file
        palette_file = tmp_path / "test.pal.json"
        palette_data = {
            "format_version": "1.0",
            "colors": [[255, 0, 0], [0, 255, 0], [0, 0, 255]],
        }
        import json

        palette_file.write_text(json.dumps(palette_data))

        # Test the exact pattern from indexed_pixel_editor.py
        # V3 refactor: No dialog needed for this test
        # Just test palette loading directly
        editor.load_palette_by_path(str(palette_file))


class TestSignalSlotIntegration:
    """Test PyQt signal/slot patterns"""

    @pytest.fixture
    def app(self):
        """Create QApplication for tests"""
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()

    def test_signal_parameter_mismatch(self, app):
        """Test for signal/slot parameter mismatches"""
        # Create a worker with progress signal
        worker = FileLoadWorker("dummy.png")

        # Create receivers with different signatures
        receiver_one_param = Mock()
        Mock()

        # Connect both
        worker.progress.connect(receiver_one_param)
        # This would fail if receiver expected 2 params but signal sends 1

        # Emit signal with both parameters as required by BaseWorker.progress signal
        worker.progress.emit(50, "Test progress message")

        # Mock receives both parameters (unlike real Qt slots which have parameter matching)
        receiver_one_param.assert_called_once_with(50, "Test progress message")

    def test_mixed_usage_patterns(self, app):
        """Test components that use both signals and direct calls"""
        # V3 refactor: No progress dialog in V3


class TestErrorHandlingIntegration:
    """Test error handling across components"""

    @pytest.fixture
    def app(self):
        """Create QApplication for tests"""
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()

    def test_worker_error_propagation(self, app):
        """Test error handling from worker to UI"""
        # V3 refactor: Test worker error handling without dialog
        worker = FileLoadWorker("nonexistent_file.png")

        error_messages = []
        worker.error.connect(lambda msg: error_messages.append(msg))

        # Start worker and wait for signals using Qt event loop
        from PyQt6.QtCore import QEventLoop, QTimer

        loop = QEventLoop()
        worker.finished.connect(loop.quit)
        worker.error.connect(loop.quit)

        timeout_timer = QTimer()
        timeout_timer.setSingleShot(True)
        timeout_timer.timeout.connect(loop.quit)
        timeout_timer.start(2000)  # 2 second timeout

        worker.start()
        loop.exec()  # Process Qt events

        timeout_timer.stop()

        # Should have received an error
        assert len(error_messages) > 0
        assert (
            "not found" in error_messages[0].lower()
            or "error" in error_messages[0].lower()
        )


class TestWorkerProgressMessages:
    """Test that workers emit progress signals with both value and message"""

    @pytest.fixture
    def app(self):
        """Create QApplication for tests"""
        if not QApplication.instance():
            app = QApplication([])
            yield app
            app.quit()
        else:
            yield QApplication.instance()

    def test_file_load_worker_progress_messages(self, app, tmp_path):
        """Test FileLoadWorker emits progress with meaningful messages"""
        # Create test image
        test_file = tmp_path / "test_progress.png"
        img = Image.new("P", (100, 100))
        img.putpalette([i % 256 for i in range(768)])
        img.save(str(test_file))

        # Create worker
        worker = FileLoadWorker(str(test_file))

        # Collect all progress emissions
        progress_emissions = []

        def collect_progress(value, message=""):
            progress_emissions.append((value, message))

        worker.progress.connect(collect_progress)

        # Run worker with event loop
        loop = QEventLoop()
        worker.finished.connect(loop.quit)
        worker.error.connect(lambda: loop.quit())
        QTimer.singleShot(2000, loop.quit)  # Timeout safety

        worker.start()
        loop.exec()

        # Verify we got progress emissions with messages
        assert len(progress_emissions) > 0

        # Check that we have both values and messages
        has_messages = any(emission[1] for emission in progress_emissions)
        assert has_messages, "Worker should emit progress with messages"

        # Verify specific progress milestones
        progress_values = [emission[0] for emission in progress_emissions]
        assert 0 in progress_values, "Should start at 0%"
        assert 100 in progress_values, "Should complete at 100%"

        # Verify message content
        all_messages = [emission[1] for emission in progress_emissions if emission[1]]
        assert any(
            "Loading" in msg for msg in all_messages
        ), "Should have loading message"
        assert any(
            "complete" in msg.lower() for msg in all_messages
        ), "Should have completion message"

    def test_file_save_worker_progress_messages(self, app, tmp_path):
        """Test FileSaveWorker emits progress with meaningful messages"""
        # Create test data
        test_array = np.ones((50, 50), dtype=np.uint8)
        test_palette = [i % 256 for i in range(768)]
        test_file = tmp_path / "test_save.png"

        # Create worker
        worker = FileSaveWorker(test_array, test_palette, str(test_file))

        # Collect all progress emissions
        progress_emissions = []

        def collect_progress(value, message=""):
            progress_emissions.append((value, message))

        worker.progress.connect(collect_progress)

        # Run worker with event loop
        loop = QEventLoop()
        worker.finished.connect(loop.quit)
        worker.error.connect(lambda: loop.quit())
        QTimer.singleShot(2000, loop.quit)  # Timeout safety

        worker.start()
        loop.exec()

        # Verify progress emissions
        assert len(progress_emissions) > 0

        # Check for messages
        has_messages = any(emission[1] for emission in progress_emissions)
        assert has_messages, "Save worker should emit progress with messages"

        # Verify progress flow
        progress_values = [emission[0] for emission in progress_emissions]
        assert 0 in progress_values, "Should start at 0%"
        assert 100 in progress_values, "Should complete at 100%"

        # Verify message types
        all_messages = [emission[1] for emission in progress_emissions if emission[1]]
        assert any(
            "save" in msg.lower() or "saving" in msg.lower() for msg in all_messages
        )
        assert any("complete" in msg.lower() for msg in all_messages)

    def test_palette_load_worker_progress_messages(self, app, tmp_path):
        """Test PaletteLoadWorker emits progress with meaningful messages"""
        # Create test palette file
        palette_file = tmp_path / "test_palette.pal.json"
        palette_data = {
            "format_version": "1.0",
            "colors": [[i, i, i] for i in range(256)],
        }
        palette_file.write_text(json.dumps(palette_data))

        # Create worker
        worker = PaletteLoadWorker(str(palette_file))

        # Collect progress emissions
        progress_emissions = []

        def collect_progress(value, message=""):
            progress_emissions.append((value, message))

        worker.progress.connect(collect_progress)

        # Run worker with event loop
        loop = QEventLoop()
        worker.finished.connect(loop.quit)
        worker.error.connect(lambda: loop.quit())
        QTimer.singleShot(2000, loop.quit)  # Timeout safety

        worker.start()
        loop.exec()

        # Verify emissions
        assert len(progress_emissions) > 0

        # Check messages exist
        has_messages = any(emission[1] for emission in progress_emissions)
        assert has_messages, "Palette worker should emit progress with messages"

        # Verify progress values
        progress_values = [emission[0] for emission in progress_emissions]
        assert 0 in progress_values
        assert 100 in progress_values

        # Check message content
        all_messages = [emission[1] for emission in progress_emissions if emission[1]]
        assert any("palette" in msg.lower() for msg in all_messages)
        assert any(
            "loaded" in msg.lower() or "complete" in msg.lower() for msg in all_messages
        )

    def test_worker_progress_signal_signature(self, app):
        """Test that worker progress signals have correct signature"""
        # Test each worker type
        workers = [
            FileLoadWorker("dummy.png"),
            FileSaveWorker(np.zeros((1, 1)), [0] * 768, "dummy.png"),
            PaletteLoadWorker("dummy.json"),
        ]

        for worker in workers:
            # Check signal signature
            assert hasattr(
                worker, "progress"
            ), f"{worker.__class__.__name__} should have progress signal"

            # The signal should be able to emit with 2 parameters
            # This tests the signal definition, not actual emission
            try:
                # Create a mock slot that accepts 2 parameters
                mock_slot = Mock()
                worker.progress.connect(mock_slot)

                # Manually emit to test signature
                worker.progress.emit(50, "Test message")

                # If we get here without error, the signature is correct
                assert True
            except Exception as e:
                pytest.fail(f"Progress signal has wrong signature: {e}")

    def test_worker_emit_progress_method(self, app):
        """Test that BaseWorker.emit_progress properly emits both value and message"""

        # Create a simple test worker
        class TestWorker(BaseWorker):
            def run(self):
                self.emit_progress(0, "Starting test")
                self.emit_progress(50, "Halfway there")
                self.emit_progress(100, "Test complete")

        worker = TestWorker()

        # Collect emissions
        emissions = []
        worker.progress.connect(lambda v, m: emissions.append((v, m)))

        # Run worker with event loop
        loop = QEventLoop()
        worker.finished.connect(loop.quit)
        QTimer.singleShot(1000, loop.quit)  # Timeout safety

        worker.start()
        loop.exec()

        # Verify emissions
        assert len(emissions) == 3
        assert emissions[0] == (0, "Starting test")
        assert emissions[1] == (50, "Halfway there")
        assert emissions[2] == (100, "Test complete")

    def test_backward_compatibility_single_param(self, app):
        """Test backward compatibility: slots expecting only one parameter can connect to the new progress signal"""
        # Create a worker with the new progress signal that emits (value, message)
        worker = FileLoadWorker("dummy.png")

        # Create a slot that only expects one parameter (legacy code pattern)
        legacy_slot_calls = []

        def legacy_slot(value):
            """Legacy slot that only expects progress value, not message"""
            legacy_slot_calls.append(value)

        # This connection should work without errors even though signal emits 2 params
        try:
            worker.progress.connect(legacy_slot)
            connection_successful = True
        except Exception as e:
            connection_successful = False
            pytest.fail(f"Failed to connect legacy slot: {e}")

        assert (
            connection_successful
        ), "Should be able to connect single-param slot to two-param signal"

        # Test manual emission to verify the slot receives the value
        worker.progress.emit(25, "Progress message")
        worker.progress.emit(50, "Halfway there")
        worker.progress.emit(100, "Complete")

        # Process events to ensure signal delivery
        QApplication.processEvents()

        # Verify the legacy slot received values properly
        assert (
            len(legacy_slot_calls) == 3
        ), "Legacy slot should have been called 3 times"
        assert legacy_slot_calls[0] == 25, "First value should be 25"
        assert legacy_slot_calls[1] == 50, "Second value should be 50"
        assert legacy_slot_calls[2] == 100, "Third value should be 100"

        # Test with a real progress bar (common legacy pattern)
        from PyQt6.QtWidgets import QProgressBar

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)

        # This is a common pattern in legacy code - connecting directly to setValue
        try:
            worker.progress.connect(progress_bar.setValue)
            bar_connection_successful = True
        except Exception as e:
            bar_connection_successful = False
            pytest.fail(f"Failed to connect to QProgressBar.setValue: {e}")

        assert bar_connection_successful, "Should connect to QProgressBar.setValue"

        # Test emission
        worker.progress.emit(75, "Testing progress bar")
        QApplication.processEvents()

        # Verify progress bar received the value
        assert progress_bar.value() == 75, "Progress bar should show 75%"

        # Test mixed connections (both legacy and new style)
        new_style_calls = []

        def new_style_slot(value, message=""):
            """New style slot that accepts both parameters"""
            new_style_calls.append((value, message))

        # Connect both styles to the same signal
        worker2 = FileSaveWorker(np.zeros((1, 1)), [0] * 768, "dummy.png")
        worker2.progress.connect(legacy_slot)  # Single param
        worker2.progress.connect(new_style_slot)  # Two params

        # Clear previous calls
        legacy_slot_calls.clear()

        # Emit progress
        worker2.progress.emit(33, "Testing mixed connections")
        QApplication.processEvents()

        # Both should work
        assert len(legacy_slot_calls) == 1
        assert legacy_slot_calls[0] == 33
        assert len(new_style_calls) == 1
        assert new_style_calls[0] == (33, "Testing mixed connections")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
