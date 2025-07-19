"""Tests for sprite injector functionality"""

import json
from unittest.mock import MagicMock

import pytest
from PIL import Image

from spritepal.core.injector import InjectionWorker, SpriteInjector, encode_4bpp_tile


# Module-level fixtures for shared use
@pytest.fixture
def temp_sprite_image(tmp_path):
    """Create a temporary 16x16 indexed color sprite"""
    img = Image.new("P", (16, 16))

    # Create a simple pattern
    pixels = []
    for y in range(16):
        for x in range(16):
            pixels.append((x + y) % 16)

    img.putdata(pixels)

    # Set a 16-color palette
    palette = []
    for i in range(16):
        palette.extend([i * 16, i * 16, i * 16])  # Grayscale
    palette.extend([0, 0, 0] * (256 - 16))  # Fill rest with black
    img.putpalette(palette)

    sprite_path = tmp_path / "test_sprite.png"
    img.save(sprite_path)
    return sprite_path


@pytest.fixture
def temp_vram(tmp_path):
    """Create a temporary VRAM file"""
    vram_data = bytearray(65536)  # 64KB
    vram_path = tmp_path / "test.vram"
    with open(vram_path, "wb") as f:
        f.write(vram_data)
    return vram_path


@pytest.fixture
def temp_metadata(tmp_path):
    """Create a temporary metadata file"""
    metadata = {
        "extraction": {
            "vram_offset": "0xC000",
            "tile_count": 100,
            "tiles_per_row": 16
        },
        "palettes": {
            "sprite_palettes": list(range(8, 16))
        }
    }
    metadata_path = tmp_path / "test.metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f)
    return metadata_path


class TestEncode4bppTile:
    """Test the 4bpp tile encoding function"""

    def test_encode_simple_tile(self):
        """Test encoding a simple 8x8 tile with known pattern"""
        # Create a tile with a diagonal pattern (0-15)
        tile_pixels = []
        for y in range(8):
            for x in range(8):
                tile_pixels.append((x + y) & 0x0F)

        # Encode the tile
        encoded = encode_4bpp_tile(tile_pixels)

        # Verify output length
        assert len(encoded) == 32
        assert isinstance(encoded, bytes)

    def test_encode_solid_color_tile(self):
        """Test encoding a solid color tile"""
        # All pixels color 5
        tile_pixels = [5] * 64
        encoded = encode_4bpp_tile(tile_pixels)

        assert len(encoded) == 32
        # Verify the pattern is consistent
        # For color 5 (0101 in binary), bp0=1, bp1=0, bp2=1, bp3=0
        # So first byte should be 0xFF (all bits set for bp0)
        assert encoded[0] == 0xFF  # bp0 for first row
        assert encoded[1] == 0x00  # bp1 for first row
        assert encoded[16] == 0xFF  # bp2 for first row
        assert encoded[17] == 0x00  # bp3 for first row

    def test_encode_invalid_tile_size(self):
        """Test encoding with invalid tile size"""
        # Wrong number of pixels
        with pytest.raises(ValueError, match="Expected 64 pixels"):
            encode_4bpp_tile([0] * 63)

        with pytest.raises(ValueError, match="Expected 64 pixels"):
            encode_4bpp_tile([0] * 65)

    def test_encode_values_clamped(self):
        """Test that pixel values are clamped to 4-bit"""
        # Values > 15 should be masked to 4 bits
        tile_pixels = [255] * 64  # All pixels 255, should become 15
        encoded = encode_4bpp_tile(tile_pixels)

        # For color 15 (1111 in binary), all bitplanes should be 0xFF
        assert encoded[0] == 0xFF   # bp0
        assert encoded[1] == 0xFF   # bp1
        assert encoded[16] == 0xFF  # bp2
        assert encoded[17] == 0xFF  # bp3


