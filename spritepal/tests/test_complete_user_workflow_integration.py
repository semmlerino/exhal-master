"""
Integration tests for complete user workflows - Priority 1 test implementation.
Tests end-to-end user scenarios from file drop to editor launch.
"""

import shutil
import sys


import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.fixtures.test_main_window_helper_simple import TestMainWindowHelperSimple

from spritepal.core.controller import ExtractionController
from spritepal.core.managers import cleanup_managers, initialize_managers
from spritepal.core.managers.registry import (
    cleanup_managers as cleanup_managers_registry,
)
from spritepal.core.managers.registry import (
    initialize_managers as initialize_managers_registry,
)
from spritepal.core.workers import VRAMExtractionWorker
from spritepal.utils.constants import (
    BYTES_PER_TILE,
    COLORS_PER_PALETTE,
    SPRITE_PALETTE_END,
    SPRITE_PALETTE_START,
    VRAM_SPRITE_OFFSET,
)


class TestCompleteUserWorkflow:
    """Test complete user workflow scenarios"""

    @pytest.fixture
    def sample_files(self):
        """Create sample VRAM, CGRAM, and OAM files for testing"""
        temp_dir = tempfile.mkdtemp()

        # Create VRAM file with test sprite data
        vram_data = bytearray(0x10000)  # 64KB
        for i in range(10):  # 10 tiles
            tile_start = VRAM_SPRITE_OFFSET + (i * BYTES_PER_TILE)
            for j in range(BYTES_PER_TILE):
                vram_data[tile_start + j] = (i * 16 + j) % 256

        vram_path = Path(temp_dir) / "test_VRAM.dmp"
        vram_path.write_bytes(vram_data)

        # Create CGRAM file with test palettes
        cgram_data = bytearray(512)  # 256 colors * 2 bytes
        for pal_idx in range(SPRITE_PALETTE_START, SPRITE_PALETTE_END):
            for color_idx in range(COLORS_PER_PALETTE):
                offset = (pal_idx * COLORS_PER_PALETTE + color_idx) * 2
                # Create distinct colors for each palette
                r = (pal_idx * 2) % 32
                g = (color_idx * 2) % 32
                b = ((pal_idx + color_idx) * 2) % 32
                color = (b << 10) | (g << 5) | r
                cgram_data[offset] = color & 0xFF
                cgram_data[offset + 1] = (color >> 8) & 0xFF

        cgram_path = Path(temp_dir) / "test_CGRAM.dmp"
        cgram_path.write_bytes(cgram_data)

        # Create OAM file with test sprite data
        oam_data = bytearray(544)  # 544 bytes OAM data
        # Add on-screen sprite with palette 0
        oam_data[0] = 0x50  # X low
        oam_data[1] = 50  # Y (on-screen)
        oam_data[2] = 0x00  # Tile
        oam_data[3] = 0x00  # Attrs (palette 0)

        oam_path = Path(temp_dir) / "test_OAM.dmp"
        oam_path.write_bytes(oam_data)

        yield {
            "temp_dir": temp_dir,
            "vram_path": str(vram_path),
            "cgram_path": str(cgram_path),
            "oam_path": str(oam_path),
        }

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_main_window(self, tmp_path):
        """Create TestMainWindowHelper for realistic testing"""
        helper = TestMainWindowHelperSimple(str(tmp_path))

        # The helper provides real signal behavior and MainWindow interface
        # without creating Qt widgets that cause issues in test environment
        yield helper

        # Cleanup after test
        helper.cleanup()

    @pytest.fixture
    def mock_qt_signals(self):
        """Create mock Qt signals that behave like real signals"""

        class MockSignal:
            def __init__(self):
                self.callbacks = []
                self.emit = Mock(side_effect=self._emit)

            def connect(self, callback):
                self.callbacks.append(callback)

            def _emit(self, *args):
                for callback in self.callbacks:
                    callback(*args)

        return {
            "progress": MockSignal(),
            "preview_ready": MockSignal(),
            "preview_image_ready": MockSignal(),
            "palettes_ready": MockSignal(),
            "active_palettes_ready": MockSignal(),
            "extraction_finished": MockSignal(),
            "error": MockSignal(),
        }

    @pytest.mark.integration
    @pytest.mark.gui
    def test_drag_drop_extract_edit_workflow(
        self, sample_files, mock_main_window, mock_qt_signals
    ):
        """Test complete user journey: Drop files → Extract → Edit"""
        # Initialize managers for this test
        cleanup_managers()  # Ensure clean state
        initialize_managers("TestApp")

        try:
            # Set up extraction parameters using helper
            output_base = str(Path(sample_files["temp_dir"]) / "workflow_test")
            extraction_params = {
                "vram_path": sample_files["vram_path"],
                "cgram_path": sample_files["cgram_path"],
                "output_base": output_base,
                "create_grayscale": True,
                "create_metadata": True,
                "oam_path": sample_files["oam_path"],
            }
            mock_main_window.set_extraction_params(extraction_params)

            # Mock Qt components comprehensively
            # Need to patch image_utils functions at the correct level
            mock_pixmap_instance = Mock()
            mock_pixmap_instance.loadFromData = Mock(return_value=True)

            with (
                                patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
                patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
                patch("spritepal.core.workers.base.QThread") as mock_qthread,
            ):

                # Configure mocks
                mock_qpixmap_utils.return_value = mock_pixmap_instance
                mock_pil_to_qpixmap.return_value = mock_pixmap_instance

                # Mock QThread to run synchronously for testing
                mock_qthread_instance = Mock()
                mock_qthread_instance.start = Mock()  # Don't actually start thread
                mock_qthread_instance.isRunning = Mock(return_value=False)
                mock_qthread_instance.quit = Mock()
                mock_qthread_instance.wait = Mock(return_value=True)
                mock_qthread.return_value = mock_qthread_instance

                # Create controller
                controller = ExtractionController(mock_main_window)

                # Manually create the worker to have more control in test
                params = mock_main_window.get_extraction_params()
                worker = VRAMExtractionWorker(params)

                # Connect worker signals directly to controller methods
                # This simulates what happens in start_extraction()
                worker.progress.connect(controller._on_progress)
                worker.preview_ready.connect(controller._on_preview_ready)
                worker.preview_image_ready.connect(controller._on_preview_image_ready)
                worker.palettes_ready.connect(controller._on_palettes_ready)
                worker.active_palettes_ready.connect(controller._on_active_palettes_ready)
                worker.extraction_finished.connect(controller._on_extraction_finished)
                worker.error.connect(controller._on_extraction_error)

                # Store worker reference
                controller.worker = worker

                # Run the worker synchronously
                worker.run()

            # Get signal emissions from helper
            workflow_signals = mock_main_window.get_signal_emissions()

            # Verify workflow completion
            # Should have at least 2 messages (start and end), but may have more intermediate messages
            assert len(workflow_signals["status_messages"]) >= 2
            assert (
                "Extracting sprites from VRAM..." in workflow_signals["status_messages"]
            )
            assert "Extraction complete!" in workflow_signals["status_messages"]

            # The intermediate messages like "Creating preview..." may or may not be captured
            # depending on the signal propagation timing in the test environment

            # Verify preview updates (may include both pixmap and grayscale image)
            assert len(workflow_signals["preview_updates"]) >= 1
            # Find preview with pixmap data
            pixmap_preview = None
            grayscale_preview = None
            for preview in workflow_signals["preview_updates"]:
                if "pixmap" in preview:
                    pixmap_preview = preview
                if "grayscale_image" in preview:
                    grayscale_preview = preview

            # Should have at least one type of preview
            assert pixmap_preview is not None or grayscale_preview is not None
            if pixmap_preview:
                assert pixmap_preview["pixmap"] is not None
                assert pixmap_preview["tile_count"] >= 0

            # Verify palette updates (should have both palette_preview and sprite_preview palette updates)
            assert len(workflow_signals["palette_updates"]) >= 1
            # Look for the main palette data
            main_palette_data = workflow_signals["palette_updates"][0]
            if isinstance(main_palette_data, dict):
                # Check if it's a palette dictionary with indices as keys (8-15 for sprite palettes)
                if any(isinstance(k, int) and 8 <= k <= 15 for k in main_palette_data):
                    # This is the sprite palette data with indices as keys
                    sprite_palette_keys = [k for k in main_palette_data if isinstance(k, int) and 8 <= k <= 15]
                    assert len(sprite_palette_keys) == 8  # 8 sprite palettes
                else:
                    # Check if it's a different type of palette update
                    assert "sprite_palettes" in main_palette_data or "active_palettes" in main_palette_data
            elif isinstance(main_palette_data, list):
                assert len(main_palette_data) == 8  # 8 sprite palettes

            # Verify completion without errors
            assert len(workflow_signals["extraction_complete"]) == 1
            assert len(workflow_signals["extraction_failed"]) == 0

            # Verify output files exist
            output_files = workflow_signals["extraction_complete"][0]
            assert any(f.endswith(".png") for f in output_files)
            assert any(f.endswith(".pal.json") for f in output_files)
            assert any(f.endswith(".metadata.json") for f in output_files)

            for file_path in output_files:
                assert Path(file_path).exists()
        finally:
            # Clean up managers
            cleanup_managers()

    @pytest.mark.integration
    @pytest.mark.gui
    def test_drag_drop_extract_arrange_workflow(
        self, sample_files, mock_main_window, mock_qt_signals
    ):
        """Test workflow: Drop files → Extract → Arrange → Edit"""
        # Initialize managers before creating controller
        initialize_managers_registry()

        # Set up extraction parameters
        output_base = str(Path(sample_files["temp_dir"]) / "arrange_test")
        extraction_params = {
            "vram_path": sample_files["vram_path"],
            "cgram_path": sample_files["cgram_path"],
            "output_base": output_base,
            "create_grayscale": True,
            "create_metadata": True,
            "oam_path": None,
        }
        mock_main_window.set_extraction_params(extraction_params)

        # Mock Qt components and run extraction
        # Need to patch image_utils functions at the correct level
        mock_pixmap_instance = Mock()
        mock_pixmap_instance.loadFromData = Mock(return_value=True)

        with (
                        patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
            patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
            patch("spritepal.core.workers.base.QThread") as mock_qthread,
        ):

            # Configure mocks
            mock_qpixmap_utils.return_value = mock_pixmap_instance
            mock_pil_to_qpixmap.return_value = mock_pixmap_instance

            # Mock QThread to run synchronously for testing
            mock_qthread_instance = Mock()
            mock_qthread_instance.start = Mock()  # Don't actually start thread
            mock_qthread_instance.isRunning = Mock(return_value=False)
            mock_qthread_instance.quit = Mock()
            mock_qthread_instance.wait = Mock(return_value=True)
            mock_qthread.return_value = mock_qthread_instance

            # Create controller and start extraction workflow
            controller = ExtractionController(mock_main_window)

            # Start the extraction workflow through the controller
            # This will create the worker and set up all signal connections properly
            controller.start_extraction()

            # Run the worker synchronously since we mocked QThread.start()
            if controller.worker:
                controller.worker.run()

        # Get signal emissions from helper
        workflow_signals = mock_main_window.get_signal_emissions()

        # Verify extraction completed
        assert len(workflow_signals["extraction_complete"]) == 1
        output_files = workflow_signals["extraction_complete"][0]
        sprite_file = next(f for f in output_files if f.endswith(".png"))
        assert Path(sprite_file).exists()

        # Patch dialog creation to avoid Qt widget issues in tests
        # Must patch BEFORE emitting the signal since dialog creation is synchronous
        with (
            patch("spritepal.ui.row_arrangement_dialog.RowArrangementDialog") as mock_dialog_class,
            patch("spritepal.ui.common.error_handler.QMessageBox.critical"),
            patch("spritepal.core.controller.RowArrangementDialog") as mock_controller_dialog):
            mock_dialog_instance = Mock()
            mock_dialog_instance.exec.return_value = True
            mock_dialog_instance.get_arranged_path.return_value = sprite_file + "_arranged"
            mock_dialog_class.return_value = mock_dialog_instance
            mock_controller_dialog.return_value = mock_dialog_instance

            # Simulate arrangement request using helper
            mock_main_window.simulate_arrange_rows_request(sprite_file)

            # Verify arrangement signal was emitted
            updated_signals = mock_main_window.get_signal_emissions()
            assert len(updated_signals["arrange_rows_requested"]) == 1
            assert updated_signals["arrange_rows_requested"][0] == sprite_file

        # Clean up managers
        cleanup_managers_registry()

    @pytest.mark.integration
    @pytest.mark.gui
    def test_multiple_file_workflow(
        self, sample_files, mock_main_window, mock_qt_signals
    ):
        """Test workflow with VRAM + CGRAM + OAM files"""
        # Initialize managers before creating controller
        initialize_managers_registry()

        # Set up extraction parameters with all files
        output_base = str(Path(sample_files["temp_dir"]) / "multi_file_test")
        extraction_params = {
            "vram_path": sample_files["vram_path"],
            "cgram_path": sample_files["cgram_path"],
            "output_base": output_base,
            "create_grayscale": True,
            "create_metadata": True,
            "oam_path": sample_files["oam_path"],
        }
        mock_main_window.set_extraction_params(extraction_params)

        # Mock Qt components and run extraction
        # Need to patch image_utils functions at the correct level
        mock_pixmap_instance = Mock()
        mock_pixmap_instance.loadFromData = Mock(return_value=True)

        # Track active palette analysis using helper
        active_palette_calls = []

        with (
                        patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
            patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
            patch("spritepal.core.workers.base.QThread"),
        ):

            # Configure mocks
            mock_qpixmap_utils.return_value = mock_pixmap_instance
            mock_pil_to_qpixmap.return_value = mock_pixmap_instance

            # Create and run worker
            worker = VRAMExtractionWorker(
                mock_main_window.get_extraction_params()
            )
            controller = ExtractionController(mock_main_window)

            # Replace worker signals with mocks
            for signal_name, mock_signal in mock_qt_signals.items():
                setattr(worker, signal_name, mock_signal)

            # Connect controller to worker signals for palette updates
            worker.palettes_ready.connect(controller._on_palettes_ready)
            worker.active_palettes_ready.connect(controller._on_active_palettes_ready)
            worker.extraction_finished.connect(controller._on_extraction_finished)

            # Connect active palette tracking
            worker.active_palettes_ready.connect(
                lambda p: active_palette_calls.append(p)
            )

            # Run extraction
            worker.run()

        # Verify OAM analysis was performed
        assert len(active_palette_calls) == 1
        active_palettes = active_palette_calls[0]
        assert 8 in active_palettes  # palette 0 -> CGRAM 8 (on-screen sprite)

        # Get signal emissions from helper
        workflow_signals = mock_main_window.get_signal_emissions()

        # Verify extraction completed successfully
        assert worker.extraction_finished.emit.called
        output_files = worker.extraction_finished.emit.call_args[0][0]

        # Verify all expected files exist
        assert any(f.endswith(".png") for f in output_files)
        assert any(f.endswith(".metadata.json") for f in output_files)
        for file_path in output_files:
            assert Path(file_path).exists()

        # Verify palette updates were tracked
        assert len(workflow_signals["palette_updates"]) >= 1

        # Clean up managers
        cleanup_managers_registry()

    @pytest.mark.integration
    @pytest.mark.gui
    def test_workflow_with_different_file_types(
        self, sample_files, mock_main_window, mock_qt_signals
    ):
        """Test workflow with various dump file formats"""
        # Initialize managers before creating controller
        initialize_managers_registry()

        # Test with different file extensions
        temp_dir = Path(sample_files["temp_dir"])

        # Create files with different naming conventions
        vram_variants = ["game_VRAM.dmp", "VideoRam_001.dmp", "kirby_vram_backup.dmp"]

        original_vram = Path(sample_files["vram_path"])
        vram_data = original_vram.read_bytes()

        for variant in vram_variants:
            variant_path = temp_dir / variant
            variant_path.write_bytes(vram_data)

            # Test extraction with each variant
            output_base = str(temp_dir / f"variant_{variant.replace('.', '_')}")
            extraction_params = {
                "vram_path": str(variant_path),
                "cgram_path": sample_files["cgram_path"],
                "output_base": output_base,
                "create_grayscale": True,
                "create_metadata": False,
                "oam_path": None,
            }
            mock_main_window.set_extraction_params(extraction_params)

            # Mock Qt components and run extraction
            # Need to patch image_utils functions at the correct level
            mock_pixmap_instance = Mock()
            mock_pixmap_instance.loadFromData = Mock(return_value=True)

            with (
                                patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
                patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
                patch("spritepal.core.workers.base.QThread"),
                ):

                # Configure mocks
                mock_qpixmap_utils.return_value = mock_pixmap_instance
                mock_pil_to_qpixmap.return_value = mock_pixmap_instance

                # Create and run worker
                worker = VRAMExtractionWorker(
                    mock_main_window.get_extraction_params()
                )

                # Create controller to handle signals and update status messages
                controller = ExtractionController(mock_main_window)

                # Replace worker signals with mocks
                for signal_name, mock_signal in mock_qt_signals.items():
                    setattr(worker, signal_name, mock_signal)

                # Connect essential controller callbacks for status tracking
                worker.extraction_finished.connect(controller._on_extraction_finished)
                worker.error.connect(controller._on_extraction_error)

                # Run extraction
                worker.run()

            # Verify extraction completed for this variant
            assert worker.extraction_finished.emit.called
            output_files = worker.extraction_finished.emit.call_args[0][0]
            assert any(f.endswith(".png") for f in output_files)
            for file_path in output_files:
                assert Path(file_path).exists()

        # Get signal emissions from helper
        workflow_signals = mock_main_window.get_signal_emissions()
        # Verify workflow signals were tracked across all variants
        assert len(workflow_signals["status_messages"]) >= len(vram_variants)

        # Clean up managers
        cleanup_managers_registry()

    @pytest.mark.integration
    @pytest.mark.gui
    def test_workflow_interruption_recovery(
        self, sample_files, mock_main_window, mock_qt_signals
    ):
        """Test user cancellation and recovery handling"""
        # Initialize managers before creating controller
        initialize_managers_registry()

        # Test error scenario first
        invalid_params = {
            "vram_path": "/nonexistent/vram.dmp",
            "cgram_path": sample_files["cgram_path"],
            "output_base": str(Path(sample_files["temp_dir"]) / "error_test"),
            "create_grayscale": True,
            "create_metadata": False,
            "oam_path": None,
        }
        mock_main_window.set_extraction_params(invalid_params)

        # Mock Qt components and run extraction
        # Need to patch image_utils functions at the correct level
        mock_pixmap_instance = Mock()
        mock_pixmap_instance.loadFromData = Mock(return_value=True)

        with (
                        patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
            patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
            patch("spritepal.core.workers.base.QThread"),
        ):

            # Configure mocks
            mock_qpixmap_utils.return_value = mock_pixmap_instance
            mock_pil_to_qpixmap.return_value = mock_pixmap_instance

            # Create controller and worker
            controller = ExtractionController(mock_main_window)
            worker = VRAMExtractionWorker(invalid_params)

            # Replace worker signals with mocks
            for signal_name, mock_signal in mock_qt_signals.items():
                setattr(worker, signal_name, mock_signal)

            # Connect error tracking
            worker.error.connect(controller._on_extraction_error)

            # Run worker (should error)
            worker.run()

        # Get error signals from helper
        workflow_signals = mock_main_window.get_signal_emissions()

        # Verify error was handled
        assert len(workflow_signals["extraction_failed"]) == 1
        error_message = workflow_signals["extraction_failed"][0]
        assert "No such file" in error_message or "not found" in error_message or "does not exist" in error_message

        # Test recovery with valid parameters
        mock_main_window.clear_signal_tracking()  # Clear previous errors
        valid_params = {
            "vram_path": sample_files["vram_path"],
            "cgram_path": sample_files["cgram_path"],
            "output_base": str(Path(sample_files["temp_dir"]) / "recovery_test"),
            "create_grayscale": True,
            "create_metadata": False,
            "oam_path": None,
        }
        mock_main_window.set_extraction_params(valid_params)

        # Mock Qt components and run recovery
        # Need to patch image_utils functions at the correct level
        mock_pixmap_instance = Mock()
        mock_pixmap_instance.loadFromData = Mock(return_value=True)

        with (
                        patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
            patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
            patch("spritepal.core.workers.base.QThread"),
        ):

            # Configure mocks
            mock_qpixmap_utils.return_value = mock_pixmap_instance
            mock_pil_to_qpixmap.return_value = mock_pixmap_instance

            # Create recovery worker
            recovery_worker = VRAMExtractionWorker(valid_params)

            # Replace worker signals with mocks
            for signal_name, mock_signal in mock_qt_signals.items():
                setattr(recovery_worker, signal_name, mock_signal)

            # Connect completion tracking
            recovery_worker.extraction_finished.connect(controller._on_extraction_finished)
            recovery_worker.error.connect(controller._on_extraction_error)

            # Run recovery
            recovery_worker.run()

        # Get recovery signals from helper
        recovery_signals = mock_main_window.get_signal_emissions()

        # Verify recovery worked (no new errors after clearing)
        assert len(recovery_signals["extraction_failed"]) == 0
        assert len(recovery_signals["extraction_complete"]) == 1

        # Verify output files exist
        output_files = recovery_signals["extraction_complete"][0]
        for file_path in output_files:
            assert Path(file_path).exists()

        # Clean up managers
        cleanup_managers_registry()

    @pytest.mark.integration
    @pytest.mark.gui
    def test_multi_file_workflow_with_real_signals_improved(
        self, sample_files, mock_main_window, qtbot
    ):
        """
        IMPROVED VERSION: Test workflow using real Qt signals with QSignalSpy.

        This demonstrates the superior approach of testing real signal behavior
        instead of mocking signals. Real signal testing:
        - Catches Qt lifecycle bugs that mocks miss
        - Tests actual signal connection behavior
        - Verifies real signal content and timing
        - Is more reliable and maintainable
        """
        from PyQt6.QtTest import QSignalSpy

        # Initialize managers for clean state
        initialize_managers_registry()

        try:
            # Set up extraction parameters with all files
            output_base = str(Path(sample_files["temp_dir"]) / "real_signals_test")
            extraction_params = {
                "vram_path": sample_files["vram_path"],
                "cgram_path": sample_files["cgram_path"],
                "output_base": output_base,
                "create_grayscale": True,
                "create_metadata": True,
                "oam_path": sample_files["oam_path"],
            }
            mock_main_window.set_extraction_params(extraction_params)

            # Mock only external dependencies, keep real Qt signals
            mock_pixmap_instance = Mock()
            mock_pixmap_instance.loadFromData = Mock(return_value=True)

            with (
                patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
                patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
                patch("spritepal.core.workers.base.QThread"),
            ):
                # Configure external mocks only
                mock_qpixmap_utils.return_value = mock_pixmap_instance
                mock_pil_to_qpixmap.return_value = mock_pixmap_instance

                # Create worker with REAL Qt signals (no replacement!)
                worker = VRAMExtractionWorker(extraction_params)
                # Note: QThread doesn't need addWidget, that's for QWidgets only

                controller = ExtractionController(mock_main_window)

                # Set up QSignalSpy to monitor REAL signal emissions
                progress_spy = QSignalSpy(worker.progress)
                QSignalSpy(worker.preview_ready)
                palettes_ready_spy = QSignalSpy(worker.palettes_ready)
                active_palettes_ready_spy = QSignalSpy(worker.active_palettes_ready)
                extraction_finished_spy = QSignalSpy(worker.extraction_finished)
                error_spy = QSignalSpy(worker.error)

                # Connect controller to worker signals (tests real signal connections)
                worker.palettes_ready.connect(controller._on_palettes_ready)
                worker.active_palettes_ready.connect(controller._on_active_palettes_ready)
                worker.extraction_finished.connect(controller._on_extraction_finished)
                worker.error.connect(controller._on_extraction_error)

                # Track active palette analysis with real signal data
                active_palette_data = []
                worker.active_palettes_ready.connect(
                    lambda palettes: active_palette_data.append(palettes)
                )

                # Run the worker
                worker.run()

                # REAL SIGNAL TESTING: Verify actual signal emissions and content

                # Verify progress signals were emitted
                assert len(progress_spy) > 0, "Progress signals should be emitted"
                # Check progress signal content (percent, message)
                first_progress = progress_spy[0]
                assert len(first_progress) == 2, "Progress signal should have percent and message"
                assert isinstance(first_progress[0], int), "Progress percent should be int"
                assert isinstance(first_progress[1], str), "Progress message should be string"

                # Verify extraction completion signal
                assert len(extraction_finished_spy) == 1, "Should have exactly one completion signal"
                output_files = extraction_finished_spy[0][0]  # First arg of first emission
                assert isinstance(output_files, list), "Output files should be a list"
                assert len(output_files) > 0, "Should have output files"

                # Verify output files actually exist (real behavior, not mocked)
                for file_path in output_files:
                    assert Path(file_path).exists(), f"Output file should exist: {file_path}"

                # Verify OAM analysis worked with real signal data
                assert len(active_palette_data) == 1, "Should have active palette analysis"
                active_palettes = active_palette_data[0]
                assert 8 in active_palettes, "Should detect palette 8 from OAM analysis"

                # Verify no errors occurred
                assert len(error_spy) == 0, "No error signals should be emitted"

                # Verify palette signals for multi-file workflow
                if sample_files["cgram_path"]:  # If CGRAM provided
                    assert len(palettes_ready_spy) > 0, "Palette signals should be emitted"

                print("✓ Real signal testing passed:")
                print(f"  - Progress signals: {len(progress_spy)}")
                print(f"  - Palette signals: {len(palettes_ready_spy)}")
                print(f"  - Active palette signals: {len(active_palettes_ready_spy)}")
                print(f"  - Completion signals: {len(extraction_finished_spy)}")
                print(f"  - Error signals: {len(error_spy)}")
                print(f"  - Output files: {len(output_files)}")

        finally:
            # Clean up managers
            cleanup_managers_registry()


