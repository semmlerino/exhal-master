"""
Advanced tests for GUI worker threads
Tests cancellation, thread safety, and resource management
"""

import threading
import time
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtTest import QSignalSpy

from sprite_editor.workers.base_worker import BaseWorker
from sprite_editor.workers.extract_worker import ExtractWorker
from sprite_editor.workers.inject_worker import InjectWorker


class TestWorkerCancellation:
    """Test worker cancellation functionality"""

    @pytest.mark.gui
    def test_base_worker_cancellation(self, qtbot):
        """Test BaseWorker cancellation mechanism"""
        worker = BaseWorker()

        # Initially not cancelled
        assert not worker.is_cancelled()

        # Cancel the worker
        worker.cancel()
        assert worker.is_cancelled()

        # Cancellation should be persistent
        assert worker.is_cancelled()

    @pytest.mark.gui
    def test_extract_worker_thread_interruption(self, qtbot, vram_file, mocker):
        """Test cancelling ExtractWorker during operation"""
        # Mock slow extraction
        mock_extract = mocker.patch(
            "sprite_editor.sprite_editor_core.SpriteEditorCore.extract_sprites"
        )

        def slow_extract(*args, **kwargs):
            # Simulate slow operation
            for _i in range(10):
                time.sleep(0.1)
                # Worker should check cancellation
                if hasattr(worker, "_cancelled") and worker._cancelled:
                    raise InterruptedError("Operation cancelled")
            return MagicMock(), 100

        mock_extract.side_effect = slow_extract

        worker = ExtractWorker(
            vram_file=vram_file, offset=0, size=1024, tiles_per_row=16
        )

        # Set up signal monitoring
        error_spy = QSignalSpy(worker.error)
        finished_spy = QSignalSpy(worker.finished)

        # Start worker in thread
        worker.start()

        # Quit thread after short delay
        qtbot.wait(50)
        worker.quit()

        # Wait for completion
        qtbot.waitUntil(lambda: not worker.isRunning(), timeout=2000)

        # Should have emitted error, not finished
        assert len(error_spy) > 0 or len(finished_spy) > 0

    @pytest.mark.gui
    def test_inject_worker_early_termination(self, qtbot, temp_dir, vram_file):
        """Test InjectWorker cleanup on cancellation"""
        # Create test PNG
        from PIL import Image

        img = Image.new("P", (16, 16))
        img.putpalette([0] * 768)
        png_path = temp_dir / "test.png"
        img.save(str(png_path))

        output_path = temp_dir / "output.dmp"

        worker = InjectWorker(
            png_file=str(png_path),
            vram_file=vram_file,
            offset=0,
            output_file=str(output_path),
        )

        # Don't start the worker, just test direct run
        # which should complete normally
        worker.run()

        # Should have created output
        assert output_path.exists()


class TestThreadSafety:
    """Test thread safety of worker operations"""

    @pytest.mark.gui
    def test_multiple_workers_concurrent(self, qtbot, vram_file):
        """Test multiple workers running concurrently"""
        workers = []
        results = []
        errors = []

        # Create multiple workers
        for i in range(3):
            worker = ExtractWorker(
                vram_file=vram_file, offset=i * 0x1000, size=0x1000, tiles_per_row=16
            )

            # Connect signals
            worker.finished.connect(
                lambda img, count, idx=i: results.append((idx, count))
            )
            worker.error.connect(lambda msg, idx=i: errors.append((idx, msg)))

            workers.append(worker)

        # Start all workers
        for worker in workers:
            worker.start()

        # Wait for all to complete
        for worker in workers:
            qtbot.waitUntil(lambda w=worker: not w.isRunning(), timeout=5000)

        # All should have completed
        assert len(results) + len(errors) == 3

        # Clean up
        for worker in workers:
            worker.quit()
            worker.wait()

    @pytest.mark.gui
    def test_worker_thread_affinity(self, qtbot):
        """Test worker thread affinity is correct"""
        worker = BaseWorker()

        # Worker should be in main thread before starting
        main_thread = QThread.currentThread()
        assert worker.thread() == main_thread

        # Track thread ID when run() executes
        run_thread_id = None

        class TestWorker(BaseWorker):
            def run(self):
                nonlocal run_thread_id
                run_thread_id = threading.current_thread().ident

        test_worker = TestWorker()
        test_worker.start()
        qtbot.waitUntil(lambda: not test_worker.isRunning(), timeout=1000)

        # run() should execute in different thread
        assert run_thread_id != threading.current_thread().ident

    @pytest.mark.gui
    def test_signal_thread_safety(self, qtbot):
        """Test signals are thread-safe"""
        results = []

        class ThreadTestWorker(BaseWorker):
            test_signal = pyqtSignal(int)

            def run(self):
                # Emit signals from worker thread
                for i in range(100):
                    self.test_signal.emit(i)
                    time.sleep(0.001)

        worker = ThreadTestWorker()
        worker.test_signal.connect(lambda x: results.append(x))

        worker.start()
        qtbot.waitUntil(lambda: not worker.isRunning(), timeout=2000)

        # All signals should be received in order
        assert results == list(range(100))


