#!/usr/bin/env python3
"""
OAM (Object Attribute Memory) parser for SNES sprite palette mapping
Extracts sprite-to-palette assignments from OAM dumps
"""

import os

try:
    from .constants import (
        BYTES_PER_OAM_ENTRY,
        KIRBY_TILE_END,
        KIRBY_TILE_START,
        KIRBY_VRAM_BASE,
        MAX_OAM_FILE_SIZE,
        OAM_ENTRIES,
        OAM_HIGH_TABLE_OFFSET,
        OAM_SIZE,
    )
    from .logging_config import get_logger
    from .security_utils import SecurityError, validate_file_path
except ImportError:
    from constants import (
        BYTES_PER_OAM_ENTRY,
        KIRBY_TILE_END,
        KIRBY_TILE_START,
        KIRBY_VRAM_BASE,
        MAX_OAM_FILE_SIZE,
        OAM_ENTRIES,
        OAM_HIGH_TABLE_OFFSET,
        OAM_SIZE,
    )
    from logging_config import get_logger
    from security_utils import SecurityError, validate_file_path


class OAMPaletteMapper:
    """Parse OAM data to map sprites to their assigned palettes"""

    def __init__(self):
        self.oam_entries = []
        self.tile_palette_map = {}  # tile_number -> palette_number
        self.vram_palette_map = {}  # vram_offset -> palette_number
        # Sorted list for efficient range queries
        # List of (start_offset, end_offset, palette)
        self.vram_palette_ranges = []
        self.logger = get_logger("oam_mapper")

    def parse_oam_dump(self, oam_file):
        """Parse OAM dump file and extract sprite entries"""
        # Validate file path
        try:
            oam_file = validate_file_path(oam_file, max_size=MAX_OAM_FILE_SIZE)
        except SecurityError:
            raise  # Re-raise security errors

        with open(oam_file, "rb") as f:
            oam_data = f.read()

        # OAM structure:
        # OAM_HIGH_TABLE_OFFSET bytes: OAM_ENTRIES sprite entries (BYTES_PER_OAM_ENTRY each)
        # OAM_HIGH_TABLE_SIZE bytes: High table (2 bits per sprite)

        # Allow partial OAM data, but warn if too small for any entries
        if len(oam_data) < BYTES_PER_OAM_ENTRY:
            raise ValueError(
                f"OAM dump too small: {
                    len(oam_data)} bytes (need at least {BYTES_PER_OAM_ENTRY})"
            )

        # Warn if less than full size
        if len(oam_data) < OAM_SIZE:
            import warnings

            warnings.warn(
                f"Partial OAM data: {
                    len(oam_data)} bytes (full size is {OAM_SIZE})",
                stacklevel=2,
            )

        # Parse main OAM table
        for i in range(OAM_ENTRIES):
            offset = i * BYTES_PER_OAM_ENTRY

            # Ensure we have enough data for this sprite entry
            if offset + BYTES_PER_OAM_ENTRY > len(oam_data):
                break

            # Read 4-byte sprite entry
            x_pos = oam_data[offset]
            y_pos = oam_data[offset + 1]
            tile_num = oam_data[offset + 2]
            attributes = oam_data[offset + 3]

            # Extract attributes
            # Bit 0-2: Palette number (0-7)
            # Bit 3-4: Priority
            # Bit 5: H-flip
            # Bit 6: V-flip
            # Bit 7: Table select (for tiles 256-511)

            palette = attributes & 0x07  # Lower 3 bits
            priority = (attributes >> 3) & 0x03
            h_flip = (attributes >> 5) & 0x01
            v_flip = (attributes >> 6) & 0x01
            tile_table = (attributes >> 7) & 0x01

            # Get size and MSB of position from high table
            high_table_offset = OAM_HIGH_TABLE_OFFSET + (i // 4)
            if high_table_offset < len(oam_data):
                high_table_byte = oam_data[high_table_offset]
                high_table_shift = (i % 4) * 2
                high_bits = (high_table_byte >> high_table_shift) & 0x03
            else:
                # Default to small sprite if high table data is missing
                high_bits = 0

            size_bit = high_bits & 0x01  # 0 = 8x8, 1 = 16x16 (or 32x32/64x64)
            x_msb = (high_bits >> 1) & 0x01

            # Calculate actual tile number (with table select)
            actual_tile = tile_num | (tile_table << 8)

            # Store sprite entry
            sprite_entry = {
                "index": i,
                "x": x_pos | (x_msb << 8),
                "y": y_pos,
                "tile": actual_tile,
                "palette": palette,
                "priority": priority,
                "h_flip": h_flip,
                "v_flip": v_flip,
                "size": "large" if size_bit else "small",
            }

            self.oam_entries.append(sprite_entry)

            # Map tile to palette
            self.tile_palette_map[actual_tile] = palette

            # For large sprites, map multiple tiles
            if size_bit:  # 16x16 sprite uses 4 tiles
                self.tile_palette_map[actual_tile + 1] = palette
                self.tile_palette_map[actual_tile + 16] = palette
                self.tile_palette_map[actual_tile + 17] = palette

    def build_vram_palette_map(self, base_vram_offset=0x6000):
        """Build a map of VRAM offsets to palette numbers"""
        # Convert tile numbers to VRAM byte offsets
        # Each tile is 32 bytes in 4bpp format

        # Validate base offset to prevent overflow
        if base_vram_offset < 0 or base_vram_offset > 0x10000:
            raise ValueError(
                f"Invalid base VRAM offset: {
                    hex(base_vram_offset)}"
            )

        for tile_num, palette in self.tile_palette_map.items():
            # Calculate VRAM offset
            # Note: This assumes tiles are stored sequentially
            # In reality, tile arrangement can be more complex

            # For Kirby sprites
            if tile_num >= KIRBY_TILE_START and tile_num < KIRBY_TILE_END:
                # Check for potential overflow before calculation
                tile_offset = tile_num - KIRBY_TILE_START
                if tile_offset < 0 or tile_offset > 0x7F:  # Max 128 tiles
                    continue

                # Safe calculation with bounds checking
                try:
                    vram_word_addr = base_vram_offset + (tile_offset * 16)
                    if vram_word_addr > 0xFFFF:  # Max VRAM address
                        continue

                    vram_byte_offset = vram_word_addr * 2
                    if vram_byte_offset < 0x20000:  # 128KB max VRAM size
                        self.vram_palette_map[vram_byte_offset] = palette
                        # Add to range list for efficient lookup
                        self.vram_palette_ranges.append(
                            (vram_byte_offset, vram_byte_offset + 32, palette)
                        )
                except (OverflowError, ValueError):
                    # Skip this tile if calculation would overflow
                    continue

        # Sort ranges by start offset for binary search
        self.vram_palette_ranges.sort(key=lambda x: x[0])

    def get_palette_for_tile(self, tile_number):
        """Get palette number for a specific tile"""
        return self.tile_palette_map.get(tile_number, None)

    def get_palette_for_vram_offset(self, vram_offset):
        """Get palette number for a specific VRAM offset using binary search"""
        # If no ranges, return None
        if not self.vram_palette_ranges:
            return None

        # Binary search for the range containing this offset
        # Find the rightmost range with start <= vram_offset
        left, right = 0, len(self.vram_palette_ranges) - 1
        result_idx = -1

        while left <= right:
            mid = (left + right) // 2
            if self.vram_palette_ranges[mid][0] <= vram_offset:
                result_idx = mid
                left = mid + 1
            else:
                right = mid - 1

        # Check if the found range contains the offset
        if result_idx >= 0:
            start, end, palette = self.vram_palette_ranges[result_idx]
            if start <= vram_offset < end:
                return palette

        return None

    def get_active_palettes(self):
        """Get list of palette numbers actually used by sprites"""
        return sorted(set(self.tile_palette_map.values()))

    def get_palette_usage_stats(self):
        """Get statistics about palette usage"""
        palette_counts = {}
        for palette in self.tile_palette_map.values():
            palette_counts[palette] = palette_counts.get(palette, 0) + 1

        return {
            "palette_counts": palette_counts,
            "active_palettes": self.get_active_palettes(),
            "total_sprites": len(self.oam_entries),
            "visible_sprites": len([s for s in self.oam_entries if s["y"] < 224]),
        }

    def find_sprites_using_palette(self, palette_num):
        """Find all sprite entries using a specific palette"""
        return [s for s in self.oam_entries if s["palette"] == palette_num]

    def find_sprites_in_region(self, x_start, y_start, x_end, y_end):
        """Find sprites within a screen region"""
        sprites = []
        for sprite in self.oam_entries:
            if x_start <= sprite["x"] <= x_end and y_start <= sprite["y"] <= y_end:
                sprites.append(sprite)
        return sprites

    def debug_dump(self):
        """Log debug information about OAM entries"""
        self.logger.info("OAM Debug Dump")
        self.logger.info("=" * 50)
        self.logger.info(f"Total sprites: {len(self.oam_entries)}")

        stats = self.get_palette_usage_stats()
        self.logger.info(f"Active palettes: {stats['active_palettes']}")
        self.logger.info(f"Visible sprites: {stats['visible_sprites']}")

        self.logger.info("Palette usage:")
        for pal, count in sorted(stats["palette_counts"].items()):
            self.logger.info(f"  Palette {pal}: {count} sprites")

        self.logger.info("First 10 visible sprites:")
        visible = [s for s in self.oam_entries if s["y"] < 224]
        for sprite in visible[:10]:
            self.logger.info(
                f"  Sprite {sprite['index']:3d}: "
                f"Pos({sprite['x']:3d},{sprite['y']:3d}) "
                f"Tile {sprite['tile']:3d} "
                f"Pal {sprite['palette']} "
                f"Size: {sprite['size']}"
            )


def create_tile_palette_map(oam_file, vram_base=KIRBY_VRAM_BASE):
    """Convenience function to create palette mapping from OAM file"""
    mapper = OAMPaletteMapper()
    mapper.parse_oam_dump(oam_file)
    # Convert byte to word address
    mapper.build_vram_palette_map(vram_base // 2)
    return mapper


if __name__ == "__main__":
    # Test with OAM dump
    import sys

    try:
        from .logging_config import setup_logging
    except ImportError:
        from logging_config import setup_logging

    # Configure logging to output to stdout when run as script
    setup_logging(level="INFO")

    oam_file = sys.argv[1] if len(sys.argv) > 1 else "OAM.dmp"

    if os.path.exists(oam_file):
        mapper = OAMPaletteMapper()
        mapper.parse_oam_dump(oam_file)
        mapper.build_vram_palette_map()
        mapper.debug_dump()
    else:
        logger = get_logger("oam_mapper.main")
        logger.error(f"OAM file not found: {oam_file}")
