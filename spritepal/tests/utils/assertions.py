"""
Common assertion functions for SpritePal tests.

This module provides reusable assertion functions that check common
conditions across tests, reducing duplication and improving consistency.
"""

from pathlib import Path
from typing import Any


def assert_valid_sprite_data(data: bytes, expected_size: int | None = None):
    """
    Assert that sprite data is valid and well-formed.

    Args:
        data: The sprite data to validate
        expected_size: expected size in bytes

    Raises:
        AssertionError: If data is not valid
    """
    assert isinstance(data, (bytes, bytearray)), "Sprite data must be bytes or bytearray"
    assert len(data) > 0, "Sprite data cannot be empty"

    if expected_size is not None:
        assert len(data) == expected_size, f"Expected {expected_size} bytes, got {len(data)}"

    # Check that data isn't all zeros (which might indicate empty/invalid data)
    non_zero_bytes = sum(1 for byte in data if byte != 0)
    assert non_zero_bytes > 0, "Sprite data cannot be all zeros"


def assert_valid_palette_data(palette_data: list[list[int]], expected_palettes: int = 16):
    """
    Assert that palette data is valid and well-formed.

    Args:
        palette_data: List of palettes, each containing RGB color values
        expected_palettes: Expected number of palettes

    Raises:
        AssertionError: If palette data is not valid
    """
    assert isinstance(palette_data, list), "Palette data must be a list"
    assert len(palette_data) == expected_palettes, f"Expected {expected_palettes} palettes, got {len(palette_data)}"

    for i, palette in enumerate(palette_data):
        assert isinstance(palette, list), f"Palette {i} must be a list"
        assert len(palette) == 16, f"Palette {i} must have 16 colors, got {len(palette)}"

        for j, color in enumerate(palette):
            assert isinstance(color, list), f"Color {j} in palette {i} must be a list"
            assert len(color) == 3, f"Color {j} in palette {i} must have 3 RGB values"

            for k, component in enumerate(color):
                assert isinstance(component, int), f"RGB component {k} must be an integer"
                assert 0 <= component <= 255, f"RGB component {k} must be 0-255, got {component}"


def assert_valid_metadata(metadata: dict[str, Any]):
    """
    Assert that sprite metadata is valid and complete.

    Args:
        metadata: The metadata dictionary to validate

    Raises:
        AssertionError: If metadata is not valid
    """
    assert isinstance(metadata, dict), "Metadata must be a dictionary"

    required_keys = ["width", "height", "palette_count", "format"]
    for key in required_keys:
        assert key in metadata, f"Metadata missing required key: {key}"

    assert isinstance(metadata["width"], int), "Width must be an integer"
    assert isinstance(metadata["height"], int), "Height must be an integer"
    assert metadata["width"] > 0, "Width must be positive"
    assert metadata["height"] > 0, "Height must be positive"

    assert isinstance(metadata["palette_count"], int), "Palette count must be an integer"
    assert metadata["palette_count"] > 0, "Palette count must be positive"


def assert_manager_state(manager: Any, expected_state: str):
    """
    Assert that a manager is in the expected state.

    Args:
        manager: The manager object to check
        expected_state: The expected state string

    Raises:
        AssertionError: If manager state is not as expected
    """
    assert hasattr(manager, "get_state"), "Manager must have get_state method"

    actual_state = manager.get_state()
    assert actual_state == expected_state, f"Expected state '{expected_state}', got '{actual_state}'"


def assert_files_exist(file_paths: list[str]):
    """
    Assert that all specified files exist.

    Args:
        file_paths: List of file paths to check

    Raises:
        AssertionError: If any file does not exist
    """
    for file_path in file_paths:
        path = Path(file_path)
        assert path.exists(), f"File does not exist: {file_path}"
        assert path.is_file(), f"Path is not a file: {file_path}"


def assert_signal_emitted(signal_mock: Any, expected_count: int = 1):
    """
    Assert that a mock signal was emitted the expected number of times.

    Args:
        signal_mock: The mock signal object
        expected_count: Expected number of emissions

    Raises:
        AssertionError: If signal was not emitted as expected
    """
    assert hasattr(signal_mock, "emit"), "Signal mock must have emit method"
    assert signal_mock.emit.call_count == expected_count, \
        f"Signal emitted {signal_mock.emit.call_count} times, expected {expected_count}"


def assert_image_properties(image_path: str, expected_width: int, expected_height: int):
    """
    Assert that an image has the expected properties.

    Args:
        image_path: Path to the image file
        expected_width: Expected image width
        expected_height: Expected image height

    Raises:
        AssertionError: If image properties don't match
    """
    from PIL import Image

    assert Path(image_path).exists(), f"Image file does not exist: {image_path}"

    with Image.open(image_path) as img:
        assert img.width == expected_width, f"Expected width {expected_width}, got {img.width}"
        assert img.height == expected_height, f"Expected height {expected_height}, got {img.height}"