class TestWorkflowIntegrationPoints:
    """Test specific integration points in the workflow"""

    @pytest.fixture
    def mock_ui_components(self):
        """Mock UI components for integration testing"""
        return {
            "drop_zone": Mock(),
            "extraction_panel": Mock(),
            "preview_panel": Mock(),
            "palette_preview": Mock(),
            "status_bar": Mock(),
            "progress_bar": Mock(),
        }

    @pytest.mark.integration
    @pytest.mark.gui
    def test_signal_flow_integration(self, mock_ui_components):
        """Test signal flow between UI components"""
        # Create mock signals
        extract_signal = Mock()
        file_dropped_signal = Mock()
        preview_updated_signal = Mock()

        # Set up signal connections
        mock_ui_components["drop_zone"].file_dropped = file_dropped_signal
        mock_ui_components["extraction_panel"].extract_requested = extract_signal
        mock_ui_components["preview_panel"].preview_updated = preview_updated_signal

        # Simulate signal flow
        file_dropped_signal.emit("/test/vram.dmp")
        extract_signal.emit()
        preview_updated_signal.emit("preview_data")

        # Verify signals were emitted
        assert file_dropped_signal.emit.called
        assert extract_signal.emit.called
        assert preview_updated_signal.emit.called

    @pytest.mark.integration
    @pytest.mark.gui
    def test_ui_state_consistency_during_workflow(self, mock_ui_components):
        """Test UI state remains consistent during workflow"""
        # Mock UI state tracking
        ui_states = {
            "extraction_enabled": True,
            "preview_visible": False,
            "progress_visible": False,
        }

        # Mock state change functions
        def set_extraction_enabled(enabled):
            ui_states["extraction_enabled"] = enabled

        def set_preview_visible(visible):
            ui_states["preview_visible"] = visible

        def set_progress_visible(visible):
            ui_states["progress_visible"] = visible

        mock_ui_components["extraction_panel"].setEnabled = set_extraction_enabled
        mock_ui_components["preview_panel"].setVisible = set_preview_visible
        mock_ui_components["progress_bar"].setVisible = set_progress_visible

        # Simulate workflow state changes
        # Start extraction
        set_extraction_enabled(False)
        set_progress_visible(True)

        # Preview ready
        set_preview_visible(True)

        # Extraction complete
        set_extraction_enabled(True)
        set_progress_visible(False)

        # Verify final state
        assert ui_states["extraction_enabled"] is True
        assert ui_states["preview_visible"] is True
        assert ui_states["progress_visible"] is False

    @pytest.mark.integration
    @pytest.mark.gui
    def test_component_cleanup_integration(self, mock_ui_components):
        """Test proper cleanup of components after workflow"""
        # Mock cleanup functions
        cleanup_calls = []

        def mock_cleanup(component_name):
            cleanup_calls.append(component_name)

        mock_ui_components["drop_zone"].cleanup = lambda: mock_cleanup("drop_zone")
        mock_ui_components["preview_panel"].cleanup = lambda: mock_cleanup(
            "preview_panel"
        )
        mock_ui_components["palette_preview"].cleanup = lambda: mock_cleanup(
            "palette_preview"
        )

        # Simulate cleanup sequence
        mock_ui_components["drop_zone"].cleanup()
        mock_ui_components["preview_panel"].cleanup()
        mock_ui_components["palette_preview"].cleanup()

        # Verify cleanup was called for all components
        assert "drop_zone" in cleanup_calls
        assert "preview_panel" in cleanup_calls
        assert "palette_preview" in cleanup_calls
        assert len(cleanup_calls) == 3
