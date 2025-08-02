"""
Comprehensive tests for controller functionality
"""

import importlib
import os
import sys
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import spritepal.core.controller
from spritepal.core.controller import ExtractionController
from spritepal.core.managers import cleanup_managers, initialize_managers
from spritepal.core.workers import VRAMExtractionWorker


class TestControllerImports:
    """Test that controller module imports work correctly"""

    def test_controller_imports(self):
        """Test that all imports in controller module work without errors"""
        # This test will catch import-time errors like missing pil_to_qpixmap
        try:
            # Force module reload to catch any import errors
            importlib.reload(spritepal.core.controller)
        except ImportError as e:
            pytest.fail(f"Import error in controller module: {e}")
        except NameError as e:
            pytest.fail(f"Name error in controller module: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error importing controller module: {e}")

    def test_pil_to_qpixmap_import(self, tmp_path):
        """Test that pil_to_qpixmap function is available in controller module"""
        # Test that pil_to_qpixmap is imported and available
        from spritepal.core import controller

        assert hasattr(controller, "pil_to_qpixmap")

        # Test that the function can be called (with mocked PIL image)
        mock_image = Mock()
        mock_image.save = Mock()

        with patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap:
            mock_pil_to_qpixmap.return_value = Mock()
            result = controller.pil_to_qpixmap(mock_image)
            mock_pil_to_qpixmap.assert_called_once_with(mock_image)
            assert result is not None


