#!/usr/bin/env python3
"""
Integrated sprite ROM finder for Kirby games.
Finds actual ROM offsets for sprites that have been decompressed to RAM.
"""

import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Tuple
import time

class SpriteRomFinder:
    """Find ROM offsets for HAL-compressed sprites."""
    
    def __init__(self, rom_path: str, exhal_path: str = None):
        self.rom_path = rom_path
        self.exhal_path = exhal_path or self._find_exhal()
        self.sprite_cache = {}  # Cache decompressed sprites
        
        # Common sprite regions in Kirby games
        self.sprite_regions = [
            (0x040000, 0x080000, "Player sprites"),
            (0x080000, 0x0C0000, "Enemy sprites"),
            (0x0C0000, 0x100000, "Boss sprites"),
            (0x100000, 0x140000, "Effects/Items"),
            (0x140000, 0x180000, "Extended sprites"),
            (0x180000, 0x1C0000, "Extra sprites"),
            (0x1C0000, 0x200000, "Bonus sprites"),
        ]
    
    def _find_exhal(self) -> str:
        """Find the exhal executable."""
        if sys.platform == "win32":
            if Path("./exhal.exe").exists():
                return "./exhal.exe"
        if Path("./exhal").exists():
            return "./exhal"
        raise FileNotFoundError("exhal tool not found. Run: python compile_hal_tools.py")
    
    def decompress_at(self, offset: int) -> Optional[bytes]:
        """Decompress data at ROM offset using exhal."""
        # Check cache first
        if offset in self.sprite_cache:
            return self.sprite_cache[offset]
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tmp:
                output_path = tmp.name
            
            cmd = [self.exhal_path, self.rom_path, f"0x{offset:X}", output_path]
            result = subprocess.run(cmd, capture_output=True, timeout=2)
            
            if result.returncode == 0 and Path(output_path).exists():
                with open(output_path, 'rb') as f:
                    data = f.read()
                Path(output_path).unlink()
                
                # Cache if valid
                if len(data) > 0:
                    self.sprite_cache[offset] = data
                    return data
            
            # Cleanup
            if Path(output_path).exists():
                Path(output_path).unlink()
                
        except Exception:
            pass
        
        return None
    
    def find_sprite(self, ram_data: bytes, quick: bool = True) -> Optional[int]:
        """
        Find ROM offset for sprite data from RAM.
        
        Args:
            ram_data: Decompressed sprite data from RAM
            quick: If True, search common regions first
        
        Returns:
            ROM offset if found, None otherwise
        """
        signature = ram_data[:min(64, len(ram_data))]
        print(f"Searching for sprite (signature: {signature[:8].hex()}...)")
        
        if quick:
            # Search common regions first
            for start, end, desc in self.sprite_regions:
                print(f"Searching {desc} (0x{start:06X}-0x{end:06X})...")
                offset = self._search_region(signature, ram_data, start, end)
                if offset:
                    return offset
        else:
            # Search entire ROM
            print("Searching entire ROM (this may take a while)...")
            return self._search_region(signature, ram_data, 0x40000, 0x400000)
        
        return None
    
    def _search_region(self, signature: bytes, full_data: bytes, 
                      start: int, end: int) -> Optional[int]:
        """Search a ROM region for matching sprite."""
        # Search with different alignments based on region size
        step = 8 if (end - start) < 0x40000 else 16
        
        for offset in range(start, end, step):
            if offset % 0x1000 == 0:
                progress = (offset - start) / (end - start) * 100
                print(f"  Progress: {progress:.1f}%", end='\r')
            
            decompressed = self.decompress_at(offset)
            
            if decompressed and len(decompressed) >= len(signature):
                if decompressed[:len(signature)] == signature:
                    # Verify full match
                    full_match = (len(decompressed) >= len(full_data) and
                                 decompressed[:len(full_data)] == full_data)
                    
                    print(f"\n✅ Found at 0x{offset:06X} ({'Full' if full_match else 'Partial'} match)")
                    return offset
        
        print()  # New line after progress
        return None
    
    def process_ram_dump(self, dump_file: str) -> Optional[int]:
        """Process a RAM dump file and find its ROM offset."""
        print(f"Processing RAM dump: {dump_file}")
        
        with open(dump_file, 'rb') as f:
            ram_data = f.read()
        
        print(f"RAM dump size: {len(ram_data)} bytes")
        
        # Try quick search first
        offset = self.find_sprite(ram_data, quick=True)
        
        if not offset:
            print("Quick search failed, trying full ROM search...")
            offset = self.find_sprite(ram_data, quick=False)
        
        return offset
    
    def process_session(self, session_file: str, output_file: str = "sprite_mapping.json"):
        """Process a session file and create RAM→ROM mapping."""
        print(f"Processing session: {session_file}")
        
        with open(session_file, 'r') as f:
            session = json.load(f)
        
        mapping = {}
        sprites = session.get("sprites", [])
        
        print(f"Found {len(sprites)} sprites in session")
        
        for i, sprite in enumerate(sprites):
            rom_offset = sprite.get("rom_offset", 0)
            
            # Check if it's a RAM offset (marked with high bit)
            if rom_offset >= 0x800000:
                ram_addr = rom_offset & 0x7FFFFF
                print(f"\nSprite {i+1}/{len(sprites)}: RAM 0x{ram_addr:06X}")
                
                # Look for RAM dump file
                dump_file = f"sprite_ram_{ram_addr:06X}.bin"
                if Path(dump_file).exists():
                    rom_offset = self.process_ram_dump(dump_file)
                    if rom_offset:
                        mapping[f"0x{ram_addr:06X}"] = f"0x{rom_offset:06X}"
                else:
                    print(f"  No dump file found: {dump_file}")
        
        # Save mapping
        with open(output_file, 'w') as f:
            json.dump(mapping, f, indent=2)
        
        print(f"\n📝 Saved mapping to {output_file}")
        print(f"   Mapped {len(mapping)} sprites")
        
        return mapping

