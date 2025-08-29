"""
Test utilities package for SpritePal test suite.

This package contains common utilities, data generators, and helper functions
used across multiple test files to eliminate duplication and provide consistency.
"""
from __future__ import annotations

from .assertions import (
    assert_manager_state,
    assert_valid_metadata,
    assert_valid_palette_data,
    assert_valid_sprite_data,
)
from .data_generators import (
    create_test_image,
    generate_palette_data,
    generate_rom_data,
    generate_sprite_data,
)
from .file_helpers import (
    cleanup_test_files,
    create_temp_directory,
    create_test_files,
)

__all__ = [
    "assert_manager_state",
    "assert_valid_metadata",
    "assert_valid_palette_data",
    "assert_valid_sprite_data",
    "cleanup_test_files",
    "create_temp_directory",
    "create_test_files",
    "create_test_image",
    "generate_palette_data",
    "generate_rom_data",
    "generate_sprite_data",
]
