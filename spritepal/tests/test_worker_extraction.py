"""
Unit tests for extraction worker implementations.

Tests the VRAMExtractionWorker and ROMExtractionWorker classes to ensure
proper manager delegation, signal handling, and error management.
"""

from unittest.mock import Mock, patch

import pytest
from PIL import Image
from PyQt6.QtTest import QSignalSpy

from spritepal.core.managers.base_manager import BaseManager
from spritepal.core.workers.extraction import ROMExtractionWorker, VRAMExtractionWorker


class TestVRAMExtractionWorker:
    """Test the VRAMExtractionWorker class."""

    def test_vram_worker_initialization(self, qtbot):
        """Test VRAM extraction worker initialization."""
        params = {
            "vram_path": "/test/vram.dmp",
            "output_base": "/test/output",
            "create_grayscale": True,
        }

        with patch("spritepal.core.workers.extraction.get_extraction_manager") as mock_get_manager:
            mock_manager = Mock(spec=BaseManager)
            mock_get_manager.return_value = mock_manager

            worker = VRAMExtractionWorker(params)
            qtbot.addWidget(worker)

            assert worker.params == params
            assert worker.manager is mock_manager
            assert worker._operation_name == "VRAMExtractionWorker"
            assert worker._connections == []

    def test_vram_manager_signal_connections(self, qtbot):
        """Test VRAM worker manager signal connections."""
        params = {
            "vram_path": "/test/vram.dmp",
            "output_base": "/test/output",
        }

        with patch("spritepal.core.workers.extraction.get_extraction_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.extraction_progress = Mock()
            mock_manager.palettes_extracted = Mock()
            mock_manager.active_palettes_found = Mock()
            mock_manager.preview_generated = Mock()

            # Mock connection objects
            mock_connection = Mock()
            mock_manager.extraction_progress.connect.return_value = mock_connection
            mock_manager.palettes_extracted.connect.return_value = mock_connection
            mock_manager.active_palettes_found.connect.return_value = mock_connection
            mock_manager.preview_generated.connect.return_value = mock_connection

            mock_get_manager.return_value = mock_manager

            worker = VRAMExtractionWorker(params)
            qtbot.addWidget(worker)

            # Test signal connections
            worker.connect_manager_signals()

            # Verify connections were made
            assert mock_manager.extraction_progress.connect.called
            assert mock_manager.palettes_extracted.connect.called
            assert mock_manager.active_palettes_found.connect.called
            assert mock_manager.preview_generated.connect.called

            # Verify connections were stored
            assert len(worker._connections) == 4

    def test_vram_preview_signal_conversion(self, qtbot):
        """Test PIL to QPixmap conversion in preview signals."""
        params = {
            "vram_path": "/test/vram.dmp",
            "output_base": "/test/output",
        }

        with patch("spritepal.core.workers.extraction.get_extraction_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.extraction_progress = Mock()
            mock_manager.palettes_extracted = Mock()
            mock_manager.active_palettes_found = Mock()
            mock_manager.preview_generated = Mock()

            # Mock connection returns
            mock_connection = Mock()
            mock_manager.extraction_progress.connect.return_value = mock_connection
            mock_manager.palettes_extracted.connect.return_value = mock_connection
            mock_manager.active_palettes_found.connect.return_value = mock_connection
            mock_manager.preview_generated.connect.return_value = mock_connection

            mock_get_manager.return_value = mock_manager

            worker = VRAMExtractionWorker(params)
            qtbot.addWidget(worker)

            # Set up signal spies
            preview_spy = QSignalSpy(worker.preview_ready)
            preview_image_spy = QSignalSpy(worker.preview_image_ready)

            # Connect signals and get the preview callback
            worker.connect_manager_signals()

            # Get the callback function from the connect call
            preview_callback = mock_manager.preview_generated.connect.call_args[0][0]

            # Create a mock PIL image
            mock_image = Mock(spec=Image.Image)
            tile_count = 10

            # Mock the pil_to_qpixmap function
            with patch("spritepal.core.workers.extraction.pil_to_qpixmap") as mock_pil_to_qpixmap:
                mock_pixmap = Mock()
                mock_pil_to_qpixmap.return_value = mock_pixmap

                # Call the preview callback
                preview_callback(mock_image, tile_count)

                # Verify pil_to_qpixmap was called
                mock_pil_to_qpixmap.assert_called_once_with(mock_image)

                # Verify signals were emitted
                assert len(preview_spy) == 1
                assert preview_spy[0] == [mock_pixmap, tile_count]

                assert len(preview_image_spy) == 1
                assert preview_image_spy[0] == [mock_image]

    def test_vram_successful_operation(self, qtbot):
        """Test successful VRAM extraction operation."""
        params = {
            "vram_path": "/test/vram.dmp",
            "output_base": "/test/output",
            "create_grayscale": True,
        }

        with patch("spritepal.core.workers.extraction.get_extraction_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.extract_from_vram.return_value = ["file1.png", "file2.pal.json"]
            mock_get_manager.return_value = mock_manager

            worker = VRAMExtractionWorker(params)
            qtbot.addWidget(worker)

            # Set up signal spies
            extraction_spy = QSignalSpy(worker.extraction_finished)
            operation_spy = QSignalSpy(worker.operation_finished)

            # Perform operation
            worker.perform_operation()

            # Verify manager was called with correct parameters
            mock_manager.extract_from_vram.assert_called_once_with(
                vram_path="/test/vram.dmp",
                output_base="/test/output",
                cgram_path=None,
                oam_path=None,
                vram_offset=None,
                create_grayscale=True,
                create_metadata=True,
                grayscale_mode=False,
            )

            # Verify completion signals
            assert len(extraction_spy) == 1
            assert extraction_spy[0] == [["file1.png", "file2.pal.json"]]

            assert len(operation_spy) == 1
            assert operation_spy[0] == [True, "Successfully extracted 2 files"]

    def test_vram_operation_error_handling(self, qtbot):
        """Test VRAM extraction error handling."""
        params = {
            "vram_path": "/test/vram.dmp",
            "output_base": "/test/output",
        }

        with patch("spritepal.core.workers.extraction.get_extraction_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.extract_from_vram.side_effect = ValueError("Test extraction error")
            mock_get_manager.return_value = mock_manager

            worker = VRAMExtractionWorker(params)
            qtbot.addWidget(worker)

            # Set up signal spies
            error_spy = QSignalSpy(worker.error)
            operation_spy = QSignalSpy(worker.operation_finished)

            # Perform operation (should handle error)
            worker.perform_operation()

            # Verify error handling
            assert len(error_spy) == 1
            assert "VRAM extraction failed: Test extraction error" in error_spy[0][0]
            assert isinstance(error_spy[0][1], ValueError)

            assert len(operation_spy) == 1
            assert operation_spy[0][0] is False  # Success = False
            assert "VRAM extraction failed: Test extraction error" in operation_spy[0][1]

    def test_vram_worker_with_real_manager_signals_improved(self, qtbot):
        """
        IMPROVED VERSION: Test VRAM worker with real manager and real signals.

        This demonstrates the superior approach of testing real manager behavior
        instead of mocking everything. Real manager testing:
        - Tests actual manager signal emissions and content
        - Verifies real manager-worker communication
        - Catches manager implementation bugs that mocks miss
        - Tests real Qt signal connection behavior
        """
        from PyQt6.QtTest import QSignalSpy
        from tests.infrastructure import RealManagerFixtureFactory, TestDataRepository


        # Create test data using the repository
        test_data_repo = TestDataRepository()

        try:
            # Use RealManagerFixtureFactory for isolated manager instances (safer)
            manager_factory = RealManagerFixtureFactory()

            # Get real test data that will pass manager validation
            test_data = test_data_repo.get_vram_extraction_data("small")  # Creates realistic test files

            params = {
                "vram_path": test_data["vram_path"],
                "cgram_path": test_data["cgram_path"],
                "output_base": test_data["output_base"],
                "create_grayscale": True,
                "create_metadata": True,
                "vram_offset": None,  # Use default offset to avoid validation errors
            }

            # Create isolated extraction manager for this test
            extraction_manager = manager_factory.create_extraction_manager(isolated=True)

            # Create worker with REAL manager (no mocking!)
            worker = VRAMExtractionWorker(params)
            # Override the worker's manager with our isolated instance for testing
            worker.manager = extraction_manager
            # Note: QThread doesn't need qtbot.addWidget()

            # Set up QSignalSpy to monitor REAL worker signals
            progress_spy = QSignalSpy(worker.progress)
            preview_ready_spy = QSignalSpy(worker.preview_ready)
            QSignalSpy(worker.preview_image_ready)
            palettes_ready_spy = QSignalSpy(worker.palettes_ready)
            QSignalSpy(worker.active_palettes_ready)
            extraction_finished_spy = QSignalSpy(worker.extraction_finished)
            operation_finished_spy = QSignalSpy(worker.operation_finished)
            error_spy = QSignalSpy(worker.error)

            # Connect to manager signals to verify real manager communication
            manager_signal_data = []
            worker.manager.extraction_progress.connect(
                lambda percent, msg: manager_signal_data.append(("progress", percent, msg))
            )
            # Fix signal signature - preview_generated expects different arguments
            worker.manager.preview_generated.connect(
                lambda *args: manager_signal_data.append(("preview", args))
            )

            # Connect manager signals to worker (tests real signal connections)
            worker.connect_manager_signals()

            # Perform the actual operation with real manager
            worker.perform_operation()

            # Disconnect worker signals before cleanup to prevent Qt object lifecycle issues
            worker.disconnect_manager_signals()

            # REAL SIGNAL TESTING: Verify actual signal emissions and content

            # Verify progress signals were emitted with real content
            assert len(progress_spy) > 0, "Progress signals should be emitted by real manager"
            # Check actual progress signal content
            first_progress = progress_spy[0]
            assert len(first_progress) == 2, "Progress should have percent and message"
            assert isinstance(first_progress[0], int), "Progress percent should be int"
            assert isinstance(first_progress[1], str), "Progress message should be string"
            assert 0 <= first_progress[0] <= 100, "Progress should be 0-100"

            # REAL BEHAVIOR: Check if operation succeeded or failed with real error handling
            if len(error_spy) == 0:
                # Success case: verify completion signals
                assert len(extraction_finished_spy) == 1, "Should have exactly one completion signal"
                output_files = extraction_finished_spy[0][0]  # First arg of first emission
                assert isinstance(output_files, list), "Output files should be a list"
                assert len(output_files) > 0, "Should have output files from real extraction"

                # Verify output files actually exist (real behavior, not mocked)
                from pathlib import Path
                for file_path in output_files:
                    assert Path(file_path).exists(), f"Real output file should exist: {file_path}"

                # Verify operation completion signal
                assert len(operation_finished_spy) == 1, "Should have operation completion"
                operation_result = operation_finished_spy[0]
                assert operation_result[0] is True, "Operation should succeed"
                print("✓ Operation completed successfully")
            else:
                # Error case: verify error handling with real errors
                assert len(error_spy) >= 1, "Should have error signals for failed operation"
                error_message = error_spy[0][0]  # Error message
                assert isinstance(error_message, str), "Error message should be string"
                print(f"✓ Real error handling tested: {error_message}")

                # Verify operation finished with failure
                assert len(operation_finished_spy) == 1, "Should have operation completion even on error"
                operation_result = operation_finished_spy[0]
                assert operation_result[0] is False, "Operation should fail"

            # Verify real manager signal communication worked
            assert len(manager_signal_data) > 0, "Real manager signals should be received"

            # Verify we got real preview data if CGRAM was provided
            if test_data["cgram_path"]:
                assert len(preview_ready_spy) > 0, "Preview signals should be emitted"
                assert len(palettes_ready_spy) > 0, "Palette signals should be emitted"

            print("✓ Real manager-worker integration test passed:")
            print(f"  - Progress signals: {len(progress_spy)}")
            print(f"  - Preview signals: {len(preview_ready_spy)}")
            print(f"  - Palette signals: {len(palettes_ready_spy)}")
            print(f"  - Completion signals: {len(extraction_finished_spy)}")
            print(f"  - Manager signals: {len(manager_signal_data)}")
            print(f"  - Output files: {len(output_files)}")
            print(f"  - No errors: {len(error_spy) == 0}")

        finally:
            # Cleanup (use manager factory cleanup instead of singleton cleanup)
            manager_factory.cleanup()
            test_data_repo.cleanup()


class TestROMExtractionWorker:
    """Test the ROMExtractionWorker class."""

    def test_rom_worker_initialization(self, qtbot):
        """Test ROM extraction worker initialization."""
        params = {
            "rom_path": "/test/rom.smc",
            "sprite_offset": 0x1000,
            "output_base": "/test/output",
            "sprite_name": "test_sprite",
        }

        with patch("spritepal.core.workers.extraction.get_extraction_manager") as mock_get_manager:
            mock_manager = Mock(spec=BaseManager)
            mock_get_manager.return_value = mock_manager

            worker = ROMExtractionWorker(params)
            qtbot.addWidget(worker)

            assert worker.params == params
            assert worker.manager is mock_manager
            assert worker._operation_name == "ROMExtractionWorker"
            assert worker._connections == []

    def test_rom_manager_signal_connections(self, qtbot):
        """Test ROM worker manager signal connections."""
        params = {
            "rom_path": "/test/rom.smc",
            "sprite_offset": 0x1000,
            "output_base": "/test/output",
            "sprite_name": "test_sprite",
        }

        with patch("spritepal.core.workers.extraction.get_extraction_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.extraction_progress = Mock()

            # Mock connection object
            mock_connection = Mock()
            mock_manager.extraction_progress.connect.return_value = mock_connection

            mock_get_manager.return_value = mock_manager

            worker = ROMExtractionWorker(params)
            qtbot.addWidget(worker)

            # Test signal connections
            worker.connect_manager_signals()

            # Verify connection was made
            assert mock_manager.extraction_progress.connect.called

            # Verify connection was stored
            assert len(worker._connections) == 1

    def test_rom_successful_operation(self, qtbot):
        """Test successful ROM extraction operation."""
        params = {
            "rom_path": "/test/rom.smc",
            "sprite_offset": 0x1000,
            "output_base": "/test/output",
            "sprite_name": "test_sprite",
            "cgram_path": "/test/cgram.dmp",
        }

        with patch("spritepal.core.workers.extraction.get_extraction_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.extract_from_rom.return_value = ["sprite.png", "sprite.pal.json"]
            mock_get_manager.return_value = mock_manager

            worker = ROMExtractionWorker(params)
            qtbot.addWidget(worker)

            # Set up signal spies
            extraction_spy = QSignalSpy(worker.extraction_finished)
            operation_spy = QSignalSpy(worker.operation_finished)

            # Perform operation
            worker.perform_operation()

            # Verify manager was called with correct parameters
            mock_manager.extract_from_rom.assert_called_once_with(
                rom_path="/test/rom.smc",
                offset=0x1000,
                output_base="/test/output",
                sprite_name="test_sprite",
                cgram_path="/test/cgram.dmp",
            )

            # Verify completion signals
            assert len(extraction_spy) == 1
            assert extraction_spy[0] == [["sprite.png", "sprite.pal.json"]]

            assert len(operation_spy) == 1
            assert operation_spy[0] == [True, "Successfully extracted 2 files"]

    def test_rom_operation_error_handling(self, qtbot):
        """Test ROM extraction error handling."""
        params = {
            "rom_path": "/test/rom.smc",
            "sprite_offset": 0x1000,
            "output_base": "/test/output",
            "sprite_name": "test_sprite",
        }

        with patch("spritepal.core.workers.extraction.get_extraction_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.extract_from_rom.side_effect = FileNotFoundError("ROM file not found")
            mock_get_manager.return_value = mock_manager

            worker = ROMExtractionWorker(params)
            qtbot.addWidget(worker)

            # Set up signal spies
            error_spy = QSignalSpy(worker.error)
            operation_spy = QSignalSpy(worker.operation_finished)

            # Perform operation (should handle error)
            worker.perform_operation()

            # Verify error handling
            assert len(error_spy) == 1
            assert "ROM extraction failed: ROM file not found" in error_spy[0][0]
            assert isinstance(error_spy[0][1], FileNotFoundError)

            assert len(operation_spy) == 1
            assert operation_spy[0][0] is False  # Success = False
            assert "ROM extraction failed: ROM file not found" in operation_spy[0][1]

    def test_rom_operation_cancellation(self, qtbot):
        """Test ROM extraction cancellation handling."""
        params = {
            "rom_path": "/test/rom.smc",
            "sprite_offset": 0x1000,
            "output_base": "/test/output",
            "sprite_name": "test_sprite",
        }

        with patch("spritepal.core.workers.extraction.get_extraction_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager

            worker = ROMExtractionWorker(params)
            qtbot.addWidget(worker)

            # Cancel the worker
            worker.cancel()

            # Performing operation should raise InterruptedError
            with pytest.raises(InterruptedError, match="Operation was cancelled"):
                worker.perform_operation()


@pytest.fixture
def qtbot():
    """Provide qtbot for Qt testing."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    class QtBot:
        def addWidget(self, widget):
            pass

    return QtBot()
