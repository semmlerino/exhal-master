#!/usr/bin/env python3
"""
Core functionality for Kirby Super Star sprite editing
Refactored from sprite_injector.py and sprite_extractor.py
"""

import os
from typing import Dict, List, Optional, Tuple, Union

from PIL import Image

try:
    from .constants import (
        BYTES_PER_TILE_4BPP, DEFAULT_TILES_PER_ROW, MAX_PNG_FILE_SIZE,
        MAX_VRAM_FILE_SIZE, PIXELS_PER_TILE, PIXEL_4BPP_MASK,
        TILE_DATA_MAX_SIZE, TILE_HEIGHT, TILE_WIDTH, VRAM_SIZE_ABSOLUTE_MAX
    )
    from .logging_config import get_logger
    from .oam_palette_mapper import OAMPaletteMapper
    from .palette_utils import get_grayscale_palette, read_cgram_palette
    from .security_utils import (SecurityError, validate_file_path,
                                 validate_output_path)
    from .tile_utils import decode_4bpp_tile, encode_4bpp_tile
except ImportError:
    from constants import (
        BYTES_PER_TILE_4BPP, DEFAULT_TILES_PER_ROW, MAX_PNG_FILE_SIZE,
        MAX_VRAM_FILE_SIZE, PIXELS_PER_TILE, PIXEL_4BPP_MASK,
        TILE_DATA_MAX_SIZE, TILE_HEIGHT, TILE_WIDTH, VRAM_SIZE_ABSOLUTE_MAX
    )
    from logging_config import get_logger
    from oam_palette_mapper import OAMPaletteMapper
    from palette_utils import get_grayscale_palette, read_cgram_palette
    from security_utils import (SecurityError, validate_file_path,
                                validate_output_path)
    from tile_utils import decode_4bpp_tile, encode_4bpp_tile


