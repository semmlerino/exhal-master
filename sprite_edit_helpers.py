#!/usr/bin/env python3
"""
Helper functions for sprite editing workflow
Provides convenient wrappers for common operations
"""

import struct


def parse_cgram(cgram_file: str) -> list[list[tuple[int, int, int]]]:
    """
    Parse CGRAM file and return all palettes as list of RGB tuples.

    Args:
        cgram_file: Path to CGRAM dump file

    Returns:
        List of 16 palettes, each containing 16 colors as (r, g, b) tuples
    """
    palettes = []

    with open(cgram_file, "rb") as f:
        cgram_data = f.read()

    for pal_idx in range(16):
        colors = []
        for color_idx in range(16):
            offset = (pal_idx * 16 + color_idx) * 2
            if offset + 2 <= len(cgram_data):
                bgr555 = struct.unpack("<H", cgram_data[offset:offset+2])[0]

                # Convert BGR555 to RGB888
                r = ((bgr555 >> 0) & 0x1F) * 8
                g = ((bgr555 >> 5) & 0x1F) * 8
                b = ((bgr555 >> 10) & 0x1F) * 8

                colors.append((r, g, b))
            else:
                colors.append((0, 0, 0))

        palettes.append(colors)

    return palettes


def bgr555_to_rgb(bgr555: int) -> tuple[int, int, int]:
    """
    Convert BGR555 to RGB tuple.

    Args:
        bgr555: 16-bit BGR555 value

    Returns:
        (r, g, b) tuple with values 0-255
    """
    r = ((bgr555 >> 0) & 0x1F) * 8
    g = ((bgr555 >> 5) & 0x1F) * 8
    b = ((bgr555 >> 10) & 0x1F) * 8
    return (r, g, b)


def rgb_to_bgr555(r: int, g: int, b: int) -> int:
    """
    Convert RGB to BGR555.

    Args:
        r, g, b: Color components (0-255)

    Returns:
        16-bit BGR555 value
    """
    r5 = min(31, r // 8)
    g5 = min(31, g // 8)
    b5 = min(31, b // 8)

    return (b5 << 10) | (g5 << 5) | r5


def decode_4bpp_tile(tile_data: bytes) -> list[int]:
    """
    Decode a 4bpp SNES tile to pixel indices.

    Args:
        tile_data: 32 bytes of tile data

    Returns:
        List of 64 pixel values (0-15)
    """
    pixels = []

    for row in range(8):
        # Get the 4 bytes for this row
        bp0 = tile_data[row * 2]
        bp1 = tile_data[row * 2 + 1]
        bp2 = tile_data[row * 2 + 16]
        bp3 = tile_data[row * 2 + 17]

        # Extract each pixel
        for col in range(8):
            bit = 7 - col
            pixel = ((bp0 >> bit) & 1) | \
                    (((bp1 >> bit) & 1) << 1) | \
                    (((bp2 >> bit) & 1) << 2) | \
                    (((bp3 >> bit) & 1) << 3)
            pixels.append(pixel)

    return pixels


def encode_4bpp_tile(pixels: list[int]) -> bytes:
    """
    Encode pixel indices to 4bpp SNES tile format.

    Args:
        pixels: List of 64 pixel values (0-15)

    Returns:
        32 bytes of tile data
    """
    tile_data = bytearray(32)

    for row in range(8):
        bp0 = bp1 = bp2 = bp3 = 0

        for col in range(8):
            pixel = pixels[row * 8 + col] & 0xF
            bit = 7 - col

            bp0 |= ((pixel >> 0) & 1) << bit
            bp1 |= ((pixel >> 1) & 1) << bit
            bp2 |= ((pixel >> 2) & 1) << bit
            bp3 |= ((pixel >> 3) & 1) << bit

        tile_data[row * 2] = bp0
        tile_data[row * 2 + 1] = bp1
        tile_data[row * 2 + 16] = bp2
        tile_data[row * 2 + 17] = bp3

    return bytes(tile_data)
