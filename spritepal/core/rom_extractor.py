"""
ROM sprite extraction functionality for SpritePal
Extracts sprites directly from ROM files using HAL decompression
"""

import os
from typing import Optional, Tuple
from PIL import Image

from spritepal.core.hal_compression import HALCompressor, HALCompressionError
from spritepal.core.rom_injector import ROMInjector, SpritePointer
from spritepal.core.sprite_config_loader import SpriteConfigLoader
from spritepal.core.default_palette_loader import DefaultPaletteLoader
from spritepal.core.rom_palette_extractor import ROMPaletteExtractor
from spritepal.utils.constants import TILE_WIDTH, TILE_HEIGHT, BYTES_PER_TILE
from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)


class ROMExtractor:
    """Handles sprite extraction directly from ROM files"""
    
    def __init__(self):
        """Initialize ROM extractor with required components"""
        self.hal_compressor = HALCompressor()
        self.rom_injector = ROMInjector()
        self.default_palette_loader = DefaultPaletteLoader()
        self.rom_palette_extractor = ROMPaletteExtractor()
        self.sprite_config_loader = SpriteConfigLoader()
        
    def extract_sprite_from_rom(
        self,
        rom_path: str,
        sprite_offset: int,
        output_base: str,
        sprite_name: str = ""
    ) -> Tuple[str, dict]:
        """
        Extract sprite from ROM at specified offset.
        
        Args:
            rom_path: Path to ROM file
            sprite_offset: Offset in ROM where sprite data is located
            output_base: Base name for output files (without extension)
            sprite_name: Name of the sprite (e.g., "kirby_normal")
            
        Returns:
            Tuple of (output_png_path, extraction_info)
        """
        try:
            # Read ROM header for validation
            header = self.rom_injector.read_rom_header(rom_path)
            logger.info(f"Extracting from ROM: {header.title}")
            
            # Find and decompress sprite data
            compressed_size, sprite_data = self.rom_injector.find_compressed_sprite(
                open(rom_path, 'rb').read(),
                sprite_offset
            )
            
            logger.info(f"Decompressed sprite from 0x{sprite_offset:X}: "
                       f"{compressed_size} bytes compressed, "
                       f"{len(sprite_data)} bytes decompressed")
            
            # Convert 4bpp data to grayscale PNG
            output_path = f"{output_base}.png"
            tile_count = self._convert_4bpp_to_png(sprite_data, output_path)
            
            # Try to extract palettes from ROM first
            palette_files = []
            rom_palettes_used = False
            
            if sprite_name:
                # Get game configuration
                game_configs = self.sprite_config_loader.config_data.get("games", {})
                game_config = None
                
                # Find matching game config by title
                for game_name, config in game_configs.items():
                    if game_name.upper() in header.title.upper():
                        game_config = config
                        break
                
                if game_config:
                    # Get palette configuration
                    palette_offset, palette_indices = self.rom_palette_extractor.get_palette_config_from_sprite_config(
                        game_config, sprite_name
                    )
                    
                    if palette_offset and palette_indices:
                        # Extract palettes from ROM
                        logger.info(f"Extracting palettes from ROM at offset 0x{palette_offset:X}")
                        palette_files = self.rom_palette_extractor.extract_palettes_from_rom(
                            rom_path, palette_offset, palette_indices, output_base
                        )
                        if palette_files:
                            rom_palettes_used = True
                            logger.info(f"Extracted {len(palette_files)} palettes from ROM")
            
            # Fall back to default palettes if ROM extraction failed
            if not palette_files and sprite_name and self.default_palette_loader.has_default_palettes(sprite_name):
                palette_files = self.default_palette_loader.create_palette_files(sprite_name, output_base)
                logger.info(f"Created {len(palette_files)} default palette files for {sprite_name}")
            
            if not palette_files:
                logger.info("No palettes available - sprite will be grayscale in editor")
            
            # Create extraction info for metadata
            extraction_info = {
                "source_type": "rom",
                "rom_source": os.path.basename(rom_path),
                "rom_offset": f"0x{sprite_offset:X}",
                "sprite_name": sprite_name,
                "compressed_size": compressed_size,
                "tile_count": tile_count,
                "extraction_size": len(sprite_data),
                "rom_title": header.title,
                "rom_checksum": f"0x{header.checksum:04X}",
                "rom_palettes_used": rom_palettes_used,
                "default_palettes_used": len(palette_files) > 0 and not rom_palettes_used,
                "palette_count": len(palette_files)
            }
            
            return output_path, extraction_info
            
        except HALCompressionError as e:
            raise Exception(f"Failed to decompress sprite: {e}")
        except Exception as e:
            logger.error(f"ROM extraction failed: {e}")
            raise
            
    def _convert_4bpp_to_png(self, tile_data: bytes, output_path: str) -> int:
        """
        Convert 4bpp tile data to grayscale PNG.
        
        Args:
            tile_data: Raw 4bpp tile data
            output_path: Path to save PNG
            
        Returns:
            Number of tiles extracted
        """
        # Calculate dimensions
        num_tiles = len(tile_data) // BYTES_PER_TILE
        tiles_per_row = 16  # Standard width for sprite sheets
        
        # Calculate image dimensions
        img_width = tiles_per_row * TILE_WIDTH
        img_height = ((num_tiles + tiles_per_row - 1) // tiles_per_row) * TILE_HEIGHT
        
        # Create grayscale image
        img = Image.new('L', (img_width, img_height), 0)
        
        # Process each tile
        for tile_idx in range(num_tiles):
            # Calculate tile position
            tile_x = (tile_idx % tiles_per_row) * TILE_WIDTH
            tile_y = (tile_idx // tiles_per_row) * TILE_HEIGHT
            
            # Extract tile data
            tile_offset = tile_idx * BYTES_PER_TILE
            tile_bytes = tile_data[tile_offset:tile_offset + BYTES_PER_TILE]
            
            # Convert 4bpp planar to pixels
            for y in range(TILE_HEIGHT):
                for x in range(TILE_WIDTH):
                    # Get pixel value from 4bpp planar format
                    pixel = self._get_4bpp_pixel(tile_bytes, x, y)
                    # Convert 4-bit value to 8-bit grayscale (0-15 -> 0-255)
                    gray_value = pixel * 17
                    img.putpixel((tile_x + x, tile_y + y), gray_value)
        
        # Save as indexed PNG
        img = img.convert('P')
        img.save(output_path, 'PNG')
        
        logger.info(f"Converted {num_tiles} tiles to {output_path}")
        return num_tiles
        
    def _get_4bpp_pixel(self, tile_data: bytes, x: int, y: int) -> int:
        """
        Get pixel value from 4bpp planar tile data.
        
        SNES 4bpp format stores 2 bitplanes together:
        - Planes 0,1 are interleaved in first 16 bytes
        - Planes 2,3 are interleaved in next 16 bytes
        """
        # Calculate byte positions
        row = y
        col = x // 8
        bit = 7 - (x % 8)
        
        # Get bits from each plane
        plane0 = (tile_data[row * 2] >> bit) & 1
        plane1 = (tile_data[row * 2 + 1] >> bit) & 1
        plane2 = (tile_data[16 + row * 2] >> bit) & 1
        plane3 = (tile_data[16 + row * 2 + 1] >> bit) & 1
        
        # Combine bits to get 4-bit value
        return (plane3 << 3) | (plane2 << 2) | (plane1 << 1) | plane0
        
    def get_known_sprite_locations(self, rom_path: str) -> dict[str, SpritePointer]:
        """
        Get known sprite locations for the given ROM.
        
        Args:
            rom_path: Path to ROM file
            
        Returns:
            Dictionary of sprite name to SpritePointer
        """
        try:
            # Read ROM header to identify the game
            header = self.rom_injector.read_rom_header(rom_path)
            
            # Check if this is Kirby Super Star
            if "KIRBY" in header.title.upper():
                return self.rom_injector.find_sprite_locations(rom_path)
            else:
                logger.warning(f"Unknown ROM: {header.title}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to get sprite locations: {e}")
            return {}