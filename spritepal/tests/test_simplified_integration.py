"""
Simplified integration tests using minimal mocking approach
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
from tests.fixtures.test_worker_helper import TestExtractionController

from spritepal.core.managers import cleanup_managers, initialize_managers
from spritepal.utils.constants import (
    BYTES_PER_TILE,
    COLORS_PER_PALETTE,
    SPRITE_PALETTE_END,
    SPRITE_PALETTE_START,
    VRAM_SPRITE_OFFSET,
)


class TestSimplifiedIntegration:
    """Integration tests with minimal mocking"""

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
        yield helper
        helper.cleanup()

    @pytest.mark.integration
    def test_simplified_extraction_workflow(self, sample_files, mock_main_window):
        """Test extraction workflow with minimal mocking"""
        # Initialize managers
        initialize_managers("TestApp")

        try:
            # Set up extraction parameters
            output_base = str(Path(sample_files["temp_dir"]) / "simplified_test")
            extraction_params = {
                "vram_path": sample_files["vram_path"],
                "cgram_path": sample_files["cgram_path"],
                "output_base": output_base,
                "create_grayscale": True,
                "create_metadata": True,
                "oam_path": sample_files["oam_path"],
            }
            mock_main_window.set_extraction_params(extraction_params)

            # Only mock Qt graphics components (necessary for headless testing)
            mock_pixmap_instance = Mock()
            mock_pixmap_instance.loadFromData = Mock(return_value=True)

            with (
                patch("spritepal.utils.image_utils.QPixmap") as mock_qpixmap_utils,
                patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap,
            ):
                # Configure only essential mocks
                mock_qpixmap_utils.return_value = mock_pixmap_instance
                mock_pil_to_qpixmap.return_value = mock_pixmap_instance

                # Use TestExtractionController (no QThread mocking needed!)
                controller = TestExtractionController(mock_main_window)

                # Start extraction workflow - runs synchronously
                controller.start_extraction()

            # Verify extraction completed
            workflow_signals = mock_main_window.get_signal_emissions()

            # Verify status messages (real extraction logic)
            assert len(workflow_signals["status_messages"]) >= 3
            assert "Extracting sprites from VRAM..." in workflow_signals["status_messages"]
            assert "Extraction complete!" in workflow_signals["status_messages"]

            # Verify real file output
            assert len(workflow_signals["extraction_complete"]) == 1
            output_files = workflow_signals["extraction_complete"][0]

            # Check actual files exist and have content
            png_file = next(f for f in output_files if f.endswith(".png"))
            pal_file = next(f for f in output_files if f.endswith(".pal.json"))
            metadata_file = next(f for f in output_files if f.endswith(".metadata.json"))

            assert Path(png_file).exists()
            assert Path(pal_file).exists()
            assert Path(metadata_file).exists()

            # Verify file contents (real extraction results)
            assert Path(png_file).stat().st_size > 0
            assert Path(pal_file).stat().st_size > 0
            assert Path(metadata_file).stat().st_size > 0

        finally:
            cleanup_managers()

    @pytest.mark.integration
    def test_real_image_processing(self, sample_files, mock_main_window):
        """Test with real PIL image processing, minimal Qt mocking"""
        initialize_managers("TestApp")

        try:
            # Test with only VRAM file (simpler scenario)
            output_base = str(Path(sample_files["temp_dir"]) / "real_image_test")
            extraction_params = {
                "vram_path": sample_files["vram_path"],
                "cgram_path": sample_files["cgram_path"],
                "output_base": output_base,
                "create_grayscale": True,
                "create_metadata": False,  # Simpler test
                "oam_path": None,
            }
            mock_main_window.set_extraction_params(extraction_params)

            # Create test worker directly (even less mocking)
            from tests.fixtures.test_worker_helper import TestExtractionWorker

            # Only mock final Qt conversion
            mock_pixmap_instance = Mock()
            with patch("spritepal.core.controller.pil_to_qpixmap") as mock_pil_to_qpixmap:
                mock_pil_to_qpixmap.return_value = mock_pixmap_instance

                # Create worker and run directly
                worker = TestExtractionWorker(extraction_params)

                # Connect to capture real signals
                progress_messages = []
                preview_images = []
                palette_data = []

                worker.progress.connect(lambda msg: progress_messages.append(msg))
                worker.preview_image_ready.connect(lambda img: preview_images.append(img))
                worker.palettes_ready.connect(lambda pal: palette_data.append(pal))

                # Run worker
                worker.run()

            # Verify real PIL image processing occurred
            assert len(progress_messages) >= 3
            assert "Extracting sprites from VRAM..." in progress_messages

            # Check that real PIL Images were generated
            assert len(preview_images) == 1
            pil_image = preview_images[0]

            # Verify it's a real PIL Image with expected properties
            from PIL import Image
            assert isinstance(pil_image, Image.Image)
            assert pil_image.size[0] > 0  # Has width
            assert pil_image.size[1] > 0  # Has height
            assert pil_image.mode in ["L", "P", "RGB", "RGBA"]  # Valid PIL mode

            # Check palette data is real
            assert len(palette_data) == 1
            palettes = palette_data[0]
            assert isinstance(palettes, dict)
            # Should have sprite palettes (indices 8-15)
            sprite_palette_keys = [k for k in palettes if isinstance(k, int) and 8 <= k <= 15]
            assert len(sprite_palette_keys) > 0

        finally:
            cleanup_managers()
