"""
Sprite calculation utilities for ROM offset and coordinate operations.

This module provides pure functions for sprite-related calculations,
including coordinate mapping, offset clamping, and grid positioning.
"""


# Import constants from existing module
from utils.constants import TILE_HEIGHT, TILE_WIDTH


def calculate_sprite_coords(
    offset: int,
    sprite_width: int = 16,
    sprites_per_row: int = 16
) -> tuple[int, int]:
    """
    Calculate sprite grid coordinates (column, row) from ROM offset.

    Args:
        offset: ROM offset in bytes
        sprite_width: Sprite width in pixels (default: 16)
        sprites_per_row: Number of sprites per row in grid layout (default: 16)

    Returns:
        Tuple of (column, row) coordinates in sprite grid

    Note:
        Assumes 4bpp (4 bits per pixel) sprite format where a 16x16 sprite
        occupies 128 bytes (16*16/2).
    """
    # Calculate sprite size in bytes (4bpp format = 4 bits per pixel)
    sprite_size_bytes = sprite_width * sprite_width // 2

    # Calculate sprite index from offset
    sprite_index = offset // sprite_size_bytes

    # Calculate grid coordinates
    row = sprite_index // sprites_per_row
    col = sprite_index % sprites_per_row

    return (col, row)


def clamp_offset(offset: int, rom_size: int) -> int:
    """
    Clamp offset to valid ROM bounds.

    Args:
        offset: Offset value to clamp
        rom_size: Size of ROM in bytes

    Returns:
        Clamped offset within valid range [0, rom_size-1]
    """
    if rom_size <= 0:
        return 0
    return max(0, min(offset, rom_size - 1))


def calculate_sprite_offset(
    col: int,
    row: int,
    sprite_width: int = 16,
    sprites_per_row: int = 16
) -> int:
    """
    Calculate ROM offset from sprite grid coordinates.

    Inverse of calculate_sprite_coords.

    Args:
        col: Column in sprite grid
        row: Row in sprite grid
        sprite_width: Sprite width in pixels (default: 16)
        sprites_per_row: Number of sprites per row (default: 16)

    Returns:
        ROM offset in bytes
    """
    sprite_size_bytes = sprite_width * sprite_width // 2
    sprite_index = row * sprites_per_row + col
    return sprite_index * sprite_size_bytes


def is_valid_sprite_offset(
    offset: int,
    rom_size: int,
    sprite_width: int = 16
) -> bool:
    """
    Check if offset points to a valid complete sprite.

    Args:
        offset: ROM offset to check
        rom_size: Total ROM size in bytes
        sprite_width: Sprite width in pixels (default: 16)

    Returns:
        True if offset can contain a complete sprite
    """
    if offset < 0 or offset >= rom_size:
        return False

    sprite_size_bytes = sprite_width * sprite_width // 2
    return offset + sprite_size_bytes <= rom_size


def align_offset_to_sprite(
    offset: int,
    sprite_width: int = 16
) -> int:
    """
    Align offset to nearest sprite boundary.

    Args:
        offset: ROM offset to align
        sprite_width: Sprite width in pixels (default: 16)

    Returns:
        Offset aligned to sprite boundary
    """
    sprite_size_bytes = sprite_width * sprite_width // 2
    return (offset // sprite_size_bytes) * sprite_size_bytes


def calculate_tiles_per_sprite(sprite_width: int = 16) -> int:
    """
    Calculate number of 8x8 tiles in a sprite.

    Args:
        sprite_width: Sprite width in pixels (must be multiple of 8)

    Returns:
        Number of 8x8 tiles
    """
    tiles_horizontal = sprite_width // TILE_WIDTH
    tiles_vertical = sprite_width // TILE_HEIGHT
    return tiles_horizontal * tiles_vertical


def calculate_sprite_size_bytes(sprite_width: int = 16, bpp: int = 4) -> int:
    """
    Calculate sprite size in bytes for given dimensions and color depth.

    Args:
        sprite_width: Sprite width in pixels (default: 16)
        bpp: Bits per pixel (default: 4 for SNES 4bpp format)

    Returns:
        Size in bytes
    """
    total_pixels = sprite_width * sprite_width
    return (total_pixels * bpp) // 8
