#!/usr/bin/env python3
"""
Demo script for ROM offset validation between Lua scripts and SpritePal.

This demonstrates the validation workflow and creates test data
to verify the validation system works correctly.
"""

import json
import tempfile
from pathlib import Path

from utils.logging_config import get_logger
from validate_lua_vs_spritepal_offsets import LuaSpritePalValidator

logger = get_logger(__name__)


def create_sample_lua_output():
    """
    Create sample Lua script output data for testing.
    
    This simulates the JSON output from the Mesen2 Lua scripts
    with various ROM offsets that should be validated.
    """
    # Sample data with known offsets that might contain sprite data
    # These are typical SNES ROM locations where sprites are often found
    sample_data = {
        "metadata": {
            "capture_time": 45.5,
            "sprites_captured": 12,
            "rom_offsets_found": 8
        },
        "rom_offsets": [
            {"offset": 0x200000, "hits": 15},  # Common sprite location
            {"offset": 0x220000, "hits": 8},   # Another common area
            {"offset": 0x240000, "hits": 12},  # Potential sprite data
            {"offset": 0x260000, "hits": 5},   # Less common area
            {"offset": 0x280000, "hits": 20},  # High activity area
            {"offset": 0x2A0000, "hits": 3},   # Rare occurrence
            {"offset": 0x300000, "hits": 7},   # Mid-range ROM
            {"offset": 0x320000, "hits": 11}   # Another test area
        ]
    }

    return sample_data


def create_sample_precise_lua_output():
    """
    Create sample output from the precise Lua script format.
    """
    sample_data = {
        "metadata": {
            "capture_time": 62.3,
            "sprites_captured": 18,
            "rom_offsets_found": 15
        },
        "unique_sprite_offsets": {
            "0x210040": True,  # Precise sprite offset
            "0x210060": True,  # Adjacent sprite data
            "0x220120": True,  # Different area
            "0x240080": True,  # Mid-ROM sprite
            "0x2600A0": True,  # High-ROM location
            "0x280040": True,  # Active area
            "0x2A0020": True,  # Sparse area
            "0x300060": True,  # Test location
            "0x320040": True,  # Final test area
            "0x340000": True   # Edge case area
        }
    }

    return sample_data


def run_validation_demo(rom_path: str):
    """
    Run a complete validation demo.
    
    Args:
        rom_path: Path to a ROM file for testing
    """
    logger.info("=== ROM Offset Validation Demo ===")

    if not Path(rom_path).exists():
        logger.error(f"ROM file not found: {rom_path}")
        logger.info("Please provide a valid ROM file path to run the demo")
        return

    # Create temporary JSON files with sample data
    with tempfile.NamedTemporaryFile(mode='w', suffix='_fixed.json', delete=False) as f:
        json.dump(create_sample_lua_output(), f, indent=2)
        fixed_json_path = f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='_precise.json', delete=False) as f:
        json.dump(create_sample_precise_lua_output(), f, indent=2)
        precise_json_path = f.name

    try:
        # Test both formats
        for json_path, script_type in [(fixed_json_path, "Fixed Offsets"), (precise_json_path, "Precise Offsets")]:
            logger.info(f"\n--- Testing {script_type} Format ---")

            # Initialize validator
            validator = LuaSpritePalValidator(rom_path)

            # Load Lua results
            lua_offsets = validator.load_lua_results(json_path)
            logger.info(f"Loaded {len(lua_offsets)} offsets from {script_type} data")

            # Validate with SpritePal
            logger.info("Running SpritePal validation on each offset...")
            validation_results = validator.validate_offsets_with_spritepal(lua_offsets)

            # Analyze results
            summary = validator.analyze_results(lua_offsets, validation_results)

            # Print results
            print(f"\n{script_type} Results:")
            print(f"  Total offsets: {summary['total_lua_offsets']}")
            print(f"  Valid sprites: {summary['valid_sprites_found']}")
            print(f"  Accuracy: {summary['accuracy_rate']:.1%}")
            print(f"  High confidence: {summary['high_confidence_sprites']}")

            # Show some example results
            if summary['valid_sprites_found'] > 0:
                print("  Example valid sprites:")
                for result in validator.results["matches"][:3]:  # Show first 3
                    print(f"    {result['offset_hex']}: confidence={result['confidence']:.3f}, "
                          f"tiles={result['tile_count']}")

    finally:
        # Clean up temporary files
        Path(fixed_json_path).unlink()
        Path(precise_json_path).unlink()


def explain_validation_process():
    """Explain how the validation process works."""
    print("""
=== ROM Offset Validation Process ===

This validation system compares two approaches to finding sprites in SNES ROMs:

1. MESEN2 LUA SCRIPTS (Runtime Detection):
   - Monitor DMA transfers during game execution
   - Track when sprite data is loaded from ROM to VRAM
   - Record ROM offsets where sprite data originates
   - Export findings as JSON with offset lists

2. SPRITEPAL MANUAL OFFSET (Static Analysis):
   - Provide direct ROM offset input via slider
   - Attempt HAL decompression at each offset
   - Validate decompressed data as sprite tiles
   - Score confidence based on visual characteristics

VALIDATION WORKFLOW:
1. Load ROM offsets discovered by Lua scripts
2. Test each offset using SpritePal's sprite detection
3. Compare results to identify:
   - True positives (Lua found valid sprites)
   - False positives (Lua found non-sprite data)
   - Confidence levels for each match

EXPECTED OUTCOMES:
- High accuracy (>80%): Lua scripts very reliable
- Medium accuracy (60-80%): Good detection with some false positives  
- Low accuracy (<60%): Many false positives, may need script tuning

CONFIDENCE LEVELS:
- High (≥0.7): Very likely to be actual sprite data
- Medium (0.4-0.7): Possible sprite data, needs review
- Low (<0.4): Unlikely to be sprite data

This validation helps ensure both systems are working correctly
and provides confidence in sprite detection accuracy.
""")


def main():
    """Main demo routine."""
    import argparse

    parser = argparse.ArgumentParser(description="Demo ROM offset validation")
    parser.add_argument("--rom", help="Path to ROM file for testing")
    parser.add_argument("--explain", action="store_true", help="Explain the validation process")

    args = parser.parse_args()

    if args.explain:
        explain_validation_process()
        return

    if args.rom:
        run_validation_demo(args.rom)
    else:
        explain_validation_process()
        print("\nTo run the demo with actual validation:")
        print("  python test_lua_validation_demo.py --rom /path/to/your/rom.smc")


if __name__ == "__main__":
    main()
