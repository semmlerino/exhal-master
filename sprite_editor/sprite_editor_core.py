#!/usr/bin/env python3
"""
Core functionality for Kirby Super Star sprite editing
Refactored from sprite_injector.py and sprite_extractor.py
"""

import struct
from typing import Optional, List, Tuple, Dict, Union
from PIL import Image
import os
try:
    from .oam_palette_mapper import OAMPaletteMapper
    from .security_utils import validate_file_path, validate_output_path, SecurityError
    from .constants import *
    from .tile_utils import decode_4bpp_tile, encode_4bpp_tile
    from .palette_utils import read_cgram_palette, get_grayscale_palette
except ImportError:
    from oam_palette_mapper import OAMPaletteMapper
    from security_utils import validate_file_path, validate_output_path, SecurityError
    from constants import *
    from tile_utils import decode_4bpp_tile, encode_4bpp_tile
    from palette_utils import read_cgram_palette, get_grayscale_palette

class SpriteEditorCore:
    """Core sprite editing functionality"""

    def __init__(self) -> None:
        self.oam_mapper: Optional[OAMPaletteMapper] = None

    # Delegate methods for backward compatibility
    @staticmethod
    def decode_4bpp_tile(data: bytes, offset: int) -> List[int]:
        """Decode a single 8x8 4bpp SNES tile."""
        return decode_4bpp_tile(data, offset)

    @staticmethod
    def encode_4bpp_tile(tile_pixels: List[int]) -> bytes:
        """Encode an 8x8 tile to SNES 4bpp format."""
        return encode_4bpp_tile(tile_pixels)

    @staticmethod
    def read_cgram_palette(cgram_file: str, palette_num: int) -> Optional[List[int]]:
        """Read a specific palette from CGRAM dump."""
        return read_cgram_palette(cgram_file, palette_num)

    @staticmethod
    def get_grayscale_palette() -> List[int]:
        """Get default grayscale palette for preview."""
        return get_grayscale_palette()

    def extract_sprites(self, vram_file: str, offset: int, size: int, tiles_per_row: int = DEFAULT_TILES_PER_ROW) -> Tuple[Image.Image, int]:
        """Extract sprites from VRAM dump."""
        try:
            # Validate file path
            vram_file = validate_file_path(vram_file, max_size=MAX_VRAM_FILE_SIZE)

            # Read VRAM data
            with open(vram_file, 'rb') as f:
                f.seek(offset)
                data = f.read(size)

            # Calculate dimensions
            total_tiles = len(data) // BYTES_PER_TILE_4BPP
            tiles_x = tiles_per_row
            tiles_y = (total_tiles + tiles_x - 1) // tiles_x

            width = tiles_x * TILE_WIDTH
            height = tiles_y * TILE_HEIGHT

            # Create indexed color image
            img = Image.new('P', (width, height))
            img.putpalette(get_grayscale_palette())

            # Decode all tiles
            pixels = []
            for tile_idx in range(total_tiles):
                if tile_idx * BYTES_PER_TILE_4BPP + BYTES_PER_TILE_4BPP <= len(data):
                    tile = decode_4bpp_tile(data, tile_idx * BYTES_PER_TILE_4BPP)
                    pixels.extend(tile)

            # Arrange tiles in image
            img_pixels = [0] * (width * height)
            for tile_idx in range(min(total_tiles, tiles_x * tiles_y)):
                tile_x = tile_idx % tiles_x
                tile_y = tile_idx // tiles_x

                for y in range(TILE_HEIGHT):
                    for x in range(TILE_WIDTH):
                        src_idx = tile_idx * PIXELS_PER_TILE + y * TILE_WIDTH + x
                        dst_x = tile_x * 8 + x
                        dst_y = tile_y * 8 + y

                        if src_idx < len(pixels) and dst_y < height and dst_x < width:
                            img_pixels[dst_y * width + dst_x] = pixels[src_idx]

            img.putdata(img_pixels)
            return img, total_tiles

        except (SecurityError, ValueError):
            # Re-raise security and validation errors as-is
            raise
        except (OSError, IOError, IndexError, MemoryError) as e:
            # File operations, data access, and memory errors
            raise RuntimeError(f"Error extracting sprites: {e}") from e

    def png_to_snes(self, png_file: str) -> Tuple[bytes, int]:
        """Convert PNG to SNES 4bpp tile data."""
        try:
            # Validate file path
            png_file = validate_file_path(png_file, max_size=MAX_PNG_FILE_SIZE)

            img = Image.open(png_file)

            # Ensure indexed color mode
            if img.mode != 'P':
                raise ValueError(f"Image must be in indexed color mode (current: {img.mode})")

            width, height = img.size
            tiles_x = (width + 7) // 8  # Round up to next tile
            tiles_y = (height + 7) // 8  # Round up to next tile
            total_tiles = tiles_x * tiles_y

            # Convert to raw pixel data
            pixels = list(img.getdata())

            # Process tiles
            output_data = bytearray()

            for tile_y in range(tiles_y):
                for tile_x in range(tiles_x):
                    # Extract 8x8 tile
                    tile_pixels = []
                    for y in range(8):
                        for x in range(8):
                            pixel_x = tile_x * 8 + x
                            pixel_y = tile_y * 8 + y
                            pixel_index = pixel_y * width + pixel_x

                            if pixel_index < len(pixels):
                                tile_pixels.append(pixels[pixel_index] & PIXEL_4BPP_MASK)
                            else:
                                tile_pixels.append(0)

                    # Encode tile
                    tile_data = encode_4bpp_tile(tile_pixels)
                    output_data.extend(tile_data)

            return bytes(output_data), total_tiles

        except (ValueError, SecurityError):
            # Re-raise validation and security errors as-is
            raise
        except (OSError, IOError, AttributeError) as e:
            # File operations and PIL/Image errors
            raise RuntimeError(f"Error converting PNG: {e}") from e

    def inject_into_vram(self, tile_data: bytes, vram_file: str, offset: int, output_file: Optional[str] = None) -> Union[str, bytes]:
        """Inject tile data into VRAM dump at specified offset."""
        try:
            # Validate file paths
            vram_file = validate_file_path(vram_file, max_size=VRAM_SIZE_ABSOLUTE_MAX)
            if output_file:
                output_file = validate_output_path(output_file)

            # Validate offset is non-negative
            if offset < 0:
                raise ValueError(f"Invalid negative offset: {offset}")

            # Read original VRAM
            with open(vram_file, 'rb') as f:
                vram_data = bytearray(f.read())

            # Validate VRAM size (typical SNES VRAM is 64KB)
            if len(vram_data) > VRAM_SIZE_ABSOLUTE_MAX:
                raise ValueError(f"VRAM file too large: {len(vram_data)} bytes")

            # Validate offset and data size
            if offset > len(vram_data):
                raise ValueError(f"Offset {hex(offset)} exceeds VRAM size")

            if len(tile_data) > TILE_DATA_MAX_SIZE:
                raise ValueError(f"Tile data too large: {len(tile_data)} bytes")

            if offset + len(tile_data) > len(vram_data):
                raise ValueError(f"Tile data ({len(tile_data)} bytes) would exceed VRAM size at offset {hex(offset)}")

            # Inject tile data
            vram_data[offset:offset + len(tile_data)] = tile_data

            # Write modified VRAM
            if output_file:
                with open(output_file, 'wb') as f:
                    f.write(vram_data)
                return output_file
            else:
                return vram_data

        except (ValueError, SecurityError):
            # Re-raise ValueError and SecurityError as-is for validation errors
            raise
        except (OSError, IOError) as e:
            # File operations errors
            raise RuntimeError(f"Error injecting into VRAM: {e}") from e

    def validate_png_for_snes(self, png_file: str) -> Tuple[bool, List[str]]:
        """Validate PNG file is suitable for SNES conversion."""
        try:
            # Validate file path
            png_file = validate_file_path(png_file, max_size=MAX_PNG_FILE_SIZE)

            img = Image.open(png_file)

            issues = []

            # Check color mode
            if img.mode != 'P':
                issues.append(f"Image is in {img.mode} mode, must be indexed (P) mode")

            # Check dimensions
            width, height = img.size
            if width % 8 != 0:
                issues.append(f"Width ({width}) must be multiple of 8")
            if height % 8 != 0:
                issues.append(f"Height ({height}) must be multiple of 8")

            # Check color count
            if img.mode == 'P':
                palette = img.getpalette()
                if palette:
                    colors_used = len(set(img.getdata()))
                    if colors_used > 16:
                        issues.append(f"Too many colors ({colors_used}), maximum is 16")

            return len(issues) == 0, issues

        except (ValueError, SecurityError):
            # Re-raise validation and security errors
            raise
        except (OSError, IOError, AttributeError, RuntimeError) as e:
            # File and PIL/Image errors
            return False, [str(e)]

    def get_vram_info(self, vram_file: str) -> Optional[Dict[str, Union[str, int]]]:
        """Get information about VRAM dump file."""
        try:
            # Validate file path
            vram_file = validate_file_path(vram_file, max_size=VRAM_SIZE_ABSOLUTE_MAX)

            file_size = os.path.getsize(vram_file)

            # Standard VRAM sizes
            if file_size == 65536:
                vram_size = "64KB (Standard)"
            elif file_size == 32768:
                vram_size = "32KB"
            else:
                vram_size = f"{file_size} bytes"

            return {
                'file': vram_file,
                'size': file_size,
                'size_text': vram_size,
                'max_offset': file_size - 1
            }
        except SecurityError:
            # Re-raise security errors
            raise
        except (OSError, IOError):
            # File operations errors
            return None

    def load_oam_mapping(self, oam_file: str) -> bool:
        """Load OAM data for palette mapping"""
        try:
            # Validate file path
            oam_file = validate_file_path(oam_file, max_size=2048)  # 2KB max for OAM

            self.oam_mapper = OAMPaletteMapper()
            self.oam_mapper.parse_oam_dump(oam_file)
            self.oam_mapper.build_vram_palette_map()
            return True
        except SecurityError:
            # Re-raise security errors
            raise
        except (OSError, IOError, AttributeError, RuntimeError) as e:
            # File operations and OAMPaletteMapper errors
            # TODO: Replace with proper logging
            print(f"Error loading OAM: {e}")
            return False

    def extract_sprites_multi_palette(self, vram_file: str, offset: int, size: int, cgram_file: str, tiles_per_row: int = 16) -> Tuple[Dict[str, Image.Image], int]:
        """Extract sprites with multiple palette previews based on OAM data"""
        try:
            # First extract the base sprite data
            base_img, total_tiles = self.extract_sprites(vram_file, offset, size, tiles_per_row)

            # If no OAM mapper, return single palette
            if not self.oam_mapper:
                return {'palette_0': base_img}, total_tiles

            # Get active palettes from OAM
            active_palettes = self.oam_mapper.get_active_palettes()

            # Create images for each active palette
            palette_images = {}

            for pal_num in active_palettes:
                # Create a copy of the base image
                img = base_img.copy()

                # Apply the palette
                if cgram_file and os.path.exists(cgram_file):
                    palette = read_cgram_palette(cgram_file, pal_num)
                    if palette:
                        img.putpalette(palette)

                palette_images[f'palette_{pal_num}'] = img

            return palette_images, total_tiles

        except (OSError, IOError, RuntimeError) as e:
            raise RuntimeError(f"Error extracting multi-palette sprites: {e}") from e

    def extract_sprites_with_correct_palettes(self, vram_file: str, offset: int, size: int, cgram_file: str, tiles_per_row: int = 16) -> Tuple[Image.Image, int]:
        """Extract sprites with each tile using its OAM-assigned palette"""
        try:
            # Read VRAM data
            with open(vram_file, 'rb') as f:
                f.seek(offset)
                data = f.read(size)

            # Calculate dimensions
            total_tiles = len(data) // BYTES_PER_TILE_4BPP
            tiles_x = tiles_per_row
            tiles_y = (total_tiles + tiles_x - 1) // tiles_x

            width = tiles_x * TILE_WIDTH
            height = tiles_y * TILE_HEIGHT

            # Create RGBA image for multi-palette rendering
            img = Image.new('RGBA', (width, height), (0, 0, 0, 0))

            # Load all palettes from CGRAM
            palettes = []
            if cgram_file and os.path.exists(cgram_file):
                for i in range(16):
                    pal = read_cgram_palette(cgram_file, i)
                    if pal:
                        palettes.append(pal)
                    else:
                        palettes.append(get_grayscale_palette())
            else:
                # Use grayscale if no CGRAM
                for i in range(16):
                    palettes.append(self.get_grayscale_palette())

            # Process each tile
            for tile_idx in range(total_tiles):
                if tile_idx * 32 + 32 <= len(data):
                    # Decode tile
                    tile_data = decode_4bpp_tile(data, tile_idx * 32)

                    # Get palette for this tile
                    tile_offset = offset + (tile_idx * 32)
                    assigned_palette = 0  # Default

                    if self.oam_mapper:
                        pal = self.oam_mapper.get_palette_for_vram_offset(tile_offset)
                        if pal is not None:
                            assigned_palette = pal

                    # Get the palette to use
                    palette = palettes[assigned_palette] if assigned_palette < len(palettes) else palettes[0]

                    # Calculate tile position
                    tile_x = tile_idx % tiles_x
                    tile_y = tile_idx // tiles_x

                    # Draw tile with correct palette
                    for y in range(8):
                        for x in range(8):
                            pixel_idx = y * 8 + x
                            if pixel_idx < len(tile_data):
                                color_idx = tile_data[pixel_idx]
                                if color_idx > 0:  # Skip transparent pixels
                                    # Get RGB from palette
                                    r = palette[color_idx * 3]
                                    g = palette[color_idx * 3 + 1]
                                    b = palette[color_idx * 3 + 2]

                                    # Set pixel
                                    px = tile_x * 8 + x
                                    py = tile_y * 8 + y
                                    if px < width and py < height:
                                        img.putpixel((px, py), (r, g, b, 255))

            return img, total_tiles

        except (OSError, IOError, IndexError) as e:
            raise RuntimeError(f"Error extracting sprites with correct palettes: {e}") from e

    def create_palette_grid_preview(self, vram_file: str, offset: int, size: int, cgram_file: str, tiles_per_row: int = 16) -> Tuple[Image.Image, int]:
        """Create a grid showing sprites with all 16 palettes"""
        try:
            # Extract base sprite data
            base_img, total_tiles = self.extract_sprites(vram_file, offset, size, tiles_per_row)

            # Create grid image (4x4 grid of palettes)
            grid_width = base_img.width * 4
            grid_height = base_img.height * 4
            grid_img = Image.new('RGB', (grid_width, grid_height), (32, 32, 32))

            # Apply each palette and place in grid
            for pal_num in range(16):
                # Create copy with palette
                img = base_img.copy()

                if cgram_file and os.path.exists(cgram_file):
                    palette = read_cgram_palette(cgram_file, pal_num)
                    if palette:
                        img.putpalette(palette)

                # Convert to RGB
                img_rgb = img.convert('RGB')

                # Calculate position in grid
                grid_x = (pal_num % 4) * base_img.width
                grid_y = (pal_num // 4) * base_img.height

                # Paste into grid
                grid_img.paste(img_rgb, (grid_x, grid_y))

                # Add palette number label (optional)
                # This would require PIL.ImageDraw

            return grid_img, total_tiles

        except (OSError, IOError, RuntimeError, AttributeError) as e:
            raise RuntimeError(f"Error creating palette grid: {e}") from e