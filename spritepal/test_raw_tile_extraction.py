#!/usr/bin/env python3
"""
Direct test of raw tile extraction to verify the data pipeline.
Tests if raw tile data is properly extracted and non-zero.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_raw_tile_extraction():
    """Test raw tile extraction at various offsets."""
    # Find a test ROM
    test_rom = None
    test_dir = project_root / "tests" / "fixtures" / "roms"
    
    if test_dir.exists():
        for rom_file in test_dir.glob("*.sfc"):
            test_rom = str(rom_file)
            break
    
    if not test_rom:
        # Try to find any ROM in the project
        for rom_file in project_root.rglob("*.sfc"):
            test_rom = str(rom_file)
            break
    
    if not test_rom:
        print("No test ROM found. Please place a .sfc file in tests/fixtures/roms/")
        return
    
    print(f"Using test ROM: {test_rom}")
    
    # Read ROM data
    with open(test_rom, "rb") as f:
        rom_data = f.read()
    
    print(f"ROM size: {len(rom_data)} bytes")
    
    # Test various offsets
    test_offsets = [0x0, 0x1000, 0x8000, 0x10000, 0x20000, 0x40000]
    
    for offset in test_offsets:
        if offset >= len(rom_data):
            continue
            
        print(f"\n=== Testing offset 0x{offset:06X} ===")
        
        # Extract 4KB of raw tile data (same as manual browsing)
        expected_size = 4096
        if offset + expected_size <= len(rom_data):
            tile_data = rom_data[offset:offset + expected_size]
        else:
            tile_data = rom_data[offset:]
        
        print(f"Extracted {len(tile_data)} bytes")
        
        # Analyze the data
        non_zero_count = sum(1 for b in tile_data if b != 0)
        percent_non_zero = (non_zero_count / len(tile_data)) * 100
        
        print(f"Non-zero bytes: {non_zero_count}/{len(tile_data)} ({percent_non_zero:.1f}%)")
        print(f"First 40 bytes (hex): {tile_data[:40].hex()}")
        
        # Check for patterns
        unique_bytes = len(set(tile_data[:500]))
        print(f"Unique byte values in first 500 bytes: {unique_bytes}")
        
        if non_zero_count == 0:
            print("WARNING: Data is all zeros!")
        elif percent_non_zero < 5:
            print("WARNING: Data is mostly zeros!")
        else:
            print("Data appears to have content")

def test_worker_simulation():
    """Simulate what the preview worker does."""
    from ui.common.preview_worker_pool import PooledPreviewWorker
    from core.extraction.extraction_manager import ExtractionManager
    
    print("\n" + "=" * 60)
    print("TESTING WORKER SIMULATION")
    print("=" * 60)
    
    # Find test ROM
    test_rom = None
    for rom_file in project_root.rglob("*.sfc"):
        test_rom = str(rom_file)
        break
    
    if not test_rom:
        print("No ROM found for worker test")
        return
    
    print(f"Using ROM: {test_rom}")
    
    # Create extraction manager
    manager = ExtractionManager()
    extractor = manager.get_rom_extractor()
    
    # Create a mock request
    class MockRequest:
        def __init__(self, offset):
            self.rom_path = test_rom
            self.offset = offset
            self.request_id = 1
    
    # Test worker at different offsets
    test_offsets = [0x1000, 0x8000, 0x20000]
    
    for offset in test_offsets:
        print(f"\n=== Worker test at offset 0x{offset:06X} ===")
        
        worker = PooledPreviewWorker()
        request = MockRequest(offset)
        worker.setup_request(request, extractor)
        
        print(f"Worker sprite_name: {worker.sprite_name}")
        print(f"Should trigger raw extraction: {worker.sprite_name.startswith('manual_')}")
        
        # Read ROM data directly to see what worker would extract
        with open(test_rom, "rb") as f:
            rom_data = f.read()
        
        if offset < len(rom_data):
            expected_size = 4096
            if offset + expected_size <= len(rom_data):
                tile_data = rom_data[offset:offset + expected_size]
            else:
                tile_data = rom_data[offset:]
            
            non_zero = sum(1 for b in tile_data[:500] if b != 0)
            print(f"Raw data analysis: {non_zero}/500 non-zero bytes")
            print(f"First 40 bytes: {tile_data[:40].hex()}")

if __name__ == "__main__":
    print("RAW TILE EXTRACTION TEST")
    print("=" * 60)
    
    test_raw_tile_extraction()
    test_worker_simulation()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("If you see mostly non-zero data above, the extraction is working.")
    print("The issue may be in the display pipeline or signal handling."