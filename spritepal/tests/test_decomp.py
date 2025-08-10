#!/usr/bin/env python3
"""
Test decompression at a known sprite offset.
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.managers.registry import initialize_managers, get_extraction_manager

def test_decompression():
    """Test if decompression works at a known sprite offset."""
    
    # Initialize managers
    print("Initializing managers...")
    initialize_managers()
    extraction_manager = get_extraction_manager()
    rom_extractor = extraction_manager.get_rom_extractor()
    
    test_rom = "Kirby Super Star (USA).sfc"
    if not os.path.exists(test_rom):
        print("ERROR: Test ROM not found!")
        return 1
    
    # Read ROM data
    with open(test_rom, "rb") as f:
        rom_data = f.read()
    
    # Test at a known sprite offset (Kirby main sprite)
    test_offset = 0x20000A  # This is where navigation found a sprite
    
    print(f"\nTesting at offset 0x{test_offset:06X}...")
    
    # First, show raw data
    raw_data = rom_data[test_offset:test_offset + 32]
    print(f"Raw data (first 32 bytes): {raw_data.hex()}")
    
    # Try decompression
    try:
        compressed_size, decompressed_data = rom_extractor.rom_injector.find_compressed_sprite(
            rom_data, test_offset, 8192  # Expected size
        )
        print(f"\nDecompression successful!")
        print(f"Compressed size: {compressed_size} bytes")
        print(f"Decompressed size: {len(decompressed_data)} bytes")
        print(f"First 32 bytes of decompressed: {decompressed_data[:32].hex()}")
        
        # Check if it looks like tile data
        num_tiles = len(decompressed_data) // 32
        print(f"Number of tiles: {num_tiles}")
        
    except Exception as e:
        print(f"\nDecompression failed: {e}")
    
    print("\nTest complete!")
    return 0

if __name__ == "__main__":
    sys.exit(test_decompression())