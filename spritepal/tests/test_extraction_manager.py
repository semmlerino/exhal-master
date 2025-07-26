"""
Tests for ExtractionManager
"""

import os
from unittest.mock import patch

import pytest
from PIL import Image

from spritepal.core.managers import ExtractionError, ExtractionManager, ValidationError
from spritepal.utils.constants import BYTES_PER_TILE


class TestExtractionManager:
    """Test ExtractionManager functionality"""

    @pytest.fixture
    def extraction_manager(self):
        """Create ExtractionManager instance"""
        return ExtractionManager()

    @pytest.fixture
    def temp_files(self, tmp_path):
        """Create temporary test files"""
        # Create test VRAM file
        vram_file = tmp_path / "test.vram"
        vram_data = b"\x00" * 0x10000  # 64KB
        vram_file.write_bytes(vram_data)

        # Create test CGRAM file
        cgram_file = tmp_path / "test.cgram"
        cgram_data = b"\x00" * 512  # 512 bytes
        cgram_file.write_bytes(cgram_data)

        # Create test OAM file
        oam_file = tmp_path / "test.oam"
        oam_data = b"\x00" * 544  # 544 bytes
        oam_file.write_bytes(oam_data)

        # Create test ROM file
        rom_file = tmp_path / "test.sfc"
        rom_data = b"\x00" * 0x400000  # 4MB
        rom_file.write_bytes(rom_data)

        return {
            "vram": str(vram_file),
            "cgram": str(cgram_file),
            "oam": str(oam_file),
            "rom": str(rom_file),
            "output_dir": str(tmp_path)
        }

    def test_initialization(self, extraction_manager):
        """Test ExtractionManager initialization"""
        assert extraction_manager.is_initialized()
        assert extraction_manager.get_name() == "ExtractionManager"
        assert extraction_manager._sprite_extractor is not None
        assert extraction_manager._rom_extractor is not None
        assert extraction_manager._palette_manager is not None

    def test_validate_extraction_params_vram(self, extraction_manager, temp_files):
        """Test VRAM extraction parameter validation"""
        # Valid params
        params = {
            "vram_path": temp_files["vram"],
            "output_base": os.path.join(temp_files["output_dir"], "test"),
            "cgram_path": temp_files["cgram"],
            "oam_path": temp_files["oam"]
        }
        extraction_manager.validate_extraction_params(params)

        # Missing required param
        invalid_params = params.copy()
        del invalid_params["output_base"]
        with pytest.raises(ValidationError, match="Missing required parameters"):
            extraction_manager.validate_extraction_params(invalid_params)

        # Non-existent file
        invalid_params = params.copy()
        invalid_params["vram_path"] = "/non/existent/file.vram"
        with pytest.raises(ValidationError, match="VRAM file does not exist"):
            extraction_manager.validate_extraction_params(invalid_params)

    def test_validate_extraction_params_rom(self, extraction_manager, temp_files):
        """Test ROM extraction parameter validation"""
        # Valid params
        params = {
            "rom_path": temp_files["rom"],
            "offset": 0x1000,
            "output_base": os.path.join(temp_files["output_dir"], "test")
        }
        extraction_manager.validate_extraction_params(params)

        # Invalid offset type
        invalid_params = params.copy()
        invalid_params["offset"] = "not_an_int"
        with pytest.raises(ValidationError, match="Invalid type for 'offset'"):
            extraction_manager.validate_extraction_params(invalid_params)

        # Negative offset
        invalid_params = params.copy()
        invalid_params["offset"] = -1
        with pytest.raises(ValidationError, match="offset must be >= 0"):
            extraction_manager.validate_extraction_params(invalid_params)

    @patch("spritepal.core.extractor.SpriteExtractor.extract_sprites_grayscale")
    def test_extract_from_vram_basic(self, mock_extract, extraction_manager, temp_files):
        """Test basic VRAM extraction"""
        # Mock the extraction
        test_img = Image.new("L", (128, 128))
        mock_extract.return_value = (test_img, 256)  # 256 tiles

        output_base = os.path.join(temp_files["output_dir"], "test")

        # Run extraction
        files = extraction_manager.extract_from_vram(
            temp_files["vram"],
            output_base,
            grayscale_mode=True  # Skip palette extraction for this test
        )

        # Verify
        assert len(files) == 1
        assert files[0] == f"{output_base}.png"
        mock_extract.assert_called_once()

    def test_extract_from_vram_validation_error(self, extraction_manager):
        """Test VRAM extraction with validation error"""
        with pytest.raises(ValidationError):
            extraction_manager.extract_from_vram(
                "/non/existent/file.vram",
                "/output/test"
            )

    def test_extract_from_vram_already_running(self, extraction_manager, temp_files):
        """Test preventing concurrent VRAM extractions"""
        output_base = os.path.join(temp_files["output_dir"], "test")

        # Start an extraction
        extraction_manager._start_operation("vram_extraction")

        # Try to start another
        with pytest.raises(ExtractionError, match="already in progress"):
            extraction_manager.extract_from_vram(
                temp_files["vram"],
                output_base
            )

        # Clean up
        extraction_manager._finish_operation("vram_extraction")

    @patch("spritepal.core.rom_extractor.ROMExtractor.extract_sprite_from_rom")
    def test_extract_from_rom_basic(self, mock_extract, extraction_manager, temp_files):
        """Test basic ROM extraction"""
        # Mock successful extraction
        mock_extract.return_value = True

        output_base = os.path.join(temp_files["output_dir"], "test")

        # Create a dummy PNG file that would be created by extract_sprite
        output_png = f"{output_base}.png"
        Image.new("L", (128, 128)).save(output_png)

        # Run extraction
        files = extraction_manager.extract_from_rom(
            temp_files["rom"],
            0x1000,
            output_base,
            "test_sprite"
        )

        # Verify
        assert len(files) >= 1
        assert files[0] == output_png
        mock_extract.assert_called_once()

    def test_extract_from_rom_validation_error(self, extraction_manager):
        """Test ROM extraction with validation error"""
        with pytest.raises(ValidationError):
            extraction_manager.extract_from_rom(
                "/non/existent/rom.sfc",
                0x1000,
                "/output/test",
                "sprite"
            )

    def test_get_sprite_preview(self, extraction_manager, temp_files):
        """Test sprite preview generation"""
        # Get preview
        tile_data, width, height = extraction_manager.get_sprite_preview(
            temp_files["rom"],
            0x1000,
            "test_sprite"
        )

        # Verify
        assert isinstance(tile_data, bytes)
        assert width == 128
        assert height == 128
        assert len(tile_data) == (width * height // 64) * BYTES_PER_TILE

    def test_get_sprite_preview_validation_error(self, extraction_manager):
        """Test sprite preview with validation error"""
        with pytest.raises(ValidationError):
            extraction_manager.get_sprite_preview(
                "/non/existent/rom.sfc",
                0x1000
            )

    def test_concurrent_operations(self, extraction_manager):
        """Test operation tracking for different operation types"""
        # Can run different operations concurrently
        assert extraction_manager._start_operation("vram_extraction")
        assert extraction_manager._start_operation("rom_extraction")
        assert extraction_manager._start_operation("sprite_preview")

        # Check all are active
        assert extraction_manager.is_operation_active("vram_extraction")
        assert extraction_manager.is_operation_active("rom_extraction")
        assert extraction_manager.is_operation_active("sprite_preview")

        # Clean up
        extraction_manager._finish_operation("vram_extraction")
        extraction_manager._finish_operation("rom_extraction")
        extraction_manager._finish_operation("sprite_preview")

    def test_signal_emissions(self, extraction_manager, qtbot):
        """Test signal emissions during extraction"""
        # Mock the extractor
        with patch.object(extraction_manager._sprite_extractor, "extract_sprites_grayscale") as mock_extract:
            test_img = Image.new("L", (128, 128))
            mock_extract.return_value = (test_img, 256)

            # Create temp files
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                vram_file = os.path.join(temp_dir, "test.vram")
                with open(vram_file, "wb") as f:
                    f.write(b"\x00" * 0x10000)

                output_base = os.path.join(temp_dir, "test")

                # Track signals
                progress_messages = []

                def on_progress(msg):
                    progress_messages.append(msg)

                extraction_manager.extraction_progress.connect(on_progress)

                # Run extraction
                with qtbot.waitSignal(extraction_manager.files_created):
                    extraction_manager.extract_from_vram(
                        vram_file,
                        output_base,
                        grayscale_mode=True
                    )

                # Verify progress messages
                assert any("Extracting sprites from VRAM" in msg for msg in progress_messages)
                assert any("complete" in msg for msg in progress_messages)

    def test_cleanup(self, extraction_manager):
        """Test cleanup does nothing (no resources to clean)"""
        extraction_manager.cleanup()  # Should not raise
