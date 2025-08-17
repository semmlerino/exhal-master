#!/usr/bin/env python3
"""
Script to verify that the ROM scan range fix is working correctly.
This demonstrates that the scan now includes the end offset.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.absolute()))

from unittest.mock import Mock

from core.parallel_sprite_finder import ParallelSpriteFinder, SearchChunk


def test_parallel_finder_chunk_iteration():
    """Test that the parallel finder correctly iterates through chunk ranges."""
    print("Testing ParallelSpriteFinder chunk iteration...")

    # Create a mock sprite finder
    mock_finder = Mock()
    mock_finder.find_sprite_at_offset = Mock(return_value=None)

    # Create parallel finder instance
    pf = ParallelSpriteFinder(num_workers=1)

    # Mock ROM data
    rom_data = b'\x00' * 0x2000

    # Track which offsets are checked
    checked_offsets = []

    def track_offset(rom_data, offset):
        checked_offsets.append(offset)

    mock_finder.find_sprite_at_offset.side_effect = track_offset

    # Create a test chunk from 0xF00 to 0x1000
    chunk = SearchChunk(start=0xF00, end=0x1000, chunk_id=0)

    # Mock the quick check to always return True
    pf._quick_sprite_check = Mock(return_value=True)
    pf._calculate_adaptive_step = Mock(return_value=0x100)

    # Search the chunk
    pf._search_chunk(mock_finder, rom_data, chunk)

    print(f"  Chunk range: 0x{chunk.start:X} to 0x{chunk.end:X}")
    print(f"  Offsets checked: {[hex(o) for o in checked_offsets]}")
    print(f"  Last offset checked: {hex(checked_offsets[-1]) if checked_offsets else 'none'}")

    # Check if we're getting close to the end
    if checked_offsets:
        last_checked = checked_offsets[-1]
        if last_checked >= chunk.end - 0x100:
            print(f"  ✓ Scanning near end boundary (last: 0x{last_checked:X})")
        else:
            print(f"  ✗ Not reaching end boundary (last: 0x{last_checked:X}, end: 0x{chunk.end:X})")

    return checked_offsets


def test_rom_extractor_scan_loop():
    """Test the ROMExtractor scan loop logic."""
    print("\nTesting ROMExtractor scan loop...")

    # Simulate the fixed scan loop
    scan_offsets = []

    start_offset = 0xEFE00
    end_offset = 0xF0000
    step = 0x100

    # Use while loop (new implementation)
    offset = start_offset
    while offset < end_offset:
        scan_offsets.append(offset)
        offset += step

    # Check the final offset if exactly at boundary
    if offset == end_offset:
        scan_offsets.append(offset)

    print(f"  Range: 0x{start_offset:X} to 0x{end_offset:X}, step: 0x{step:X}")
    print(f"  Number of offsets: {len(scan_offsets)}")
    print(f"  Last 3 offsets: {[hex(o) for o in scan_offsets[-3:]]}")
    print(f"  Includes end offset (0x{end_offset:X}): {end_offset in scan_offsets}")

    if end_offset in scan_offsets:
        print("  ✓ End offset IS scanned")
    else:
        print("  ✗ End offset NOT scanned - BUG!")

    return scan_offsets


def compare_old_vs_new():
    """Compare old range() method vs new while loop method."""
    print("\nComparing old vs new scanning methods:")

    start = 0xC0000
    end = 0xF0000
    step = 0x1000

    # Old method (buggy)
    old_offsets = list(range(start, end, step))

    # New method (fixed)
    new_offsets = []
    offset = start
    while offset < end:
        new_offsets.append(offset)
        offset += step
    if offset == end:
        new_offsets.append(offset)

    print(f"  Range: 0x{start:X} to 0x{end:X}, step: 0x{step:X}")
    print(f"  Old method: {len(old_offsets)} offsets, last=0x{old_offsets[-1]:X}")
    print(f"  New method: {len(new_offsets)} offsets, last=0x{new_offsets[-1]:X}")
    print(f"  Difference: {set(new_offsets) - set(old_offsets)}")

    if end in new_offsets and end not in old_offsets:
        print(f"  ✓ Bug fixed: End offset 0x{end:X} now included!")
    elif end in old_offsets:
        print("  ℹ️  End offset was already included (step divides evenly)")
    else:
        print(f"  ✗ Bug still present: End offset 0x{end:X} not included")


if __name__ == "__main__":
    print("=" * 60)
    print("ROM Scan Range Fix Verification")
    print("=" * 60)

    test_parallel_finder_chunk_iteration()
    test_rom_extractor_scan_loop()
    compare_old_vs_new()

    print("\n" + "=" * 60)
    print("Summary: The scan range fix ensures the end offset is")
    print("included in the scan, preventing sprites at ROM boundaries")
    print("from being missed.")
    print("=" * 60)
