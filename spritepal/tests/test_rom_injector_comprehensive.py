"""
Comprehensive unit tests for ROM injection functionality
"""

import os
import struct
import tempfile
from unittest.mock import MagicMock, mock_open, patch

import pytest

from spritepal.core.hal_compression import HALCompressionError
from spritepal.core.rom_injector import (
    ROMHeader,
    ROMInjectionWorker,
    ROMInjector,
    SpritePointer,
)


class TestROMHeader:
    """Test ROMHeader dataclass"""

    def test_rom_header_creation(self):
        """Test creating a ROM header"""
        header = ROMHeader(
            title="TEST ROM",
            rom_type=0x20,
            rom_size=0x08,
            sram_size=0x00,
            checksum=0x1234,
            checksum_complement=0xEDCB,
            header_offset=0,
        )

        assert header.title == "TEST ROM"
        assert header.rom_type == 0x20
        assert header.rom_size == 0x08
        assert header.sram_size == 0x00
        assert header.checksum == 0x1234
        assert header.checksum_complement == 0xEDCB
        assert header.header_offset == 0

    def test_rom_header_equality(self):
        """Test ROM header equality comparison"""
        header1 = ROMHeader(
            title="TEST",
            rom_type=0x20,
            rom_size=0x08,
            sram_size=0x00,
            checksum=0x1234,
            checksum_complement=0xEDCB,
            header_offset=0,
        )
        header2 = ROMHeader(
            title="TEST",
            rom_type=0x20,
            rom_size=0x08,
            sram_size=0x00,
            checksum=0x1234,
            checksum_complement=0xEDCB,
            header_offset=0,
        )
        header3 = ROMHeader(
            title="DIFFERENT",
            rom_type=0x20,
            rom_size=0x08,
            sram_size=0x00,
            checksum=0x1234,
            checksum_complement=0xEDCB,
            header_offset=0,
        )

        assert header1 == header2
        assert header1 != header3


class TestSpritePointer:
    """Test SpritePointer dataclass"""

    def test_sprite_pointer_creation(self):
        """Test creating a sprite pointer"""
        pointer = SpritePointer(
            offset=0x0C8000, bank=0x0C, address=0x8000, compressed_size=0x1000
        )

        assert pointer.offset == 0x0C8000
        assert pointer.bank == 0x0C
        assert pointer.address == 0x8000
        assert pointer.compressed_size == 0x1000

    def test_sprite_pointer_optional_compressed_size(self):
        """Test sprite pointer with optional compressed size"""
        pointer = SpritePointer(offset=0x0C8000, bank=0x0C, address=0x8000)

        assert pointer.compressed_size is None


class TestROMInjectorInit:
    """Test ROMInjector initialization"""

    def test_rom_injector_init(self):
        """Test ROM injector initialization"""
        injector = ROMInjector()

        assert injector.hal_compressor is not None
        assert injector.rom_data is None
        assert injector.header is None
        assert injector.sprite_config_loader is not None

    def test_rom_injector_inherits_from_sprite_injector(self):
        """Test that ROMInjector inherits from SpriteInjector"""
        from spritepal.core.injector import SpriteInjector

        injector = ROMInjector()
        assert isinstance(injector, SpriteInjector)