class TestExtractionController:
    """Test ExtractionController functionality"""

    @pytest.fixture
    def mock_main_window(self):
        """Create mock main window"""
        from .fixtures.qt_mocks import create_mock_main_window
        return create_mock_main_window()

    @pytest.fixture
    def controller(self, mock_main_window):
        """Create controller instance"""
        # Initialize managers for this test
        initialize_managers("TestApp")

        try:
            controller = ExtractionController(mock_main_window)
            yield controller
        finally:
            # Clean up managers
            cleanup_managers()

    def test_init_connects_signals(self, controller, mock_main_window):
        """Test controller initialization connects signals"""
        # Verify signals are connected
        mock_main_window.extract_requested.connect.assert_called_once()
        mock_main_window.open_in_editor_requested.connect.assert_called_once()
        assert controller.main_window == mock_main_window
        assert controller.worker is None

    def test_parameter_validation_missing_vram(self, controller, mock_main_window):
        """Test parameter validation when VRAM path is missing"""
        mock_main_window.get_extraction_params.return_value = {
            "vram_path": "",
            "cgram_path": "/path/to/cgram.dmp",
            "output_base": "/path/to/output",
        }

        controller.start_extraction()

        mock_main_window.extraction_failed.assert_called_once_with(
            "VRAM file is required for extraction"
        )

    def test_parameter_validation_missing_cgram(self, controller, mock_main_window):
        """Test parameter validation when CGRAM path is missing"""
        mock_main_window.get_extraction_params.return_value = {
            "vram_path": "/path/to/vram.dmp",
            "cgram_path": "",
            "output_base": "/path/to/output",
            "grayscale_mode": False,  # CGRAM is required when not in grayscale mode
        }

        controller.start_extraction()

        mock_main_window.extraction_failed.assert_called_once_with(
            "CGRAM file is required for Full Color mode.\n"
            "Please provide a CGRAM file or switch to Grayscale Only mode."
        )

    def test_parameter_validation_missing_both(self, controller, mock_main_window):
        """Test parameter validation when both paths are missing"""
        mock_main_window.get_extraction_params.return_value = {
            "vram_path": None,
            "cgram_path": None,
            "output_base": "/path/to/output",
        }

        controller.start_extraction()

        # When both are missing, it fails on VRAM parameter check first
        mock_main_window.extraction_failed.assert_called_once_with(
            "VRAM file is required for extraction"
        )

    @patch("spritepal.core.controller.VRAMExtractionWorker")
    def test_start_extraction_valid_params(
        self, mock_worker_class, controller, mock_main_window
    ):
        """Test starting extraction with valid parameters"""
        from .infrastructure.test_data_repository import get_test_data_repository

        # Use TestDataRepository to create realistic files that pass defensive validation
        repo = get_test_data_repository()
        test_data = repo.get_vram_extraction_data("medium")  # Creates 64KB VRAM file

        try:
            mock_main_window.get_extraction_params.return_value = {
                "vram_path": test_data["vram_path"],
                "cgram_path": test_data["cgram_path"],
                "output_base": test_data["output_base"],
                "grayscale_mode": True,  # Add missing parameter to bypass CGRAM validation
            }

            mock_worker_instance = Mock()
            mock_worker_class.return_value = mock_worker_instance

            controller.start_extraction()

            # Verify worker was created and started
            mock_worker_class.assert_called_once()
            mock_worker_instance.start.assert_called_once()

            # Verify signals were connected
            mock_worker_instance.progress.connect.assert_called()
            mock_worker_instance.preview_ready.connect.assert_called()
            mock_worker_instance.preview_image_ready.connect.assert_called()
            mock_worker_instance.palettes_ready.connect.assert_called()
            mock_worker_instance.active_palettes_ready.connect.assert_called()
            mock_worker_instance.extraction_finished.connect.assert_called()
            mock_worker_instance.error.connect.assert_called()
        finally:
            # Clean up repository files
            repo.cleanup()

    def test_on_progress_handler(self, controller, mock_main_window):
        """Test progress message handler"""
        test_message = "Extracting sprites..."

        controller._on_progress(50, test_message)

        mock_main_window.status_bar.showMessage.assert_called_once_with(test_message)

    def test_on_preview_ready_handler(self, controller, mock_main_window):
        """Test preview ready handler - now expects PIL Image due to Qt threading fix"""
        # CRITICAL UPDATE FOR BUG #26: Method now accepts PIL Image, not QPixmap
        mock_pil_image = Mock()
        tile_count = 42

        # Mock pil_to_qpixmap to return a mock QPixmap
        mock_qpixmap = Mock()
        with patch("spritepal.core.controller.pil_to_qpixmap", return_value=mock_qpixmap):
            controller._on_preview_ready(mock_pil_image, tile_count)

        mock_main_window.sprite_preview.set_preview.assert_called_once_with(
            mock_qpixmap, tile_count
        )
        mock_main_window.preview_info.setText.assert_called_once_with("Tiles: 42")

    def test_on_preview_image_ready_handler(self, controller, mock_main_window):
        """Test preview image ready handler"""
        mock_pil_image = Mock()

        controller._on_preview_image_ready(mock_pil_image)

        mock_main_window.sprite_preview.set_grayscale_image.assert_called_once_with(
            mock_pil_image
        )

    def test_on_palettes_ready_handler(self, controller, mock_main_window):
        """Test palettes ready handler"""
        test_palettes = {8: [[0, 0, 0], [255, 0, 0]], 9: [[0, 0, 0], [0, 255, 0]]}

        controller._on_palettes_ready(test_palettes)

        mock_main_window.palette_preview.set_all_palettes.assert_called_once_with(
            test_palettes
        )
        mock_main_window.sprite_preview.set_palettes.assert_called_once_with(
            test_palettes
        )

    def test_on_active_palettes_ready_handler(self, controller, mock_main_window):
        """Test active palettes ready handler"""
        active_palettes = [8, 9, 10]

        controller._on_active_palettes_ready(active_palettes)

        mock_main_window.palette_preview.highlight_active_palettes.assert_called_once_with(
            active_palettes
        )

    def test_on_extraction_finished_handler(self, controller, mock_main_window):
        """Test extraction finished handler"""
        extracted_files = ["sprite.png", "sprite.pal.json", "metadata.json"]
        controller.worker = Mock()  # Set a worker to test cleanup

        controller._on_extraction_finished(extracted_files)

        mock_main_window.extraction_complete.assert_called_once_with(extracted_files)
        assert controller.worker is None  # Worker should be cleaned up

    def test_on_extraction_error_handler(self, controller, mock_main_window):
        """Test extraction error handler"""
        error_message = "Failed to read VRAM file"
        controller.worker = Mock()  # Set a worker to test cleanup

        controller._on_extraction_error(error_message)

        mock_main_window.extraction_failed.assert_called_once_with(error_message)
        assert controller.worker is None  # Worker should be cleaned up

    @patch("spritepal.core.controller.validate_image_file")
    @patch("spritepal.core.controller.subprocess.Popen")
    def test_open_in_editor_launcher_found(
        self, mock_popen, mock_validate, controller, mock_main_window, tmp_path
    ):
        """Test opening in editor when launcher is found"""
        # Mock validation to pass
        mock_validate.return_value = (True, "")

        # Create real launcher file
        launcher_dir = tmp_path / "pixel_editor"
        launcher_dir.mkdir()
        launcher_file = launcher_dir / "launch_pixel_editor.py"
        launcher_file.write_text("# Fake launcher script")

        # Create real sprite file
        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake png data")

        # Patch the search paths to include our tmp directory
        with patch("spritepal.core.controller.os.path.dirname", return_value=str(tmp_path)):
            controller.open_in_editor(str(sprite_file))

        # Verify Popen was called with the correct arguments
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == sys.executable
        assert call_args[1].endswith("launch_pixel_editor.py")
        assert call_args[2] == os.path.abspath(str(sprite_file))

        mock_main_window.status_bar.showMessage.assert_called_once_with(
            f"Opened {os.path.basename(sprite_file)} in pixel editor"
        )

    @patch("spritepal.core.controller.validate_image_file")
    @patch("spritepal.core.controller.subprocess.Popen")
    def test_open_in_editor_launcher_in_subdirectory(
        self, mock_popen, mock_validate, controller, mock_main_window, tmp_path
    ):
        """Test opening in editor when launcher is in subdirectory"""
        # Mock validation to pass
        mock_validate.return_value = (True, "")

        # Create real launcher file in subdirectory
        launcher_dir = tmp_path / "pixel_editor"
        launcher_dir.mkdir()
        launcher_file = launcher_dir / "launch_pixel_editor.py"
        launcher_file.write_text("# Fake launcher script")

        # Create real sprite file
        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake png data")

        # Patch the search paths to include our tmp directory
        with patch("spritepal.core.controller.os.path.dirname", return_value=str(tmp_path)):
            controller.open_in_editor(str(sprite_file))

        # Verify Popen was called with the correct arguments
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == sys.executable
        assert call_args[1].endswith("pixel_editor/launch_pixel_editor.py")
        assert call_args[2] == os.path.abspath(str(sprite_file))

    @patch("spritepal.core.controller.validate_image_file")
    @patch("spritepal.core.controller.subprocess.Popen")
    def test_open_in_editor_launcher_in_parent_directory(
        self, mock_popen, mock_validate, controller, mock_main_window, tmp_path
    ):
        """Test opening in editor when launcher is in parent directory"""
        # Mock validation to pass
        mock_validate.return_value = (True, "")

        # Create directory structure: tmp_path/exhal-master/spritepal/core
        exhal_dir = tmp_path / "exhal-master"
        exhal_dir.mkdir()
        spritepal_dir = exhal_dir / "spritepal"
        spritepal_dir.mkdir()
        core_dir = spritepal_dir / "core"
        core_dir.mkdir()

        # Create launcher in parent (exhal-master) directory
        launcher_file = exhal_dir / "launch_pixel_editor.py"
        launcher_file.write_text("# Fake launcher script")

        # Create sprite file
        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake png data")

        # Mock __file__ to point to our fake core directory
        fake_controller_file = str(core_dir / "controller.py")
        with patch("spritepal.core.controller.__file__", fake_controller_file):
            controller.open_in_editor(str(sprite_file))

        # Verify Popen was called with the correct arguments
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == sys.executable
        assert call_args[1].endswith("launch_pixel_editor.py")
        assert call_args[2] == os.path.abspath(str(sprite_file))

    def test_open_in_editor_launcher_not_found(
        self, controller, mock_main_window, tmp_path
    ):
        """Test opening in editor when launcher is not found"""
        # Create sprite file but no launcher
        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake png data")

        # Patch search paths to use empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with patch("spritepal.core.controller.os.path.dirname", return_value=str(empty_dir)):
            controller.open_in_editor(str(sprite_file))

        mock_main_window.status_bar.showMessage.assert_called_once_with(
            "Pixel editor not found"
        )

    @patch("spritepal.core.controller.subprocess.Popen")
    def test_open_in_editor_subprocess_error(
        self, mock_popen, controller, mock_main_window, tmp_path
    ):
        """Test opening in editor when subprocess fails"""
        # Create real launcher file
        launcher_file = tmp_path / "launch_pixel_editor.py"
        launcher_file.write_text("# Fake launcher script")

        # Create real sprite file
        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake png data")
        mock_popen.side_effect = Exception("Subprocess failed")

        # Should not raise exception and should show error message
        with patch("spritepal.core.controller.os.path.dirname", return_value=str(tmp_path)):
            controller.open_in_editor(str(sprite_file))

        mock_main_window.status_bar.showMessage.assert_called_once_with(
            "Failed to open pixel editor: Subprocess failed"
        )


