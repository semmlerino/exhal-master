#!/usr/bin/env python3
"""
Common utilities for the pixel editor
Extracted to avoid duplication between modules
"""

# Standard library imports
import traceback
from datetime import datetime, timezone
from pathlib import Path, PosixPath, WindowsPath
from typing import Any, Optional, Union

# ================================================================================
# Debug Configuration
# ================================================================================

DEBUG_MODE = True  # Set to False to disable debug logging


# ================================================================================
# Debug Logging Utilities
# ================================================================================


def debug_log(category: str, message: str, level: str = "INFO") -> None:
    """Enhanced debug logging with timestamps and categories

    Args:
        category: Category for the log message (e.g., "EDITOR", "CANVAS", "PALETTE")
        message: The log message to display
        level: Log level ("INFO", "WARNING", "ERROR", "DEBUG")
    """
    if not DEBUG_MODE:
        return

    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
    formatted_msg = f"[{timestamp}] [{category}] [{level}] {message}"

    # Color coding for different log levels
    if level == "ERROR":
        print(f"\033[91m{formatted_msg}\033[0m")  # Red
    elif level == "WARNING":
        print(f"\033[93m{formatted_msg}\033[0m")  # Yellow
    elif level == "DEBUG":
        print(f"\033[94m{formatted_msg}\033[0m")  # Blue
    else:
        print(formatted_msg)  # Default


def debug_color(color_index: int, rgb: Optional[tuple[int, int, int]] = None) -> str:
    """Format color information for debugging

    Args:
        color_index: The palette index of the color
        rgb: Optional RGB tuple for the color

    Returns:
        Formatted string with color information
    """
    if rgb:
        hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        return f"Index {color_index} (RGB: {rgb}, Hex: {hex_color})"
    return f"Index {color_index}"


def debug_exception(category: str, exception: Exception) -> None:
    """Log exceptions with full traceback

    Args:
        category: Category for the log message
        exception: The exception to log
    """
    debug_log(
        category, f"Exception: {type(exception).__name__}: {exception!s}", "ERROR"
    )
    if DEBUG_MODE:
        traceback.print_exc()


# ================================================================================
# Color Validation Utilities
# ================================================================================


def validate_color_index(index: int, max_colors: int = 16) -> int:
    """Validate and clamp a color index to valid range

    Args:
        index: The color index to validate
        max_colors: Maximum number of colors (default 16 for 4bpp)

    Returns:
        Clamped color index in valid range
    """
    return max(0, min(max_colors - 1, int(index)))


def validate_rgb_color(color: Union[tuple, list]) -> tuple[int, int, int]:
    """Validate and normalize an RGB color tuple

    Args:
        color: RGB color as tuple or list

    Returns:
        Valid RGB tuple with values clamped to 0-255
    """
    if not isinstance(color, (tuple, list)) or len(color) < 3:
        return (0, 0, 0)

    r = max(0, min(255, int(color[0]) if color[0] is not None else 0))
    g = max(0, min(255, int(color[1]) if color[1] is not None else 0))
    b = max(0, min(255, int(color[2]) if color[2] is not None else 0))

    return (r, g, b)


def is_grayscale_color(rgb: tuple[int, int, int]) -> bool:
    """Check if an RGB color is grayscale

    Args:
        rgb: RGB color tuple

    Returns:
        True if the color is grayscale (R=G=B)
    """
    return rgb[0] == rgb[1] == rgb[2]


def is_grayscale_palette(colors: list[tuple[int, int, int]]) -> bool:
    """Check if an entire palette is grayscale

    Args:
        colors: List of RGB color tuples

    Returns:
        True if all colors in the palette are grayscale
    """
    return all(is_grayscale_color(color) for color in colors)


# ================================================================================
# Palette Extraction Helpers
# ================================================================================


def extract_palette_from_pil_image(
    pil_image: Any, max_colors: int = 16
) -> list[tuple[int, int, int]]:
    """Extract palette colors from a PIL image

    Args:
        pil_image: PIL Image object with palette
        max_colors: Maximum number of colors to extract

    Returns:
        List of RGB color tuples
    """
    colors = []

    if hasattr(pil_image, "palette") and pil_image.palette:
        palette_data = pil_image.palette.palette
        for i in range(max_colors):
            if i * 3 + 2 < len(palette_data):
                r = palette_data[i * 3]
                g = palette_data[i * 3 + 1]
                b = palette_data[i * 3 + 2]
                colors.append((r, g, b))
            else:
                colors.append((0, 0, 0))
    else:
        # No palette, return default grayscale
        for i in range(max_colors):
            gray = (i * 255) // (max_colors - 1)
            colors.append((gray, gray, gray))

    return colors


def create_grayscale_palette(num_colors: int = 16) -> list[tuple[int, int, int]]:
    """Create a grayscale palette with the specified number of colors

    Args:
        num_colors: Number of colors in the palette

    Returns:
        List of RGB color tuples forming a grayscale gradient
    """
    colors = []
    for i in range(num_colors):
        gray = (i * 255) // (num_colors - 1)
        colors.append((gray, gray, gray))
    return colors