class TestROMInjectorReadHeader:
    """Test ROM header reading functionality"""

    def create_test_rom_data(self, title="TEST ROM", rom_type=0x20, smc_header=False):
        """Create test ROM data with valid header"""
        rom_size = 0x8000
        if smc_header:
            rom_size += 512

        rom_data = bytearray(rom_size)

        # SMC header if requested
        header_offset = 512 if smc_header else 0

        # SNES header at 0x7FC0 (LoROM) or 0xFFC0 (HiROM)
        header_pos = header_offset + 0x7FC0

        # Title (21 bytes) - pad with spaces, not null bytes
        title_bytes = title.encode("ascii")[:21].ljust(21, b" ")
        rom_data[header_pos : header_pos + 21] = title_bytes

        # ROM type, size, SRAM size
        rom_data[header_pos + 21] = rom_type
        rom_data[header_pos + 23] = 0x08  # ROM size
        rom_data[header_pos + 24] = 0x00  # SRAM size

        # Checksum and complement (must XOR to 0xFFFF)
        checksum = 0x1234
        complement = checksum ^ 0xFFFF
        struct.pack_into("<H", rom_data, header_pos + 28, complement)
        struct.pack_into("<H", rom_data, header_pos + 30, checksum)

        return rom_data

    def test_read_rom_header_valid_lorom(self):
        """Test reading valid LoROM header"""
        rom_data = self.create_test_rom_data("KIRBY SUPER STAR", 0x20)

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(rom_data)
            tmp_path = tmp.name

        try:
            injector = ROMInjector()
            header = injector.read_rom_header(tmp_path)

            assert header.title == "KIRBY SUPER STAR"
            assert header.rom_type == 0x20
            assert header.rom_size == 0x08
            assert header.sram_size == 0x00
            assert header.checksum == 0x1234
            assert header.checksum_complement == 0xEDCB
            assert header.header_offset == 0

        finally:
            os.unlink(tmp_path)

    def test_read_rom_header_with_smc_header(self):
        """Test reading ROM with SMC header"""
        rom_data = self.create_test_rom_data("SMC ROM", 0x20, smc_header=True)

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(rom_data)
            tmp_path = tmp.name

        try:
            injector = ROMInjector()
            header = injector.read_rom_header(tmp_path)

            assert header.title == "SMC ROM"
            assert header.header_offset == 512

        finally:
            os.unlink(tmp_path)

    def test_read_rom_header_invalid_checksum(self):
        """Test reading ROM with invalid checksum"""
        # Create larger ROM data so it can have headers at both locations
        rom_data = bytearray(0x10000)  # 64KB

        # Add invalid headers at both locations
        for header_pos in [0x7FC0, 0xFFC0]:
            # Title (21 bytes) - pad with spaces, not null bytes
            title_bytes = b"BAD ROM".ljust(21, b" ")
            rom_data[header_pos : header_pos + 21] = title_bytes

            # ROM type, size, SRAM size
            rom_data[header_pos + 21] = 0x20
            rom_data[header_pos + 23] = 0x08
            rom_data[header_pos + 24] = 0x00

            # Invalid checksum (doesn't XOR to 0xFFFF)
            rom_data[header_pos + 28] = 0x00
            rom_data[header_pos + 29] = 0x00
            rom_data[header_pos + 30] = 0x00
            rom_data[header_pos + 31] = 0x00

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(rom_data)
            tmp_path = tmp.name

        try:
            injector = ROMInjector()
            with pytest.raises(
                ValueError, match="Could not find valid SNES ROM header"
            ):
                injector.read_rom_header(tmp_path)

        finally:
            os.unlink(tmp_path)

    def test_read_rom_header_file_not_found(self):
        """Test reading non-existent ROM file"""
        injector = ROMInjector()

        with pytest.raises(FileNotFoundError):
            injector.read_rom_header("/path/to/nonexistent/file.sfc")

    def test_read_rom_header_too_small(self):
        """Test reading ROM file that's too small"""
        # Create a ROM that's too small to contain a header
        rom_data = bytearray(1024)

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(rom_data)
            tmp_path = tmp.name

        try:
            injector = ROMInjector()
            # This should raise an exception (either ValueError or IndexError)
            # because the file is too small to contain a valid header
            with pytest.raises((ValueError, IndexError)):
                injector.read_rom_header(tmp_path)

        finally:
            os.unlink(tmp_path)

    def test_read_rom_header_non_ascii_title(self):
        """Test reading ROM with non-ASCII characters in title"""
        # Create ROM data manually with non-ASCII bytes
        rom_data = bytearray(0x8000)
        header_pos = 0x7FC0

        # Title with non-ASCII bytes (simulate what might be in a ROM)
        title_bytes = b"T\xebST R\xf6M"  # Contains non-ASCII bytes
        title_bytes = title_bytes[:21].ljust(21, b" ")
        rom_data[header_pos : header_pos + 21] = title_bytes

        # ROM type, size, SRAM size
        rom_data[header_pos + 21] = 0x20
        rom_data[header_pos + 23] = 0x08
        rom_data[header_pos + 24] = 0x00

        # Checksum and complement (must XOR to 0xFFFF)
        checksum = 0x1234
        complement = checksum ^ 0xFFFF
        struct.pack_into("<H", rom_data, header_pos + 28, complement)
        struct.pack_into("<H", rom_data, header_pos + 30, checksum)

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(rom_data)
            tmp_path = tmp.name

        try:
            injector = ROMInjector()
            header = injector.read_rom_header(tmp_path)

            # Should handle non-ASCII characters gracefully
            assert header.title is not None
            assert isinstance(header.title, str)

        finally:
            os.unlink(tmp_path)


