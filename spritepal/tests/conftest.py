"""
Centralized pytest configuration and fixtures for SpritePal tests.

This module provides common fixtures and configuration to eliminate duplication
across the test suite and provide consistent testing infrastructure.
"""

import sys
import tempfile
from pathlib import Path

import pytest

# Add parent directories to path - centralized path setup
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import SpritePal components after path setup
from spritepal.core.managers import cleanup_managers, initialize_managers
from spritepal.utils.constants import BYTES_PER_TILE, VRAM_SPRITE_OFFSET

# Import mock utilities
from .fixtures.qt_mocks import (
    create_mock_extraction_worker,
    create_mock_main_window,
    create_mock_signals,
)

# Import Qt test helpers for proper parent widgets


@pytest.fixture(autouse=True)
def setup_managers():
    """
    Setup managers for all tests.

    This fixture is automatically used by all tests to ensure proper
    manager initialization and cleanup. It replaces the duplicated
    setup_managers fixtures across multiple test files.
    """
    initialize_managers("TestApp")
    yield
    cleanup_managers()


@pytest.fixture
def test_data_factory():
    """
    Factory for creating common test data structures.

    Returns a factory function that can create various types of test data
    with consistent patterns used across the test suite.
    """
    def _create_test_data(data_type: str, size: int | None = None, **kwargs) -> bytearray:
        """
        Create test data of specified type.

        Args:
            data_type: Type of data - 'vram', 'cgram', 'oam'
            size: size override
            **kwargs: Additional parameters for data generation

        Returns:
            bytearray with test data
        """
        if data_type == "vram":
            default_size = 0x10000  # 64KB
            data = bytearray(size or default_size)

            # Add some realistic sprite data at VRAM offset
            start_offset = kwargs.get("sprite_offset", VRAM_SPRITE_OFFSET)
            tile_count = kwargs.get("tile_count", 10)

            for i in range(tile_count):
                offset = start_offset + i * BYTES_PER_TILE
                if offset + BYTES_PER_TILE <= len(data):
                    for j in range(BYTES_PER_TILE):
                        data[offset + j] = (i + j) % 256

            return data

        if data_type == "cgram":
            default_size = 512  # 256 colors * 2 bytes
            data = bytearray(size or default_size)

            # Add some realistic palette data
            for i in range(0, len(data), 2):
                # Create BGR555 color values
                data[i] = i % 256
                data[i + 1] = (i // 2) % 32

            return data

        if data_type == "oam":
            default_size = 544  # Standard OAM size
            data = bytearray(size or default_size)

            # Add some realistic OAM data
            for i in range(0, min(len(data), 512), 4):  # 4 bytes per entry
                data[i] = i % 256      # X position
                data[i + 1] = i % 224  # Y position
                data[i + 2] = i % 256  # Tile index
                data[i + 3] = 0x20     # Attributes

            return data

        raise ValueError(f"Unknown data type: {data_type}")

    return _create_test_data


@pytest.fixture
def temp_files():
    """
    Factory for creating temporary test files.

    Returns a factory function that creates temporary files with test data
    and automatically cleans them up after the test.
    """
    created_files = []

    def _create_temp_file(data: bytes, suffix: str = ".dmp") -> str:
        """Create a temporary file with the given data"""
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        temp_file.write(data)
        temp_file.close()
        created_files.append(temp_file.name)
        return temp_file.name

    yield _create_temp_file

    # Cleanup
    import os
    for file_path in created_files:
        try:
            os.unlink(file_path)
        except OSError:
            pass  # File might already be deleted


@pytest.fixture
def standard_test_params(test_data_factory, temp_files):
    """
    Create standard test parameters used across integration tests.

    This fixture provides the common set of test parameters that many
    integration tests use, reducing duplication in test setup.
    """
    # Create standard test data
    vram_data = test_data_factory("vram")
    cgram_data = test_data_factory("cgram")
    oam_data = test_data_factory("oam")

    # Create temporary files
    vram_file = temp_files(vram_data, ".dmp")
    cgram_file = temp_files(cgram_data, ".dmp")
    oam_file = temp_files(oam_data, ".dmp")

    return {
        "vram_path": vram_file,
        "cgram_path": cgram_file,
        "oam_path": oam_file,
        "output_base": "test_output",
        "create_grayscale": True,
        "create_metadata": True,
        "vram_data": vram_data,
        "cgram_data": cgram_data,
        "oam_data": oam_data,
    }


@pytest.fixture
def mock_extraction_signals():
    """
    Provide a standard set of mock signals for extraction testing.

    This replaces the various signal creation patterns across test files
    with a single, consistent fixture.
    """
    return create_mock_signals()


@pytest.fixture
def mock_main_window_configured():
    """
    Provide a fully configured mock main window for controller testing.

    This replaces the various main window mock creation patterns
    with a single, comprehensive fixture.
    """
    return create_mock_main_window()


@pytest.fixture
def mock_extraction_worker_configured():
    """
    Provide a fully configured mock extraction worker for testing.

    This replaces the various worker mock creation patterns
    with a single, comprehensive fixture.
    """
    return create_mock_extraction_worker()


@pytest.fixture
def minimal_sprite_data(test_data_factory):
    """
    Create minimal but valid sprite data for quick tests.

    This provides a lightweight alternative to full test data
    for tests that just need basic sprite data structure.
    """
    return {
        "vram": test_data_factory("vram", size=0x1000),  # 4KB
        "cgram": test_data_factory("cgram", size=32),    # 1 palette
        "width": 64,
        "height": 64,
        "tile_count": 8,
    }


# Test markers for better test organization
def pytest_configure(config):
    """Configure pytest with custom markers for SpritePal tests"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "mock: mark test as using mocks"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "manager: mark test as testing manager classes"
    )
    config.addinivalue_line(
        "markers", "gui: mark test as requiring GUI (may be skipped in headless)"
    )
