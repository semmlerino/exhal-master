"""
Test data generation utilities for SpritePal tests.

This module provides functions to generate consistent test data across
different test files, eliminating duplication and ensuring test consistency.
"""
from __future__ import annotations

import random

from PIL import Image


def generate_sprite_data(
    width: int = 128,
    height: int = 128,
    pattern: str = "gradient",
    tile_size: int = 8
) -> bytearray:
    """
    Generate sprite data for testing.

    Args:
        width: Sprite width in pixels
        height: Sprite height in pixels
        pattern: Data pattern - "gradient", "checkerboard", "random", "tiles"
        tile_size: Size of tiles for tile-based patterns

    Returns:
        bytearray containing sprite data
    """
    data = bytearray(width * height)

    if pattern == "gradient":
        # Create a gradient pattern
        for y in range(height):
            for x in range(width):
                value = int((x + y) / (width + height) * 255) % 16
                data[y * width + x] = value

    elif pattern == "checkerboard":
        # Create a checkerboard pattern
        for y in range(height):
            for x in range(width):
                if (x // tile_size + y // tile_size) % 2 == 0:
                    data[y * width + x] = 15
                else:
                    data[y * width + x] = 0

    elif pattern == "tiles":
        # Create distinct tile patterns
        tiles_x = width // tile_size
        tiles_y = height // tile_size

        for tile_y in range(tiles_y):
            for tile_x in range(tiles_x):
                tile_value = (tile_x + tile_y) % 16

                for y in range(tile_size):
                    for x in range(tile_size):
                        pixel_x = tile_x * tile_size + x
                        pixel_y = tile_y * tile_size + y

                        if pixel_x < width and pixel_y < height:
                            data[pixel_y * width + pixel_x] = tile_value

    elif pattern == "random":
        # Create random data with seed for reproducibility
        random.seed(42)
        for i in range(len(data)):
            data[i] = random.randint(0, 15)

    else:
        # Default: simple incrementing pattern
        for i in range(len(data)):
            data[i] = i % 16

    return data

def generate_palette_data(
    palette_count: int = 16,
    colors_per_palette: int = 16,
    style: str = "varied"
) -> list[list[list[int]]]:
    """
    Generate palette data for testing.

    Args:
        palette_count: Number of palettes to generate
        colors_per_palette: Number of colors per palette
        style: Palette style - "varied", "grayscale", "rainbow", "monochrome"

    Returns:
        List of palettes, each containing RGB color values
    """
    palettes = []

    for palette_idx in range(palette_count):
        palette = []

        for color_idx in range(colors_per_palette):
            if style == "grayscale":
                # Grayscale palette
                gray_value = int(color_idx / colors_per_palette * 255)
                color = [gray_value, gray_value, gray_value]

            elif style == "rainbow":
                # Rainbow palette
                hue = color_idx / colors_per_palette
                rgb = _hsv_to_rgb(hue, 1.0, 1.0)
                color = [int(c * 255) for c in rgb]

            elif style == "monochrome":
                # Single color with brightness variations
                base_hue = palette_idx / palette_count
                brightness = color_idx / colors_per_palette
                rgb = _hsv_to_rgb(base_hue, 1.0, brightness)
                color = [int(c * 255) for c in rgb]

            else:  # "varied"
                # Varied colors with consistent patterns
                red = (palette_idx * 16 + color_idx * 8) % 256
                green = (palette_idx * 8 + color_idx * 16) % 256
                blue = (palette_idx * 24 + color_idx * 4) % 256
                color = [red, green, blue]

            palette.append(color)

        palettes.append(palette)

    return palettes

def generate_rom_data(
    size: int = 0x400000,  # 4MB
    add_sprites: bool = True,
    sprite_count: int = 10
) -> bytearray:
    """
    Generate ROM data for testing.

    Args:
        size: ROM size in bytes
        add_sprites: Whether to add sprite data
        sprite_count: Number of sprites to embed

    Returns:
        bytearray containing ROM data
    """
    data = bytearray(size)

    # Fill with pseudo-random data to simulate ROM content
    random.seed(12345)
    for i in range(size):
        data[i] = random.randint(0, 255)

    if add_sprites:
        # Add some recognizable sprite patterns at known offsets
        sprite_size = 32 * 32  # 32x32 pixels

        for sprite_idx in range(sprite_count):
            # Place sprites at regular intervals
            offset = 0x100000 + sprite_idx * sprite_size * 2

            if offset + sprite_size <= size:
                sprite_data = generate_sprite_data(32, 32, "tiles")
                data[offset:offset + len(sprite_data)] = sprite_data

    return data

def create_test_image(
    width: int = 128,
    height: int = 128,
    mode: str = "L",
    pattern: str = "gradient"
) -> Image.Image:
    """
    Create a test image for image processing tests.

    Args:
        width: Image width
        height: Image height
        mode: PIL image mode ("L", "RGB", "RGBA", "P")
        pattern: Image pattern

    Returns:
        PIL Image object
    """
    if mode == "L":
        # Grayscale image
        sprite_data = generate_sprite_data(width, height, pattern)
        # Convert 4-bit values to 8-bit grayscale
        gray_data = bytes(value * 17 for value in sprite_data)
        img = Image.frombytes("L", (width, height), gray_data)

    elif mode == "RGB":
        # RGB color image
        rgb_data = bytearray(width * height * 3)
        sprite_data = generate_sprite_data(width, height, pattern)

        for i, pixel_value in enumerate(sprite_data):
            rgb_data[i * 3] = pixel_value * 17      # Red
            rgb_data[i * 3 + 1] = (pixel_value * 13) % 256  # Green
            rgb_data[i * 3 + 2] = (pixel_value * 19) % 256  # Blue

        img = Image.frombytes("RGB", (width, height), bytes(rgb_data))

    elif mode == "P":
        # Indexed color image with palette
        sprite_data = generate_sprite_data(width, height, pattern)
        img = Image.new("P", (width, height))
        img.putdata(sprite_data)

        # Create a simple palette
        palette_data = []
        for i in range(256):
            if i < 16:
                # Use actual colors for first 16 entries
                palette_data.extend([i * 17, (i * 13) % 256, (i * 19) % 256])
            else:
                # Fill rest with black
                palette_data.extend([0, 0, 0])

        img.putpalette(palette_data)

    else:
        # Default: create simple solid color image
        img = Image.new(mode, (width, height), 128)

    return img

def _hsv_to_rgb(h: float, s: float, v: float) -> tuple[float, float, float]:
    """Convert HSV color to RGB."""
    import colorsys
    return colorsys.hsv_to_rgb(h, s, v)

def generate_oam_data(entry_count: int = 128) -> bytearray:
    """
    Generate OAM (Object Attribute Memory) data for testing.

    Args:
        entry_count: Number of OAM entries to generate

    Returns:
        bytearray containing OAM data
    """
    data = bytearray(entry_count * 4)  # 4 bytes per OAM entry

    for i in range(entry_count):
        offset = i * 4

        # X position (0-255)
        data[offset] = (i * 16) % 256

        # Y position (0-223, avoid bottom of screen)
        data[offset + 1] = (i * 12) % 224

        # Tile index
        data[offset + 2] = i % 256

        # Attributes (palette, priority, flip flags)
        palette = (i % 8) << 1  # Palette 0-7 in bits 1-3
        data[offset + 3] = 0x20 | palette  # Bit 5 set for visibility

    return data

def generate_cgram_data(palette_count: int = 16) -> bytearray:
    """
    Generate CGRAM (Color Graphics RAM) data for testing.

    Args:
        palette_count: Number of 16-color palettes to generate

    Returns:
        bytearray containing CGRAM data in BGR555 format
    """
    data = bytearray(palette_count * 16 * 2)  # 2 bytes per color

    palettes = generate_palette_data(palette_count, 16, "varied")

    for palette_idx, palette in enumerate(palettes):
        for color_idx, color in enumerate(palette):
            offset = (palette_idx * 16 + color_idx) * 2

            # Convert RGB888 to BGR555
            r, g, b = color
            r555 = (r >> 3) & 0x1F
            g555 = (g >> 3) & 0x1F
            b555 = (b >> 3) & 0x1F

            # Pack as little-endian BGR555
            bgr555 = (b555 << 10) | (g555 << 5) | r555
            data[offset] = bgr555 & 0xFF
            data[offset + 1] = (bgr555 >> 8) & 0xFF

    return data
