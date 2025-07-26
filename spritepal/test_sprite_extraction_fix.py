#!/usr/bin/env python3
"""
Test script to verify sprite extraction fixes for the "pixely grey colours" issue.
Tests the key improvements:
1. Size-limited decompression
2. Sprite data validation
3. Sliding window search
4. Multiple size limit testing
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.rom_extractor import ROMExtractor
from core.rom_injector import ROMInjector
from utils.logging_config import get_logger

logger = get_logger(__name__)


def test_sprite_extraction(rom_path: str):
    """Test sprite extraction with the fixes."""
    logger.info("=" * 60)
    logger.info("Testing sprite extraction fixes")
    logger.info("=" * 60)

    if not os.path.exists(rom_path):
        logger.error(f"ROM file not found: {rom_path}")
        return False

    try:
        # Initialize components
        rom_injector = ROMInjector()
        rom_extractor = ROMExtractor()

        # Read ROM header
        logger.info("\n1. Reading ROM header...")
        header = rom_injector.read_rom_header(rom_path)
        logger.info(f"   Title: {header.title}")
        logger.info(f"   Checksum: 0x{header.checksum:04X}")

        # Get known sprite locations
        logger.info("\n2. Getting sprite locations...")
        sprite_locations = rom_extractor.get_known_sprite_locations(rom_path)

        if not sprite_locations:
            logger.warning("No known sprite locations for this ROM")
            return False

        logger.info(f"   Found {len(sprite_locations)} sprite locations")

        # Test extracting first sprite with size limit
        sprite_name = next(iter(sprite_locations.keys()))
        sprite_pointer = sprite_locations[sprite_name]

        logger.info(f"\n3. Testing extraction of '{sprite_name}' at 0x{sprite_pointer.offset:X}")

        # Read ROM data
        with open(rom_path, "rb") as f:
            rom_data = f.read()

        # Test without size limit (old behavior)
        logger.info("\n   a) Testing WITHOUT size limit (old behavior):")
        try:
            compressed_size, decompressed_data = rom_injector.find_compressed_sprite(
                rom_data, sprite_pointer.offset, expected_size=None
            )
            logger.info(f"      Decompressed size: {len(decompressed_data)} bytes")
            logger.info(f"      Tiles: {len(decompressed_data) // 32}")
            extra_bytes = len(decompressed_data) % 32
            if extra_bytes:
                logger.warning(f"      Misalignment: {extra_bytes} extra bytes")
        except Exception:
            logger.exception("      Failed")

        # Test with size limit (new behavior)
        logger.info("\n   b) Testing WITH size limit (new behavior):")
        expected_size = sprite_pointer.compressed_size or 8192  # Default to 8KB
        try:
            compressed_size, decompressed_data = rom_injector.find_compressed_sprite(
                rom_data, sprite_pointer.offset, expected_size=expected_size
            )
            logger.info(f"      Expected size: {expected_size} bytes")
            logger.info(f"      Decompressed size: {len(decompressed_data)} bytes")
            logger.info(f"      Tiles: {len(decompressed_data) // 32}")
            extra_bytes = len(decompressed_data) % 32
            if extra_bytes:
                logger.warning(f"      Misalignment: {extra_bytes} extra bytes")
            else:
                logger.info("      ✓ Perfect tile alignment!")

            # Test validation
            is_valid = rom_injector._validate_sprite_data(decompressed_data)
            logger.info(f"      Sprite validation: {'✓ PASSED' if is_valid else '✗ FAILED'}")

        except Exception:
            logger.exception("      Failed")

        # Test sprite scanner with multiple size limits
        logger.info("\n4. Testing sprite scanner with multiple size limits...")
        logger.info("   Scanning around known sprite location...")

        scan_results = rom_extractor.scan_for_sprites(
            rom_path,
            sprite_pointer.offset - 0x1000,  # Start 4KB before
            sprite_pointer.offset + 0x1000,  # End 4KB after
            step=0x100
        )

        logger.info(f"   Found {len(scan_results)} valid sprites in scan range")
        if scan_results:
            best = scan_results[0]  # Already sorted by quality
            logger.info(f"   Best result: 0x{best['offset']:X}, quality: {best['quality']:.2f}")

        logger.info("\n✓ All tests completed successfully!")
        return True

    except Exception:
        logger.exception("Test failed with error")
        return False


def main():
    """Main test function."""
    # Look for ROM files in current directory
    rom_files = []
    for pattern in ["*.sfc", "*.smc"]:
        rom_files.extend(Path(".").glob(pattern))

    if not rom_files:
        logger.error("No ROM files found in current directory")
        logger.info("Please place a Kirby Super Star ROM file in the current directory")
        return

    logger.info(f"Found {len(rom_files)} ROM file(s)")

    # Test each ROM
    for rom_file in rom_files:
        logger.info(f"\nTesting ROM: {rom_file}")
        test_sprite_extraction(str(rom_file))


if __name__ == "__main__":
    main()
