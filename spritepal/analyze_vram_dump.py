#!/usr/bin/env python3
"""
Analyze VRAM dumps to identify sprite patterns and search for them in ROM
"""

import os
import sys

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, parent_dir)

# Import after path setup
from spritepal.core.hal_compression import HALCompressor
from spritepal.core.rom_extractor import ROMExtractor
from spritepal.utils.logging_config import get_logger

logger = get_logger(__name__)

class VRAMAnalyzer:
    """Analyze VRAM dumps to find sprite patterns"""

    def __init__(self):
        self.rom_extractor: ROMExtractor = ROMExtractor()
        self.hal_compressor: HALCompressor = HALCompressor()

    def load_vram_dump(self, vram_path: str) -> bytes:
        """Load VRAM dump file"""
        logger.info(f"Loading VRAM dump: {vram_path}")
        with open(vram_path, "rb") as f:
            vram_data = f.read()
        logger.info(f"Loaded {len(vram_data)} bytes of VRAM data")
        return vram_data

    def extract_sprite_area(self, vram_data: bytes, start_offset: int = 0xC000, size: int = 0x4000) -> bytes:
        """Extract sprite tile area from VRAM (typically at 0xC000)"""
        sprite_data = vram_data[start_offset:start_offset + size]
        logger.info(f"Extracted sprite area: 0x{start_offset:04X}-0x{start_offset+size:04X} ({size} bytes)")
        return sprite_data

    def find_non_empty_tiles(self, sprite_data: bytes, tile_size: int = 32) -> list[tuple[int, bytes]]:
        """Find non-empty tiles in sprite data"""
        tiles = []
        num_tiles = len(sprite_data) // tile_size

        for i in range(num_tiles):
            tile_offset = i * tile_size
            tile_data = sprite_data[tile_offset:tile_offset + tile_size]

            # Check if tile is not empty (not all zeros)
            if any(b != 0 for b in tile_data):
                tiles.append((tile_offset, tile_data))

        logger.info(f"Found {len(tiles)} non-empty tiles out of {num_tiles} total")
        return tiles

    def analyze_tile_patterns(self, tiles: list[tuple[int, bytes]]) -> None:
        """Analyze patterns in tiles"""
        if not tiles:
            logger.warning("No tiles to analyze")
            return

        # Analyze first few tiles
        logger.info("\nAnalyzing first 5 non-empty tiles:")
        for i, (offset, tile_data) in enumerate(tiles[:5]):
            logger.info(f"\nTile {i+1} at offset 0x{offset:04X}:")

            # Show first 16 bytes (first 2 bitplanes)
            logger.info(f"  Bitplanes 0-1: {' '.join(f'{b:02X}' for b in tile_data[:16])}")
            logger.info(f"  Bitplanes 2-3: {' '.join(f'{b:02X}' for b in tile_data[16:32])}")

            # Calculate some statistics
            non_zero = sum(1 for b in tile_data if b != 0)
            unique_bytes = len(set(tile_data))
            logger.info(f"  Non-zero bytes: {non_zero}/32, Unique values: {unique_bytes}")

    def search_rom_for_pattern(self, rom_path: str, pattern: bytes, max_results: int = 5) -> list[int]:
        """Search ROM for a specific tile pattern"""
        logger.info(f"\nSearching ROM for pattern ({len(pattern)} bytes)...")

        with open(rom_path, "rb") as f:
            rom_data = f.read()

        found_offsets = []
        search_start = 0

        while len(found_offsets) < max_results:
            offset = rom_data.find(pattern, search_start)
            if offset == -1:
                break

            found_offsets.append(offset)
            logger.info(f"  Found at ROM offset: 0x{offset:06X}")
            search_start = offset + 1

        return found_offsets

    def search_compressed_patterns(self, rom_path: str, pattern: bytes, scan_range: tuple[int, int] = (0xC0000, 0xF0000)) -> list[tuple[int, int]]:
        """Search for pattern in decompressed ROM data"""
        logger.info(f"\nSearching for pattern in compressed ROM data (0x{scan_range[0]:X}-0x{scan_range[1]:X})...")

        with open(rom_path, "rb") as f:
            rom_data = f.read()

        found_locations = []

        # Scan ROM in steps
        for offset in range(scan_range[0], scan_range[1], 0x100):
            if offset >= len(rom_data):
                break

            try:
                # Try to decompress at this offset
                _, decompressed = self.rom_extractor.rom_injector.find_compressed_sprite(
                    rom_data, offset, expected_size=65536  # Large size to get full data
                )

                if len(decompressed) > 0:
                    # Search for pattern in decompressed data
                    pattern_offset = decompressed.find(pattern)
                    if pattern_offset != -1:
                        logger.info(f"  Found at ROM offset 0x{offset:06X}, decompressed offset +{pattern_offset}")
                        found_locations.append((offset, pattern_offset))

            except Exception:
                # Decompression failed, continue
                continue

        return found_locations

    def analyze_dumps(self, vram_path: str, rom_path: str | None = None):
        """Main analysis function"""
        logger.info("="*60)
        logger.info("VRAM Dump Analysis")
        logger.info("="*60)

        # Load VRAM dump
        vram_data = self.load_vram_dump(vram_path)

        # Extract sprite area
        sprite_data = self.extract_sprite_area(vram_data)

        # Find non-empty tiles
        tiles = self.find_non_empty_tiles(sprite_data)

        # Analyze tile patterns
        self.analyze_tile_patterns(tiles)

        if tiles and rom_path:
            # Search for first few tiles in ROM
            logger.info("\n" + "="*60)
            logger.info("ROM Pattern Search")
            logger.info("="*60)

            for i, (_offset, tile_data) in enumerate(tiles[:3]):
                logger.info(f"\nSearching for tile {i+1} pattern...")

                # Search uncompressed
                uncompressed_offsets = self.search_rom_for_pattern(rom_path, tile_data)
                if not uncompressed_offsets:
                    logger.info("  Not found uncompressed")

                # Search compressed
                compressed_locations = self.search_compressed_patterns(rom_path, tile_data)
                if compressed_locations:
                    logger.info(f"  Found in {len(compressed_locations)} compressed blocks")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python analyze_vram_dump.py <vram_dump_path> [rom_path]")
        return

    vram_path = sys.argv[1]
    rom_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(vram_path):
        print(f"VRAM dump not found: {vram_path}")
        return

    if rom_path and not os.path.exists(rom_path):
        print(f"ROM not found: {rom_path}")
        return

    analyzer = VRAMAnalyzer()
    analyzer.analyze_dumps(vram_path, rom_path)


if __name__ == "__main__":
    main()