class TestROMInjectorChecksum:
    """Test ROM checksum calculation functionality"""

    def test_calculate_checksum_basic(self):
        """Test basic checksum calculation"""
        rom_data = bytearray(0x8000)

        # Fill with test pattern
        for i in range(0, len(rom_data), 2):
            rom_data[i] = 0x12
            rom_data[i + 1] = 0x34

        injector = ROMInjector()
        injector.header = ROMHeader(
            title="TEST",
            rom_type=0x20,
            rom_size=0x08,
            sram_size=0x00,
            checksum=0,
            checksum_complement=0,
            header_offset=0,
        )

        checksum, complement = injector.calculate_checksum(rom_data)

        # Verify checksum and complement XOR to 0xFFFF
        assert (checksum ^ complement) == 0xFFFF
        assert isinstance(checksum, int)
        assert isinstance(complement, int)

    def test_calculate_checksum_with_smc_header(self):
        """Test checksum calculation with SMC header"""
        rom_data = bytearray(0x8000 + 512)  # ROM + SMC header

        # Fill ROM data (skip SMC header)
        for i in range(512, len(rom_data), 2):
            rom_data[i] = 0xAB
            rom_data[i + 1] = 0xCD

        injector = ROMInjector()
        injector.header = ROMHeader(
            title="TEST",
            rom_type=0x20,
            rom_size=0x08,
            sram_size=0x00,
            checksum=0,
            checksum_complement=0,
            header_offset=512,
        )

        checksum, complement = injector.calculate_checksum(rom_data)

        # Verify checksum and complement XOR to 0xFFFF
        assert (checksum ^ complement) == 0xFFFF

    def test_calculate_checksum_odd_length(self):
        """Test checksum calculation with odd length data"""
        rom_data = bytearray(0x8001)  # Odd length

        # Fill with test pattern
        for i in range(len(rom_data)):
            rom_data[i] = 0x55

        injector = ROMInjector()
        injector.header = ROMHeader(
            title="TEST",
            rom_type=0x20,
            rom_size=0x08,
            sram_size=0x00,
            checksum=0,
            checksum_complement=0,
            header_offset=0,
        )

        checksum, complement = injector.calculate_checksum(rom_data)

        # Should handle odd length gracefully
        assert (checksum ^ complement) == 0xFFFF

    def test_update_rom_checksum_without_header(self):
        """Test updating checksum without loaded header"""
        rom_data = bytearray(0x8000)

        injector = ROMInjector()
        # Don't set header

        with pytest.raises(ValueError, match="ROM header not loaded"):
            injector.update_rom_checksum(rom_data)

    def test_update_rom_checksum_basic(self):
        """Test updating ROM checksum"""
        rom_data = bytearray(0x8000)

        # Fill with test pattern
        for i in range(len(rom_data)):
            rom_data[i] = 0x42

        injector = ROMInjector()
        injector.header = ROMHeader(
            title="TEST",
            rom_type=0x20,
            rom_size=0x08,
            sram_size=0x00,
            checksum=0,
            checksum_complement=0,
            header_offset=0,
        )

        # Update checksum
        injector.update_rom_checksum(rom_data)

        # Verify checksum was written to ROM
        header_pos = 0x7FC0
        complement = struct.unpack("<H", rom_data[header_pos + 28 : header_pos + 30])[0]
        checksum = struct.unpack("<H", rom_data[header_pos + 30 : header_pos + 32])[0]

        assert (checksum ^ complement) == 0xFFFF
        assert injector.header.checksum == checksum
        assert injector.header.checksum_complement == complement


