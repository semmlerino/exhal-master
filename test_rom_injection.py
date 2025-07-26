#!/usr/bin/env python3
"""
Test script for ROM injection functionality
"""

import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spritepal.core.hal_compression import HALCompressor
from spritepal.core.rom_injector import ROMInjector


def test_hal_tools():
    """Test if HAL compression tools are available"""
    print("Testing HAL compression tools...")
    
    try:
        compressor = HALCompressor()
        success, message = compressor.test_tools()
        print(f"HAL tools test: {message}")
        return success
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_rom_header(rom_path):
    """Test reading ROM header"""
    print(f"\nTesting ROM header reading for: {rom_path}")
    
    if not os.path.exists(rom_path):
        print(f"ROM file not found: {rom_path}")
        return False
        
    try:
        injector = ROMInjector()
        header = injector.read_rom_header(rom_path)
        
        print(f"ROM Title: {header.title}")
        print(f"ROM Type: 0x{header.rom_type:02X}")
        print(f"ROM Size: {1 << (header.rom_size + 10)} KB")
        print(f"Checksum: 0x{header.checksum:04X}")
        print(f"Complement: 0x{header.checksum_complement:04X}")
        
        return True
    except Exception as e:
        print(f"Error reading ROM header: {e}")
        return False


def test_sprite_locations(rom_path):
    """Test finding sprite locations"""
    print(f"\nFinding sprite locations...")
    
    try:
        injector = ROMInjector()
        locations = injector.find_sprite_locations(rom_path)
        
        print(f"Found {len(locations)} sprite locations:")
        for name, pointer in locations.items():
            print(f"  - {name}: 0x{pointer.offset:06X} (Bank: ${pointer.bank:02X})")
            
        return True
    except Exception as e:
        print(f"Error finding sprite locations: {e}")
        return False


def test_compression():
    """Test HAL compression/decompression"""
    print("\nTesting compression...")
    
    try:
        compressor = HALCompressor()
        
        # Test data
        test_data = b"Hello World! " * 100  # Repetitive data compresses well
        print(f"Original size: {len(test_data)} bytes")
        
        # Compress
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
            compressed_file = tmp.name
            
        compressed_size = compressor.compress_to_file(test_data, compressed_file)
        print(f"Compressed size: {compressed_size} bytes")
        print(f"Compression ratio: {compressed_size / len(test_data):.2%}")
        
        # Clean up
        os.unlink(compressed_file)
        
        return True
    except Exception as e:
        print(f"Error during compression test: {e}")
        return False


def main():
    """Run all tests"""
    print("SpritePal ROM Injection Test Suite")
    print("=" * 50)
    
    # Test 1: HAL tools
    if not test_hal_tools():
        print("\nHAL tools not available. Please build them first:")
        print("  cd /path/to/exhal-master")
        print("  make")
        return 1
    
    # Test 2: Compression
    if not test_compression():
        return 1
    
    # Test 3: ROM operations (if ROM provided)
    if len(sys.argv) > 1:
        rom_path = sys.argv[1]
        
        if not test_rom_header(rom_path):
            return 1
            
        if not test_sprite_locations(rom_path):
            return 1
    else:
        print("\nNo ROM file provided. Skipping ROM tests.")
        print("Usage: python test_rom_injection.py <rom_file>")
    
    print("\n" + "=" * 50)
    print("All tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())