class TestSpriteInjector:
    """Test the SpriteInjector class"""

    @pytest.fixture
    def injector(self):
        """Create a SpriteInjector instance"""
        return SpriteInjector()

    def test_load_metadata(self, injector, temp_metadata):
        """Test loading metadata from JSON file"""
        metadata = injector.load_metadata(str(temp_metadata))

        assert metadata is not None
        assert "extraction" in metadata
        assert metadata["extraction"]["vram_offset"] == "0xC000"
        assert metadata["extraction"]["tile_count"] == 100

    def test_validate_sprite_valid(self, injector, temp_sprite_image):
        """Test validating a valid sprite"""
        valid, message = injector.validate_sprite(str(temp_sprite_image))

        assert valid is True
        assert "successful" in message.lower()
        assert injector.sprite_path == str(temp_sprite_image)

    def test_validate_sprite_wrong_mode(self, injector, tmp_path):
        """Test validating sprite with wrong color mode"""
        # Create RGB image
        img = Image.new("RGB", (16, 16))
        sprite_path = tmp_path / "rgb_sprite.png"
        img.save(sprite_path)

        valid, message = injector.validate_sprite(str(sprite_path))

        assert valid is False
        assert "indexed color mode" in message

    def test_validate_sprite_wrong_dimensions(self, injector, tmp_path):
        """Test validating sprite with non-multiple-of-8 dimensions"""
        # Create 17x17 image (not multiple of 8)
        img = Image.new("P", (17, 17))
        sprite_path = tmp_path / "odd_sprite.png"
        img.save(sprite_path)

        valid, message = injector.validate_sprite(str(sprite_path))

        assert valid is False
        assert "multiples of 8" in message

    def test_validate_sprite_too_many_colors(self, injector, tmp_path):
        """Test validating sprite with too many colors"""
        # Create image that actually uses 32 different colors
        img = Image.new("P", (16, 16))

        # Create pixel data that uses 32 different color indices
        pixels = []
        for i in range(256):  # 16x16 = 256 pixels
            pixels.append(i % 32)  # Use colors 0-31

        img.putdata(pixels)

        # Set palette (doesn't matter how big it is, we care about used colors)
        palette = []
        for i in range(256):
            palette.extend([i, i, i])
        img.putpalette(palette)

        sprite_path = tmp_path / "many_colors_sprite.png"
        img.save(sprite_path)

        valid, message = injector.validate_sprite(str(sprite_path))

        assert valid is False
        assert "too many colors" in message
        assert "32" in message  # Should report actual color count

    def test_validate_sprite_256_palette_16_colors_used(self, injector, tmp_path):
        """Test validating sprite with 256-color palette but only 16 colors used"""
        # Create image that uses only 16 colors but has a 256-color palette
        img = Image.new("P", (16, 16))

        # Create pixel data that only uses colors 0-15
        pixels = []
        for y in range(16):
            for x in range(16):
                pixels.append((x + y) % 16)  # Only use colors 0-15

        img.putdata(pixels)

        # Set a full 256-color palette (like pixel editor does)
        palette = []
        for i in range(256):
            palette.extend([i, i, i])  # Grayscale palette
        img.putpalette(palette)

        sprite_path = tmp_path / "256_palette_16_colors.png"
        img.save(sprite_path)

        # This should pass validation because only 16 colors are actually used
        valid, message = injector.validate_sprite(str(sprite_path))

        assert valid is True
        assert "successful" in message.lower()

    def test_validate_sprite_nonexistent(self, injector):
        """Test validating non-existent sprite file"""
        valid, message = injector.validate_sprite("/nonexistent/sprite.png")

        assert valid is False
        assert "Error" in message

    def test_convert_png_to_4bpp(self, injector, temp_sprite_image):
        """Test converting PNG to 4bpp format"""
        tile_data = injector.convert_png_to_4bpp(str(temp_sprite_image))

        # 16x16 pixels = 2x2 tiles = 4 tiles * 32 bytes/tile = 128 bytes
        assert len(tile_data) == 128
        assert isinstance(tile_data, bytes)

    def test_convert_png_to_4bpp_rgb_mode(self, injector, tmp_path):
        """Test converting RGB PNG (should auto-convert to indexed)"""
        # Create RGB image
        img = Image.new("RGB", (16, 16), color=(100, 100, 100))
        sprite_path = tmp_path / "rgb_sprite.png"
        img.save(sprite_path)

        tile_data = injector.convert_png_to_4bpp(str(sprite_path))

        assert len(tile_data) == 128
        assert isinstance(tile_data, bytes)

    def test_inject_sprite_success(self, injector, temp_sprite_image, temp_vram, tmp_path):
        """Test successful sprite injection"""
        output_path = tmp_path / "output.vram"

        success, message = injector.inject_sprite(
            str(temp_sprite_image),
            str(temp_vram),
            str(output_path),
            offset=0xC000
        )

        assert success is True
        assert "Successfully injected" in message
        assert output_path.exists()

        # Verify output file size
        assert output_path.stat().st_size == 65536

    def test_inject_sprite_with_metadata_offset(self, injector, temp_sprite_image,
                                               temp_vram, temp_metadata, tmp_path):
        """Test injection using offset from metadata"""
        # Load metadata first
        injector.load_metadata(str(temp_metadata))

        output_path = tmp_path / "output.vram"

        # Don't provide offset, should use metadata
        success, message = injector.inject_sprite(
            str(temp_sprite_image),
            str(temp_vram),
            str(output_path),
            offset=None
        )

        assert success is True
        assert "0xC000" in message  # Should use metadata offset

    def test_inject_sprite_offset_too_large(self, injector, temp_sprite_image,
                                           temp_vram, tmp_path):
        """Test injection with offset that would exceed VRAM"""
        output_path = tmp_path / "output.vram"

        # Try to inject at end of VRAM
        success, message = injector.inject_sprite(
            str(temp_sprite_image),
            str(temp_vram),
            str(output_path),
            offset=0xFFF0  # Too close to end
        )

        assert success is False
        assert "exceed VRAM size" in message

    def test_inject_sprite_file_error(self, injector, temp_sprite_image, tmp_path):
        """Test injection with file read error"""
        output_path = tmp_path / "output.vram"

        success, message = injector.inject_sprite(
            str(temp_sprite_image),
            "/nonexistent/vram.bin",
            str(output_path),
            offset=0xC000
        )

        assert success is False
        assert "Error" in message

    def test_get_extraction_info(self, injector, temp_metadata):
        """Test getting extraction info from metadata"""
        injector.load_metadata(str(temp_metadata))

        info = injector.get_extraction_info()

        assert info is not None
        assert info["vram_offset"] == "0xC000"
        assert info["tile_count"] == 100

    def test_get_extraction_info_no_metadata(self, injector):
        """Test getting extraction info without metadata"""
        info = injector.get_extraction_info()

        assert info is None


