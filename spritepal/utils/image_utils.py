"""Image utility functions for SpritePal"""

import io
import logging
from typing import Optional

from PIL import Image
from PyQt6.QtGui import QPixmap

logger = logging.getLogger(__name__)


def pil_to_qpixmap(pil_image: Image.Image) -> Optional[QPixmap]:
    """
    Convert PIL image to QPixmap with proper error handling.

    Args:
        pil_image: PIL Image object to convert

    Returns:
        QPixmap object or None if conversion fails
    """
    if not pil_image:
        return None

    try:
        # Convert PIL image to QPixmap through bytes buffer
        buffer = io.BytesIO()
        pil_image.save(buffer, format="PNG")
        buffer.seek(0)

        pixmap = QPixmap()
        if pixmap.loadFromData(buffer.read()):
            return pixmap
        logger.error("Failed to load pixmap from buffer data")
        return None

    except Exception as e:
        logger.exception(f"Failed to convert PIL to QPixmap: {e}")
        return None


def create_checkerboard_pattern(width: int, height: int,
                              tile_size: int = 8,
                              color1: tuple[int, int, int] = (200, 200, 200),
                              color2: tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """
    Create a checkerboard pattern image.

    Args:
        width: Image width in pixels
        height: Image height in pixels
        tile_size: Size of each checkerboard tile
        color1: RGB tuple for first color
        color2: RGB tuple for second color

    Returns:
        PIL Image with checkerboard pattern
    """
    img = Image.new("RGB", (width, height))

    # Create checkerboard using efficient array operations
    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            # Determine color based on position
            is_even = ((x // tile_size) + (y // tile_size)) % 2 == 0
            color = color1 if is_even else color2

            # Fill tile area
            for dy in range(min(tile_size, height - y)):
                for dx in range(min(tile_size, width - x)):
                    img.putpixel((x + dx, y + dy), color)

    return img