class TestROMInjectorCompression:
    """Test ROM compression-related functionality"""

    def test_estimate_compressed_size_with_padding(self):
        """Test compressed size estimation with padding"""
        # Create ROM data with padding patterns
        rom_data = bytearray(0x2000)
        offset = 0x1000

        # Add some data
        for i in range(0x500):
            rom_data[offset + i] = i % 256

        # Add padding (0xFF pattern)
        for i in range(0x500, 0x600):
            rom_data[offset + i] = 0xFF

        injector = ROMInjector()
        size = injector._estimate_compressed_size(rom_data, offset)

        # Should detect padding and return reasonable size
        assert size > 0
        assert size <= 0x600

    def test_estimate_compressed_size_with_zero_padding(self):
        """Test compressed size estimation with zero padding"""
        rom_data = bytearray(0x2000)
        offset = 0x1000

        # Add some data
        for i in range(0x300):
            rom_data[offset + i] = i % 256

        # Add zero padding
        for i in range(0x300, 0x400):
            rom_data[offset + i] = 0x00

        injector = ROMInjector()
        size = injector._estimate_compressed_size(rom_data, offset)

        # Should detect padding and return reasonable size
        assert size > 0
        assert size <= 0x400

    def test_estimate_compressed_size_no_padding(self):
        """Test compressed size estimation without clear padding"""
        rom_data = bytearray(0x2000)
        offset = 0x1000

        # Fill with random-looking data (no clear padding)
        for i in range(0x1000):
            rom_data[offset + i] = (i * 17 + 42) % 256

        injector = ROMInjector()
        size = injector._estimate_compressed_size(rom_data, offset)

        # Should return default size
        assert size == 0x1000

    def test_estimate_compressed_size_near_end_of_rom(self):
        """Test compressed size estimation near end of ROM"""
        rom_data = bytearray(0x1100)
        offset = 0x1000  # Near end

        injector = ROMInjector()
        size = injector._estimate_compressed_size(rom_data, offset)

        # Should not exceed ROM bounds
        assert size <= 0x100

    @patch("spritepal.core.rom_injector.tempfile.NamedTemporaryFile")
    @patch("spritepal.core.rom_injector.os.unlink")
    def test_find_compressed_sprite_success(self, mock_unlink, mock_temp):
        """Test finding compressed sprite data"""
        mock_temp_file = MagicMock()
        mock_temp_file.name = "/tmp/test_rom"
        mock_temp.return_value.__enter__.return_value = mock_temp_file

        rom_data = bytearray(0x8000)
        offset = 0x1000

        injector = ROMInjector()
        injector.hal_compressor = MagicMock()
        injector.hal_compressor.decompress_from_rom.return_value = b"decompressed_data"

        # Mock the size estimation
        with patch.object(injector, "_estimate_compressed_size", return_value=0x800):
            size, data = injector.find_compressed_sprite(rom_data, offset)

        assert size == 0x800
        assert data == b"decompressed_data"
        injector.hal_compressor.decompress_from_rom.assert_called_once_with(
            "/tmp/test_rom", offset
        )
        mock_unlink.assert_called_once_with("/tmp/test_rom")

    @patch("spritepal.core.rom_injector.tempfile.NamedTemporaryFile")
    @patch("spritepal.core.rom_injector.os.unlink")
    def test_find_compressed_sprite_decompression_error(self, mock_unlink, mock_temp):
        """Test finding compressed sprite with decompression error"""
        mock_temp_file = MagicMock()
        mock_temp_file.name = "/tmp/test_rom"
        mock_temp.return_value.__enter__.return_value = mock_temp_file

        rom_data = bytearray(0x8000)
        offset = 0x1000

        injector = ROMInjector()
        injector.hal_compressor = MagicMock()
        injector.hal_compressor.decompress_from_rom.side_effect = HALCompressionError(
            "Decompression failed"
        )

        with pytest.raises(HALCompressionError):
            injector.find_compressed_sprite(rom_data, offset)

        # Should still clean up temp file
        mock_unlink.assert_called_once_with("/tmp/test_rom")


