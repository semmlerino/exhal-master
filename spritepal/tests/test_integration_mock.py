"""
Mock-based integration tests that work in any environment.
These tests mock Qt components to test business logic without requiring a display.

MODERNIZED: Uses consolidated mock infrastructure from conftest.py
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import business logic components - no more manual path setup needed
from core.controller import ExtractionController
from core.extractor import SpriteExtractor
from core.palette_manager import PaletteManager

# Systematic pytest markers applied based on test content analysis
pytestmark = [
    pytest.mark.file_io,
    pytest.mark.headless,
    pytest.mark.integration,
    pytest.mark.mock_only,
    pytest.mark.no_qt,
    pytest.mark.parallel_safe,
    pytest.mark.rom_data,
    pytest.mark.ci_safe,
    pytest.mark.signals_slots,
]

@pytest.mark.mock
class TestVRAMExtractionWorkerMocked:
    """Test VRAMExtractionWorker with mocked Qt components using modern fixtures."""

    def test_worker_with_mocked_qt(
        self, standard_test_params, mock_extraction_worker
    ):
        """Test worker functionality with mocked Qt components"""

        # Manager setup handled by centralized fixture
        try:
            # Use the pre-configured mock worker from fixtures
            worker = mock_extraction_worker

            # Update worker with test parameters
            worker.params = standard_test_params

            # Track emitted data
            progress_messages = []
            preview_data = []
            finished_files = []

            # Connect handlers
            worker.progress.connect(lambda percent, msg: progress_messages.append(msg))
            worker.preview_ready.connect(lambda pm, tc: preview_data.append((pm, tc)))
            worker.extraction_finished.connect(lambda files: finished_files.extend(files))

            # Run the worker directly (not as thread)
            worker.run()

            # Verify files were created
            assert worker.extraction_finished.emit.called
            call_args = worker.extraction_finished.emit.call_args[0][0]
            assert len(call_args) >= 1
            assert any(f.endswith(".png") for f in call_args)

            # If CGRAM was provided, should have palette files too
            if standard_test_params.get("cgram_path"):
                assert any(f.endswith(".pal.json") for f in call_args)

        except Exception as e:
            # Add error context for debugging
            pytest.fail(f"Test failed: {e}")
        # Manager cleanup handled by centralized fixture

    @patch("utils.image_utils.QPixmap")
    def test_pixmap_creation_mocked(self, mock_qpixmap):
        """Test pixmap creation with mocked QPixmap"""
        from PIL import Image

        # Create test image
        test_image = Image.new("P", (128, 128), 0)

        # Mock QPixmap
        mock_pixmap_instance = Mock()
        mock_pixmap_instance.loadFromData = Mock(return_value=True)
        mock_qpixmap.return_value = mock_pixmap_instance

        # Import and test the pil_to_qpixmap function
        from core.controller import pil_to_qpixmap

        # Test pixmap creation
        result = pil_to_qpixmap(test_image)

        # Verify
        assert result == mock_pixmap_instance
        assert mock_pixmap_instance.loadFromData.called

        # Check that PNG data was passed
        call_args = mock_pixmap_instance.loadFromData.call_args[0][0]
        assert isinstance(call_args, bytes)
        assert len(call_args) > 0  # Should have PNG data

class TestControllerMocked:
    """Test ExtractionController with mocked components"""

    @patch("core.controller.QObject")
    @patch("core.controller.VRAMExtractionWorker")
    def test_controller_workflow(
        self, mock_worker_class, mock_qobject,
        mock_main_window_configured, standard_test_params
    ):
        """Test controller workflow with mocks"""
        # Use centralized mock main window, update its extraction params
        mock_main_window_configured.get_extraction_params.return_value = standard_test_params

        # Create mock worker
        mock_worker = Mock()
        mock_worker_class.return_value = mock_worker

        # Create controller with centralized mock main window
        controller = ExtractionController(mock_main_window_configured)

        # Mock validation to allow worker creation with fake file paths
        with patch.object(controller.extraction_manager, "validate_extraction_params"):
            # Start extraction
            controller.start_extraction()

        # Verify worker was created and started
        assert mock_worker_class.called
        assert mock_worker.start.called

        # Verify signals were connected
        assert mock_worker.progress.connect.called
        assert mock_worker.preview_ready.connect.called
        assert mock_worker.palettes_ready.connect.called
        assert mock_worker.extraction_finished.connect.called
        assert mock_worker.error.connect.called

class TestBusinessLogicOnly:
    """Test pure business logic without Qt dependencies"""

    def test_extraction_workflow_no_qt(self, standard_test_params):
        """Test the extraction workflow without any Qt components"""
        # Use centralized test data and file paths

        # Test extraction using centralized test files
        extractor = SpriteExtractor()
        output_png = standard_test_params["output_base"] + ".png"
        img, num_tiles = extractor.extract_sprites_grayscale(
            standard_test_params["vram_path"], output_png
        )

        assert Path(output_png).exists()
        assert num_tiles > 0

        # Test palette extraction using centralized test files
        palette_manager = PaletteManager()
        palette_manager.load_cgram(standard_test_params["cgram_path"])

        palettes = palette_manager.get_sprite_palettes()
        assert len(palettes) == 8  # Palettes 8-15

        # Test palette file creation
        pal_file = standard_test_params["output_base"] + ".pal.json"
        palette_manager.create_palette_json(8, pal_file, output_png)
        assert Path(pal_file).exists()