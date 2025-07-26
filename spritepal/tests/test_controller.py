"""
Comprehensive tests for controller functionality
"""

import importlib
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import spritepal.core.controller
from spritepal.core.controller import ExtractionController, ExtractionWorker
from spritepal.core.managers import cleanup_managers, initialize_managers


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

        # When both are missing, it fails on VRAM check first
        mock_main_window.extraction_failed.assert_called_once_with(
            "VRAM file is required for extraction"
        )

    @patch("spritepal.core.controller.ExtractionWorker")
    def test_start_extraction_valid_params(
        self, mock_worker_class, controller, mock_main_window
    ):
        """Test starting extraction with valid parameters"""
        mock_main_window.get_extraction_params.return_value = {
            "vram_path": "/path/to/vram.dmp",
            "cgram_path": "/path/to/cgram.dmp",
            "output_base": "/path/to/output",
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
        mock_worker_instance.finished.connect.assert_called()
        mock_worker_instance.error.connect.assert_called()

    def test_on_progress_handler(self, controller, mock_main_window):
        """Test progress message handler"""
        test_message = "Extracting sprites..."

        controller._on_progress(test_message)

        mock_main_window.status_bar.showMessage.assert_called_once_with(test_message)

    def test_on_preview_ready_handler(self, controller, mock_main_window):
        """Test preview ready handler"""
        mock_pixmap = Mock()
        tile_count = 42

        controller._on_preview_ready(mock_pixmap, tile_count)

        mock_main_window.sprite_preview.set_preview.assert_called_once_with(
            mock_pixmap, tile_count
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


class TestExtractionWorker:
    """Test ExtractionWorker functionality"""

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
        """Create worker instance"""
        return ExtractionWorker(worker_params)

    def test_init_creates_components(self, worker, worker_params):
        """Test worker initialization stores parameters"""
        assert worker.params == worker_params
        assert worker.manager is None  # Manager is only set during run()


    @patch("spritepal.core.controller.get_extraction_manager")
    @patch("spritepal.core.controller.pil_to_qpixmap")
    def test_run_full_workflow_success(self, mock_pil_to_qpixmap, mock_get_manager, worker):
        """Test successful full workflow execution"""
        # Mock manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        # Mock extraction result
        mock_manager.extract_from_vram.return_value = [
            "output.png", "output.pal.json", "output.metadata.json"
        ]

        # Mock pixmap conversion
        mock_pixmap = Mock()
        mock_pil_to_qpixmap.return_value = mock_pixmap

        # Mock signals
        worker.progress = Mock()
        worker.preview_ready = Mock()
        worker.preview_image_ready = Mock()
        worker.palettes_ready = Mock()
        worker.active_palettes_ready = Mock()
        worker.finished = Mock()
        worker.error = Mock()

        # Run worker
        worker.run()

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

        # Verify finished signal was emitted
        worker.finished.emit.assert_called_once_with([
            "output.png", "output.pal.json", "output.metadata.json"
        ])
        worker.error.emit.assert_not_called()

    @patch("spritepal.core.controller.get_extraction_manager")
    def test_run_error_handling(self, mock_get_manager, worker):
        """Test error handling in worker"""
        # Mock manager to raise exception
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.extract_from_vram.side_effect = Exception("Test error")

        # Mock signals
        worker.progress = Mock()
        worker.error = Mock()
        worker.finished = Mock()

        # Run worker
        worker.run()

        # Verify error was emitted
        worker.error.emit.assert_called_once_with("Test error")
        worker.finished.emit.assert_not_called()

    @patch("spritepal.core.controller.get_extraction_manager")
    @patch("spritepal.core.controller.pil_to_qpixmap")
    def test_run_without_cgram(self, mock_pil_to_qpixmap, mock_get_manager, worker):
        """Test running without CGRAM file"""
        worker.params["cgram_path"] = None

        # Mock manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.extract_from_vram.return_value = ["output.png"]

        # Mock signals
        worker.progress = Mock()
        worker.preview_ready = Mock()
        worker.preview_image_ready = Mock()
        worker.palettes_ready = Mock()
        worker.finished = Mock()
        worker.error = Mock()

        worker.run()

        # Verify manager was called with None cgram_path
        mock_manager.extract_from_vram.assert_called_once()
        call_args = mock_manager.extract_from_vram.call_args[1]
        assert call_args["cgram_path"] is None

        worker.finished.emit.assert_called_once()
        worker.error.emit.assert_not_called()

    @patch("spritepal.core.controller.get_extraction_manager")
    @patch("spritepal.core.controller.pil_to_qpixmap")
    def test_run_without_oam(self, mock_pil_to_qpixmap, mock_get_manager, worker):
        """Test running without OAM file"""
        worker.params["oam_path"] = None

        # Mock manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.extract_from_vram.return_value = [
            "output.png", "output.pal.json", "output.metadata.json"
        ]

        # Mock signals
        worker.progress = Mock()
        worker.preview_ready = Mock()
        worker.preview_image_ready = Mock()
        worker.palettes_ready = Mock()
        worker.active_palettes_ready = Mock()
        worker.finished = Mock()
        worker.error = Mock()

        worker.run()

        # Verify manager was called with None oam_path
        mock_manager.extract_from_vram.assert_called_once()
        call_args = mock_manager.extract_from_vram.call_args[1]
        assert call_args.get("oam_path") is None

        worker.finished.emit.assert_called_once()
        worker.error.emit.assert_not_called()

    @patch("spritepal.core.controller.get_extraction_manager")
    @patch("spritepal.core.controller.pil_to_qpixmap")
    def test_run_without_metadata_creation(self, mock_pil_to_qpixmap, mock_get_manager, worker):
        """Test running without metadata creation"""
        worker.params["create_metadata"] = False

        # Mock manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.extract_from_vram.return_value = [
            "output.png", "output.pal.json"
        ]

        # Mock signals
        worker.progress = Mock()
        worker.preview_ready = Mock()
        worker.preview_image_ready = Mock()
        worker.palettes_ready = Mock()
        worker.finished = Mock()
        worker.error = Mock()

        worker.run()

        # Verify manager was called with create_metadata=False
        mock_manager.extract_from_vram.assert_called_once()
        call_args = mock_manager.extract_from_vram.call_args[1]
        assert call_args["create_metadata"] is False

        worker.finished.emit.assert_called_once()
        worker.error.emit.assert_not_called()

    @patch("spritepal.core.controller.get_extraction_manager")
    @patch("spritepal.core.controller.pil_to_qpixmap")
    def test_run_without_grayscale_creation(self, mock_pil_to_qpixmap, mock_get_manager, worker):
        """Test running without grayscale palette creation"""
        worker.params["create_grayscale"] = False

        # Mock manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.extract_from_vram.return_value = ["output.png"]

        # Mock signals
        worker.progress = Mock()
        worker.preview_ready = Mock()
        worker.preview_image_ready = Mock()
        worker.palettes_ready = Mock()
        worker.finished = Mock()
        worker.error = Mock()

        worker.run()

        # Verify manager was called with create_grayscale=False
        mock_manager.extract_from_vram.assert_called_once()
        call_args = mock_manager.extract_from_vram.call_args[1]
        assert call_args["create_grayscale"] is False

        worker.finished.emit.assert_called_once()
        worker.error.emit.assert_not_called()

    @patch("spritepal.core.controller.get_extraction_manager")
    @patch("spritepal.core.controller.pil_to_qpixmap")
    def test_signal_emission_order(self, mock_pil_to_qpixmap, mock_get_manager, worker):
        """Test that finished signal is emitted after successful extraction"""
        # Mock manager
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.extract_from_vram.return_value = [
            "output.png", "output.pal.json", "output.metadata.json"
        ]

        # Track if finished was called
        finished_called = False
        finished_args = None

        def track_finished(files):
            nonlocal finished_called, finished_args
            finished_called = True
            finished_args = files

        worker.finished = Mock()
        worker.finished.emit = track_finished
        worker.error = Mock()

        worker.run()

        # Verify finished was called with the correct files
        assert finished_called
        assert finished_args == ["output.png", "output.pal.json", "output.metadata.json"]
        worker.error.emit.assert_not_called()