class TestROMInjectorSpriteInjection:
    """Test sprite injection functionality"""

    def create_test_rom_data(self, title="TEST ROM", rom_type=0x20):
        """Create test ROM data"""
        rom_data = bytearray(
            0x20000
        )  # 128KB - definitely large enough for any header location

        # SNES header at 0x7FC0
        header_pos = 0x7FC0

        # Title (21 bytes) - pad with spaces, not null bytes
        title_bytes = title.encode("ascii")[:21].ljust(21, b" ")
        rom_data[header_pos : header_pos + 21] = title_bytes

        # ROM type, size, SRAM size
        rom_data[header_pos + 21] = rom_type
        rom_data[header_pos + 23] = 0x08
        rom_data[header_pos + 24] = 0x00

        # Checksum and complement
        checksum = 0x1234
        complement = checksum ^ 0xFFFF
        struct.pack_into("<H", rom_data, header_pos + 28, complement)
        struct.pack_into("<H", rom_data, header_pos + 30, checksum)

        return rom_data

    @patch("spritepal.core.rom_injector.tempfile.NamedTemporaryFile")
    @patch("spritepal.core.rom_injector.os.unlink")
    def test_inject_sprite_to_rom_success(self, mock_unlink, mock_temp):
        """Test successful sprite injection"""
        # Create test ROM
        rom_data = self.create_test_rom_data("TEST ROM")

        # Mock file operations
        mock_temp_file = MagicMock()
        mock_temp_file.name = "/tmp/compressed.bin"
        mock_temp.return_value.__enter__.return_value = mock_temp_file

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                rom_path = os.path.join(temp_dir, "test.sfc")
                sprite_path = os.path.join(temp_dir, "sprite.png")
                output_path = os.path.join(temp_dir, "output.sfc")

                # Write test ROM
                with open(rom_path, "wb") as f:
                    f.write(rom_data)

                # Create dummy sprite file
                with open(sprite_path, "wb") as f:
                    f.write(b"PNG_DATA")

                injector = ROMInjector()

                # Mock methods
                injector.convert_png_to_4bpp = MagicMock(return_value=b"4bpp_data")
                injector.find_compressed_sprite = MagicMock(
                    return_value=(0x1000, b"original_data")
                )
                injector.hal_compressor = MagicMock()
                injector.hal_compressor.compress_to_file = MagicMock(return_value=0x800)

                # Mock compressed file reading more specifically
                original_open = open

                def mock_open_func(path, mode="r", **kwargs):
                    if path == "/tmp/compressed.bin":
                        return mock_open(read_data=b"compressed_data")()
                    return original_open(path, mode, **kwargs)

                with patch("builtins.open", side_effect=mock_open_func):
                    success, message = injector.inject_sprite_to_rom(
                        sprite_path, rom_path, output_path, 0x1000, False
                    )

                assert success is True
                assert "Successfully injected sprite" in message
                assert "0x1000" in message
                assert os.path.exists(output_path)
        except OSError as e:
            # If temp directory cleanup fails, that's not our test's fault
            if "Directory not empty" in str(e):
                pass  # Ignore cleanup errors
            else:
                raise

    def test_inject_sprite_to_rom_sprite_too_large(self):
        """Test sprite injection with sprite too large"""
        # Use minimum valid ROM size to pass initial validation
        rom_data = bytearray(0x80000)  # 512KB - minimum valid ROM size

        # Set up proper SNES header at 0x7FC0 (LoROM)
        header_pos = 0x7FC0
        title_bytes = "TEST ROM".encode("ascii")[:21].ljust(21, b" ")
        rom_data[header_pos : header_pos + 21] = title_bytes
        rom_data[header_pos + 21] = 0x20  # LoROM
        rom_data[header_pos + 23] = 0x0A  # ROM size (512KB)
        rom_data[header_pos + 24] = 0x00  # SRAM size

        # Calculate proper checksum for the ROM data
        # Clear checksum fields first
        rom_data[header_pos + 28 : header_pos + 32] = b"\x00\x00\x00\x00"

        # Calculate checksum (sum of all bytes)
        checksum = sum(rom_data) & 0xFFFF
        complement = checksum ^ 0xFFFF

        # Store checksum and complement
        rom_data[header_pos + 28 : header_pos + 30] = struct.pack("<H", checksum)
        rom_data[header_pos + 30 : header_pos + 32] = struct.pack("<H", complement)

        with tempfile.TemporaryDirectory() as temp_dir:
            rom_path = os.path.join(temp_dir, "test.sfc")
            sprite_path = os.path.join(temp_dir, "sprite.png")
            output_path = os.path.join(temp_dir, "output.sfc")

            # Write test ROM
            with open(rom_path, "wb") as f:
                f.write(rom_data)

            # Create dummy sprite file
            with open(sprite_path, "wb") as f:
                f.write(b"PNG_DATA")

            injector = ROMInjector()

            # Mock methods - compressed size larger than original
            injector.convert_png_to_4bpp = MagicMock(return_value=b"4bpp_data")
            injector.find_compressed_sprite = MagicMock(
                return_value=(0x800, b"original_data")
            )
            injector.hal_compressor = MagicMock()
            injector.hal_compressor.compress_to_file = MagicMock(
                return_value=0x1000
            )  # Too large

            # Mock ROM validation to pass initial checks and reach sprite size check
            with patch("spritepal.core.rom_validator.ROMValidator.validate_rom_for_injection") as mock_validate:
                mock_validate.return_value = (
                    {"title": "TEST ROM", "checksum": 0x1234, "rom_type": 0x20},
                    0
                )

                with patch("spritepal.core.rom_injector.tempfile.NamedTemporaryFile"):
                    with patch("spritepal.core.rom_injector.os.unlink"):
                        success, message = injector.inject_sprite_to_rom(
                            sprite_path, rom_path, output_path, 0x1000, False
                        )

            assert success is False
            assert "Compressed sprite too large" in message

    def test_inject_sprite_to_rom_compression_error(self):
        """Test sprite injection with compression error"""
        rom_data = self.create_test_rom_data("TEST ROM")

        with tempfile.TemporaryDirectory() as temp_dir:
            rom_path = os.path.join(temp_dir, "test.sfc")
            sprite_path = os.path.join(temp_dir, "sprite.png")
            output_path = os.path.join(temp_dir, "output.sfc")

            # Write test ROM
            with open(rom_path, "wb") as f:
                f.write(rom_data)

            # Create dummy sprite file
            with open(sprite_path, "wb") as f:
                f.write(b"PNG_DATA")

            injector = ROMInjector()

            # Mock methods - compression fails
            injector.convert_png_to_4bpp = MagicMock(return_value=b"4bpp_data")
            injector.find_compressed_sprite = MagicMock(
                return_value=(0x1000, b"original_data")
            )
            injector.hal_compressor = MagicMock()
            injector.hal_compressor.compress_to_file.side_effect = HALCompressionError(
                "Compression failed"
            )

            # Mock ROM validation to pass initial checks and reach compression error
            with patch("spritepal.core.rom_validator.ROMValidator.validate_rom_for_injection") as mock_validate:
                mock_validate.return_value = (
                    {"title": "TEST ROM", "checksum": 0x1234, "rom_type": 0x20},
                    0
                )

                success, message = injector.inject_sprite_to_rom(
                    sprite_path, rom_path, output_path, 0x1000, False
                )

            assert success is False
            assert "Compression error" in message

    def test_inject_sprite_to_rom_file_not_found(self):
        """Test sprite injection with missing files"""
        injector = ROMInjector()

        success, message = injector.inject_sprite_to_rom(
            "/nonexistent/sprite.png",
            "/nonexistent/rom.sfc",
            "/tmp/output.sfc",
            0x1000,
            False,
        )

        assert success is False
        assert "ROM injection error" in message


