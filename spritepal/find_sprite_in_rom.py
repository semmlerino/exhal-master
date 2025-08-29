#!/usr/bin/env python3
"""
Find HAL-compressed sprites in ROM by matching decompressed data from RAM.

This script helps locate the original ROM offset of sprites that have been
decompressed into RAM by searching for compressed data that matches.
"""

import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple
import struct

def decompress_at_offset(rom_path: str, offset: int, exhal_path: str = "./exhal") -> Optional[bytes]:
    """
    Try to decompress data at a specific ROM offset using exhal.
    
    Returns decompressed bytes or None if decompression fails.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp_out:
            output_path = tmp_out.name
        
        # Run exhal to decompress
        cmd = [exhal_path, rom_path, f"0x{offset:X}", output_path]
        result = subprocess.run(cmd, capture_output=True, timeout=5)
        
        if result.returncode == 0 and Path(output_path).exists():
            with open(output_path, 'rb') as f:
                data = f.read()
            Path(output_path).unlink()  # Clean up
            return data if len(data) > 0 else None
        
        # Clean up on failure
        if Path(output_path).exists():
            Path(output_path).unlink()
        return None
        
    except Exception as e:
        print(f"Error decompressing at 0x{offset:X}: {e}")
        return None

def find_sprite_in_rom(
    rom_path: str, 
    target_data: bytes, 
    start_offset: int = 0, 
    end_offset: Optional[int] = None,
    signature_size: int = 64
) -> List[int]:
    """
    Search ROM for HAL-compressed sprites matching target data.
    
    Args:
        rom_path: Path to ROM file
        target_data: Decompressed sprite data to match (from RAM)
        start_offset: Start searching from this offset
        end_offset: Stop searching at this offset (None = end of ROM)
        signature_size: Only compare first N bytes for speed
    
    Returns:
        List of ROM offsets where matching sprites were found
    """
    matches = []
    
    # Read ROM
    with open(rom_path, 'rb') as f:
        rom_data = f.read()
    
    if end_offset is None:
        end_offset = len(rom_data)
    
    # Create signature from target data
    signature = target_data[:min(signature_size, len(target_data))]
    print(f"Searching for sprite with {len(signature)}-byte signature...")
    print(f"Signature: {signature[:16].hex()}...")
    
    # Search ROM in chunks (HAL compression usually starts on even boundaries)
    offset = start_offset
    checked = 0
    
    while offset < end_offset:
        # Show progress
        if checked % 1000 == 0:
            progress = (offset - start_offset) / (end_offset - start_offset) * 100
            print(f"Progress: {progress:.1f}% (0x{offset:06X})", end='\r')
        
        # Try to decompress at this offset
        decompressed = decompress_at_offset(rom_path, offset)
        
        if decompressed and len(decompressed) >= len(signature):
            # Check if signature matches
            if decompressed[:len(signature)] == signature:
                print(f"\nFound match at ROM offset 0x{offset:06X}!")
                matches.append(offset)
                
                # Verify full match if requested
                if len(decompressed) >= len(target_data):
                    if decompressed[:len(target_data)] == target_data:
                        print(f"  Full match confirmed ({len(target_data)} bytes)")
                    else:
                        print(f"  Partial match only (signature matches but full data differs)")
        
        # Move to next potential offset
        # HAL compression headers are usually aligned
        offset += 2  # Check every 2 bytes (can adjust for speed)
        checked += 1
    
    print(f"\nSearch complete. Found {len(matches)} matches.")
    return matches

def dump_ram_region(ram_dump_file: str, address: int, size: int) -> bytes:
    """
    Extract a region from a RAM dump file.
    
    Args:
        ram_dump_file: Path to RAM dump (from save state or memory export)
        address: RAM address (e.g., 0x7E1234)
        size: Number of bytes to extract
    
    Returns:
        Extracted bytes
    """
    with open(ram_dump_file, 'rb') as f:
        # Adjust address based on dump format
        # For WRAM dumps, addresses 0x7E0000-0x7FFFFF map to offset 0x0000-0x1FFFF
        if address >= 0x7E0000:
            offset = address - 0x7E0000
        else:
            offset = address
        
        f.seek(offset)
        return f.read(size)

def quick_sprite_search(rom_path: str, ram_address: int, sprite_size: int = 0x800) -> Optional[int]:
    """
    Quick search for a sprite using common Kirby sprite locations.
    
    This checks known sprite table regions first for faster results.
    """
    # Common sprite regions in Kirby games (adjust based on your ROM)
    sprite_regions = [
        (0x040000, 0x080000),  # Common sprite bank 1
        (0x080000, 0x0C0000),  # Common sprite bank 2
        (0x0C0000, 0x100000),  # Common sprite bank 3
        (0x100000, 0x140000),  # Extended sprites
        (0x140000, 0x180000),  # More sprites
        (0x180000, 0x1C0000),  # Even more sprites
    ]
    
    print(f"Quick searching common sprite regions for RAM address 0x{ram_address:06X}...")
    
    # Would need actual RAM data here - this is a template
    # In practice, you'd dump the RAM from Mesen2 first
    
    for start, end in sprite_regions:
        print(f"Checking region 0x{start:06X}-0x{end:06X}...")
        # Search this region
        # matches = find_sprite_in_rom(rom_path, target_data, start, end)
        # if matches:
        #     return matches[0]
    
    return None

def main():
    """Example usage of the sprite finder."""
    
    if len(sys.argv) < 2:
        print("Usage: python find_sprite_in_rom.py <rom_path> [ram_dump] [ram_address]")
        print("\nExample:")
        print("  python find_sprite_in_rom.py kirby.sfc ram.bin 0x7ECBA1")
        print("\nThis will search the ROM for compressed sprites that match")
        print("the data found at the specified RAM address.")
        return
    
    rom_path = sys.argv[1]
    
    if not Path(rom_path).exists():
        print(f"ROM file not found: {rom_path}")
        return
    
    # Check for exhal tool
    exhal_path = "./exhal"
    if sys.platform == "win32":
        exhal_path = "./exhal.exe"
    
    if not Path(exhal_path).exists():
        print(f"exhal tool not found at {exhal_path}")
        print("Please compile exhal first: python compile_hal_tools.py")
        return
    
    print(f"ROM: {rom_path}")
    print(f"Using exhal: {exhal_path}")
    
    if len(sys.argv) >= 4:
        ram_dump = sys.argv[2]
        ram_address = int(sys.argv[3], 16) if sys.argv[3].startswith("0x") else int(sys.argv[3])
        
        print(f"RAM dump: {ram_dump}")
        print(f"RAM address: 0x{ram_address:06X}")
        
        # Extract sprite data from RAM dump
        sprite_data = dump_ram_region(ram_dump, ram_address, 0x800)  # Assuming 2KB sprite
        
        # Search ROM for this sprite
        matches = find_sprite_in_rom(rom_path, sprite_data)
        
        if matches:
            print("\nMatching ROM offsets:")
            for offset in matches:
                print(f"  0x{offset:06X}")
            print(f"\nYou can now use offset 0x{matches[0]:06X} in SpritePal!")
    else:
        # Demo mode - just show how it works
        print("\nDemo mode - showing how to search for sprites...")
        print("To actually search, provide a RAM dump and address.")
        
        # You could add a test search here with known data

if __name__ == "__main__":
    main()