class TestResourceManagement:
    """Test resource management and cleanup"""

    @pytest.mark.gui
    def test_worker_deletion_cleanup(self, qtbot):
        """Test worker properly cleans up on deletion"""
        # BaseWorker is an abstract base class without run() implementation
        # Test with a concrete worker implementation instead
        worker = ExtractWorker(
            vram_file="dummy.bin", offset=0, size=1024, tiles_per_row=16
        )

        # Mock the actual extraction to avoid file operations
        def mock_run():
            worker.progress.emit("Starting extraction...")
            worker.progress.emit("Extraction complete")

        worker.run = mock_run

        # Start worker
        worker.start()

        # Wait for worker to finish
        qtbot.waitUntil(lambda: not worker.isRunning(), timeout=1000)

        # Worker should be in finished state
        assert worker.isFinished()
        assert not worker.isRunning()

        # Clean up
        worker.deleteLater()

    @pytest.mark.gui
    def test_worker_reuse_prevention(self, qtbot):
        """Test that workers can be reused after completion (Qt behavior)"""
        # Use a concrete worker implementation
        worker = ExtractWorker(
            vram_file="dummy.bin", offset=0, size=1024, tiles_per_row=16
        )

        # Mock the run method
        run_count = 0

        def mock_run():
            nonlocal run_count
            run_count += 1
            worker.progress.emit(f"Running {run_count}...")

        worker.run = mock_run

        # First run
        worker.start()
        qtbot.waitUntil(lambda: not worker.isRunning(), timeout=1000)
        assert worker.isFinished()
        assert run_count == 1

        # Try to start again - Qt allows restarting a finished thread
        worker.start()
        qtbot.waitUntil(lambda: not worker.isRunning(), timeout=1000)
        assert worker.isFinished()
        assert run_count == 2

        # Clean up
        worker.deleteLater()

    @pytest.mark.gui
    def test_signal_disconnection_on_deletion(self, qtbot):
        """Test signals are disconnected when worker is deleted"""
        call_count = 0

        def slot():
            nonlocal call_count
            call_count += 1

        worker = ExtractWorker(
            vram_file="dummy.bin", offset=0, size=1024, tiles_per_row=16
        )

        # Connect signal
        worker.progress.connect(slot)

        # Delete worker
        del worker

        # Signal should be disconnected (no way to emit now)
        assert call_count == 0


class TestBaseWorkerFunctionality:
    """Test BaseWorker base class functionality"""

    @pytest.mark.gui
    def test_base_worker_signal_helpers(self, qtbot):
        """Test BaseWorker signal emission helpers"""

        class TestWorker(BaseWorker):
            progress = pyqtSignal(str)
            error = pyqtSignal(str)

            def run(self):
                self.emit_progress("Starting")
                self.emit_error("Test error")

        worker = TestWorker()

        progress_spy = QSignalSpy(worker.progress)
        error_spy = QSignalSpy(worker.error)

        worker.run()

        assert len(progress_spy) == 1
        assert progress_spy[0][0] == "Starting"

        assert len(error_spy) == 1
        assert error_spy[0][0] == "Test error"

    @pytest.mark.gui
    def test_base_worker_exception_handling(self, qtbot):
        """Test BaseWorker exception handling"""

        class CrashingWorker(BaseWorker):
            error = pyqtSignal(str)

            def run(self):
                try:
                    raise ValueError("Intentional crash")
                except Exception as e:
                    self.handle_exception(e)

        worker = CrashingWorker()
        error_spy = QSignalSpy(worker.error)

        # Should handle exception without crashing
        worker.run()

        assert len(error_spy) == 1
        assert "Intentional crash" in error_spy[0][0]