class TestROMInjectorSpriteLocations:
    """Test sprite location functionality"""

    def test_find_sprite_locations_basic(self):
        """Test finding sprite locations"""
        injector = ROMInjector()

        # Mock ROM header and sprite config lookup
        mock_header = ROMHeader(
            title="KIRBY SUPER STAR",
            rom_type=0x20,
            rom_size=0x0A,
            sram_size=0x00,
            checksum=0x8A5C,  # USA version checksum
            checksum_complement=0x75A3,
            header_offset=0,
        )

        with patch.object(injector, "read_rom_header", return_value=mock_header):
            with tempfile.NamedTemporaryFile() as tmp:
                locations = injector.find_sprite_locations(tmp.name)

        # Should return known locations from sprite config
        assert isinstance(locations, dict)
        assert "High_Quality_Sprite_1" in locations
        assert "High_Quality_Sprite_2" in locations
        assert "High_Quality_Sprite_3" in locations

        # Check structure
        for _name, pointer in locations.items():
            assert isinstance(pointer, SpritePointer)
            assert pointer.offset is not None
            assert pointer.bank is not None
            assert pointer.address is not None

    def test_find_sprite_locations_pointer_calculation(self):
        """Test sprite pointer calculation"""
        injector = ROMInjector()

        # Mock ROM header to return Kirby Super Star
        mock_header = ROMHeader(
            title="KIRBY SUPER STAR",
            rom_type=0x20,
            rom_size=0x0A,
            sram_size=0x00,
            checksum=0x8A5C,  # USA version checksum
            checksum_complement=0x75A3,
            header_offset=0,
        )

        with patch.object(injector, "read_rom_header", return_value=mock_header):
            with tempfile.NamedTemporaryFile() as tmp:
                locations = injector.find_sprite_locations(tmp.name)

        # Check specific calculations for the first sprite
        sprite_1 = locations["High_Quality_Sprite_1"]
        assert sprite_1.offset == 0x200000
        assert sprite_1.bank == 0x20
        assert sprite_1.address == 0x0000


