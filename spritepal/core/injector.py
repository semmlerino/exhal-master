"""
Sprite injection functionality for SpritePal
Handles reinsertion of edited sprites back into VRAM
"""

import json
from typing import Optional

from PIL import Image
from PyQt6.QtCore import QThread, pyqtSignal

from spritepal.utils.constants import (
    TILE_HEIGHT,
    TILE_WIDTH,
    VRAM_SPRITE_OFFSET,
)


def encode_4bpp_tile(tile_pixels: list[int]) -> bytes:
    """
    Encode an 8x8 tile to SNES 4bpp format.
    Adapted from sprite_editor/tile_utils.py
    """
    if len(tile_pixels) != 64:
        raise ValueError(f"Expected 64 pixels, got {len(tile_pixels)}")

    output = bytearray(32)

    for y in range(8):
        bp0 = 0
        bp1 = 0
        bp2 = 0
        bp3 = 0

        # Encode each pixel in the row
        for x in range(8):
            pixel = tile_pixels[y * 8 + x] & 0x0F  # Ensure 4-bit value
            bp0 |= ((pixel & 1) >> 0) << (7 - x)
            bp1 |= ((pixel & 2) >> 1) << (7 - x)
            bp2 |= ((pixel & 4) >> 2) << (7 - x)
            bp3 |= ((pixel & 8) >> 3) << (7 - x)

        # Store bitplanes in SNES format
        output[y * 2] = bp0
        output[y * 2 + 1] = bp1
        output[16 + y * 2] = bp2
        output[16 + y * 2 + 1] = bp3

    return bytes(output)


class SpriteInjector:
    """Handles sprite injection back to VRAM"""

    def __init__(self) -> None:
        self.metadata: Optional[dict] = None
        self.sprite_path: Optional[str] = None
        self.vram_data: Optional[bytearray] = None

    def load_metadata(self, metadata_path: str) -> dict:
        """Load extraction metadata from JSON file"""
        with open(metadata_path) as f:
            self.metadata = json.load(f)
        return self.metadata

    def validate_sprite(self, sprite_path: str) -> tuple[bool, str]:
        """Validate sprite file format and dimensions"""
        try:
            img = Image.open(sprite_path)

            # Check if indexed color mode
            if img.mode != "P":
                return False, f"Image must be in indexed color mode (found {img.mode})"

            # Check dimensions are multiples of 8
            width, height = img.size
            if width % 8 != 0 or height % 8 != 0:
                return (
                    False,
                    f"Image dimensions must be multiples of 8 (found {width}x{height})",
                )

            # Check color count - count actual unique colors used
            unique_colors = len(set(img.getdata()))
            if unique_colors > 16:
                return False, f"Image has too many colors ({unique_colors}, max 16)"

        except Exception as e:
            return False, f"Error validating sprite: {e!s}"
        else:
            self.sprite_path = sprite_path
            return True, "Sprite validation successful"

    def convert_png_to_4bpp(self, png_path: str) -> bytes:
        """Convert PNG to SNES 4bpp tile data"""
        img = Image.open(png_path)

        # Ensure indexed color mode
        if img.mode != "P":
            img = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=16)  # type: ignore

        width, height = img.size
        tiles_x = width // TILE_WIDTH
        tiles_y = height // TILE_HEIGHT

        # Convert to raw pixel data
        pixels = list(img.getdata())

        # Process tiles
        output_data = bytearray()

        for tile_y in range(tiles_y):
            for tile_x in range(tiles_x):
                # Extract 8x8 tile
                tile_pixels = []
                for y in range(TILE_HEIGHT):
                    for x in range(TILE_WIDTH):
                        pixel_x = tile_x * TILE_WIDTH + x
                        pixel_y = tile_y * TILE_HEIGHT + y
                        pixel_index = pixel_y * width + pixel_x

                        if pixel_index < len(pixels):
                            tile_pixels.append(pixels[pixel_index] & 0x0F)
                        else:
                            tile_pixels.append(0)

                # Encode tile
                tile_data = encode_4bpp_tile(tile_pixels)
                output_data.extend(tile_data)

        return bytes(output_data)

    def inject_sprite(
        self,
        sprite_path: str,
        vram_path: str,
        output_path: str,
        offset: Optional[int] = None,
    ) -> tuple[bool, str]:
        """Inject sprite into VRAM at specified offset"""
        try:
            # Use offset from metadata if not provided
            if offset is None and self.metadata and "extraction" in self.metadata:
                offset_str = self.metadata["extraction"].get("vram_offset", "0xC000")
                offset = int(offset_str, 16)
            elif offset is None:
                offset = VRAM_SPRITE_OFFSET

            # Convert PNG to 4bpp
            tile_data = self.convert_png_to_4bpp(sprite_path)

            # Read original VRAM
            with open(vram_path, "rb") as f:
                self.vram_data = bytearray(f.read())

            # Validate offset
            if offset + len(tile_data) > len(self.vram_data):
                return (
                    False,
                    f"Tile data ({len(tile_data)} bytes) would exceed VRAM size at offset 0x{offset:04X}",
                )

            # Inject tile data
            self.vram_data[offset : offset + len(tile_data)] = tile_data

            # Write modified VRAM
            with open(output_path, "wb") as f:
                f.write(self.vram_data)

            return (
                True,
                f"Successfully injected {len(tile_data)} bytes at offset 0x{offset:04X}",
            )

        except Exception as e:
            return False, f"Error injecting sprite: {e!s}"

    def get_extraction_info(self) -> Optional[dict]:
        """Get extraction information from metadata"""
        if self.metadata and "extraction" in self.metadata:
            extraction_info = self.metadata["extraction"]
            return extraction_info if isinstance(extraction_info, dict) else None
        return None


class InjectionWorker(QThread):
    """Worker thread for sprite injection process"""

    progress = pyqtSignal(str)  # status message
    finished = pyqtSignal(bool, str)  # success, message

    def __init__(
        self,
        sprite_path: str,
        vram_input: str,
        vram_output: str,
        offset: int,
        metadata_path: Optional[str] = None,
    ):
        super().__init__()
        self.sprite_path = sprite_path
        self.vram_input = vram_input
        self.vram_output = vram_output
        self.offset = offset
        self.metadata_path = metadata_path
        self.injector = SpriteInjector()

    def run(self) -> None:
        """Run the injection process"""
        try:
            # Load metadata if available
            if self.metadata_path:
                self.progress.emit("Loading metadata...")
                self.injector.load_metadata(self.metadata_path)

            # Validate sprite
            self.progress.emit("Validating sprite file...")
            valid, message = self.injector.validate_sprite(self.sprite_path)
            if not valid:
                self.finished.emit(False, message)
                return

            # Perform injection
            self.progress.emit("Converting sprite to 4bpp format...")
            self.progress.emit(f"Injecting into VRAM at offset 0x{self.offset:04X}...")

            success, message = self.injector.inject_sprite(
                self.sprite_path, self.vram_input, self.vram_output, self.offset
            )

            if success:
                self.progress.emit("Injection complete!")

            self.finished.emit(success, message)

        except Exception as e:
            self.finished.emit(False, f"Unexpected error: {e!s}")
