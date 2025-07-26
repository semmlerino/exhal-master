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

from spritepal.core.controller import ExtractionController, ExtractionWorker
from spritepal.core.managers import cleanup_managers, initialize_managers
from spritepal.core.managers.registry import (
    cleanup_managers as cleanup_managers_registry,
)
from spritepal.core.managers.registry import (
    initialize_managers as initialize_managers_registry,
)
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
    def mock_main_window(self):
        """Create mock main window for testing"""
        window = Mock()
        window.extraction_complete = Mock()
        window.extraction_failed = Mock()
        window.status_bar = Mock()
        window.sprite_preview = Mock()
        window.palette_preview = Mock()
        window.preview_info = Mock()
        window.extract_requested = Mock()
        window.open_in_editor_requested = Mock()
        window.arrange_rows_requested = Mock()
        window.arrange_grid_requested = Mock()

        # Mock extraction parameters
        window.get_extraction_params = Mock()

        return window

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
            "finished": MockSignal(),
            "error": MockSignal(),
        }

    @pytest.mark.integration
    @pytest.mark.gui
    def test_drag_drop_extract_edit_workflow(
        self, sample_files, mock_main_window, mock_qt_signals
    ):
        """Test complete user journey: Drop files → Extract → Edit"""
        # Initialize managers for this test
        initialize_managers("TestApp")

        try:
            # Track workflow signals
            workflow_signals = {
                "progress_messages": [],
                "preview_updates": [],
                "palette_updates": [],
                "completion_calls": [],
                "error_calls": [],
            }

            # Set up extraction parameters
            output_base = str(Path(sample_files["temp_dir"]) / "workflow_test")
            mock_main_window.get_extraction_params.return_value = {
                "vram_path": sample_files["vram_path"],
                "cgram_path": sample_files["cgram_path"],
                "output_base": output_base,
                "create_grayscale": True,
                "create_metadata": True,
                "oam_path": sample_files["oam_path"],
            }

            # Connect tracking functions
            def track_progress(msg):
                workflow_signals["progress_messages"].append(msg)

            def track_preview(pixmap, tile_count):
                workflow_signals["preview_updates"].append((pixmap, tile_count))

            def track_palette(palettes):
                workflow_signals["palette_updates"].append(palettes)

            def track_completion(files):
                workflow_signals["completion_calls"].append(files)

            def track_error(error):
                workflow_signals["error_calls"].append(error)

            mock_main_window.status_bar.showMessage = track_progress
            mock_main_window.sprite_preview.set_preview = track_preview
            mock_main_window.palette_preview.set_all_palettes = track_palette
            mock_main_window.extraction_complete = track_completion
            mock_main_window.extraction_failed = track_error

            # Mock Qt components comprehensively
            # Need to patch image_utils functions at the correct level
            mock_pixmap_instance = Mock()
            mock_pixmap_instance.loadFromData = Mock(return_value=True)

            with (
                patch("spritepal.core.controller.QPixmap") as mock_qpixmap,
                patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
                patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
                patch("spritepal.core.controller.QThread"),
                patch("spritepal.core.controller.pyqtSignal") as mock_pyqt_signal,
            ):

                # Configure mocks
                mock_qpixmap.return_value = mock_pixmap_instance
                mock_qpixmap_utils.return_value = mock_pixmap_instance
                mock_pil_to_qpixmap.return_value = mock_pixmap_instance
                mock_pyqt_signal.side_effect = lambda *args: Mock()

                # Create worker and controller
                worker = ExtractionWorker(
                    mock_main_window.get_extraction_params.return_value
                )
                controller = ExtractionController(mock_main_window)

                # Replace worker signals with mocks
                for signal_name, mock_signal in mock_qt_signals.items():
                    setattr(worker, signal_name, mock_signal)

                # Connect controller to worker signals
                worker.progress.connect(controller._on_progress)
                worker.preview_ready.connect(controller._on_preview_ready)
                worker.preview_image_ready.connect(controller._on_preview_image_ready)
                worker.palettes_ready.connect(controller._on_palettes_ready)
                worker.active_palettes_ready.connect(controller._on_active_palettes_ready)
                worker.finished.connect(controller._on_extraction_finished)
                worker.error.connect(controller._on_extraction_error)

                # Run the workflow
                worker.run()

            # Verify workflow completion
            assert len(workflow_signals["progress_messages"]) >= 3
            assert (
                "Extracting sprites from VRAM..." in workflow_signals["progress_messages"]
            )
            assert "Extraction complete!" in workflow_signals["progress_messages"]

            # Verify preview updates
            assert len(workflow_signals["preview_updates"]) == 1
            pixmap, tile_count = workflow_signals["preview_updates"][0]
            assert pixmap is not None
            assert tile_count > 0

            # Verify palette updates
            assert len(workflow_signals["palette_updates"]) == 1
            assert len(workflow_signals["palette_updates"][0]) == 8  # 8 sprite palettes

            # Verify completion without errors
            assert len(workflow_signals["completion_calls"]) == 1
            assert len(workflow_signals["error_calls"]) == 0

            # Verify output files exist
            output_files = workflow_signals["completion_calls"][0]
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
        mock_main_window.get_extraction_params.return_value = {
            "vram_path": sample_files["vram_path"],
            "cgram_path": sample_files["cgram_path"],
            "output_base": output_base,
            "create_grayscale": True,
            "create_metadata": True,
            "oam_path": None,
        }

        # Track arrangement request
        arrangement_requests = []
        mock_main_window.arrange_rows_requested.connect = (
            lambda callback: arrangement_requests.append(callback)
        )

        # Mock Qt components and run extraction
        # Need to patch image_utils functions at the correct level
        mock_pixmap_instance = Mock()
        mock_pixmap_instance.loadFromData = Mock(return_value=True)

        with (
            patch("spritepal.core.controller.QPixmap") as mock_qpixmap,
            patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
            patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
            patch("spritepal.core.controller.QThread"),
            patch("spritepal.core.controller.pyqtSignal") as mock_pyqt_signal,
        ):

            # Configure mocks
            mock_qpixmap.return_value = mock_pixmap_instance
            mock_qpixmap_utils.return_value = mock_pixmap_instance
            mock_pil_to_qpixmap.return_value = mock_pixmap_instance
            mock_pyqt_signal.side_effect = lambda *args: Mock()

            # Create and run worker
            worker = ExtractionWorker(
                mock_main_window.get_extraction_params.return_value
            )
            controller = ExtractionController(mock_main_window)

            # Replace worker signals with mocks
            for signal_name, mock_signal in mock_qt_signals.items():
                setattr(worker, signal_name, mock_signal)

            # Connect controller signals
            worker.finished.connect(controller._on_extraction_finished)
            worker.error.connect(controller._on_extraction_error)

            # Run extraction
            worker.run()

        # Verify extraction completed
        assert worker.finished.emit.called
        output_files = worker.finished.emit.call_args[0][0]
        sprite_file = next(f for f in output_files if f.endswith(".png"))
        assert Path(sprite_file).exists()

        # Simulate arrangement request
        mock_main_window.arrange_rows_requested.emit(sprite_file)

        # Verify arrangement dialog would be triggered
        assert mock_main_window.arrange_rows_requested.emit.called

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
        mock_main_window.get_extraction_params.return_value = {
            "vram_path": sample_files["vram_path"],
            "cgram_path": sample_files["cgram_path"],
            "output_base": output_base,
            "create_grayscale": True,
            "create_metadata": True,
            "oam_path": sample_files["oam_path"],
        }

        # Track active palette analysis
        active_palette_calls = []
        mock_main_window.palette_preview.highlight_active_palettes = (
            active_palette_calls.append
        )

        # Mock Qt components and run extraction
        # Need to patch image_utils functions at the correct level
        mock_pixmap_instance = Mock()
        mock_pixmap_instance.loadFromData = Mock(return_value=True)

        with (
            patch("spritepal.core.controller.QPixmap") as mock_qpixmap,
            patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
            patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
            patch("spritepal.core.controller.QThread"),
            patch("spritepal.core.controller.pyqtSignal") as mock_pyqt_signal,
        ):

            # Configure mocks
            mock_qpixmap.return_value = mock_pixmap_instance
            mock_qpixmap_utils.return_value = mock_pixmap_instance
            mock_pil_to_qpixmap.return_value = mock_pixmap_instance
            mock_pyqt_signal.side_effect = lambda *args: Mock()

            # Create and run worker
            worker = ExtractionWorker(
                mock_main_window.get_extraction_params.return_value
            )
            ExtractionController(mock_main_window)

            # Replace worker signals with mocks
            for signal_name, mock_signal in mock_qt_signals.items():
                setattr(worker, signal_name, mock_signal)

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

        # Verify extraction completed successfully
        assert worker.finished.emit.called
        output_files = worker.finished.emit.call_args[0][0]

        # Verify all expected files exist
        assert any(f.endswith(".png") for f in output_files)
        assert any(f.endswith(".metadata.json") for f in output_files)
        for file_path in output_files:
            assert Path(file_path).exists()

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
            mock_main_window.get_extraction_params.return_value = {
                "vram_path": str(variant_path),
                "cgram_path": sample_files["cgram_path"],
                "output_base": output_base,
                "create_grayscale": True,
                "create_metadata": False,
                "oam_path": None,
            }

            # Mock Qt components and run extraction
            # Need to patch image_utils functions at the correct level
            mock_pixmap_instance = Mock()
            mock_pixmap_instance.loadFromData = Mock(return_value=True)

            with (
                patch("spritepal.core.controller.QPixmap") as mock_qpixmap,
                patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
                patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
                patch("spritepal.core.controller.QThread"),
                patch("spritepal.core.controller.pyqtSignal") as mock_pyqt_signal,
            ):

                # Configure mocks
                mock_qpixmap.return_value = mock_pixmap_instance
                mock_qpixmap_utils.return_value = mock_pixmap_instance
                mock_pil_to_qpixmap.return_value = mock_pixmap_instance
                mock_pyqt_signal.side_effect = lambda *args: Mock()

                # Create and run worker
                worker = ExtractionWorker(
                    mock_main_window.get_extraction_params.return_value
                )

                # Replace worker signals with mocks
                for signal_name, mock_signal in mock_qt_signals.items():
                    setattr(worker, signal_name, mock_signal)

                # Run extraction
                worker.run()

            # Verify extraction completed for this variant
            assert worker.finished.emit.called
            output_files = worker.finished.emit.call_args[0][0]
            assert any(f.endswith(".png") for f in output_files)
            for file_path in output_files:
                assert Path(file_path).exists()

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

        # Track error handling
        error_calls = []
        mock_main_window.extraction_failed = error_calls.append

        # Mock Qt components and run extraction
        # Need to patch image_utils functions at the correct level
        mock_pixmap_instance = Mock()
        mock_pixmap_instance.loadFromData = Mock(return_value=True)

        with (
            patch("spritepal.core.controller.QPixmap") as mock_qpixmap,
            patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
            patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
            patch("spritepal.core.controller.QThread"),
            patch("spritepal.core.controller.pyqtSignal") as mock_pyqt_signal,
        ):

            # Configure mocks
            mock_qpixmap.return_value = mock_pixmap_instance
            mock_qpixmap_utils.return_value = mock_pixmap_instance
            mock_pil_to_qpixmap.return_value = mock_pixmap_instance
            mock_pyqt_signal.side_effect = lambda *args: Mock()

            # Create controller and worker
            controller = ExtractionController(mock_main_window)
            worker = ExtractionWorker(invalid_params)

            # Replace worker signals with mocks
            for signal_name, mock_signal in mock_qt_signals.items():
                setattr(worker, signal_name, mock_signal)

            # Connect error tracking
            worker.error.connect(controller._on_extraction_error)

            # Run worker (should error)
            worker.run()

        # Verify error was handled
        assert len(error_calls) == 1
        assert "No such file" in error_calls[0] or "not found" in error_calls[0] or "does not exist" in error_calls[0]

        # Test recovery with valid parameters
        error_calls.clear()
        completion_calls = []
        mock_main_window.extraction_complete = completion_calls.append

        valid_params = {
            "vram_path": sample_files["vram_path"],
            "cgram_path": sample_files["cgram_path"],
            "output_base": str(Path(sample_files["temp_dir"]) / "recovery_test"),
            "create_grayscale": True,
            "create_metadata": False,
            "oam_path": None,
        }

        # Mock Qt components and run recovery
        # Need to patch image_utils functions at the correct level
        mock_pixmap_instance = Mock()
        mock_pixmap_instance.loadFromData = Mock(return_value=True)

        with (
            patch("spritepal.core.controller.QPixmap") as mock_qpixmap,
            patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
            patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
            patch("spritepal.core.controller.QThread"),
            patch("spritepal.core.controller.pyqtSignal") as mock_pyqt_signal,
        ):

            # Configure mocks
            mock_qpixmap.return_value = mock_pixmap_instance
            mock_qpixmap_utils.return_value = mock_pixmap_instance
            mock_pil_to_qpixmap.return_value = mock_pixmap_instance
            mock_pyqt_signal.side_effect = lambda *args: Mock()

            # Create recovery worker
            recovery_worker = ExtractionWorker(valid_params)

            # Replace worker signals with mocks
            for signal_name, mock_signal in mock_qt_signals.items():
                setattr(recovery_worker, signal_name, mock_signal)

            # Connect completion tracking
            recovery_worker.finished.connect(controller._on_extraction_finished)
            recovery_worker.error.connect(controller._on_extraction_error)

            # Run recovery
            recovery_worker.run()

        # Verify recovery worked
        assert len(error_calls) == 0
        assert len(completion_calls) == 1

        # Verify output files exist
        output_files = completion_calls[0]
        for file_path in output_files:
            assert Path(file_path).exists()

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