class TestROMInjectionWorker:
    """Test ROM injection worker thread"""

    def test_rom_injection_worker_init(self):
        """Test ROM injection worker initialization"""
        worker = ROMInjectionWorker(
            sprite_path="/test/sprite.png",
            rom_input="/test/input.sfc",
            rom_output="/test/output.sfc",
            sprite_offset=0x1000,
            fast_compression=True,
            metadata_path="/test/metadata.json",
        )

        assert worker.sprite_path == "/test/sprite.png"
        assert worker.rom_input == "/test/input.sfc"
        assert worker.rom_output == "/test/output.sfc"
        assert worker.sprite_offset == 0x1000
        assert worker.fast_compression is True
        assert worker.metadata_path == "/test/metadata.json"
        assert isinstance(worker.injector, ROMInjector)

    def test_rom_injection_worker_init_without_metadata(self):
        """Test ROM injection worker initialization without metadata"""
        worker = ROMInjectionWorker(
            sprite_path="/test/sprite.png",
            rom_input="/test/input.sfc",
            rom_output="/test/output.sfc",
            sprite_offset=0x1000,
        )

        assert worker.metadata_path is None
        assert worker.fast_compression is False

    @patch("spritepal.core.rom_injector.ROMInjector")
    @patch("spritepal.core.sprite_validator.SpriteValidator.validate_sprite_comprehensive")
    @patch("spritepal.core.rom_validator.ROMValidator.validate_rom_for_injection")
    @patch("spritepal.utils.rom_backup.ROMBackupManager.create_backup")
    def test_rom_injection_worker_run_success(self, mock_create_backup, mock_validate_rom, mock_validate_sprite, mock_injector_class):
        """Test successful ROM injection worker run"""
        # Mock injector
        mock_injector = MagicMock()
        mock_injector_class.return_value = mock_injector

        # Mock injector methods
        mock_injector.validate_sprite.return_value = (True, "Valid sprite")
        mock_injector.hal_compressor.test_tools.return_value = (True, "Tools OK")
        mock_injector.read_rom_header.return_value = ROMHeader(
            title="TEST ROM",
            rom_type=0x20,
            rom_size=0x08,
            sram_size=0x00,
            checksum=0x1234,
            checksum_complement=0xEDCB,
            header_offset=0,
        )
        mock_injector.inject_sprite_to_rom.return_value = (True, "Success message")

        # Mock external methods
        mock_validate_sprite.return_value = (True, [], [])
        mock_validate_rom.return_value = ({"title": "TEST ROM"}, 0)
        mock_create_backup.return_value = None

        worker = ROMInjectionWorker(
            sprite_path="/test/sprite.png",
            rom_input="/test/input.sfc",
            rom_output="/test/output.sfc",
            sprite_offset=0x1000,
        )

        # Mock signals
        worker.progress = MagicMock()
        worker.finished = MagicMock()

        # Run worker
        worker.run()

        # Verify progress signals
        worker.progress.emit.assert_called()
        progress_calls = [call[0][0] for call in worker.progress.emit.call_args_list]
        assert "Validating sprite file..." in progress_calls
        assert "Checking compression tools..." in progress_calls
        assert "Reading ROM header..." in progress_calls
        assert "ROM: TEST ROM" in progress_calls
        assert "Converting sprite to 4bpp format..." in progress_calls
        assert "Compressing sprite data..." in progress_calls
        assert "Injecting into ROM at offset 0x1000..." in progress_calls
        assert "Updating ROM checksum..." in progress_calls
        assert "ROM injection complete!" in progress_calls

        # Verify finished signal
        worker.finished.emit.assert_called_once_with(True, "Success message")

    @patch("spritepal.core.rom_injector.ROMInjector")
    def test_rom_injection_worker_run_invalid_sprite(self, mock_injector_class):
        """Test ROM injection worker run with invalid sprite"""
        # Mock injector
        mock_injector = MagicMock()
        mock_injector_class.return_value = mock_injector

        # Mock sprite validation failure
        mock_injector.validate_sprite.return_value = (False, "Invalid sprite format")

        worker = ROMInjectionWorker(
            sprite_path="/test/sprite.png",
            rom_input="/test/input.sfc",
            rom_output="/test/output.sfc",
            sprite_offset=0x1000,
        )

        # Mock signals
        worker.progress = MagicMock()
        worker.finished = MagicMock()

        # Run worker
        worker.run()

        # Should emit failure
        worker.finished.emit.assert_called_once_with(False, "Invalid sprite format")

    @patch("spritepal.core.rom_injector.ROMInjector")
    @patch("spritepal.core.sprite_validator.SpriteValidator.validate_sprite_comprehensive")
    def test_rom_injection_worker_run_tools_error(self, mock_validate_sprite, mock_injector_class):
        """Test ROM injection worker run with tools error"""
        # Mock injector
        mock_injector = MagicMock()
        mock_injector_class.return_value = mock_injector

        # Mock validation success but tools failure
        mock_injector.validate_sprite.return_value = (True, "Valid sprite")
        mock_validate_sprite.return_value = (True, [], [])  # Enhanced validation passes
        mock_injector.hal_compressor.test_tools.return_value = (
            False,
            "Tools not found",
        )

        worker = ROMInjectionWorker(
            sprite_path="/test/sprite.png",
            rom_input="/test/input.sfc",
            rom_output="/test/output.sfc",
            sprite_offset=0x1000,
        )

        # Mock signals
        worker.progress = MagicMock()
        worker.finished = MagicMock()

        # Run worker
        worker.run()

        # Should emit failure
        worker.finished.emit.assert_called_once_with(False, "Tools not found")

    @patch("spritepal.core.rom_injector.ROMInjector")
    def test_rom_injection_worker_run_with_metadata(self, mock_injector_class):
        """Test ROM injection worker run with metadata"""
        # Mock injector
        mock_injector = MagicMock()
        mock_injector_class.return_value = mock_injector

        # Mock all methods to succeed
        mock_injector.validate_sprite.return_value = (True, "Valid sprite")
        mock_injector.hal_compressor.test_tools.return_value = (True, "Tools OK")
        mock_injector.read_rom_header.return_value = ROMHeader(
            title="TEST ROM",
            rom_type=0x20,
            rom_size=0x08,
            sram_size=0x00,
            checksum=0x1234,
            checksum_complement=0xEDCB,
            header_offset=0,
        )
        mock_injector.inject_sprite_to_rom.return_value = (True, "Success message")

        worker = ROMInjectionWorker(
            sprite_path="/test/sprite.png",
            rom_input="/test/input.sfc",
            rom_output="/test/output.sfc",
            sprite_offset=0x1000,
            metadata_path="/test/metadata.json",
        )

        # Mock signals
        worker.progress = MagicMock()
        worker.finished = MagicMock()

        # Run worker
        worker.run()

        # Verify metadata loading was called
        mock_injector.load_metadata.assert_called_once_with("/test/metadata.json")

        # Verify progress includes metadata loading
        progress_calls = [call[0][0] for call in worker.progress.emit.call_args_list]
        assert "Loading metadata..." in progress_calls

    @patch("spritepal.core.rom_injector.ROMInjector")
    def test_rom_injection_worker_run_exception(self, mock_injector_class):
        """Test ROM injection worker run with unexpected exception"""
        # Mock injector
        mock_injector = MagicMock()
        mock_injector_class.return_value = mock_injector

        # Mock exception during validation
        mock_injector.validate_sprite.side_effect = Exception("Unexpected error")

        worker = ROMInjectionWorker(
            sprite_path="/test/sprite.png",
            rom_input="/test/input.sfc",
            rom_output="/test/output.sfc",
            sprite_offset=0x1000,
        )

        # Mock signals
        worker.progress = MagicMock()
        worker.finished = MagicMock()

        # Run worker
        worker.run()

        # Should emit unexpected error
        worker.finished.emit.assert_called_once_with(
            False, "Unexpected error: Unexpected error"
        )


if __name__ == "__main__":
    pytest.main([__file__])
