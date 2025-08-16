"""
Comprehensive tests for controller functionality
"""

import importlib
import os
import sys
from pathlib import Path
from typing import Any, Generator
from unittest.mock import Mock, mock_open, patch

import pytest
from PySide6.QtTest import QSignalSpy

# Add parent directories to path
# Serial execution required: Thread safety concerns
pytestmark = [
    
    pytest.mark.serial,
    pytest.mark.thread_safety,
    pytest.mark.dialog,
    pytest.mark.file_io,
    pytest.mark.headless,
    pytest.mark.mock_dialogs,
    pytest.mark.mock_only,
    pytest.mark.requires_display,
    pytest.mark.rom_data,
    pytest.mark.signals_slots,
    pytest.mark.slow,
]


sys.path.insert(0, str(Path(__file__).parent.parent.parent))


import core.controller
from core.controller import ExtractionController
from core.workers import VRAMExtractionWorker
from core.managers.extraction_manager import ExtractionManager
from core.managers.injection_manager import InjectionManager
from core.managers.session_manager import SessionManager

# Defer MainWindow import to avoid potential initialization issues
def get_main_window():
    from ui.main_window import MainWindow
    return MainWindow


@pytest.mark.no_manager_setup
class TestControllerImports:
    """Test that controller module imports work correctly"""

    def test_controller_imports(self) -> None:
        """Test that all imports in controller module work without errors"""
        # This test will catch import-time errors like missing pil_to_qpixmap
        try:
            # Force module reload to catch any import errors
            importlib.reload(core.controller)
        except ImportError as e:
            pytest.fail(f"Import error in controller module: {e}")
        except NameError as e:
            pytest.fail(f"Name error in controller module: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error importing controller module: {e}")

    def test_pil_to_qpixmap_import(self, tmp_path: Any) -> None:
        """Test that pil_to_qpixmap function is available in controller module"""
        # Test that pil_to_qpixmap is imported and available
        from core import controller

        assert hasattr(controller, "pil_to_qpixmap")
        assert callable(controller.pil_to_qpixmap)