class TestInjectionWorker:
    """Test the InjectionWorker thread"""

    @pytest.fixture
    def mock_signals(self):
        """Create mock signals for testing"""
        return {
            "progress": MagicMock(),
            "finished": MagicMock()
        }

    def test_worker_successful_injection(self, temp_sprite_image, temp_vram,
                                       tmp_path, mock_signals):
        """Test worker thread successful injection"""
        output_path = tmp_path / "output.vram"

        worker = InjectionWorker(
            str(temp_sprite_image),
            str(temp_vram),
            str(output_path),
            0xC000,
            None
        )

        # Mock signals
        worker.progress = mock_signals["progress"]
        worker.finished = mock_signals["finished"]

        # Run the worker
        worker.run()

        # Check signals were emitted
        assert mock_signals["progress"].emit.call_count >= 3
        mock_signals["finished"].emit.assert_called_once()

        # Check finished signal arguments
        success, message = mock_signals["finished"].emit.call_args[0]
        assert success is True
        assert "Successfully" in message

    def test_worker_with_metadata(self, temp_sprite_image, temp_vram,
                                 temp_metadata, tmp_path, mock_signals):
        """Test worker with metadata loading"""
        output_path = tmp_path / "output.vram"

        worker = InjectionWorker(
            str(temp_sprite_image),
            str(temp_vram),
            str(output_path),
            0xC000,
            str(temp_metadata)
        )

        worker.progress = mock_signals["progress"]
        worker.finished = mock_signals["finished"]

        worker.run()

        # Should emit "Loading metadata..." message
        progress_calls = [call[0][0] for call in mock_signals["progress"].emit.call_args_list]
        assert any("metadata" in msg.lower() for msg in progress_calls)

    def test_worker_validation_failure(self, temp_vram, tmp_path, mock_signals):
        """Test worker with sprite validation failure"""
        # Create invalid sprite (RGB mode)
        img = Image.new("RGB", (16, 16))
        sprite_path = tmp_path / "invalid_sprite.png"
        img.save(sprite_path)

        output_path = tmp_path / "output.vram"

        worker = InjectionWorker(
            str(sprite_path),
            str(temp_vram),
            str(output_path),
            0xC000,
            None
        )

        worker.progress = mock_signals["progress"]
        worker.finished = mock_signals["finished"]

        worker.run()

        # Should fail with validation error
        success, message = mock_signals["finished"].emit.call_args[0]
        assert success is False
        assert "indexed color mode" in message

    def test_worker_exception_handling(self, tmp_path, mock_signals):
        """Test worker exception handling"""
        output_path = tmp_path / "output.vram"

        worker = InjectionWorker(
            "/nonexistent/sprite.png",
            "/nonexistent/vram.bin",
            str(output_path),
            0xC000,
            None
        )

        worker.progress = mock_signals["progress"]
        worker.finished = mock_signals["finished"]

        worker.run()

        # Should fail gracefully
        success, message = mock_signals["finished"].emit.call_args[0]
        assert success is False
        assert "Error" in message or "error" in message