class SpriteEditorCore:
    """Core sprite editing functionality"""

    def __init__(self) -> None:
        self.oam_mapper: Optional[OAMPaletteMapper] = None
        self.logger = get_logger('core')

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
    def read_cgram_palette(cgram_file: str,
                           palette_num: int) -> Optional[List[int]]:
        """Read a specific palette from CGRAM dump."""
        return read_cgram_palette(cgram_file, palette_num)

    @staticmethod
    def get_grayscale_palette() -> List[int]:
        """Get default grayscale palette for preview."""
        return get_grayscale_palette()

    def _decode_all_tiles(self, data: bytes) -> List[int]:
        """Decode all tiles from VRAM data into a flat pixel array."""
        pixels = []
        total_tiles = len(data) // BYTES_PER_TILE_4BPP
        for tile_idx in range(total_tiles):
            if tile_idx * BYTES_PER_TILE_4BPP + \
                    BYTES_PER_TILE_4BPP <= len(data):
                tile = decode_4bpp_tile(data, tile_idx * BYTES_PER_TILE_4BPP)
                pixels.extend(tile)
        return pixels

    def _arrange_tiles_in_indexed_image(
            self, pixels: List[int], total_tiles: int, tiles_x: int, tiles_y: int, width: int, height: int) -> List[int]:
        """Arrange decoded tile pixels into final image layout."""
        img_pixels = [0] * (width * height)
        for tile_idx in range(min(total_tiles, tiles_x * tiles_y)):
            tile_x = tile_idx % tiles_x
            tile_y = tile_idx // tiles_x

            for y in range(TILE_HEIGHT):
                for x in range(TILE_WIDTH):
                    src_idx = tile_idx * PIXELS_PER_TILE + y * TILE_WIDTH + x
                    dst_x = tile_x * TILE_WIDTH + x
                    dst_y = tile_y * TILE_HEIGHT + y

                    if src_idx < len(
                            pixels) and dst_y < height and dst_x < width:
                        img_pixels[dst_y * width + dst_x] = pixels[src_idx]
        return img_pixels

    def extract_sprites(self, vram_file: str, offset: int, size: int,
                        tiles_per_row: int = DEFAULT_TILES_PER_ROW) -> Tuple[Image.Image, int]:
        """Extract sprites from VRAM dump."""
        try:
            # Validate file path
            vram_file = validate_file_path(
                vram_file, max_size=MAX_VRAM_FILE_SIZE)

            # Read VRAM data
            with open(vram_file, 'rb') as f:
                f.seek(offset)
                data = f.read(size)

            # Calculate dimensions
            total_tiles, tiles_x, tiles_y, width, height = self._calculate_sprite_dimensions(
                len(data), tiles_per_row)

            # Create indexed color image
            img = Image.new('P', (width, height))
            img.putpalette(get_grayscale_palette())

            # Decode all tiles and arrange in image
            pixels = self._decode_all_tiles(data)
            img_pixels = self._arrange_tiles_in_indexed_image(
                pixels, total_tiles, tiles_x, tiles_y, width, height)

            img.putdata(img_pixels)
            return img, total_tiles

        except (SecurityError, ValueError):
            # Re-raise security and validation errors as-is
            raise
        except (OSError, IOError, IndexError, MemoryError) as e:
            # File operations, data access, and memory errors
            raise RuntimeError(f"Error extracting sprites: {e}") from e

    def _calculate_tile_grid_dimensions(
            self, width: int, height: int) -> Tuple[int, int, int]:
        """Calculate tile grid dimensions from image size."""
        tiles_x = (width + 7) // 8  # Round up to next tile
        tiles_y = (height + 7) // 8  # Round up to next tile
        total_tiles = tiles_x * tiles_y
        return tiles_x, tiles_y, total_tiles

    def _extract_tile_from_image(
            self, pixels: List[int], tile_x: int, tile_y: int, img_width: int) -> List[int]:
        """Extract an 8x8 tile from image pixel data."""
        tile_pixels = []
        for y in range(TILE_HEIGHT):
            for x in range(TILE_WIDTH):
                pixel_x = tile_x * TILE_WIDTH + x
                pixel_y = tile_y * TILE_HEIGHT + y
                pixel_index = pixel_y * img_width + pixel_x

                if pixel_index < len(pixels):
                    tile_pixels.append(pixels[pixel_index] & PIXEL_4BPP_MASK)
                else:
                    tile_pixels.append(0)
        return tile_pixels

    def png_to_snes(self, png_file: str) -> Tuple[bytes, int]:
        """Convert PNG to SNES 4bpp tile data."""
        try:
            # Validate file path
            png_file = validate_file_path(png_file, max_size=MAX_PNG_FILE_SIZE)

            img = Image.open(png_file)

            # Ensure indexed color mode
            if img.mode != 'P':
                raise ValueError(
                    f"Image must be in indexed color mode (current: {img.mode})")

            width, height = img.size
            tiles_x, tiles_y, total_tiles = self._calculate_tile_grid_dimensions(
                width, height)

            # Convert to raw pixel data
            pixels = list(img.getdata())

            # Process tiles
            output_data = bytearray()

            for tile_y in range(tiles_y):
                for tile_x in range(tiles_x):
                    # Extract and encode 8x8 tile
                    tile_pixels = self._extract_tile_from_image(
                        pixels, tile_x, tile_y, width)
                    tile_data = encode_4bpp_tile(tile_pixels)
                    output_data.extend(tile_data)

            return bytes(output_data), total_tiles

        except (ValueError, SecurityError):
            # Re-raise validation and security errors as-is
            raise
        except (OSError, IOError, AttributeError) as e:
            # File operations and PIL/Image errors
            raise RuntimeError(f"Error converting PNG: {e}") from e

    def inject_into_vram(self, tile_data: bytes, vram_file: str, offset: int,
                         output_file: Optional[str] = None) -> Union[str, bytes]:
        """Inject tile data into VRAM dump at specified offset."""
        try:
            # Validate file paths
            vram_file = validate_file_path(
                vram_file, max_size=VRAM_SIZE_ABSOLUTE_MAX)
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
                raise ValueError(
                    f"VRAM file too large: {
                        len(vram_data)} bytes")

            # Validate offset and data size
            if offset > len(vram_data):
                raise ValueError(f"Offset {hex(offset)} exceeds VRAM size")

            if len(tile_data) > TILE_DATA_MAX_SIZE:
                raise ValueError(
                    f"Tile data too large: {
                        len(tile_data)} bytes")

            if offset + len(tile_data) > len(vram_data):
                raise ValueError(
                    f"Tile data ({
                        len(tile_data)} bytes) would exceed VRAM size at offset {
                        hex(offset)}")

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
                issues.append(
                    f"Image is in {
                        img.mode} mode, must be indexed (P) mode")

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
                        issues.append(
                            f"Too many colors ({colors_used}), maximum is 16")

            return len(issues) == 0, issues

        except (ValueError, SecurityError):
            # Re-raise validation and security errors
            raise
        except (OSError, IOError, AttributeError, RuntimeError) as e:
            # File and PIL/Image errors
            return False, [str(e)]

    def get_vram_info(
            self, vram_file: str) -> Optional[Dict[str, Union[str, int]]]:
        """Get information about VRAM dump file."""
        try:
            # Validate file path
            vram_file = validate_file_path(
                vram_file, max_size=VRAM_SIZE_ABSOLUTE_MAX)

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
            oam_file = validate_file_path(
                oam_file, max_size=2048)  # 2KB max for OAM

            self.oam_mapper = OAMPaletteMapper()
            self.oam_mapper.parse_oam_dump(oam_file)
            self.oam_mapper.build_vram_palette_map()
            return True
        except SecurityError:
            # Re-raise security errors
            raise
        except (OSError, IOError, AttributeError, RuntimeError) as e:
            # File operations and OAMPaletteMapper errors
            self.logger.error(f"Error loading OAM: {e}")
            return False

    def extract_sprites_multi_palette(self, vram_file: str, offset: int, size: int,
                                      cgram_file: str, tiles_per_row: int = 16) -> Tuple[Dict[str, Image.Image], int]:
        """Extract sprites with multiple palette previews based on OAM data"""
        try:
            # Validate file paths
            vram_file = validate_file_path(vram_file, max_size=MAX_VRAM_FILE_SIZE)
            if cgram_file:
                cgram_file = validate_file_path(cgram_file)
            
            # First extract the base sprite data
            base_img, total_tiles = self.extract_sprites(
                vram_file, offset, size, tiles_per_row)

            palette_images = {}
            
            # If we have OAM data, create OAM-correct version first
            if self.oam_mapper and cgram_file and os.path.exists(cgram_file):
                try:
                    oam_correct_img, _ = self.extract_sprites_with_correct_palettes(
                        vram_file, offset, size, cgram_file, tiles_per_row)
                    palette_images['oam_correct'] = oam_correct_img
                except Exception as e:
                    self.logger.warning(f"Could not create OAM-correct image: {e}")

            # Get active palettes from OAM
            if self.oam_mapper:
                active_palettes = self.oam_mapper.get_active_palettes()
                if not active_palettes:
                    # If no active palettes found, show first 8
                    active_palettes = list(range(8))
            else:
                # No OAM data, return single palette
                return {'palette_0': base_img}, total_tiles

            # Create images for each active palette
            for pal_num in active_palettes:
                # Validate palette index
                pal_num = self._validate_palette_index(pal_num)
                
                # Create a copy of the base image
                img = base_img.copy()

                # Apply the palette
                if cgram_file and os.path.exists(cgram_file):
                    palette = read_cgram_palette(cgram_file, pal_num)
                    if palette:
                        img.putpalette(palette)
                else:
                    # Use grayscale if no CGRAM
                    img.putpalette(get_grayscale_palette())

                palette_images[f'palette_{pal_num}'] = img

            return palette_images, total_tiles

        except (OSError, IOError, RuntimeError, SecurityError) as e:
            raise RuntimeError(
                f"Error extracting multi-palette sprites: {e}") from e

    def _calculate_sprite_dimensions(
            self, data_size: int, tiles_per_row: int) -> Tuple[int, int, int, int, int]:
        """Calculate sprite layout dimensions from data size."""
        total_tiles = data_size // BYTES_PER_TILE_4BPP
        tiles_x = tiles_per_row
        tiles_y = (total_tiles + tiles_x - 1) // tiles_x
        width = tiles_x * TILE_WIDTH
        height = tiles_y * TILE_HEIGHT
        return total_tiles, tiles_x, tiles_y, width, height

    def _load_palettes_from_cgram(self, cgram_file: str) -> List[List[int]]:
        """Load all 16 palettes from CGRAM file or use grayscale fallback."""
        palettes = []
        
        # Validate CGRAM file if provided
        if cgram_file:
            try:
                cgram_file = validate_file_path(cgram_file)
                if not os.path.exists(cgram_file):
                    self.logger.warning(f"CGRAM file not found: {cgram_file}, using grayscale palettes")
                    cgram_file = None
            except SecurityError:
                self.logger.error(f"Security error accessing CGRAM file: {cgram_file}")
                cgram_file = None
        
        # Load palettes
        if cgram_file:
            for i in range(16):
                try:
                    pal = read_cgram_palette(cgram_file, i)
                    if pal and len(pal) >= 48:  # Ensure palette has at least 16 colors (16*3 RGB values)
                        palettes.append(pal)
                    else:
                        self.logger.warning(f"Invalid palette {i} in CGRAM, using grayscale")
                        palettes.append(get_grayscale_palette())
                except Exception as e:
                    self.logger.warning(f"Error reading palette {i}: {e}, using grayscale")
                    palettes.append(get_grayscale_palette())
        else:
            # Use grayscale if no CGRAM
            for i in range(16):
                palettes.append(get_grayscale_palette())
        
        return palettes

    def _get_tile_palette_assignment(self, tile_offset: int) -> int:
        """Get palette assignment for a tile at given VRAM offset."""
        if self.oam_mapper:
            pal = self.oam_mapper.get_palette_for_vram_offset(tile_offset)
            if pal is not None:
                return pal
        return 0  # Default palette

    def _draw_tile_to_rgba_image(self, img: Image.Image, tile_data: List[int], palette: List[int],
                                 tile_x: int, tile_y: int, width: int, height: int) -> None:
        """Draw a single tile to RGBA image using specified palette."""
        for y in range(TILE_HEIGHT):
            for x in range(TILE_WIDTH):
                pixel_idx = y * TILE_WIDTH + x
                if pixel_idx < len(tile_data):
                    color_idx = tile_data[pixel_idx]
                    if color_idx > 0:  # Skip transparent pixels
                        # Validate color index
                        color_idx = min(color_idx, 15)  # Clamp to valid range
                        
                        # Ensure palette has enough data
                        palette_idx = color_idx * 3
                        if palette_idx + 2 < len(palette):
                            # Get RGB from palette
                            r = palette[palette_idx]
                            g = palette[palette_idx + 1]
                            b = palette[palette_idx + 2]
                        else:
                            # Fallback to gray if palette is incomplete
                            gray = (color_idx * 255) // 15
                            r = g = b = gray

                        # Set pixel
                        px = tile_x * TILE_WIDTH + x
                        py = tile_y * TILE_HEIGHT + y
                        if px < width and py < height:
                            img.putpixel((px, py), (r, g, b, 255))

    def extract_sprites_with_correct_palettes(
            self, vram_file: str, offset: int, size: int, cgram_file: str, tiles_per_row: int = 16) -> Tuple[Image.Image, int]:
        """Extract sprites with each tile using its OAM-assigned palette"""
        try:
            # Validate file paths
            vram_file = validate_file_path(vram_file, max_size=MAX_VRAM_FILE_SIZE)
            if cgram_file:
                cgram_file = validate_file_path(cgram_file)
            
            # Read VRAM data
            with open(vram_file, 'rb') as f:
                f.seek(offset)
                data = f.read(size)

            # Calculate dimensions
            total_tiles, tiles_x, tiles_y, width, height = self._calculate_sprite_dimensions(
                len(data), tiles_per_row)

            # Create RGBA image for multi-palette rendering
            img = Image.new('RGBA', (width, height), (0, 0, 0, 0))

            # Load all palettes from CGRAM
            palettes = self._load_palettes_from_cgram(cgram_file)

            # Process each tile
            for tile_idx in range(total_tiles):
                if tile_idx * BYTES_PER_TILE_4BPP + \
                        BYTES_PER_TILE_4BPP <= len(data):
                    # Decode tile
                    tile_data = decode_4bpp_tile(
                        data, tile_idx * BYTES_PER_TILE_4BPP)

                    # Get palette for this tile
                    tile_offset = offset + (tile_idx * BYTES_PER_TILE_4BPP)
                    assigned_palette = self._get_tile_palette_assignment(
                        tile_offset)

                    # Get the palette to use
                    palette = palettes[assigned_palette] if assigned_palette < len(
                        palettes) else palettes[0]

                    # Calculate tile position
                    tile_x = tile_idx % tiles_x
                    tile_y = tile_idx // tiles_x

                    # Draw tile with correct palette
                    self._draw_tile_to_rgba_image(
                        img, tile_data, palette, tile_x, tile_y, width, height)

            return img, total_tiles

        except (OSError, IOError, IndexError) as e:
            raise RuntimeError(
                f"Error extracting sprites with correct palettes: {e}") from e

    def create_palette_grid_preview(self, vram_file: str, offset: int, size: int,
                                    cgram_file: str, tiles_per_row: int = 16) -> Tuple[Image.Image, int]:
        """Create a grid showing sprites with all 16 palettes, highlighting active ones"""
        try:
            # Validate file paths
            vram_file = validate_file_path(vram_file, max_size=MAX_VRAM_FILE_SIZE)
            if cgram_file:
                cgram_file = validate_file_path(cgram_file)
            
            # Extract base sprite data
            base_img, total_tiles = self.extract_sprites(
                vram_file, offset, size, tiles_per_row)

            # Get active palette information from OAM
            active_palettes = set()
            palette_usage = {}
            if self.oam_mapper:
                active_palettes = set(self.oam_mapper.get_active_palettes())
                palette_usage = self._get_active_palette_info()

            # Create grid image (4x4 grid of palettes) with borders
            border_size = 4
            cell_width = base_img.width + border_size * 2
            cell_height = base_img.height + border_size * 2
            grid_width = cell_width * 4
            grid_height = cell_height * 4
            grid_img = Image.new(
                'RGB', (grid_width, grid_height), (32, 32, 32))

            # Import PIL.ImageDraw for labels and borders
            from PIL import ImageDraw
            draw = ImageDraw.Draw(grid_img)

            # Apply each palette and place in grid
            for pal_num in range(16):
                # Create copy with palette
                img = base_img.copy()

                if cgram_file and os.path.exists(cgram_file):
                    palette = read_cgram_palette(cgram_file, pal_num)
                    if palette:
                        img.putpalette(palette)
                else:
                    img.putpalette(get_grayscale_palette())

                # Convert to RGB
                img_rgb = img.convert('RGB')

                # Calculate position in grid
                grid_col = pal_num % 4
                grid_row = pal_num // 4
                cell_x = grid_col * cell_width
                cell_y = grid_row * cell_height
                img_x = cell_x + border_size
                img_y = cell_y + border_size

                # Draw border based on whether palette is active
                border_color = (0, 255, 0) if pal_num in active_palettes else (64, 64, 64)
                border_width = 3 if pal_num in active_palettes else 1
                
                # Draw border rectangle
                for i in range(border_width):
                    draw.rectangle(
                        [(cell_x + i, cell_y + i), 
                         (cell_x + cell_width - 1 - i, cell_y + cell_height - 1 - i)],
                        outline=border_color
                    )

                # Paste image
                grid_img.paste(img_rgb, (img_x, img_y))

                # Add palette number label
                label = f"P{pal_num}"
                if pal_num in palette_usage:
                    label += f" ({palette_usage[pal_num]})"
                    
                # Draw text background for readability
                text_bbox = draw.textbbox((0, 0), label)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                draw.rectangle(
                    [(img_x + 2, img_y + 2), 
                     (img_x + text_width + 6, img_y + text_height + 6)],
                    fill=(0, 0, 0, 180)
                )
                
                # Draw label text
                text_color = (0, 255, 0) if pal_num in active_palettes else (255, 255, 255)
                draw.text((img_x + 4, img_y + 4), label, fill=text_color)

            return grid_img, total_tiles

        except (OSError, IOError, RuntimeError, AttributeError, SecurityError) as e:
            raise RuntimeError(f"Error creating palette grid: {e}") from e
    
    def _validate_palette_index(self, palette_num: int) -> int:
        """Validate and clamp palette index to valid range (0-15)."""
        if not isinstance(palette_num, int):
            raise ValueError(f"Palette number must be an integer, got {type(palette_num)}")
        if palette_num < 0:
            self.logger.warning(f"Palette number {palette_num} is negative, clamping to 0")
            return 0
        if palette_num > 15:
            self.logger.warning(f"Palette number {palette_num} exceeds maximum (15), clamping to 15")
            return 15
        return palette_num
    
    def _get_active_palette_info(self) -> Dict[int, int]:
        """Get information about which palettes are actively used based on OAM data."""
        if not self.oam_mapper:
            return {}
        
        stats = self.oam_mapper.get_palette_usage_stats()
        return stats.get('palette_counts', {})