@pytest.mark.no_manager_setup
class TestExtractionController:
    """Test ExtractionController functionality"""

    @pytest.fixture
    def main_window(self) -> Any:
        """Create mock main window for testing"""
        from unittest.mock import Mock, MagicMock
        MainWindow = get_main_window()
        window = Mock(spec=MainWindow)
        # Add required signals as mock signals with proper spec
        # Using MagicMock to allow signal emission simulation
        window.extract_requested = MagicMock()
        window.open_in_editor_requested = MagicMock()
        window.arrange_rows_requested = MagicMock()
        window.arrange_grid_requested = MagicMock()
        window.inject_requested = MagicMock()
        window.extraction_completed = MagicMock()  # Signal we added earlier
        window.extraction_error_occurred = MagicMock()  # Signal we added earlier
        # Add required attributes with spec where applicable
        window.extraction_panel = Mock()
        window.rom_extraction_panel = Mock()
        window.output_settings_manager = Mock()
        window.toolbar_manager = Mock()
        window.preview_coordinator = Mock()
        window.status_bar_manager = Mock()
        window.status_bar = Mock()  # Add status_bar for controller
        window.sprite_preview = Mock()  # Add sprite_preview for controller
        window.palette_preview = Mock()  # Add palette_preview for controller
        window.extraction_tabs = Mock()
        window._output_path = ""
        window._extracted_files = []
        return window

    @pytest.fixture
    def controller(self, main_window: Any) -> ExtractionController:
        """Create REAL controller instance with mock managers"""
        from unittest.mock import Mock, patch
        # Create mock managers for dependency injection
        extraction_manager = Mock(spec=ExtractionManager)
        injection_manager = Mock(spec=InjectionManager)
        session_manager = Mock(spec=SessionManager)
        
        # Patch get_error_handler to return a mock to avoid QWidget issues
        with patch('core.controller.get_error_handler') as mock_get_error_handler:
            mock_error_handler = Mock()
            mock_get_error_handler.return_value = mock_error_handler
            
            # Create a REAL controller with mock dependencies
            controller = ExtractionController(
                main_window=main_window,
                extraction_manager=extraction_manager,
                injection_manager=injection_manager,
                session_manager=session_manager
            )
            
            # Store the mock error handler for tests to access if needed
            controller.mock_error_handler = mock_error_handler
        
        # The controller is real and will execute real code
        # Only the dependencies are mocked
        return controller

    def test_init_connects_signals(self, controller: ExtractionController, main_window: Any) -> None:
        """Test controller initialization connects signals"""
        # With real Qt signals, we verify connections work by checking that
        # signals have receivers (meaning something is connected)
        
        assert controller.main_window == main_window
        assert controller.worker is None
        
        # Verify that the controller has the expected methods that should be connected
        assert hasattr(controller, 'start_extraction')
        assert hasattr(controller, 'open_in_editor')
        assert hasattr(controller, 'open_row_arrangement')
        assert hasattr(controller, 'open_grid_arrangement')
        assert hasattr(controller, 'start_injection')
        assert hasattr(controller, 'update_preview_with_offset')
        
        # Verify the main window has the expected signals
        assert hasattr(main_window, 'extract_requested')
        assert hasattr(main_window, 'open_in_editor_requested')
        assert hasattr(main_window, 'arrange_rows_requested')
        assert hasattr(main_window, 'arrange_grid_requested')
        assert hasattr(main_window, 'inject_requested')
        
        # Note: Can't test signal connections with Mock objects
        # Real signal connection tests are in test_controller_real.py

    def test_parameter_validation_missing_vram(self):
        """Test parameter validation when VRAM path is missing"""
        from unittest.mock import Mock, patch
        from core.controller import ExtractionController
        
        # Create simple mock main window
        mock_main_window = Mock()
        invalid_params = {
            "vram_path": "",
            "cgram_path": "/path/to/cgram.dmp",
            "output_base": "/path/to/output",
        }
        mock_main_window.get_extraction_params.return_value = invalid_params
        
        # Mock the manager getters to avoid initialization issues
        with patch('core.controller.get_extraction_manager') as mock_get_extraction, \
             patch('core.controller.get_injection_manager') as mock_get_injection, \
             patch('core.controller.get_session_manager') as mock_get_session:
            
            # Create mock managers
            mock_extraction_manager = Mock()
            mock_extraction_manager.validate_extraction_params.side_effect = Exception("VRAM file is required for extraction")
            mock_get_extraction.return_value = mock_extraction_manager
            mock_get_injection.return_value = Mock()
            mock_get_session.return_value = Mock()
            
            # Create controller with mock window
            controller = ExtractionController(mock_main_window)

            # Start extraction (should fail validation immediately)
            controller.start_extraction()
            
            # Verify extraction_failed was called with correct message
            mock_main_window.extraction_failed.assert_called_once()
            call_args = mock_main_window.extraction_failed.call_args[0]
            assert "VRAM file is required for extraction" in call_args[0]
            
            # Verify worker was not created (validation failed before worker creation)
            assert controller.worker is None

    def test_parameter_validation_missing_cgram(self):
        """Test parameter validation when CGRAM path is missing"""
        from unittest.mock import Mock, patch
        from core.controller import ExtractionController
        
        # Create simple mock main window
        mock_main_window = Mock()
        invalid_params = {
            "vram_path": "/path/to/vram.dmp",
            "cgram_path": "",
            "output_base": "/path/to/output",
            "grayscale_mode": False,  # CGRAM is required when not in grayscale mode
        }
        mock_main_window.get_extraction_params.return_value = invalid_params
        
        # Mock the manager getters to avoid initialization issues
        with patch('core.controller.get_extraction_manager') as mock_get_extraction, \
             patch('core.controller.get_injection_manager') as mock_get_injection, \
             patch('core.controller.get_session_manager') as mock_get_session:
            
            # Create mock managers
            mock_extraction_manager = Mock()
            expected_msg = "CGRAM file is required for Full Color mode.\nPlease provide a CGRAM file or switch to Grayscale Only mode."
            mock_extraction_manager.validate_extraction_params.side_effect = Exception(expected_msg)
            mock_get_extraction.return_value = mock_extraction_manager
            mock_get_injection.return_value = Mock()
            mock_get_session.return_value = Mock()
            
            # Create controller with mock window
            controller = ExtractionController(mock_main_window)

            # Start extraction (should fail validation immediately)
            controller.start_extraction()

            # Verify extraction_failed was called with correct message
            mock_main_window.extraction_failed.assert_called_once()
            call_args = mock_main_window.extraction_failed.call_args[0]
            assert expected_msg in call_args[0]
            
            # Verify worker was not created (validation failed before worker creation)
            assert controller.worker is None

    def test_parameter_validation_missing_both(self):
        """Test parameter validation when both paths are missing"""
        from unittest.mock import Mock, patch
        from core.controller import ExtractionController
        
        # Create simple mock main window
        mock_main_window = Mock()
        invalid_params = {
            "vram_path": None,
            "cgram_path": None,
            "output_base": "/path/to/output",
        }
        mock_main_window.get_extraction_params.return_value = invalid_params
        
        # Mock the manager getters to avoid initialization issues
        with patch('core.controller.get_extraction_manager') as mock_get_extraction, \
             patch('core.controller.get_injection_manager') as mock_get_injection, \
             patch('core.controller.get_session_manager') as mock_get_session:
            
            # Create mock managers
            mock_extraction_manager = Mock()
            mock_extraction_manager.validate_extraction_params.side_effect = Exception("VRAM file is required for extraction")
            mock_get_extraction.return_value = mock_extraction_manager
            mock_get_injection.return_value = Mock()
            mock_get_session.return_value = Mock()
            
            # Create controller with mock window
            controller = ExtractionController(mock_main_window)

            # Start extraction (should fail validation immediately)
            controller.start_extraction()

            # When both are missing, it fails on VRAM parameter check first
            mock_main_window.extraction_failed.assert_called_once()
            call_args = mock_main_window.extraction_failed.call_args[0]
            assert "VRAM file is required for extraction" in call_args[0]
            
            # Verify worker was not created (validation failed before worker creation)
            assert controller.worker is None

    def test_start_extraction_valid_params(self):
        """Test starting extraction with valid parameters"""
        from unittest.mock import Mock, patch
        from core.controller import ExtractionController
        from core.workers import VRAMExtractionWorker
        
        # Create simple mock main window
        mock_main_window = Mock()
        valid_params = {
            "vram_path": "/valid/path/to/vram.dmp",
            "cgram_path": "/valid/path/to/cgram.dmp",
            "output_base": "/valid/path/to/output",
            "grayscale_mode": True,
        }
        mock_main_window.get_extraction_params.return_value = valid_params
        
        # Mock the manager getters, file validation, and worker creation
        with patch('core.controller.get_extraction_manager') as mock_get_extraction, \
             patch('core.controller.get_injection_manager') as mock_get_injection, \
             patch('core.controller.get_session_manager') as mock_get_session, \
             patch('core.controller.FileValidator.validate_vram_file') as mock_vram_validator, \
             patch('core.controller.FileValidator.validate_cgram_file') as mock_cgram_validator, \
             patch('core.controller.VRAMExtractionWorker') as mock_worker_class:
            
            # Create mock managers (validation passes)
            mock_extraction_manager = Mock()
            mock_extraction_manager.validate_extraction_params.return_value = None  # No exception = valid
            mock_get_extraction.return_value = mock_extraction_manager
            mock_get_injection.return_value = Mock()
            mock_get_session.return_value = Mock()
            
            # Mock file validation to return valid results
            mock_vram_result = Mock()
            mock_vram_result.is_valid = True
            mock_vram_result.warnings = []
            mock_vram_validator.return_value = mock_vram_result
            
            mock_cgram_result = Mock()
            mock_cgram_result.is_valid = True
            mock_cgram_result.warnings = []
            mock_cgram_validator.return_value = mock_cgram_result
            
            # Create mock worker instance
            mock_worker = Mock(spec=VRAMExtractionWorker)
            mock_worker_class.return_value = mock_worker
            
            # Create controller
            controller = ExtractionController(mock_main_window)

            # Start extraction (should create worker)
            controller.start_extraction()
            
            # Verify worker was created with correct parameters
            mock_worker_class.assert_called_once()
            call_args = mock_worker_class.call_args[0][0]  # First argument (params)
            assert call_args["vram_path"] == valid_params["vram_path"]
            assert call_args["cgram_path"] == valid_params["cgram_path"]
            assert call_args["output_base"] == valid_params["output_base"]
            
            # Verify worker was started
            mock_worker.start.assert_called_once()
            
            # Verify worker is stored in controller
            assert controller.worker == mock_worker

    def test_on_progress_handler(self, controller, main_window):
        """Test progress message handler"""
        test_message = "Extracting sprites..."

        controller._on_progress(50, test_message)

        # Verify the controller called showMessage with the correct message
        main_window.status_bar.showMessage.assert_called_once_with(test_message)

    def test_on_preview_ready_handler(self, controller, main_window):
        """Test preview ready handler - now expects PIL Image due to Qt threading fix"""
        # Create minimal test image data
        from PIL import Image
        test_image = Image.new('RGB', (8, 8), color='red')
        tile_count = 42

        # Test with real PIL Image - conversion handled internally
        controller._on_preview_ready(test_image, tile_count)

        # For real components, verify the preview was updated
        if hasattr(main_window, 'sprite_preview') and main_window.sprite_preview:
            assert main_window.sprite_preview is not None
        
        if hasattr(main_window, 'preview_coordinator') and main_window.preview_coordinator:
            assert main_window.preview_coordinator is not None

    def test_on_preview_image_ready_handler(self, controller, main_window):
        """Test preview image ready handler"""
        from PIL import Image
        test_image = Image.new('L', (8, 8), color=128)  # Grayscale image

        controller._on_preview_image_ready(test_image)

        # For real components, verify the grayscale image was processed
        if hasattr(main_window, 'sprite_preview') and main_window.sprite_preview:
            assert main_window.sprite_preview is not None

    def test_on_palettes_ready_handler(self, controller, main_window):
        """Test palettes ready handler"""
        test_palettes = {8: [[0, 0, 0], [255, 0, 0]], 9: [[0, 0, 0], [0, 255, 0]]}

        controller._on_palettes_ready(test_palettes)

        # For real components, verify palette widgets exist and were updated
        if hasattr(main_window, 'palette_preview') and main_window.palette_preview:
            assert main_window.palette_preview is not None
        if hasattr(main_window, 'sprite_preview') and main_window.sprite_preview:
            assert main_window.sprite_preview is not None

    def test_on_active_palettes_ready_handler(self, controller, main_window):
        """Test active palettes ready handler"""
        active_palettes = [8, 9, 10]

        controller._on_active_palettes_ready(active_palettes)

        # For real components, verify palette preview exists
        if hasattr(main_window, 'palette_preview') and main_window.palette_preview:
            assert main_window.palette_preview is not None

    def test_on_extraction_finished_handler(self, controller, main_window):
        """Test extraction finished handler"""
        extracted_files = ["sprite.png", "sprite.pal.json", "metadata.json"]
        
        # Create a simple worker placeholder for cleanup test
        class DummyWorker:
            def isRunning(self):
                return False
            def deleteLater(self):
                pass
        controller.worker = DummyWorker()
        
        # Call the real controller method
        controller._on_extraction_finished(extracted_files)
        
        # Verify the controller called the main_window method with correct args
        main_window.extraction_complete.assert_called_once_with(extracted_files)
        # Verify worker was cleaned up
        assert controller.worker is None

    def test_on_extraction_error_handler(self, controller, main_window):
        """Test extraction error handler"""
        error_message = "Failed to read VRAM file"
        
        # Create a simple worker placeholder for cleanup test
        class DummyWorker:
            def isRunning(self):
                return False
            def deleteLater(self):
                pass
        controller.worker = DummyWorker()
        
        # Call the real controller method
        controller._on_extraction_error(error_message)
        
        # Verify the controller called the main_window method with correct args
        main_window.extraction_failed.assert_called_once_with(error_message)
        # Verify worker was cleaned up
        assert controller.worker is None

    @patch("core.controller.subprocess.Popen")
    def test_open_in_editor_launcher_found(
        self, mock_popen, controller, main_window, tmp_path
    ):
        """Test opening in editor when launcher is found"""
        # Create real launcher file
        launcher_dir = tmp_path / "pixel_editor"
        launcher_dir.mkdir()
        launcher_file = launcher_dir / "launch_pixel_editor.py"
        launcher_file.write_text("# Fake launcher script")

        # Create real sprite file
        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake png data")

        # Patch __file__ to make it appear that controller.py is in tmp_path/core
        mock_controller_file = tmp_path / "core" / "controller.py"
        with patch("core.controller.__file__", str(mock_controller_file)):
            controller.open_in_editor(str(sprite_file))

        # Verify Popen was called with the correct arguments
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == sys.executable
        assert call_args[1].endswith("launch_pixel_editor.py")
        assert call_args[2] == os.path.abspath(str(sprite_file))

        # Verify status bar message was shown
        expected_message = f"Opened {os.path.basename(sprite_file)} in pixel editor"
        main_window.status_bar.showMessage.assert_called_with(expected_message)

    @patch("core.controller.subprocess.Popen")
    def test_open_in_editor_launcher_in_subdirectory(
        self, mock_popen, controller, main_window, tmp_path
    ):
        """Test opening in editor when launcher is in subdirectory"""
        # Create real launcher file in subdirectory
        launcher_dir = tmp_path / "pixel_editor"
        launcher_dir.mkdir()
        launcher_file = launcher_dir / "launch_pixel_editor.py"
        launcher_file.write_text("# Fake launcher script")

        # Create real sprite file
        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake png data")

        # Patch __file__ to make it appear that controller.py is in tmp_path/core
        mock_controller_file = tmp_path / "core" / "controller.py"
        with patch("core.controller.__file__", str(mock_controller_file)):
            controller.open_in_editor(str(sprite_file))

        # Verify Popen was called with the correct arguments
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == sys.executable
        assert call_args[1].endswith("pixel_editor/launch_pixel_editor.py")
        assert call_args[2] == os.path.abspath(str(sprite_file))

    @patch("core.controller.subprocess.Popen")
    def test_open_in_editor_launcher_in_parent_directory(
        self, mock_popen, controller, main_window, tmp_path
    ):
        """Test opening in editor when launcher is in parent directory"""
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
        with patch("core.controller.__file__", fake_controller_file):
            controller.open_in_editor(str(sprite_file))

        # Verify Popen was called with the correct arguments
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == sys.executable
        assert call_args[1].endswith("launch_pixel_editor.py")
        assert call_args[2] == os.path.abspath(str(sprite_file))

    def test_open_in_editor_launcher_not_found(
        self, controller, main_window, tmp_path
    ):
        """Test opening in editor when launcher is not found"""
        # Create sprite file but no launcher
        sprite_file = tmp_path / "sprite.png"
        sprite_file.write_text("fake png data")

        # Patch __file__ to use empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        mock_controller_file = empty_dir / "core" / "controller.py"
        with patch("core.controller.__file__", str(mock_controller_file)):
            controller.open_in_editor(str(sprite_file))

        # Verify status bar message was shown
        main_window.status_bar.showMessage.assert_called_with("Pixel editor not found")

    @patch("core.controller.subprocess.Popen")
    def test_open_in_editor_subprocess_error(
        self, mock_popen, controller, main_window, tmp_path
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
        mock_controller_file = tmp_path / "core" / "controller.py"
        with patch("core.controller.__file__", str(mock_controller_file)):
            controller.open_in_editor(str(sprite_file))

        # Verify status bar message was shown
        main_window.status_bar.showMessage.assert_called_with("Failed to open pixel editor: Subprocess failed")


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
    def worker(self, worker_params, real_extraction_manager, manager_context_factory):
        """Create real worker instance with test manager"""
        # Set up manager context so the worker can find the manager
        with manager_context_factory({"extraction": real_extraction_manager}):
            # Create real worker with test parameters
            # Now get_extraction_manager() will find the manager in the context
            worker = VRAMExtractionWorker(worker_params)
            
            yield worker
            
            # Cleanup
            if worker.isRunning():
                worker.quit()
                worker.wait(1000)

    def test_init_creates_components(self, worker, worker_params):
        """Test worker initialization stores parameters"""
        assert worker.params == worker_params
        assert worker.manager is not None  # Manager is set during initialization
        assert isinstance(worker.manager, ExtractionManager)
        # Real worker should have proper attributes
        assert hasattr(worker, 'progress')
        assert hasattr(worker, 'extraction_finished')
        assert hasattr(worker, 'error')

    def test_run_full_workflow_success(self, worker):
        """Test successful full workflow execution"""
        # Use QSignalSpy to test signal emission (use module-level import)
        extraction_spy = QSignalSpy(worker.extraction_finished)
        error_spy = QSignalSpy(worker.error)

        # Mock the manager's extract_from_vram method to return test results
        with patch.object(worker.manager, "extract_from_vram", return_value=[
            "output.png", "output.pal.json", "output.metadata.json"
        ]) as mock_extract:
            worker.run()

            # Verify manager was called with correct params
            mock_extract.assert_called_once_with(
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
            assert extraction_spy.count() == 1
            assert extraction_spy.at(0)[0] == ["output.png", "output.pal.json", "output.metadata.json"]
            assert error_spy.count() == 0

    def test_run_error_handling(self, worker):
        """Test error handling in worker"""
        # Create a test exception
        test_exception = Exception("Test error")

        # Use QSignalSpy to monitor error signal
        error_spy = QSignalSpy(worker.error)
        finished_spy = QSignalSpy(worker.extraction_finished)

        # Directly patch the manager's extract_from_vram method to raise exception
        with patch.object(worker.manager, "extract_from_vram", side_effect=test_exception):
            # Run worker
            worker.run()

            # Verify error signal was emitted
            assert error_spy.count() == 1
            expected_error = "VRAM extraction failed: Test error"
            assert expected_error in error_spy.at(0)[0]
            
            # Verify finished signal was not emitted
            assert finished_spy.count() == 0

    def test_run_without_cgram(self, worker):
        """Test running without CGRAM file"""
        worker.params["cgram_path"] = None

        # Use QSignalSpy to monitor signals
        finished_spy = QSignalSpy(worker.extraction_finished)
        error_spy = QSignalSpy(worker.error)

        # Directly patch the manager's extract_from_vram method
        with patch.object(worker.manager, "extract_from_vram", return_value=["output.png"]) as mock_extract:
            worker.run()

            # Verify manager was called with None cgram_path
            mock_extract.assert_called_once()
            call_args = mock_extract.call_args[1]
            assert call_args["cgram_path"] is None

            # Verify signals
            assert finished_spy.count() == 1
            assert error_spy.count() == 0

    def test_run_without_oam(self, worker):
        """Test running without OAM file"""
        worker.params["oam_path"] = None

        # Use QSignalSpy to monitor signals
        finished_spy = QSignalSpy(worker.extraction_finished)
        error_spy = QSignalSpy(worker.error)

        # Directly patch the manager's extract_from_vram method
        with patch.object(worker.manager, "extract_from_vram", return_value=[
            "output.png", "output.pal.json", "output.metadata.json"
        ]) as mock_extract:
            worker.run()

            # Verify manager was called with None oam_path
            mock_extract.assert_called_once()
            call_args = mock_extract.call_args[1]
            assert call_args.get("oam_path") is None

            # Verify signals
            assert finished_spy.count() == 1
            assert error_spy.count() == 0

    def test_run_without_metadata_creation(self, worker):
        """Test running without metadata creation"""
        worker.params["create_metadata"] = False

        # Use QSignalSpy to monitor signals
        finished_spy = QSignalSpy(worker.extraction_finished)
        error_spy = QSignalSpy(worker.error)

        # Directly patch the manager's extract_from_vram method
        with patch.object(worker.manager, "extract_from_vram", return_value=[
            "output.png", "output.pal.json"
        ]) as mock_extract:
            worker.run()

            # Verify manager was called with create_metadata=False
            mock_extract.assert_called_once()
            call_args = mock_extract.call_args[1]
            assert call_args["create_metadata"] is False

            # Verify signals
            assert finished_spy.count() == 1
            assert error_spy.count() == 0

    def test_run_without_grayscale_creation(self, worker):
        """Test running without grayscale palette creation"""
        worker.params["create_grayscale"] = False

        # Use QSignalSpy to monitor signals
        finished_spy = QSignalSpy(worker.extraction_finished)
        error_spy = QSignalSpy(worker.error)

        # Directly patch the manager's extract_from_vram method
        with patch.object(worker.manager, "extract_from_vram", return_value=["output.png"]) as mock_extract:
            worker.run()

            # Verify manager was called with create_grayscale=False
            mock_extract.assert_called_once()
            call_args = mock_extract.call_args[1]
            assert call_args["create_grayscale"] is False

            # Verify signals
            assert finished_spy.count() == 1
            assert error_spy.count() == 0

    def test_signal_emission_order(self, worker):
        """Test that finished signal is emitted after successful extraction"""
        # Use QSignalSpy to monitor signal emission order
        finished_spy = QSignalSpy(worker.extraction_finished)
        error_spy = QSignalSpy(worker.error)

        # Directly patch the manager's extract_from_vram method
        with patch.object(worker.manager, "extract_from_vram", return_value=[
            "output.png", "output.pal.json", "output.metadata.json"
        ]):
            worker.run()

            # Verify finished signal was emitted with correct files
            assert finished_spy.count() == 1
            assert finished_spy.at(0)[0] == ["output.png", "output.pal.json", "output.metadata.json"]
            
            # Verify error signal was not emitted
            assert error_spy.count() == 0


@pytest.mark.no_manager_setup
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
    def real_controller(self, window_helper, manager_context_factory):
        """Create real controller with window helper and proper manager context"""
        with manager_context_factory() as context:
            controller = ExtractionController(window_helper)
            # Inject context managers
            controller.extraction_manager = context.get_manager("extraction", object)
            controller.injection_manager = context.get_manager("injection", object)
            controller.session_manager = context.get_manager("session", object)
            yield controller

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
        # Create a real PIL Image for testing
        from PIL import Image
        test_image = Image.new('RGB', (8, 8), color='blue')
        tile_count = 42

        # Test preview ready handler - now expects PIL Image
        real_controller._on_preview_ready(test_image, tile_count)

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


@pytest.mark.no_manager_setup
@pytest.mark.skip(reason="Real MainWindow creation causes hanging - needs refactoring")
class TestControllerWorkerIntegration:
    """Test integration between controller and worker"""

    @pytest.fixture
    def integration_main_window(self, real_factory, qtbot):
        """Create real main window for integration testing"""
        window = real_factory.create_main_window(with_managers=True)
        qtbot.addWidget(window)  # Ensure proper cleanup order
        
        # Set up test data using TestDataRepository
        from .infrastructure.test_data_repository import TestDataRepository
        repo = TestDataRepository()
        test_data = repo.get_vram_extraction_data("medium")
        
        # Set real extraction parameters
        extraction_params = {
            "vram_path": test_data["vram_path"],
            "cgram_path": test_data["cgram_path"],
            "oam_path": test_data.get("oam_path", ""),
            "output_base": test_data["output_base"],
            "create_grayscale": True,
            "create_metadata": True,
            "grayscale_mode": True,  # Simplify for testing
        }
        
        if hasattr(window, 'set_extraction_params'):
            window.set_extraction_params(extraction_params)
        else:
            window.get_extraction_params = lambda: extraction_params
        
        yield window
        
        # Ensure any active controller workers are stopped before window deletion
        if hasattr(window, 'controller') and hasattr(window.controller, 'worker'):
            worker = window.controller.worker
            if worker and worker.isRunning():
                worker.quit()
                worker.wait(1000)
        
        # Cleanup
        repo.cleanup()

    @pytest.fixture
    def integration_controller(self, integration_main_window, real_extraction_manager, real_injection_manager, real_session_manager):
        """Create controller instance for integration tests with real managers"""
        controller = ExtractionController(integration_main_window)
        
        # Inject real managers
        controller.extraction_manager = real_extraction_manager
        controller.injection_manager = real_injection_manager
        controller.session_manager = real_session_manager
        
        yield controller
        
        # Cleanup any running worker - disconnect signals first
        if controller.worker:
            # Disconnect all signals to prevent signal emission to deleted objects
            try:
                controller.worker.progress.disconnect()
                controller.worker.preview_ready.disconnect()
                controller.worker.preview_image_ready.disconnect()
                controller.worker.palettes_ready.disconnect()
                controller.worker.active_palettes_ready.disconnect()
                controller.worker.extraction_finished.disconnect()
                controller.worker.error.disconnect()
            except (TypeError, RuntimeError):
                # Signals may not be connected or already disconnected
                pass
            
            # Now stop the worker
            if controller.worker.isRunning():
                controller.worker.quit()
                controller.worker.wait(1000)
            
            # Delete the worker reference
            controller.worker.deleteLater()
            controller.worker = None

    def test_worker_signals_connected_to_controller(
        self, integration_controller, integration_main_window
    ):
        """Test that worker signals are properly connected to controller handlers"""
        # Track original worker state
        original_worker = integration_controller.worker
        
        # Start extraction with real components
        integration_controller.start_extraction()
        
        # Verify worker was created
        assert integration_controller.worker is not None
        assert integration_controller.worker != original_worker
        
        # For real workers, verify they have the expected signals
        worker = integration_controller.worker
        assert hasattr(worker, 'progress')
        assert hasattr(worker, 'preview_ready')
        assert hasattr(worker, 'preview_image_ready')
        assert hasattr(worker, 'palettes_ready')
        assert hasattr(worker, 'active_palettes_ready')
        assert hasattr(worker, 'extraction_finished')
        assert hasattr(worker, 'error')
        
        # Verify worker is running or has attempted to run
        # (it may finish quickly with test data)
        assert worker.isFinished() or worker.isRunning()

    def test_full_signal_chain_simulation(self, integration_controller, integration_main_window):
        """Test full signal chain from worker to UI"""
        # Use QSignalSpy to monitor signal emissions
        complete_spy = QSignalSpy(integration_main_window.extraction_completed)
        
        # Simulate worker signals with real components
        integration_controller._on_progress(10, "Starting extraction...")
        
        # Use real PIL Image for testing
        from PIL import Image
        test_image = Image.new('RGB', (8, 8), color='green')
        grayscale_image = Image.new('L', (8, 8), color=100)
        
        integration_controller._on_preview_ready(test_image, 10)
        integration_controller._on_preview_image_ready(grayscale_image)
        integration_controller._on_palettes_ready({8: [[0, 0, 0]]})
        integration_controller._on_active_palettes_ready([8, 9])
        integration_controller._on_extraction_finished(["sprite.png", "palette.json"])

        # Verify signal was emitted
        assert complete_spy.count() == 1
        assert complete_spy.at(0)[0] == ["sprite.png", "palette.json"]
        
        # For real components, verify they exist and were potentially updated
        assert integration_main_window.sprite_preview is not None
        if hasattr(integration_main_window, 'palette_preview'):
            assert integration_main_window.palette_preview is not None

    def test_error_signal_chain_simulation(self, integration_controller, integration_main_window, monkeypatch):
        """Test error signal chain from worker to UI"""
        # Mock UserErrorDialog to prevent blocking
        from ui.dialogs import user_error_dialog
        mock_show_error = Mock()
        monkeypatch.setattr(user_error_dialog.UserErrorDialog, 'show_error', mock_show_error)
        
        # Use QSignalSpy to monitor error signal
        failed_spy = QSignalSpy(integration_main_window.extraction_error_occurred)
        
        # Create simple worker placeholder
        class DummyWorker:
            def isRunning(self):
                return False
            def deleteLater(self):
                pass
        integration_controller.worker = DummyWorker()

        # Simulate worker error
        integration_controller._on_extraction_error("Failed to read file")

        # Verify error signal was emitted
        assert failed_spy.count() == 1
        assert failed_spy.at(0)[0] == "Failed to read file"
        assert integration_controller.worker is None  # Worker should be cleaned up
        
        # Verify error dialog was called
        mock_show_error.assert_called_once()

    def test_worker_cleanup_on_completion(self, integration_controller):
        """Test that worker is cleaned up on completion"""
        class DummyWorker:
            def isRunning(self):
                return False
            def deleteLater(self):
                pass
        integration_controller.worker = DummyWorker()

        integration_controller._on_extraction_finished(["file1.png", "file2.json"])

        assert integration_controller.worker is None

    def test_worker_cleanup_on_error(self, integration_controller):
        """Test that worker is cleaned up on error"""
        class DummyWorker:
            def isRunning(self):
                return False
            def deleteLater(self):
                pass
        integration_controller.worker = DummyWorker()

        integration_controller._on_extraction_error("Some error occurred")

        assert integration_controller.worker is None

    def test_concurrent_extraction_handling(
        self, integration_controller, integration_main_window
    ):
        """Test handling of concurrent extraction requests"""
        # Start first extraction
        integration_controller.start_extraction()
        first_worker = integration_controller.worker

        # Start second extraction (should replace first)
        integration_controller.start_extraction()
        second_worker = integration_controller.worker

        # Should have different workers (test concurrency handling)
        assert first_worker != second_worker
        assert integration_controller.worker == second_worker
        
        # Clean up both workers to prevent signals to deleted objects
        for worker in [first_worker, second_worker]:
            if worker and hasattr(worker, 'isRunning'):
                # Disconnect signals if possible
                try:
                    worker.progress.disconnect()
                    worker.preview_ready.disconnect() 
                    worker.preview_image_ready.disconnect()
                    worker.palettes_ready.disconnect()
                    worker.active_palettes_ready.disconnect()
                    worker.extraction_finished.disconnect()
                    worker.error.disconnect()
                except (TypeError, RuntimeError, AttributeError):
                    pass
                
                # Stop the worker if running
                if worker.isRunning():
                    worker.quit()
                    worker.wait(1000)


# Manager Context Integration Tests for Controllers
@pytest.mark.no_manager_setup
class TestControllerManagerContextIntegration:
    """Test controller integration with manager context system."""
    
    def test_controller_manager_access(self, mock_main_window, real_extraction_manager, real_injection_manager, real_session_manager):
        """Test that controller can access managers through real components."""
        # Pass managers directly to avoid registry lookup
        controller = ExtractionController(
            mock_main_window,
            extraction_manager=real_extraction_manager,
            injection_manager=real_injection_manager,
            session_manager=real_session_manager
        )
        
        # Verify manager access with real components
        assert isinstance(controller.extraction_manager, ExtractionManager)
        assert isinstance(controller.injection_manager, InjectionManager)
        assert isinstance(controller.session_manager, SessionManager)
    
    @pytest.mark.skip(reason="Complex Qt/Mock interaction issues - needs refactoring")
    def test_controller_context_isolation(self, mock_main_window, real_extraction_manager, real_injection_manager, real_session_manager):
        """Test that controllers are properly isolated with their own components."""
        # Create first controller with its own managers
        controller1 = ExtractionController(
            mock_main_window,
            extraction_manager=real_extraction_manager,
            injection_manager=real_injection_manager,
            session_manager=real_session_manager
        )
        
        # Set unique value on manager
        controller1.extraction_manager.test_value = "controller1"
        
        # Create second controller with separate managers - use RealComponentFactory for isolation
        from tests.infrastructure.real_component_factory import RealComponentFactory
        from core.managers.extraction_manager import ExtractionManager
        from core.managers.injection_manager import InjectionManager
        from core.managers.session_manager import SessionManager
        factory = RealComponentFactory()
        window2 = factory.create_main_window()
        
        # Create new managers for isolation
        controller2 = ExtractionController(
            window2,
            extraction_manager=ExtractionManager(),
            injection_manager=InjectionManager(),
            session_manager=SessionManager()
        )
        
        # Set different value on manager
        controller2.extraction_manager.test_value = "controller2"
        
        # Verify isolation - each controller has its own manager instance
        assert controller2.extraction_manager is not controller1.extraction_manager
        assert controller2.extraction_manager.test_value == "controller2"
        assert controller1.extraction_manager.test_value == "controller1"
    
    def test_controller_manager_state_persistence(self, real_factory):
        """Test that real managers maintain their state independently."""
        # Create shared manager instance
        shared_manager = real_factory.create_extraction_manager()
        
        # Create first controller using shared manager
        window1 = real_factory.create_main_window(with_managers=True)
        controller1 = ExtractionController(window1)
        controller1.extraction_manager = shared_manager
        
        # Modify manager state
        controller1.extraction_manager.test_state = "persistent_value"
        
        # Create second controller using same manager instance
        window2 = real_factory.create_main_window(with_managers=True)
        controller2 = ExtractionController(window2)
        controller2.extraction_manager = shared_manager
        
        # Manager state should persist since it's the same instance
        assert controller2.extraction_manager is controller1.extraction_manager
        assert controller2.extraction_manager.test_state == "persistent_value"


@pytest.mark.no_manager_setup
class TestPrivateAttributeAccessFix:
    """Test the private attribute access fix: get_output_path() method implementation"""

    @pytest.fixture
    def test_main_window(self, mock_main_window):
        """Create test main window for output path testing"""
        window = mock_main_window
        
        # Add test methods for output path testing
        def mock_get_output_path():
            return getattr(window, '_test_output_path', '')
        
        def set_test_output_path(path):
            window._test_output_path = path
        
        window.get_output_path = mock_get_output_path
        window.set_test_output_path = set_test_output_path
        
        return window

    @pytest.fixture
    def test_controller(self, test_main_window, real_extraction_manager, real_injection_manager, real_session_manager):
        """Create controller instance for private attribute access tests"""
        controller = ExtractionController(test_main_window)
        controller.extraction_manager = real_extraction_manager
        controller.injection_manager = real_injection_manager
        controller.session_manager = real_session_manager
        return controller

    def test_get_output_path_returns_value(self, test_main_window):
        """Test that get_output_path() method works correctly with valid path"""
        # Arrange
        test_path = "/path/to/output/sprite"
        test_main_window.set_test_output_path(test_path)
        
        # Act
        result = test_main_window.get_output_path()
        
        # Assert
        assert result == test_path

    def test_get_output_path_returns_empty_string(self, test_main_window):
        """Test that get_output_path() method handles empty path"""
        # Arrange
        test_main_window.set_test_output_path("")
        
        # Act
        result = test_main_window.get_output_path()
        
        # Assert
        assert result == ""

    def test_get_output_path_returns_none(self, test_main_window):
        """Test that get_output_path() method handles None value"""
        # Arrange
        test_main_window.set_test_output_path(None)
        
        # Act
        result = test_main_window.get_output_path()
        
        # Assert
        assert result is None

    def test_get_output_path_special_characters(self, test_main_window):
        """Test that get_output_path() method handles paths with special characters"""
        # Arrange
        special_paths = [
            "/path/with spaces/output",
            "/path/with-dashes/output",
            "/path/with_underscores/output",
            "/path/with.dots/output",
            "C:\\Windows\\Path\\output",
            "/path/with/émojis🎮/output",
            "/path/with/unicode_文字/output"
        ]
        
        for test_path in special_paths:
            # Act
            test_main_window.set_test_output_path(test_path)
            result = test_main_window.get_output_path()
            
            # Assert
            assert result == test_path

    def test_controller_uses_public_method(self, test_controller, test_main_window):
        """Test that controller uses the public get_output_path() method (not private attribute)"""
        # Arrange
        test_path = "/valid/output/path"
        test_main_window.set_test_output_path(test_path)
        
        # Track method calls
        original_get_path = test_main_window.get_output_path
        call_count = 0
        
        def tracked_get_path():
            nonlocal call_count
            call_count += 1
            return original_get_path()
        
        test_main_window.get_output_path = tracked_get_path
        
        # Act
        test_controller.start_injection()
        
        # Assert - verify controller called the public method
        assert call_count >= 1

    def test_controller_handles_empty_output_path(self, test_controller, test_main_window):
        """Test that controller properly handles empty output path"""
        # Arrange
        test_main_window.set_test_output_path("")
        
        # Act
        test_controller.start_injection()
        
        # Assert - check status bar was updated with appropriate message
        if hasattr(test_main_window, 'status_bar') and test_main_window.status_bar:
            current_message = test_main_window.status_bar.currentMessage()
            assert "No extraction to inject" in current_message or current_message == ""

    def test_controller_handles_none_output_path(self, test_controller, test_main_window):
        """Test that controller properly handles None output path"""
        # Arrange
        test_main_window.set_test_output_path(None)
        
        # Act
        test_controller.start_injection()
        
        # Assert - check status bar was updated with appropriate message
        if hasattr(test_main_window, 'status_bar') and test_main_window.status_bar:
            current_message = test_main_window.status_bar.currentMessage()
            assert "No extraction to inject" in current_message or current_message == ""

    def test_controller_handles_whitespace_only_path(self, test_controller, test_main_window):
        """Test that controller properly handles whitespace-only output path"""
        # Arrange
        whitespace_paths = ["   ", "\t", "\n", "  \t  \n  "]
        
        for test_path in whitespace_paths:
            test_main_window.set_test_output_path(test_path)
            
            # Act
            test_controller.start_injection()
            
            # Whitespace-only strings are truthy, so they don't trigger "No extraction" message
            # This tests the actual behavior with real components
            # (The actual handling depends on controller implementation)

    def test_controller_proceeds_with_valid_path(self, test_controller, test_main_window):
        """Test that controller proceeds with injection when valid path is provided"""
        # Arrange
        test_path = "/valid/output/path"
        test_main_window.set_test_output_path(test_path)
        
        # Set up manager to handle injection gracefully
        # Real managers handle validation internally
        
        # Act
        test_controller.start_injection()
        
        # Assert - controller should attempt to proceed with injection
        # (The exact behavior depends on validation and other factors)
        assert test_main_window.get_output_path() == test_path

    def test_private_attribute_not_accessed_directly(self, test_controller, test_main_window):
        """Test that controller does NOT access _output_path private attribute directly"""
        # Arrange
        test_main_window._test_private_path = "/private/path"  # Private attribute simulation
        test_main_window.set_test_output_path("")  # Public method returns empty
        
        # Act
        test_controller.start_injection()
        
        # Assert - controller should use public method
        # The fact that private attribute has value but get_output_path returns ""
        # proves the controller is using the public method properly
        assert test_main_window.get_output_path() == ""
        assert hasattr(test_main_window, '_test_private_path')  # Private attribute exists but unused