"""
Core sprite extraction functionality
"""

import os
from pathlib import Path
from PIL import Image

from spritepal.utils.constants import (
    VRAM_SPRITE_OFFSET, VRAM_SPRITE_SIZE,
    BYTES_PER_TILE, TILE_WIDTH, TILE_HEIGHT,
    DEFAULT_TILES_PER_ROW
)


class SpriteExtractor:
    """Handles sprite extraction from VRAM dumps"""
    
    def __init__(self):
        self.vram_data = None
        self.offset = VRAM_SPRITE_OFFSET
        self.size = VRAM_SPRITE_SIZE
        self.tiles_per_row = DEFAULT_TILES_PER_ROW
        
    def load_vram(self, vram_path):
        """Load VRAM dump file"""
        with open(vram_path, 'rb') as f:
            self.vram_data = f.read()
            
    def extract_tiles(self, offset=None, size=None):
        """Extract tiles from VRAM data"""
        if offset is None:
            offset = self.offset
        if size is None:
            size = self.size
            
        # Read sprite data from offset
        if offset + size > len(self.vram_data):
            size = len(self.vram_data) - offset
            
        sprite_data = self.vram_data[offset:offset + size]
        
        # Calculate number of tiles
        num_tiles = len(sprite_data) // BYTES_PER_TILE
        
        # Extract each tile
        tiles = []
        for tile_idx in range(num_tiles):
            tile_offset = tile_idx * BYTES_PER_TILE
            tile_data = sprite_data[tile_offset:tile_offset + BYTES_PER_TILE]
            
            # Decode 4bpp tile
            pixels = self._decode_4bpp_tile(tile_data)
            tiles.append(pixels)
            
        return tiles, num_tiles
        
    def _decode_4bpp_tile(self, tile_data):
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
                if b0 & (1 << bit): pixel |= 1
                if b1 & (1 << bit): pixel |= 2
                if b2 & (1 << bit): pixel |= 4
                if b3 & (1 << bit): pixel |= 8
                row.append(pixel)
            pixels.append(row)
            
        return pixels
        
    def create_grayscale_image(self, tiles, tiles_per_row=None):
        """Create a grayscale image from tiles"""
        if tiles_per_row is None:
            tiles_per_row = self.tiles_per_row
            
        num_tiles = len(tiles)
        rows = (num_tiles + tiles_per_row - 1) // tiles_per_row
        
        # Create image
        img_width = tiles_per_row * TILE_WIDTH
        img_height = rows * TILE_HEIGHT
        
        img = Image.new('P', (img_width, img_height))
        
        # Set grayscale palette
        grayscale_palette = []
        for i in range(256):
            gray = (i * 255) // 15 if i < 16 else 0
            grayscale_palette.extend([gray, gray, gray])
        img.putpalette(grayscale_palette)
        
        # Place tiles
        for tile_idx, pixels in enumerate(tiles):
            tile_x = (tile_idx % tiles_per_row) * TILE_WIDTH
            tile_y = (tile_idx // tiles_per_row) * TILE_HEIGHT
            
            for y, row in enumerate(pixels):
                for x, pixel in enumerate(row):
                    img.putpixel((tile_x + x, tile_y + y), pixel)
                    
        return img
        
    def extract_sprites_grayscale(self, vram_path, output_path, offset=None, size=None, tiles_per_row=None):
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
        
    def get_preview_image(self, vram_path, offset=None, size=None, max_tiles=64):
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