def create_indexed_palette(colors: list[tuple[int, int, int]]) -> list[int]:
    """Create a flat palette list for PIL putpalette

    Args:
        colors: List of RGB color tuples

    Returns:
        Flat list of RGB values suitable for PIL Image.putpalette()
    """
    palette: list[int] = []
    for color in colors:
        palette.extend(validate_rgb_color(color))

    # Pad to 256 colors (768 values)
    while len(palette) < 768:
        palette.extend([0, 0, 0])

    return palette


# ================================================================================
# Palette File Validation
# ================================================================================


def validate_palette_file(data: dict) -> bool:
    """Validate that a JSON file is a valid palette file

    Args:
        data: Dictionary loaded from JSON file

    Returns:
        True if the file has valid palette structure
    """
    try:
        # Check for expected structure
        if "palette" in data and "colors" in data["palette"]:
            colors = data["palette"]["colors"]
            return len(colors) >= 16 and all(
                isinstance(color, (list, tuple)) and len(color) >= 3 for color in colors
            )
    except (KeyError, TypeError, AttributeError):
        return False

    return False


def validate_metadata_palette(data: dict) -> bool:
    """Validate that a JSON file contains metadata format palettes

    Args:
        data: Dictionary loaded from JSON file

    Returns:
        True if the file has valid metadata palette structure
    """
    try:
        # Check for palette_colors structure
        if "palette_colors" in data:
            palette_colors = data["palette_colors"]
            # Check if it has sprite palettes (8-15)
            return any(str(i) in palette_colors for i in range(8, 16))
    except (KeyError, TypeError, AttributeError):
        return False

    return False


# ================================================================================
# Color Analysis Utilities
# ================================================================================


def count_unique_colors(colors: list[tuple[int, int, int]]) -> int:
    """Count the number of unique colors in a palette

    Args:
        colors: List of RGB color tuples

    Returns:
        Number of unique colors
    """
    return len(set(colors))


def count_non_black_colors(colors: list[tuple[int, int, int]]) -> int:
    """Count the number of non-black colors in a palette

    Args:
        colors: List of RGB color tuples

    Returns:
        Number of colors that are not pure black (0, 0, 0)
    """
    return sum(1 for color in colors if color != (0, 0, 0))


def get_color_brightness(rgb: tuple[int, int, int]) -> float:
    """Calculate the perceived brightness of a color

    Args:
        rgb: RGB color tuple

    Returns:
        Brightness value (0-255)
    """
    # Using standard luminance formula
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


def should_use_white_text(rgb: tuple[int, int, int]) -> bool:
    """Determine if white text should be used on a given background color

    Args:
        rgb: RGB color tuple of the background

    Returns:
        True if white text should be used, False for black text
    """
    return get_color_brightness(rgb) < 128


# ================================================================================
# Default Palettes
# ================================================================================

# Default grayscale palette for proper visualization
DEFAULT_GRAYSCALE_PALETTE = [
    (0, 0, 0),  # 0 - Black (transparent)
    (17, 17, 17),  # 1
    (34, 34, 34),  # 2
    (51, 51, 51),  # 3
    (68, 68, 68),  # 4
    (85, 85, 85),  # 5
    (102, 102, 102),  # 6
    (119, 119, 119),  # 7
    (136, 136, 136),  # 8
    (153, 153, 153),  # 9
    (170, 170, 170),  # 10
    (187, 187, 187),  # 11
    (204, 204, 204),  # 12
    (221, 221, 221),  # 13
    (238, 238, 238),  # 14
    (255, 255, 255),  # 15 - White
]

# Default color palette (for color mode)
DEFAULT_COLOR_PALETTE = [
    (0, 0, 0),  # 0 - Black (transparent)
    (255, 183, 197),  # 1 - Kirby pink
    (255, 255, 255),  # 2 - White
    (64, 64, 64),  # 3 - Dark gray (outline)
    (255, 0, 0),  # 4 - Red
    (0, 0, 255),  # 5 - Blue
    (255, 220, 220),  # 6 - Light pink
    (200, 120, 150),  # 7 - Dark pink
    (255, 255, 0),  # 8 - Yellow
    (0, 255, 0),  # 9 - Green
    (255, 128, 0),  # 10 - Orange
    (128, 0, 255),  # 11 - Purple
    (0, 128, 128),  # 12 - Teal
    (128, 128, 0),  # 13 - Olive
    (128, 128, 128),  # 14 - Gray
    (192, 192, 192),  # 15 - Light gray
]


# ================================================================================
# JSON Serialization Utilities
# ================================================================================


def sanitize_for_json(obj: Any) -> Any:
    """Convert non-JSON-serializable objects to JSON-safe types.

    Args:
        obj: Object to sanitize

    Returns:
        JSON-safe version of the object

    Notes:
        Handles Path objects, bytes, and other non-serializable types
    """
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, (Path, WindowsPath, PosixPath)):
        return str(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="ignore")
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    if hasattr(obj, "__dict__"):
        # Try to convert objects with __dict__ to a string representation
        return str(obj)
    # Fallback to string representation
    return str(obj)
