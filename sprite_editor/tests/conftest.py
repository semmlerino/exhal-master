"""
Shared pytest fixtures and configuration for sprite editor tests
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_vram_data():
    """Create sample VRAM data (64KB of test data)"""
    # Create a pattern that's easy to verify
    data = bytearray(65536)
    for i in range(0, 65536, 32):
        # Create a simple pattern for each tile
        for j in range(32):
            data[i + j] = (i // 32 + j) % 256
    return bytes(data)


@pytest.fixture
def sample_cgram_data():
    """Create sample CGRAM palette data (512 bytes)"""
    data = bytearray(512)
    # Create 16 test palettes
    for pal in range(16):
        for color in range(16):
            # Create BGR555 color
            r = (color * 2) & 0x1F
            g = (color * 2) & 0x1F
            b = (color * 2) & 0x1F
            bgr555 = (b << 10) | (g << 5) | r

            offset = pal * 32 + color * 2
            data[offset] = bgr555 & 0xFF
            data[offset + 1] = (bgr555 >> 8) & 0xFF
    return bytes(data)


@pytest.fixture
def sample_oam_data():
    """Create sample OAM data (544 bytes)"""
    data = bytearray(544)

    # Create some test sprites
    for i in range(10):  # First 10 sprites
        offset = i * 4
        data[offset] = 100 + i * 10  # X position
        data[offset + 1] = 50 + i * 5  # Y position
        data[offset + 2] = 0x80 + i  # Tile number
        data[offset + 3] = i % 8  # Attributes (palette in lower 3 bits)

    # High table (just zeros for simplicity)
    for i in range(512, 544):
        data[i] = 0

    return bytes(data)


@pytest.fixture
def sample_4bpp_tile():
    """Create a sample 4bpp tile (32 bytes)"""
    # Create a simple diagonal pattern
    tile_data = bytearray(32)
    for y in range(8):
        # Set bitplane 0 to diagonal
        tile_data[y * 2] = 1 << (7 - y)
        # Other bitplanes empty
        tile_data[y * 2 + 1] = 0
        tile_data[16 + y * 2] = 0
        tile_data[16 + y * 2 + 1] = 0
    return bytes(tile_data)


@pytest.fixture
def vram_file(temp_dir, sample_vram_data):
    """Create a temporary VRAM dump file"""
    vram_path = temp_dir / "VRAM.dmp"
    vram_path.write_bytes(sample_vram_data)
    return str(vram_path)


@pytest.fixture
def cgram_file(temp_dir, sample_cgram_data):
    """Create a temporary CGRAM dump file"""
    cgram_path = temp_dir / "CGRAM.dmp"
    cgram_path.write_bytes(sample_cgram_data)
    return str(cgram_path)


@pytest.fixture
def oam_file(temp_dir, sample_oam_data):
    """Create a temporary OAM dump file"""
    oam_path = temp_dir / "OAM.dmp"
    oam_path.write_bytes(sample_oam_data)
    return str(oam_path)

# Security fixtures removed for personal project
