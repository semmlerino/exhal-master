"""
ROM sprite extraction functionality for SpritePal
Extracts sprites directly from ROM files using HAL decompression
"""

import math
import os
from typing import Any

from PIL import Image

from spritepal.core.default_palette_loader import DefaultPaletteLoader
from spritepal.core.hal_compression import HALCompressionError, HALCompressor
from spritepal.core.rom_injector import ROMInjector, SpritePointer
from spritepal.core.rom_palette_extractor import ROMPaletteExtractor
from spritepal.core.sprite_config_loader import SpriteConfigLoader
from spritepal.utils.constants import BYTES_PER_TILE, TILE_HEIGHT, TILE_WIDTH
from spritepal.utils.logging_config import get_logger
from spritepal.utils.rom_exceptions import ROMCompressionError

logger = get_logger(__name__)


class ROMExtractor:
    """Handles sprite extraction directly from ROM files"""

    def __init__(self) -> None:
        """Initialize ROM extractor with required components"""
        logger.debug("Initializing ROMExtractor")
        self.hal_compressor: HALCompressor = HALCompressor()
        self.rom_injector: ROMInjector = ROMInjector()
        self.default_palette_loader: DefaultPaletteLoader = DefaultPaletteLoader()
        self.rom_palette_extractor: ROMPaletteExtractor = ROMPaletteExtractor()
        self.sprite_config_loader: SpriteConfigLoader = SpriteConfigLoader()
        logger.info("ROMExtractor initialized with HAL compression and palette extraction support")

    def extract_sprite_from_rom(
        self, rom_path: str, sprite_offset: int, output_base: str, sprite_name: str = ""
    ) -> tuple[str, dict[str, Any]]:
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
        logger.info("=" * 60)
        logger.info(f"Starting ROM sprite extraction: offset=0x{sprite_offset:X}, sprite={sprite_name or 'unnamed'}")
        logger.debug(f"ROM path: {rom_path}")
        logger.debug(f"Output base: {output_base}")

        try:
            # Read ROM header for validation
            header = self.rom_injector.read_rom_header(rom_path)
            logger.info(f"ROM identified: {header.title} (checksum: 0x{header.checksum:04X})")

            # Find and decompress sprite data
            logger.info(f"Reading ROM data from: {rom_path}")
            with open(rom_path, "rb") as rom_file:
                rom_data = rom_file.read()
            logger.debug(f"ROM size: {len(rom_data)} bytes")

            # Get sprite config if available to get expected size
            expected_size = None
            if sprite_name:
                # Get sprite configurations for this ROM
                sprite_configs = self.sprite_config_loader.get_game_sprites(
                    header.title, header.checksum
                )
                if sprite_name in sprite_configs:
                    expected_size = sprite_configs[sprite_name].estimated_size
                    logger.debug(f"Using expected size from config: {expected_size} bytes")
                else:
                    logger.debug(f"No sprite config found for '{sprite_name}', decompressing without size limit")

            logger.info(f"Decompressing sprite data at offset 0x{sprite_offset:X}")
            compressed_size, sprite_data = self.rom_injector.find_compressed_sprite(
                rom_data, sprite_offset, expected_size
            )

            logger.info(
                f"Decompressed sprite from 0x{sprite_offset:X}: "
                f"{compressed_size} bytes compressed, "
                f"{len(sprite_data)} bytes decompressed"
            )

            # Convert 4bpp data to grayscale PNG
            output_path = f"{output_base}.png"
            logger.info(f"Converting decompressed data to PNG: {output_path}")
            tile_count = self._convert_4bpp_to_png(sprite_data, output_path)

            # Try to extract palettes from ROM first
            palette_files = []
            rom_palettes_used = False

            if sprite_name:
                logger.debug(f"Looking for palette configuration for sprite: {sprite_name}")
                # Get game configuration
                game_configs = self.sprite_config_loader.config_data.get("games", {})
                game_config = None

                # Find matching game config by title
                for game_name, config in game_configs.items():
                    if game_name.upper() in header.title.upper():
                        game_config = config
                        logger.debug(f"Found game configuration: {game_name}")
                        break

                if game_config:
                    # Get palette configuration
                    logger.debug(f"Getting palette configuration for {sprite_name}")
                    palette_offset, palette_indices = (
                        self.rom_palette_extractor.get_palette_config_from_sprite_config(
                            game_config, sprite_name
                        )
                    )

                    if palette_offset and palette_indices:
                        # Extract palettes from ROM
                        logger.info(
                            f"Extracting palettes from ROM at offset 0x{palette_offset:X}"
                        )
                        logger.debug(f"Palette indices: {palette_indices}")
                        palette_files = (
                            self.rom_palette_extractor.extract_palettes_from_rom(
                                rom_path, palette_offset, palette_indices, output_base
                            )
                        )
                        if palette_files:
                            rom_palettes_used = True
                            logger.info(
                                f"Successfully extracted {len(palette_files)} palettes from ROM"
                            )
                            for pf in palette_files:
                                logger.debug(f"  - {os.path.basename(pf)}")
                        else:
                            logger.warning("Failed to extract palettes from ROM")
                    else:
                        logger.debug("No palette configuration found for this sprite")

            # Fall back to default palettes if ROM extraction failed
            if (
                not palette_files
                and sprite_name
                and self.default_palette_loader.has_default_palettes(sprite_name)
            ):
                logger.info(f"Falling back to default palettes for {sprite_name}")
                palette_files = self.default_palette_loader.create_palette_files(
                    sprite_name, output_base
                )
                logger.info(
                    f"Created {len(palette_files)} default palette files for {sprite_name}"
                )
                for pf in palette_files:
                    logger.debug(f"  - {os.path.basename(pf)}")

            if not palette_files:
                logger.info(
                    "No palettes available - sprite will be grayscale in editor"
                )

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
                "default_palettes_used": len(palette_files) > 0
                and not rom_palettes_used,
                "palette_count": len(palette_files),
            }

        except HALCompressionError as e:
            logger.exception("HAL decompression failed")
            raise ROMCompressionError(f"Failed to decompress sprite: {e}") from e
        except Exception:
            logger.exception("ROM extraction failed")
            raise
        else:
            logger.info("ROM extraction completed successfully")
            logger.info(f"Output: {output_path} ({tile_count} tiles)")
            logger.info(f"Palettes: {len(palette_files)} files")
            logger.info("=" * 60)

            return output_path, extraction_info

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

        # Check if we have partial tile data
        if len(tile_data) % BYTES_PER_TILE != 0:
            logger.warning(f"Tile data not aligned: {len(tile_data)} bytes ({len(tile_data) % BYTES_PER_TILE} extra bytes)")

        # Calculate image dimensions
        img_width = tiles_per_row * TILE_WIDTH
        img_height = ((num_tiles + tiles_per_row - 1) // tiles_per_row) * TILE_HEIGHT

        logger.info(f"Converting 4bpp data: {len(tile_data)} bytes -> {num_tiles} tiles")
        logger.debug(f"Tiles per row: {tiles_per_row}")
        logger.debug(f"Image dimensions: {img_width}x{img_height} pixels")

        # Create grayscale image
        img = Image.new("L", (img_width, img_height), 0)

        # Process each tile
        log_interval = 100  # Log progress every 100 tiles

        for tile_idx in range(num_tiles):
            # Calculate tile position
            tile_x = (tile_idx % tiles_per_row) * TILE_WIDTH
            tile_y = (tile_idx // tiles_per_row) * TILE_HEIGHT

            if (tile_idx + 1) % log_interval == 0:
                logger.debug(f"Processing tile {tile_idx + 1}/{num_tiles}")

            # Extract tile data
            tile_offset = tile_idx * BYTES_PER_TILE
            tile_bytes = tile_data[tile_offset : tile_offset + BYTES_PER_TILE]

            # Convert 4bpp planar to pixels
            for y in range(TILE_HEIGHT):
                for x in range(TILE_WIDTH):
                    # Get pixel value from 4bpp planar format
                    pixel = self._get_4bpp_pixel(tile_bytes, x, y)
                    # Convert 4-bit value to 8-bit grayscale (0-15 -> 0-255)
                    gray_value = pixel * 17
                    img.putpixel((tile_x + x, tile_y + y), gray_value)

        # Save as indexed PNG
        img = img.convert("P")
        img.save(output_path, "PNG")

        logger.info(f"Saved PNG: {output_path} ({img.width}x{img.height} pixels, {num_tiles} tiles)")
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
        logger.info(f"Getting known sprite locations for ROM: {rom_path}")
        try:
            # Read ROM header to identify the game
            header = self.rom_injector.read_rom_header(rom_path)

            # Check if this is Kirby Super Star
            if "KIRBY" in header.title.upper():
                logger.debug(f"Detected Kirby ROM: {header.title}")
                locations = self.rom_injector.find_sprite_locations(rom_path)
                logger.info(f"Found {len(locations)} sprite locations")
                return locations

        except Exception:
            logger.exception("Failed to get sprite locations")
            return {}
        else:
            logger.warning(f"Unknown ROM: {header.title} - no sprite locations available")
            return {}

    def scan_for_sprites(
        self, rom_path: str, start_offset: int, end_offset: int, step: int = 0x100
    ) -> list[dict[str, Any]]:
        """
        Scan ROM for valid sprite data within a range of offsets.

        Args:
            rom_path: Path to ROM file
            start_offset: Starting offset to scan from
            end_offset: Ending offset to scan to
            step: Step size between scan attempts (default: 256 bytes)

        Returns:
            List of dictionaries containing valid sprite locations found
        """
        logger.info(f"Scanning ROM for sprites: 0x{start_offset:X} to 0x{end_offset:X} (step: 0x{step:X})")
        found_sprites = []

        try:
            # Read ROM data once
            with open(rom_path, "rb") as rom_file:
                rom_data = rom_file.read()

            rom_size = len(rom_data)
            logger.debug(f"ROM size: {rom_size} bytes")

            # Ensure end offset is within ROM bounds
            if end_offset > rom_size:
                logger.warning(f"End offset 0x{end_offset:X} exceeds ROM size, adjusting to 0x{rom_size:X}")
                end_offset = rom_size

            scan_count = 0

            # Scan through the range
            for offset in range(start_offset, end_offset, step):
                scan_count += 1

                # Show progress every 100 scans
                if scan_count % 100 == 0:
                    logger.debug(f"Scanned {scan_count} offsets... (currently at 0x{offset:X})")

                try:
                    # Try to decompress sprite at this offset
                    compressed_size, sprite_data = self.rom_injector.find_compressed_sprite(
                        rom_data, offset
                    )

                    # Check if data is valid
                    if len(sprite_data) > 0:
                        # Validate alignment
                        bytes_per_tile = BYTES_PER_TILE
                        extra_bytes = len(sprite_data) % bytes_per_tile
                        num_tiles = len(sprite_data) // bytes_per_tile

                        # Only accept perfectly aligned data or minor misalignment
                        if extra_bytes <= bytes_per_tile // 4 and num_tiles >= 16:  # At least 16 tiles
                            alignment_status = "perfect" if extra_bytes == 0 else f"{extra_bytes} extra bytes"

                            sprite_info = {
                                "offset": offset,
                                "offset_hex": f"0x{offset:X}",
                                "compressed_size": compressed_size,
                                "decompressed_size": len(sprite_data),
                                "tile_count": num_tiles,
                                "alignment": alignment_status,
                                "quality": self._assess_sprite_quality(sprite_data)
                            }

                            found_sprites.append(sprite_info)
                            logger.info(
                                f"Found valid sprite at 0x{offset:X}: "
                                f"{num_tiles} tiles, {compressed_size} bytes compressed, "
                                f"alignment: {alignment_status}"
                            )

                except Exception:
                    # Decompression failed, not a valid sprite location
                    continue

            logger.info(f"Scan complete: checked {scan_count} offsets, found {len(found_sprites)} valid sprites")

            # Sort by quality score (higher is better)
            found_sprites.sort(key=lambda x: x["quality"], reverse=True)

            return found_sprites

        except Exception:
            logger.exception("Failed to scan for sprites")
            return []

    def _assess_sprite_quality(self, sprite_data: bytes, check_embedded: bool = True) -> float:
        """
        Assess the quality of sprite data based on various heuristics.

        Args:
            sprite_data: Decompressed sprite data

        Returns:
            Quality score (0.0 to 1.0)
        """
        score = 0.0
        bytes_per_tile = BYTES_PER_TILE

        # 1. Size validation (most important)
        data_size = len(sprite_data)
        if data_size == 0:
            return 0.0

        # Reject data that's too large (likely not sprite data)
        if data_size > 65536:  # 64KB absolute max
            return 0.0

        # Check data size alignment
        extra_bytes = data_size % bytes_per_tile
        if extra_bytes == 0:
            score += 0.2  # Perfect alignment
        elif extra_bytes > 16:  # Too much misalignment
            return 0.0  # Reject badly misaligned data
        elif extra_bytes <= 8:
            score += 0.1  # Minor misalignment acceptable

        # 2. Tile count validation
        num_tiles = data_size // bytes_per_tile
        if 32 <= num_tiles <= 256:  # Typical sprite size for Kirby
            score += 0.2
        elif 16 <= num_tiles < 32 or 256 < num_tiles <= 512:
            score += 0.1
        elif num_tiles < 16:  # Too small
            score *= 0.5  # Heavily penalize
        elif num_tiles > 512:  # Too large
            return 0.0

        # 3. Entropy analysis - sprites should have moderate entropy
        entropy = self._calculate_entropy(sprite_data[:min(1024, data_size)])
        if 2.0 <= entropy <= 6.0:  # Graphics data typically has moderate entropy
            score += 0.2
        elif entropy < 1.0 or entropy > 7.0:  # Too uniform or too random
            score *= 0.5  # Penalize

        # 4. Check for 4bpp tile structure
        tiles_checked = min(10, num_tiles)
        valid_tile_count = 0

        for i in range(tiles_checked):
            tile_offset = i * bytes_per_tile
            tile_data = sprite_data[tile_offset:tile_offset + bytes_per_tile]
            if len(tile_data) == bytes_per_tile and self._validate_4bpp_tile(tile_data):
                valid_tile_count += 1

        tile_validity_ratio = valid_tile_count / tiles_checked if tiles_checked > 0 else 0
        if tile_validity_ratio >= 0.8:
            score += 0.3
        elif tile_validity_ratio >= 0.5:
            score += 0.15
        elif tile_validity_ratio < 0.3:
            score *= 0.5  # Penalize low validity

        # 5. Pattern analysis - check for graphics patterns
        if self._has_graphics_patterns(sprite_data):
            score += 0.1

        # 6. For PAL ROMs, check if sprite might be embedded within the data
        if check_embedded and score < 0.5 and data_size > 16384:
            # Check common embedded offsets
            for test_offset in [512, 1024, 2048, 4096]:
                if test_offset + 8192 <= data_size:
                    embedded_data = sprite_data[test_offset:test_offset + 8192]
                    # Recursive call but without embedded check to avoid infinite recursion
                    embedded_score = self._assess_sprite_quality(embedded_data, check_embedded=False)
                    if embedded_score > score:
                        logger.debug(f"Found better quality sprite embedded at offset +{test_offset}")
                        return embedded_score

        return min(score, 1.0)

    def _has_4bpp_characteristics(self, data: bytes) -> bool:
        """
        Check if data has characteristics of 4bpp sprite data.

        Args:
            data: Sprite data to check

        Returns:
            True if data appears to be 4bpp sprite data
        """
        if len(data) < BYTES_PER_TILE:
            return False

        # Check first tile for 4bpp structure
        tile_data = data[:BYTES_PER_TILE]

        # In 4bpp format, bitplanes are organized in a specific way
        # Check for reasonable bit patterns (not all 0 or all 1)
        bitplane_variety = 0

        for i in range(0, 16, 2):  # First two bitplanes
            byte1 = tile_data[i]
            byte2 = tile_data[i + 1]
            if 0 < byte1 < 255 or 0 < byte2 < 255:
                bitplane_variety += 1

        for i in range(16, 32, 2):  # Second two bitplanes
            byte1 = tile_data[i]
            byte2 = tile_data[i + 1]
            if 0 < byte1 < 255 or 0 < byte2 < 255:
                bitplane_variety += 1

        # Expect some variety in the bitplanes
        return bitplane_variety >= 4

    def _calculate_entropy(self, data: bytes) -> float:
        """
        Calculate Shannon entropy of data.

        Args:
            data: Data to analyze

        Returns:
            Entropy value (0-8 for byte data)
        """
        if not data:
            return 0.0

        # Count byte frequencies
        byte_counts = [0] * 256
        for byte in data:
            byte_counts[byte] += 1

        # Calculate entropy
        entropy = 0.0
        data_len = len(data)

        for count in byte_counts:
            if count > 0:
                probability = count / data_len
                # Use proper log2 calculation
                entropy -= probability * math.log2(probability)

        return entropy

    def _validate_4bpp_tile(self, tile_data: bytes) -> bool:
        """
        Validate if a single tile has valid 4bpp sprite characteristics.

        Args:
            tile_data: 32 bytes of tile data

        Returns:
            True if tile appears valid
        """
        if len(tile_data) != 32:
            return False

        # Check for completely empty or full tile (common in non-sprite data)
        if tile_data in (b"\x00" * 32, b"\xff" * 32):
            return False

        # Check bitplane structure
        plane_validity = 0

        # Check first two bitplanes (bytes 0-15)
        plane01_zeros = sum(1 for b in tile_data[0:16] if b == 0)
        plane01_ones = sum(1 for b in tile_data[0:16] if b == 0xFF)
        if plane01_zeros < 15 and plane01_ones < 15:  # Not all blank/full
            plane_validity += 1

        # Check second two bitplanes (bytes 16-31)
        plane23_zeros = sum(1 for b in tile_data[16:32] if b == 0)
        plane23_ones = sum(1 for b in tile_data[16:32] if b == 0xFF)
        if plane23_zeros < 15 and plane23_ones < 15:  # Not all blank/full
            plane_validity += 1

        # Check for bitplane patterns that indicate graphics
        # In sprites, bitplanes often have correlated patterns
        correlation = 0
        for i in range(8):  # Check each row
            # Get bytes from each bitplane pair
            p0 = tile_data[i*2]
            p1 = tile_data[i*2 + 1]
            p2 = tile_data[16 + i*2]
            p3 = tile_data[16 + i*2 + 1]

            # Check if there's some correlation between planes
            if (p0 & p2) != 0 or (p1 & p3) != 0:
                correlation += 1

        return plane_validity >= 1 and correlation >= 2

    def _has_graphics_patterns(self, data: bytes) -> bool:
        """
        Check for patterns typical of graphics data.

        Args:
            data: Sprite data to analyze

        Returns:
            True if data shows graphics patterns
        """
        if len(data) < 64:
            return False

        # Check for repeating patterns at tile boundaries
        # Graphics often have similar tiles or tile patterns
        pattern_matches = 0
        bytes_per_tile = BYTES_PER_TILE

        for i in range(0, min(len(data) - bytes_per_tile*2, 256), bytes_per_tile):
            tile1 = data[i:i+bytes_per_tile]
            tile2 = data[i+bytes_per_tile:i+bytes_per_tile*2]

            # Count similar bytes between adjacent tiles
            similar_bytes = sum(1 for j in range(bytes_per_tile) if tile1[j] == tile2[j])

            # Adjacent tiles often share some similarity in sprites
            if 4 <= similar_bytes <= 28:  # Some similarity but not identical
                pattern_matches += 1

        # Expect some pattern matches in real sprite data
        return pattern_matches >= 2

    def find_best_sprite_offsets(
        self, rom_path: str, base_offset: int, search_range: int = 0x1000
    ) -> list[int]:
        """
        Find the best sprite offsets around a base offset.

        Args:
            rom_path: Path to ROM file
            base_offset: Base offset to search around
            search_range: Range to search in both directions

        Returns:
            List of valid offsets, sorted by quality
        """
        logger.info(f"Finding best sprite offsets around 0x{base_offset:X} (range: ±0x{search_range:X})")

        # Calculate search bounds
        start_offset = max(0, base_offset - search_range)
        end_offset = base_offset + search_range

        # Scan with smaller steps for more precise results
        found_sprites = self.scan_for_sprites(rom_path, start_offset, end_offset, step=0x10)

        # Extract just the offsets from high-quality results
        best_offsets = []
        for sprite_info in found_sprites:
            if sprite_info["quality"] >= 0.5:  # Only high-quality sprites
                best_offsets.append(sprite_info["offset"])

        logger.info(f"Found {len(best_offsets)} high-quality sprite offsets")
        return best_offsets[:5]  # Return top 5 offsets