class TestControllerWorkerIntegration:
    """Test integration between controller and worker"""

    @pytest.fixture
    def mock_main_window(self):
        """Create mock main window"""
        window = Mock()
        window.extract_requested = Mock()
        window.open_in_editor_requested = Mock()
        window.status_bar = Mock()
        window.sprite_preview = Mock()
        window.preview_info = Mock()
        window.palette_preview = Mock()
        window.extraction_complete = Mock()
        window.extraction_failed = Mock()
        window.get_extraction_params.return_value = {
            "vram_path": "/path/to/vram.dmp",
            "cgram_path": "/path/to/cgram.dmp",
            "output_base": "/path/to/output",
            "create_grayscale": True,
            "create_metadata": True,
        }
        return window

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

    @patch("spritepal.core.controller.ExtractionWorker")
    def test_worker_signals_connected_to_controller(
        self, mock_worker_class, controller, mock_main_window
    ):
        """Test that worker signals are properly connected to controller handlers"""
        mock_worker = Mock()
        mock_worker_class.return_value = mock_worker

        controller.start_extraction()

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
        mock_worker.finished.connect.assert_called_once_with(
            controller._on_extraction_finished
        )
        mock_worker.error.connect.assert_called_once_with(
            controller._on_extraction_error
        )

    def test_full_signal_chain_simulation(self, controller, mock_main_window):
        """Test full signal chain from worker to UI"""
        # Simulate worker signals
        controller._on_progress("Starting extraction...")
        controller._on_preview_ready(Mock(), 10)
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

    @patch("spritepal.core.controller.ExtractionWorker")
    def test_concurrent_extraction_handling(
        self, mock_worker_class, controller, mock_main_window
    ):
        """Test handling of concurrent extraction requests"""
        # Create different mock instances for each call
        first_mock_worker = Mock()
        second_mock_worker = Mock()
        mock_worker_class.side_effect = [first_mock_worker, second_mock_worker]

        # Start first extraction
        controller.start_extraction()
        first_worker = controller.worker

        # Start second extraction (should replace first)
        controller.start_extraction()
        second_worker = controller.worker

        # Should have different workers
        assert first_worker != second_worker
        assert controller.worker == second_worker
        assert first_worker == first_mock_worker
        assert second_worker == second_mock_worker
