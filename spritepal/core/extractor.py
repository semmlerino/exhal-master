"""
Core sprite extraction functionality
"""

from typing import Optional
from PIL import Image

from spritepal.utils.constants import (
    BYTES_PER_TILE,
    DEFAULT_TILES_PER_ROW,
    TILE_HEIGHT,
    TILE_WIDTH,
    VRAM_SPRITE_OFFSET,
    VRAM_SPRITE_SIZE,
)
from spritepal.utils.validation import validate_vram_file, validate_offset


class SpriteExtractor:
    """Handles sprite extraction from VRAM dumps"""

    def __init__(self) -> None:
        self.vram_data: Optional[bytes] = None
        self.offset = VRAM_SPRITE_OFFSET
        self.size = VRAM_SPRITE_SIZE
        self.tiles_per_row = DEFAULT_TILES_PER_ROW

    def load_vram(self, vram_path: str) -> None:
        """Load VRAM dump file with validation"""
        # Validate file before loading
        is_valid, error_msg = validate_vram_file(vram_path)
        if not is_valid:
            raise ValueError(f"Invalid VRAM file: {error_msg}")
        
        with open(vram_path, "rb") as f:
            self.vram_data = f.read()

    def extract_tiles(self, offset: Optional[int] = None, size: Optional[int] = None) -> tuple[list[list[list[int]]], int]:
        """Extract tiles from VRAM data"""
        if self.vram_data is None:
            raise ValueError("VRAM data not loaded. Call load_vram() first.")
            
        if offset is None:
            offset = self.offset
        if size is None:
            size = self.size

        # Validate offset
        is_valid, error_msg = validate_offset(offset, len(self.vram_data))
        if not is_valid:
            raise ValueError(f"Invalid offset: {error_msg}")

        # Read sprite data from offset
        if offset + size > len(self.vram_data):
            size = len(self.vram_data) - offset

        sprite_data = self.vram_data[offset : offset + size]

        # Calculate number of tiles
        num_tiles = len(sprite_data) // BYTES_PER_TILE

        # Extract each tile
        tiles = []
        for tile_idx in range(num_tiles):
            tile_offset = tile_idx * BYTES_PER_TILE
            tile_data = sprite_data[tile_offset : tile_offset + BYTES_PER_TILE]

            # Decode 4bpp tile
            pixels = self._decode_4bpp_tile(tile_data)
            tiles.append(pixels)

        return tiles, num_tiles

    def _decode_4bpp_tile(self, tile_data: bytes) -> list[list[int]]:
        """Decode a 4bpp SNES tile to pixel indices"""
        pixels = []

        # 4bpp SNES format: 32 bytes per 8x8 tile
        for y in range(8):
            row = []
            # Get the 4 bytes for this row
            b0 = tile_data[y * 2] if y * 2 < len(tile_data) else 0
            b1 = tile_data[y * 2 + 1] if y * 2 + 1 < len(tile_data) else 0
            b2 = tile_data[y * 2 + 16] if y * 2 + 16 < len(tile_data) else 0
            b3 = tile_data[y * 2 + 17] if y * 2 + 17 < len(tile_data) else 0

            # Decode each pixel in the row
            for x in range(8):
                bit = 7 - x
                pixel = 0
                if b0 & (1 << bit):
                    pixel |= 1
                if b1 & (1 << bit):
                    pixel |= 2
                if b2 & (1 << bit):
                    pixel |= 4
                if b3 & (1 << bit):
                    pixel |= 8
                row.append(pixel)
            pixels.append(row)

        return pixels

    def create_grayscale_image(self, tiles: list[list[list[int]]], tiles_per_row: Optional[int] = None) -> Image.Image:
        """Create a grayscale image from tiles"""
        if tiles_per_row is None:
            tiles_per_row = self.tiles_per_row

        num_tiles = len(tiles)
        rows = (num_tiles + tiles_per_row - 1) // tiles_per_row

        # Create image
        img_width = tiles_per_row * TILE_WIDTH
        img_height = rows * TILE_HEIGHT

        # Create image data as bytes for efficient processing
        img_data = bytearray(img_width * img_height)
        
        # Place tiles directly into byte array
        for tile_idx, pixels in enumerate(tiles):
            tile_x = (tile_idx % tiles_per_row) * TILE_WIDTH
            tile_y = (tile_idx // tiles_per_row) * TILE_HEIGHT

            for y, row in enumerate(pixels):
                row_offset = (tile_y + y) * img_width + tile_x
                # Copy entire row at once
                img_data[row_offset:row_offset + TILE_WIDTH] = row

        # Create image from bytes
        img = Image.frombytes('P', (img_width, img_height), bytes(img_data))
        
        # Set grayscale palette
        grayscale_palette = []
        for i in range(256):
            gray = (i * 255) // 15 if i < 16 else 0
            grayscale_palette.extend([gray, gray, gray])
        img.putpalette(grayscale_palette)

        return img

    def extract_sprites_grayscale(
        self, vram_path: str, output_path: str, offset: Optional[int] = None, size: Optional[int] = None, tiles_per_row: Optional[int] = None
    ) -> tuple[Image.Image, int]:
        """Extract sprites as grayscale image"""
        # Load VRAM
        self.load_vram(vram_path)

        # Extract tiles
        tiles, num_tiles = self.extract_tiles(offset, size)

        # Create image
        img = self.create_grayscale_image(tiles, tiles_per_row)

        # Save
        img.save(output_path)

        return img, num_tiles

    def get_preview_image(self, vram_path: str, offset: Optional[int] = None, size: Optional[int] = None, max_tiles: int = 64) -> tuple[Image.Image, int]:
        """Get a preview image of the sprites"""
        # Load VRAM
        self.load_vram(vram_path)

        # Extract limited tiles for preview
        tiles, num_tiles = self.extract_tiles(offset, size)

        # Limit tiles for preview
        if len(tiles) > max_tiles:
            tiles = tiles[:max_tiles]

        # Use smaller grid for preview
        preview_tiles_per_row = min(8, self.tiles_per_row)

        # Create preview image
        img = self.create_grayscale_image(tiles, preview_tiles_per_row)

        return img, num_tiles