def main():
    """Main entry point with improved CLI."""
    if len(sys.argv) < 3:
        print("🎮 Kirby Sprite ROM Finder")
        print("=" * 40)
        print("\nUsage:")
        print("  Single sprite:  python sprite_rom_finder.py <rom> <ram_dump.bin>")
        print("  Session:        python sprite_rom_finder.py <rom> --session <session.json>")
        print("  Quick test:     python sprite_rom_finder.py <rom> --test")
        print("\nExamples:")
        print("  python sprite_rom_finder.py kirby.sfc sprite_ram_7ECBA1.bin")
        print("  python sprite_rom_finder.py kirby.sfc --session sprite_session.json")
        return
    
    rom_path = sys.argv[1]
    
    if not Path(rom_path).exists():
        print(f"❌ ROM not found: {rom_path}")
        return
    
    finder = SpriteRomFinder(rom_path)
    
    if len(sys.argv) > 2:
        if sys.argv[2] == "--session":
            # Process entire session
            session_file = sys.argv[3] if len(sys.argv) > 3 else "sprite_session.json"
            finder.process_session(session_file)
            
        elif sys.argv[2] == "--test":
            # Test with a known sprite pattern
            print("🧪 Running test search...")
            test_data = bytes([0x10, 0x20, 0x30, 0x40] * 16)  # Test pattern
            offset = finder.find_sprite(test_data, quick=True)
            if offset:
                print(f"Test found at 0x{offset:06X}")
            else:
                print("Test pattern not found (expected)")
                
        else:
            # Process single RAM dump
            dump_file = sys.argv[2]
            offset = finder.process_ram_dump(dump_file)
            
            if offset:
                print("\n" + "=" * 40)
                print(f"🎯 SUCCESS!")
                print(f"   ROM offset: 0x{offset:06X}")
                print(f"   Use this in SpritePal to edit the sprite")
                print("=" * 40)
            else:
                print("\n❌ Sprite not found in ROM")
                print("   The sprite may use a different compression")
                print("   or be constructed from multiple parts")

if __name__ == "__main__":
    main()