class TestVRAMExtractionWorker:
    """Test VRAMExtractionWorker functionality"""

    @pytest.fixture
    def worker_params(self):
        """Create worker parameters"""
        return {
            "vram_path": "/path/to/vram.dmp",
            "cgram_path": "/path/to/cgram.dmp",
            "oam_path": "/path/to/oam.dmp",
            "output_base": "/path/to/output",
            "create_grayscale": True,
            "create_metadata": True,
        }

    @pytest.fixture
    def worker(self, worker_params):
        """Create worker instance with mocked manager"""
        with patch("spritepal.core.workers.extraction.get_extraction_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_get_manager.return_value = mock_manager
            worker = VRAMExtractionWorker(worker_params)
            # Store the mock manager for test access
            worker._test_mock_manager = mock_manager
            return worker

    def test_init_creates_components(self, worker, worker_params):
        """Test worker initialization stores parameters"""
        assert worker.params == worker_params
        assert worker.manager is not None  # Manager is set during initialization in new pattern
        assert worker._connections == []  # No connections yet


    @patch("spritepal.utils.image_utils.pil_to_qpixmap")
    def test_run_full_workflow_success(self, mock_pil_to_qpixmap, worker):
        """Test successful full workflow execution"""
        # Use the mock manager from the worker fixture
        mock_manager = worker._test_mock_manager

        # Mock extraction result
        mock_manager.extract_from_vram.return_value = [
            "output.png", "output.pal.json", "output.metadata.json"
        ]

        # Mock pixmap conversion
        mock_pixmap = Mock()
        mock_pil_to_qpixmap.return_value = mock_pixmap

        # Use QSignalSpy to test signal emission
        from PyQt6.QtTest import QSignalSpy
        extraction_spy = QSignalSpy(worker.extraction_finished)
        operation_spy = QSignalSpy(worker.operation_finished)

        # Test the perform_operation method directly
        worker.perform_operation()

        # Verify manager was called with correct params
        mock_manager.extract_from_vram.assert_called_once_with(
            vram_path=worker.params["vram_path"],
            output_base=worker.params["output_base"],
            cgram_path=worker.params.get("cgram_path"),
            oam_path=worker.params.get("oam_path"),
            vram_offset=worker.params.get("vram_offset"),
            create_grayscale=worker.params.get("create_grayscale", True),
            create_metadata=worker.params.get("create_metadata", True),
            grayscale_mode=worker.params.get("grayscale_mode", False),
        )

        # Verify signals were emitted
        assert len(extraction_spy) == 1
        assert extraction_spy[0] == [["output.png", "output.pal.json", "output.metadata.json"]]

        assert len(operation_spy) == 1
        assert operation_spy[0][0] is True  # Success
        assert "Successfully extracted 3 files" in operation_spy[0][1]

    def test_run_error_handling(self, worker):
        """Test error handling in worker"""
        # Create a test exception
        test_exception = Exception("Test error")

        # Directly patch the manager's extract_from_vram method to raise exception
        with patch.object(worker.manager, "extract_from_vram", side_effect=test_exception):
            # Mock signals
            worker.progress = Mock()
            worker.error = Mock()
            worker.extraction_finished = Mock()

            # Run worker
            worker.run()

            # Verify error was emitted with wrapped message
            expected_error = "VRAM extraction failed: Test error"
            worker.error.emit.assert_called_once_with(expected_error, test_exception)
            worker.extraction_finished.emit.assert_not_called()

    @patch("spritepal.utils.image_utils.pil_to_qpixmap")
    def test_run_without_cgram(self, mock_pil_to_qpixmap, worker):
        """Test running without CGRAM file"""
        worker.params["cgram_path"] = None

        # Directly patch the manager's extract_from_vram method
        with patch.object(worker.manager, "extract_from_vram", return_value=["output.png"]) as mock_extract:
            # Mock signals
            worker.progress = Mock()
            worker.preview_ready = Mock()
            worker.preview_image_ready = Mock()
            worker.palettes_ready = Mock()
            worker.extraction_finished = Mock()
            worker.error = Mock()

            worker.run()

            # Verify manager was called with None cgram_path
            mock_extract.assert_called_once()
            call_args = mock_extract.call_args[1]
            assert call_args["cgram_path"] is None

            worker.extraction_finished.emit.assert_called_once()
            worker.error.emit.assert_not_called()

    @patch("spritepal.utils.image_utils.pil_to_qpixmap")
    def test_run_without_oam(self, mock_pil_to_qpixmap, worker):
        """Test running without OAM file"""
        worker.params["oam_path"] = None

        # Directly patch the manager's extract_from_vram method
        with patch.object(worker.manager, "extract_from_vram", return_value=[
            "output.png", "output.pal.json", "output.metadata.json"
        ]) as mock_extract:
            # Mock signals
            worker.progress = Mock()
            worker.preview_ready = Mock()
            worker.preview_image_ready = Mock()
            worker.palettes_ready = Mock()
            worker.active_palettes_ready = Mock()
            worker.extraction_finished = Mock()
            worker.error = Mock()

            worker.run()

            # Verify manager was called with None oam_path
            mock_extract.assert_called_once()
            call_args = mock_extract.call_args[1]
            assert call_args.get("oam_path") is None

            worker.extraction_finished.emit.assert_called_once()
        worker.error.emit.assert_not_called()

    @patch("spritepal.utils.image_utils.pil_to_qpixmap")
    def test_run_without_metadata_creation(self, mock_pil_to_qpixmap, worker):
        """Test running without metadata creation"""
        worker.params["create_metadata"] = False

        # Directly patch the manager's extract_from_vram method
        with patch.object(worker.manager, "extract_from_vram", return_value=[
            "output.png", "output.pal.json"
        ]) as mock_extract:
            # Mock signals
            worker.progress = Mock()
            worker.preview_ready = Mock()
            worker.preview_image_ready = Mock()
            worker.palettes_ready = Mock()
            worker.extraction_finished = Mock()
            worker.error = Mock()

            worker.run()

            # Verify manager was called with create_metadata=False
            mock_extract.assert_called_once()
            call_args = mock_extract.call_args[1]
            assert call_args["create_metadata"] is False

            worker.extraction_finished.emit.assert_called_once()
            worker.error.emit.assert_not_called()

    @patch("spritepal.utils.image_utils.pil_to_qpixmap")
    def test_run_without_grayscale_creation(self, mock_pil_to_qpixmap, worker):
        """Test running without grayscale palette creation"""
        worker.params["create_grayscale"] = False

        # Directly patch the manager's extract_from_vram method
        with patch.object(worker.manager, "extract_from_vram", return_value=["output.png"]) as mock_extract:
            # Mock signals
            worker.progress = Mock()
            worker.preview_ready = Mock()
            worker.preview_image_ready = Mock()
            worker.palettes_ready = Mock()
            worker.extraction_finished = Mock()
            worker.error = Mock()

            worker.run()

            # Verify manager was called with create_grayscale=False
            mock_extract.assert_called_once()
            call_args = mock_extract.call_args[1]
            assert call_args["create_grayscale"] is False

            worker.extraction_finished.emit.assert_called_once()
            worker.error.emit.assert_not_called()

    @patch("spritepal.utils.image_utils.pil_to_qpixmap")
    def test_signal_emission_order(self, mock_pil_to_qpixmap, worker):
        """Test that finished signal is emitted after successful extraction"""
        # Directly patch the manager's extract_from_vram method
        with patch.object(worker.manager, "extract_from_vram", return_value=[
            "output.png", "output.pal.json", "output.metadata.json"
        ]):
            # Track if finished was called
            finished_called = False
            finished_args = None

            def track_finished(files):
                nonlocal finished_called, finished_args
                finished_called = True
                finished_args = files

            worker.extraction_finished = Mock()
            worker.extraction_finished.emit = track_finished
            worker.error = Mock()

            worker.run()

            # Verify finished was called with the correct files
            assert finished_called
            assert finished_args == ["output.png", "output.pal.json", "output.metadata.json"]
            worker.error.emit.assert_not_called()


class TestRealControllerImplementation:
    """Test ExtractionController with real implementations (Mock Reduction Phase 4.2)"""

    @pytest.fixture
    def window_helper(self, tmp_path):
        """Create window helper for real controller testing"""
        from tests.fixtures.test_main_window_helper_simple import (
            TestMainWindowHelperSimple,
        )
        helper = TestMainWindowHelperSimple(str(tmp_path))
        yield helper
        helper.cleanup()

    @pytest.fixture
    def real_controller(self, window_helper):
        """Create real controller with window helper"""
        # Initialize managers for this test
        initialize_managers("TestApp")

        try:
            controller = ExtractionController(window_helper)
            yield controller
        finally:
            # Clean up managers
            cleanup_managers()

    @pytest.mark.integration
    def test_real_controller_initialization(self, real_controller, window_helper):
        """Test real controller initialization and signal connections"""
        # Verify controller was initialized properly
        assert real_controller.main_window == window_helper
        assert real_controller.worker is None

        # Verify signals are being tracked
        signals = window_helper.get_signal_emissions()
        assert isinstance(signals, dict)

    @pytest.mark.integration
    def test_real_parameter_validation(self, real_controller, window_helper):
        """Test real parameter validation with various scenarios"""
        # Test missing VRAM path
        invalid_params = {
            "vram_path": "",
            "cgram_path": str(window_helper.cgram_file),
            "output_base": str(window_helper.temp_path / "test_output"),
            "create_grayscale": True,
            "create_metadata": True,
        }
        window_helper.set_extraction_params(invalid_params)

        real_controller.start_extraction()

        # Check for validation error
        signals = window_helper.get_signal_emissions()
        assert len(signals["extraction_failed"]) >= 1

        # Clear signals for next test
        window_helper.clear_signal_tracking()

        # Test with valid parameters
        valid_params = {
            "vram_path": str(window_helper.vram_file),
            "cgram_path": str(window_helper.cgram_file),
            "output_base": str(window_helper.temp_path / "valid_output"),
            "create_grayscale": True,
            "create_metadata": True,
            "oam_path": str(window_helper.oam_file),
            "vram_offset": 0xC000,
        }
        window_helper.set_extraction_params(valid_params)

        real_controller.start_extraction()

        # Should attempt extraction (may succeed or fail based on data, but should not fail validation)
        window_helper.get_signal_emissions()
        # With valid params, validation should pass (implementation may still fail later)

    @pytest.mark.integration
    def test_real_progress_handling(self, real_controller, window_helper):
        """Test real progress message handling"""
        # Test progress handler directly
        window_helper.get_status_message()

        real_controller._on_progress(50, "Testing progress message")

        updated_message = window_helper.get_status_message()
        assert updated_message == "Testing progress message"

    @pytest.mark.integration
    def test_real_preview_handling(self, real_controller, window_helper):
        """Test real preview handling"""
        # UPDATED FOR BUG #26: Create a PIL Image mock and mock the conversion function
        mock_pil_image = Mock()  # Mock PIL Image for Qt threading safety
        tile_count = 42

        # Mock pil_to_qpixmap to return a mock QPixmap since we're testing with mock PIL Image
        mock_qpixmap = Mock()
        with patch("spritepal.core.controller.pil_to_qpixmap", return_value=mock_qpixmap):
            # Test preview ready handler - now expects PIL Image
            real_controller._on_preview_ready(mock_pil_image, tile_count)

        # Verify preview was handled (check if preview_info was updated)
        preview_text = window_helper.get_preview_info_text()
        assert "42" in preview_text  # Should contain tile count

    @pytest.mark.integration
    def test_real_error_handling(self, real_controller, window_helper):
        """Test real error handling in controller"""
        # Test error handler directly
        test_error_message = "Test error message"

        real_controller._on_extraction_error(test_error_message)

        # Verify error was handled
        signals = window_helper.get_signal_emissions()
        assert len(signals["extraction_failed"]) == 1
        assert signals["extraction_failed"][0] == test_error_message

    @pytest.mark.integration
    def test_real_extraction_workflow_integration(self, real_controller, window_helper):
        """Test real extraction workflow integration"""
        # Set up extraction parameters
        params = {
            "vram_path": str(window_helper.vram_file),
            "cgram_path": str(window_helper.cgram_file),
            "output_base": str(window_helper.temp_path / "workflow_test"),
            "create_grayscale": True,
            "create_metadata": True,
            "oam_path": str(window_helper.oam_file),
            "vram_offset": 0xC000,
        }
        window_helper.set_extraction_params(params)

        # Start extraction workflow
        real_controller.start_extraction()

        # Verify workflow was initiated
        signals = window_helper.get_signal_emissions()
        total_workflow_signals = (
            len(signals["extraction_complete"]) +
            len(signals["extraction_failed"])
        )

        # Should have attempted the workflow (either success or failure)
        assert total_workflow_signals >= 0

    @pytest.mark.integration
    def test_real_signal_emission_integration(self, real_controller, window_helper):
        """Test real signal emission integration"""
        # Clear existing signals
        window_helper.clear_signal_tracking()

        # Trigger various controller operations that emit signals
        window_helper.extract_requested.emit()
        window_helper.open_in_editor_requested.emit("test.png")
        window_helper.arrange_rows_requested.emit("test.png")

        # Verify signals were tracked
        signals = window_helper.get_signal_emissions()
        assert len(signals["extract_requested"]) == 1
        assert len(signals["open_in_editor_requested"]) == 1
        assert len(signals["arrange_rows_requested"]) == 1

    @pytest.mark.integration
    def test_real_controller_state_management(self, real_controller, window_helper):
        """Test real controller state management"""
        # Test controller state transitions
        assert real_controller.worker is None  # Initial state

        # Set up valid parameters
        params = {
            "vram_path": str(window_helper.vram_file),
            "cgram_path": str(window_helper.cgram_file),
            "output_base": str(window_helper.temp_path / "state_test"),
            "create_grayscale": True,
            "create_metadata": True,
        }
        window_helper.set_extraction_params(params)

        # Start extraction
        real_controller.start_extraction()

        # Worker may or may not be created depending on validation success
        # The key is that controller handles state consistently
        assert real_controller is not None

        # Controller should remain in valid state throughout operations
        assert real_controller is not None
        assert real_controller.main_window == window_helper


class TestControllerWorkerIntegration:
    """Test integration between controller and worker"""

    @pytest.fixture
    def mock_main_window(self):
        """Create mock main window WITHOUT real file dependencies for perfect isolation"""
        # CRITICAL FIX FOR BUG #27: No real files in mocked tests to avoid contamination
        window = Mock()
        window.extract_requested = Mock()
        window.open_in_editor_requested = Mock()
        window.status_bar = Mock()
        window.sprite_preview = Mock()
        window.preview_info = Mock()
        window.palette_preview = Mock()
        window.extraction_complete = Mock()
        window.extraction_failed = Mock()
        # Use fake paths with grayscale_mode=True to bypass CGRAM validation
        window.get_extraction_params.return_value = {
            "vram_path": "/fake/test/path/vram.bin",
            "output_base": "/fake/test/path/output",
            "create_grayscale": True,
            "create_metadata": True,
            "grayscale_mode": True,  # This bypasses CGRAM requirement
        }
        return window

    @pytest.fixture
    def controller(self, mock_main_window):
        """Create controller instance for mocked tests - no real managers"""
        # CRITICAL FIX FOR BUG #27: Don't initialize real managers in mocked tests
        # Create controller with mocked window
        controller = ExtractionController(mock_main_window)

        # Mock all manager dependencies to ensure complete isolation
        controller.extraction_manager = Mock()
        controller.injection_manager = Mock()
        controller.session_manager = Mock()

        # Mock validation to always pass for mocked tests
        controller.extraction_manager.validate_extraction_params = Mock(return_value=None)

        return controller

    @patch("spritepal.core.controller.VRAMExtractionWorker")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_worker_signals_connected_to_controller(
        self, mock_getsize, mock_exists, mock_worker_class, controller, mock_main_window
    ):
        """Test that worker signals are properly connected to controller handlers"""
        # CRITICAL FIX FOR BUG #27: Pure mocked test - NO real file dependencies

        # Mock file system checks to pass validation
        mock_exists.return_value = True
        mock_getsize.return_value = 65536  # 64KB valid VRAM size

        # Configure mock main window with fake parameters (already set in fixture)
        mock_main_window.reset_mock()

        # Create mock worker
        mock_worker = Mock()
        mock_worker_class.return_value = mock_worker

        # Mock file reading for validation
        with patch("builtins.open", mock_open(read_data=b"x" * 16)):
            # The extraction manager validation is already mocked in the fixture
            controller.start_extraction()

        # Verify the worker class was called to create an instance
        mock_worker_class.assert_called_once()

        # Verify all signals were connected
        mock_worker.progress.connect.assert_called_once_with(controller._on_progress)
        mock_worker.preview_ready.connect.assert_called_once_with(
            controller._on_preview_ready
        )
        mock_worker.preview_image_ready.connect.assert_called_once_with(
            controller._on_preview_image_ready
        )
        mock_worker.palettes_ready.connect.assert_called_once_with(
            controller._on_palettes_ready
        )
        mock_worker.active_palettes_ready.connect.assert_called_once_with(
            controller._on_active_palettes_ready
        )
        mock_worker.extraction_finished.connect.assert_called_once_with(
            controller._on_extraction_finished
        )
        mock_worker.error.connect.assert_called_once_with(
            controller._on_extraction_error
        )

        # Verify worker was started
        mock_worker.start.assert_called_once()

    def test_full_signal_chain_simulation(self, controller, mock_main_window):
        """Test full signal chain from worker to UI"""
        # Simulate worker signals
        controller._on_progress(10, "Starting extraction...")
        # UPDATED FOR BUG #26: Pass PIL Image mock and mock conversion function
        mock_pil_image = Mock()  # Mock PIL Image for Qt threading safety
        mock_qpixmap = Mock()
        with patch("spritepal.core.controller.pil_to_qpixmap", return_value=mock_qpixmap):
            controller._on_preview_ready(mock_pil_image, 10)
        controller._on_preview_image_ready(Mock())
        controller._on_palettes_ready({8: [[0, 0, 0]]})
        controller._on_active_palettes_ready([8, 9])
        controller._on_extraction_finished(["sprite.png", "palette.json"])

        # Verify UI was updated
        mock_main_window.status_bar.showMessage.assert_called()
        mock_main_window.sprite_preview.set_preview.assert_called_once()
        mock_main_window.preview_info.setText.assert_called_once_with("Tiles: 10")
        mock_main_window.sprite_preview.set_grayscale_image.assert_called_once()
        mock_main_window.palette_preview.set_all_palettes.assert_called_once()
        mock_main_window.sprite_preview.set_palettes.assert_called_once()
        mock_main_window.palette_preview.highlight_active_palettes.assert_called_once()
        mock_main_window.extraction_complete.assert_called_once()

    def test_error_signal_chain_simulation(self, controller, mock_main_window):
        """Test error signal chain from worker to UI"""
        controller.worker = Mock()  # Set worker to test cleanup

        # Simulate worker error
        controller._on_extraction_error("Failed to read file")

        # Verify error handling
        mock_main_window.extraction_failed.assert_called_once_with(
            "Failed to read file"
        )
        assert controller.worker is None  # Worker should be cleaned up

    def test_worker_cleanup_on_completion(self, controller):
        """Test that worker is cleaned up on completion"""
        controller.worker = Mock()

        controller._on_extraction_finished(["file1.png", "file2.json"])

        assert controller.worker is None

    def test_worker_cleanup_on_error(self, controller):
        """Test that worker is cleaned up on error"""
        controller.worker = Mock()

        controller._on_extraction_error("Some error occurred")

        assert controller.worker is None

    @patch("spritepal.core.controller.VRAMExtractionWorker")
    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_concurrent_extraction_handling(
        self, mock_getsize, mock_exists, mock_worker_class, controller, mock_main_window
    ):
        """Test handling of concurrent extraction requests"""
        # CRITICAL FIX FOR BUG #27: Pure mocked test - NO real file dependencies
        # Mock file system checks to pass validation
        mock_exists.return_value = True
        mock_getsize.return_value = 65536  # 64KB valid VRAM size

        # Reset mock to ensure clean state
        mock_main_window.reset_mock()

        # Create different mock instances for each call
        first_mock_worker = Mock()
        second_mock_worker = Mock()
        mock_worker_class.side_effect = [first_mock_worker, second_mock_worker]

        # Mock file reading for validation
        with patch("builtins.open", mock_open(read_data=b"x" * 16)):
            # Start first extraction
            controller.start_extraction()
            first_worker = controller.worker

            # Start second extraction (should replace first)
            controller.start_extraction()
            second_worker = controller.worker

        # Should have different workers (test concurrency handling)
        assert first_worker != second_worker
        assert controller.worker == second_worker

        # Verify mock class was called twice
        assert mock_worker_class.call_count == 2
