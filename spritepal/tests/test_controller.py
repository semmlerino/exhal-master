"""
Comprehensive tests for controller functionality
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spritepal.core.controller import ExtractionController, ExtractionWorker


class TestControllerImports:
    """Test that controller module imports work correctly"""
    
    def test_controller_imports(self):
        """Test that all imports in controller module work without errors"""
        # This test will catch import-time errors like missing pil_to_qpixmap
        try:
            import spritepal.core.controller
            # Force module reload to catch any import errors
            import importlib
            importlib.reload(spritepal.core.controller)
        except ImportError as e:
            pytest.fail(f"Import error in controller module: {e}")
        except NameError as e:
            pytest.fail(f"Name error in controller module: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error importing controller module: {e}")
    
    def test_pil_to_qpixmap_import(self):
        """Test that pil_to_qpixmap function is available"""
        from spritepal.core.controller import ExtractionWorker
        
        # Create a worker instance to test the method
        worker_params = {
            "vram_path": "/path/to/vram.dmp",
            "cgram_path": "/path/to/cgram.dmp", 
            "output_base": "/path/to/output",
            "create_grayscale": True,
            "create_metadata": True,
        }
        
        with (
            patch("spritepal.core.controller.SpriteExtractor"),
            patch("spritepal.core.controller.PaletteManager"),
        ):
            worker = ExtractionWorker(worker_params)
            
            # Test that the method exists and can be called
            assert hasattr(worker, '_create_pixmap_from_image')
            
            # Test with a mock image - this should not raise NameError
            mock_image = Mock()
            mock_image.save = Mock()
            
            with patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap:
                mock_pil_to_qpixmap.return_value = Mock()
                result = worker._create_pixmap_from_image(mock_image)
                mock_pil_to_qpixmap.assert_called_once_with(mock_image)


class TestExtractionController:
    """Test ExtractionController functionality"""

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
        return window

    @pytest.fixture
    def controller(self, mock_main_window):
        """Create controller instance"""
        return ExtractionController(mock_main_window)

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
            "VRAM and CGRAM files are required"
        )

    def test_parameter_validation_missing_cgram(self, controller, mock_main_window):
        """Test parameter validation when CGRAM path is missing"""
        mock_main_window.get_extraction_params.return_value = {
            "vram_path": "/path/to/vram.dmp",
            "cgram_path": "",
            "output_base": "/path/to/output",
        }

        controller.start_extraction()

        mock_main_window.extraction_failed.assert_called_once_with(
            "VRAM and CGRAM files are required"
        )

    def test_parameter_validation_missing_both(self, controller, mock_main_window):
        """Test parameter validation when both paths are missing"""
        mock_main_window.get_extraction_params.return_value = {
            "vram_path": None,
            "cgram_path": None,
            "output_base": "/path/to/output",
        }

        controller.start_extraction()

        mock_main_window.extraction_failed.assert_called_once_with(
            "VRAM and CGRAM files are required"
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
    @patch("spritepal.core.controller.os.path.exists")
    def test_open_in_editor_launcher_found(
        self, mock_exists, mock_popen, mock_validate, controller, mock_main_window
    ):
        """Test opening in editor when launcher is found"""
        # Mock validation to pass
        mock_validate.return_value = (True, "")
        
        # Mock exists to return True for the first launcher path
        mock_exists.side_effect = lambda path: path.endswith("launch_pixel_editor.py")
        sprite_file = "/path/to/sprite.png"

        controller.open_in_editor(sprite_file)

        # Verify Popen was called with the correct arguments
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == sys.executable
        assert call_args[1].endswith("launch_pixel_editor.py")
        assert call_args[2] == os.path.abspath(sprite_file)
        
        mock_main_window.status_bar.showMessage.assert_called_once_with(
            f"Opened {os.path.basename(sprite_file)} in pixel editor"
        )

    @patch("spritepal.core.controller.validate_image_file")
    @patch("spritepal.core.controller.subprocess.Popen")
    @patch("spritepal.core.controller.os.path.exists")
    def test_open_in_editor_launcher_in_subdirectory(
        self, mock_exists, mock_popen, mock_validate, controller, mock_main_window
    ):
        """Test opening in editor when launcher is in subdirectory"""
        # Mock validation to pass
        mock_validate.return_value = (True, "")
        
        # Mock exists to return True for the second launcher path (in subdirectory)
        mock_exists.side_effect = lambda path: "pixel_editor/launch_pixel_editor.py" in path
        sprite_file = "/path/to/sprite.png"

        controller.open_in_editor(sprite_file)

        # Verify Popen was called with the correct arguments
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == sys.executable
        assert call_args[1].endswith("pixel_editor/launch_pixel_editor.py")
        assert call_args[2] == os.path.abspath(sprite_file)

    @patch("spritepal.core.controller.validate_image_file")
    @patch("spritepal.core.controller.subprocess.Popen")
    @patch("spritepal.core.controller.os.path.exists")
    def test_open_in_editor_launcher_in_parent_directory(
        self, mock_exists, mock_popen, mock_validate, controller, mock_main_window
    ):
        """Test opening in editor when launcher is in parent directory"""
        # Mock validation to pass
        mock_validate.return_value = (True, "")
        
        # Mock exists to return True for the third launcher path (in parent directory)
        mock_exists.side_effect = lambda path: path.endswith("launch_pixel_editor.py") and "exhal-master" in path
        sprite_file = "/path/to/sprite.png"

        controller.open_in_editor(sprite_file)

        # Verify Popen was called with the correct arguments
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == sys.executable
        assert call_args[1].endswith("launch_pixel_editor.py")
        assert call_args[2] == os.path.abspath(sprite_file)

    @patch("spritepal.core.controller.os.path.exists")
    def test_open_in_editor_launcher_not_found(
        self, mock_exists, controller, mock_main_window
    ):
        """Test opening in editor when launcher is not found"""
        mock_exists.return_value = False
        sprite_file = "/path/to/sprite.png"

        controller.open_in_editor(sprite_file)

        mock_main_window.status_bar.showMessage.assert_called_once_with(
            "Pixel editor not found"
        )

    @patch("spritepal.core.controller.subprocess.Popen")
    @patch("spritepal.core.controller.os.path.exists")
    def test_open_in_editor_subprocess_error(
        self, mock_exists, mock_popen, controller, mock_main_window
    ):
        """Test opening in editor when subprocess fails"""
        mock_exists.return_value = True
        mock_popen.side_effect = Exception("Subprocess failed")
        sprite_file = "/path/to/sprite.png"

        # Should not raise exception and should show error message
        controller.open_in_editor(sprite_file)

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
        with (
            patch("spritepal.core.controller.SpriteExtractor"),
            patch("spritepal.core.controller.PaletteManager"),
        ):
            return ExtractionWorker(worker_params)

    def test_init_creates_components(self, worker, worker_params):
        """Test worker initialization creates extractor and palette manager"""
        assert worker.params == worker_params
        assert worker.extractor is not None
        assert worker.palette_manager is not None

    def test_create_pixmap_from_image_valid_pil(self, worker):
        """Test creating pixmap from valid PIL image"""
        test_image = Image.new("RGB", (32, 32), "red")

        with patch("spritepal.utils.image_utils.QPixmap") as mock_pixmap:
            mock_pixmap_instance = Mock()
            mock_pixmap_instance.loadFromData.return_value = True
            mock_pixmap.return_value = mock_pixmap_instance

            result = worker._create_pixmap_from_image(test_image)

            assert result == mock_pixmap_instance
            mock_pixmap_instance.loadFromData.assert_called_once()

    def test_create_pixmap_from_image_invalid_format(self, worker):
        """Test creating pixmap from invalid image format"""
        # Create an image that can't be saved as PNG
        test_image = Mock()
        test_image.save.side_effect = OSError("Cannot save image")

        # The function should handle the error gracefully and return None
        result = worker._create_pixmap_from_image(test_image)
        assert result is None

    @patch("spritepal.utils.image_utils.QPixmap")
    def test_run_full_workflow_success(self, mock_pixmap, worker):
        """Test successful full workflow execution"""
        # Mock image and pixmap
        mock_image = Mock()
        mock_pixmap_instance = Mock()
        mock_pixmap.return_value = mock_pixmap_instance

        # Mock extractor
        worker.extractor.extract_sprites_grayscale.return_value = (mock_image, 10)

        # Mock palette manager
        worker.palette_manager.load_cgram = Mock()
        worker.palette_manager.get_sprite_palettes.return_value = {8: [[0, 0, 0]]}
        worker.palette_manager.create_palette_json = Mock()
        worker.palette_manager.create_metadata_json.return_value = "metadata.json"
        worker.palette_manager.analyze_oam_palettes.return_value = [8, 9]

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

        # Verify all signals were emitted
        assert worker.progress.emit.call_count >= 4
        worker.preview_ready.emit.assert_called_once()
        worker.preview_image_ready.emit.assert_called_once()
        worker.palettes_ready.emit.assert_called_once()
        worker.active_palettes_ready.emit.assert_called_once()
        worker.finished.emit.assert_called_once()
        worker.error.emit.assert_not_called()

    def test_run_error_handling(self, worker):
        """Test error handling in worker"""
        # Mock extractor to raise exception
        worker.extractor.extract_sprites_grayscale.side_effect = Exception("Test error")

        # Mock signals
        worker.progress = Mock()
        worker.error = Mock()
        worker.finished = Mock()

        # Run worker
        worker.run()

        # Verify error was emitted
        worker.error.emit.assert_called_once_with("Test error")
        worker.finished.emit.assert_not_called()

    def test_run_without_cgram(self, worker):
        """Test running without CGRAM file"""
        worker.params["cgram_path"] = None

        # Mock extractor
        mock_image = Mock()
        worker.extractor.extract_sprites_grayscale.return_value = (mock_image, 10)

        # Mock signals
        worker.progress = Mock()
        worker.preview_ready = Mock()
        worker.preview_image_ready = Mock()
        worker.palettes_ready = Mock()
        worker.finished = Mock()
        worker.error = Mock()

        with patch("spritepal.utils.image_utils.QPixmap"):
            worker.run()

        # Should not call palette-related methods
        worker.palettes_ready.emit.assert_not_called()
        worker.finished.emit.assert_called_once()
        worker.error.emit.assert_not_called()

    def test_run_without_oam(self, worker):
        """Test running without OAM file"""
        worker.params["oam_path"] = None

        # Mock extractor
        mock_image = Mock()
        worker.extractor.extract_sprites_grayscale.return_value = (mock_image, 10)

        # Mock palette manager
        worker.palette_manager.load_cgram = Mock()
        worker.palette_manager.get_sprite_palettes.return_value = {8: [[0, 0, 0]]}
        worker.palette_manager.create_palette_json = Mock()
        worker.palette_manager.create_metadata_json.return_value = "metadata.json"

        # Mock signals
        worker.progress = Mock()
        worker.preview_ready = Mock()
        worker.preview_image_ready = Mock()
        worker.palettes_ready = Mock()
        worker.active_palettes_ready = Mock()
        worker.finished = Mock()
        worker.error = Mock()

        with patch("spritepal.utils.image_utils.QPixmap"):
            worker.run()

        # Should not call OAM analysis
        worker.active_palettes_ready.emit.assert_not_called()
        worker.finished.emit.assert_called_once()
        worker.error.emit.assert_not_called()

    def test_run_without_metadata_creation(self, worker):
        """Test running without metadata creation"""
        worker.params["create_metadata"] = False

        # Mock extractor
        mock_image = Mock()
        worker.extractor.extract_sprites_grayscale.return_value = (mock_image, 10)

        # Mock palette manager
        worker.palette_manager.load_cgram = Mock()
        worker.palette_manager.get_sprite_palettes.return_value = {8: [[0, 0, 0]]}
        worker.palette_manager.create_palette_json = Mock()
        worker.palette_manager.create_metadata_json = Mock()

        # Mock signals
        worker.progress = Mock()
        worker.preview_ready = Mock()
        worker.preview_image_ready = Mock()
        worker.palettes_ready = Mock()
        worker.finished = Mock()
        worker.error = Mock()

        with patch("spritepal.utils.image_utils.QPixmap"):
            worker.run()

        # Should not call metadata creation
        worker.palette_manager.create_metadata_json.assert_not_called()
        worker.finished.emit.assert_called_once()
        worker.error.emit.assert_not_called()

    def test_run_without_grayscale_creation(self, worker):
        """Test running without grayscale palette creation"""
        worker.params["create_grayscale"] = False

        # Mock extractor
        mock_image = Mock()
        worker.extractor.extract_sprites_grayscale.return_value = (mock_image, 10)

        # Mock palette manager
        worker.palette_manager.load_cgram = Mock()
        worker.palette_manager.get_sprite_palettes.return_value = {8: [[0, 0, 0]]}
        worker.palette_manager.create_palette_json = Mock()

        # Mock signals
        worker.progress = Mock()
        worker.preview_ready = Mock()
        worker.preview_image_ready = Mock()
        worker.palettes_ready = Mock()
        worker.finished = Mock()
        worker.error = Mock()

        with patch("spritepal.utils.image_utils.QPixmap"):
            worker.run()

        # Should not call palette file creation
        worker.palette_manager.create_palette_json.assert_not_called()
        worker.finished.emit.assert_called_once()
        worker.error.emit.assert_not_called()

    def test_signal_emission_order(self, worker):
        """Test that signals are emitted in correct order"""
        # Mock extractor
        mock_image = Mock()
        worker.extractor.extract_sprites_grayscale.return_value = (mock_image, 10)

        # Mock palette manager
        worker.palette_manager.load_cgram = Mock()
        worker.palette_manager.get_sprite_palettes.return_value = {8: [[0, 0, 0]]}
        worker.palette_manager.create_palette_json = Mock()
        worker.palette_manager.create_metadata_json.return_value = "metadata.json"
        worker.palette_manager.analyze_oam_palettes.return_value = [8, 9]

        # Track signal emission order
        signal_order = []

        def track_signal(signal_name):
            def emit_tracker(*args):
                signal_order.append(signal_name)

            return emit_tracker

        worker.progress = Mock()
        worker.progress.emit = track_signal("progress")
        worker.preview_ready = Mock()
        worker.preview_ready.emit = track_signal("preview_ready")
        worker.preview_image_ready = Mock()
        worker.preview_image_ready.emit = track_signal("preview_image_ready")
        worker.palettes_ready = Mock()
        worker.palettes_ready.emit = track_signal("palettes_ready")
        worker.active_palettes_ready = Mock()
        worker.active_palettes_ready.emit = track_signal("active_palettes_ready")
        worker.finished = Mock()
        worker.finished.emit = track_signal("finished")

        with patch("spritepal.utils.image_utils.QPixmap"):
            worker.run()

        # Verify signals were emitted in logical order
        assert "preview_ready" in signal_order
        assert "preview_image_ready" in signal_order
        assert "palettes_ready" in signal_order
        assert "active_palettes_ready" in signal_order
        assert "finished" in signal_order
        assert signal_order.index("preview_ready") < signal_order.index(
            "palettes_ready"
        )
        assert signal_order.index("palettes_ready") < signal_order.index("finished")


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
        return ExtractionController(mock_main_window)

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