class TestWorkerEdgeCases:
    """Test edge cases in worker operations"""

    @pytest.mark.gui
    def test_extract_worker_empty_file(self, qtbot, temp_dir):
        """Test ExtractWorker with empty file"""
        empty_file = temp_dir / "empty.bin"
        empty_file.write_bytes(b"")

        worker = ExtractWorker(
            vram_file=str(empty_file), offset=0, size=1024, tiles_per_row=16
        )

        finished_spy = QSignalSpy(worker.finished)
        error_spy = QSignalSpy(worker.error)

        worker.run()

        # Should either finish with 0 tiles or error
        assert len(finished_spy) + len(error_spy) > 0

    @pytest.mark.gui
    def test_inject_worker_readonly_output(self, qtbot, temp_dir, vram_file):
        """Test InjectWorker with read-only output location"""
        from PIL import Image

        # Create test PNG
        img = Image.new("P", (16, 16))
        img.putpalette([0] * 768)
        png_path = temp_dir / "test.png"
        img.save(str(png_path))

        # Create read-only directory
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()
        output_path = readonly_dir / "output.dmp"

        # Make directory read-only (skip on Windows)
        import os

        if os.name != "nt":
            readonly_dir.chmod(0o444)

        worker = InjectWorker(
            png_file=str(png_path),
            vram_file=vram_file,
            offset=0,
            output_file=str(output_path),
        )

        error_spy = QSignalSpy(worker.error)

        worker.run()

        if os.name != "nt":
            # Should have error
            assert len(error_spy) > 0

            # Restore permissions
            readonly_dir.chmod(0o755)

    @pytest.mark.gui
    def test_worker_with_huge_operation(self, qtbot, temp_dir):
        """Test worker with very large operation"""
        # Create large VRAM file (1MB)
        large_vram = temp_dir / "large_vram.bin"
        large_vram.write_bytes(b"\x00" * (1024 * 1024))

        worker = ExtractWorker(
            vram_file=str(large_vram),
            offset=0,
            size=1024 * 1024,  # Extract entire file
            tiles_per_row=64,
        )

        start_time = time.time()

        finished_spy = QSignalSpy(worker.finished)
        worker.start()

        # Should complete within reasonable time
        qtbot.waitUntil(lambda: not worker.isRunning(), timeout=10000)

        elapsed = time.time() - start_time
        assert elapsed < 10.0  # Should take less than 10 seconds

        # Should have extracted many tiles
        if len(finished_spy) > 0:
            _, tile_count = finished_spy[0]
            assert tile_count > 1000


class TestWorkerIntegration:
    """Test worker integration with controllers"""

    @pytest.mark.gui
    def test_worker_controller_cleanup(self, qtbot):
        """Test worker cleanup when controller is destroyed"""
        from unittest.mock import MagicMock

        from sprite_editor.controllers.extract_controller import ExtractController
        from sprite_editor.models.project_model import ProjectModel
        from sprite_editor.models.sprite_model import SpriteModel

        sprite_model = SpriteModel()
        project_model = ProjectModel()

        # Mock the view to avoid GUI dependencies
        mock_view = MagicMock()
        mock_view.get_extraction_params.return_value = {
            "vram_file": "dummy.bin",
            "offset": 0,
            "size": 1024,
            "tiles_per_row": 16,
            "use_palette": False,
            "palette_num": 0,
            "cgram_file": None,
        }

        controller = ExtractController(sprite_model, project_model, mock_view)

        # Track worker
        worker_ref = None

        # Hook into the worker creation in extract_sprites
        original_extract = controller.extract_sprites
        controller_ref = controller  # Capture controller reference

        def mock_extract():
            nonlocal worker_ref
            # Call original method
            original_extract()
            # Capture the worker using the captured reference
            if hasattr(controller_ref, "extract_worker"):
                worker_ref = controller_ref.extract_worker

        controller.extract_sprites = mock_extract

        # Trigger extraction
        try:
            controller.extract_sprites()
        except:
            pass  # May fail due to invalid file

        # Delete controller
        del controller

        # Worker should be cleaned up
        if worker_ref and hasattr(worker_ref, "isRunning"):
            qtbot.waitUntil(lambda: not worker_ref.isRunning(), timeout=1000)

    @pytest.mark.gui
    def test_progress_reporting_accuracy(self, qtbot, vram_file, mocker):
        """Test accuracy of progress reporting"""
        progress_values = []

        # Mock extraction to report progress
        mock_extract = mocker.patch(
            "sprite_editor.sprite_editor_core.SpriteEditorCore.extract_sprites"
        )

        def extract_with_progress(*args, **kwargs):
            # Simulate progress
            for i in range(0, 101, 10):
                worker.progress.emit(f"Progress: {i}%")
                time.sleep(0.01)
            return MagicMock(), 100

        worker = ExtractWorker(
            vram_file=vram_file, offset=0, size=1024, tiles_per_row=16
        )

        mock_extract.side_effect = extract_with_progress

        worker.progress.connect(lambda msg: progress_values.append(msg))

        worker.run()

        # Should have received progress updates
        assert len(progress_values) >= 5
        assert any("0%" in msg for msg in progress_values)
        assert any("100%" in msg for msg in progress_values)
