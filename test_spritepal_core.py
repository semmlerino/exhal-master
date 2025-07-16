#!/usr/bin/env python3
"""
Test SpritePal core functionality without GUI
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from spritepal.core.extractor import SpriteExtractor
from spritepal.core.palette_manager import PaletteManager


def test_extraction():
    """Test sprite extraction"""
    print("Testing SpritePal Core Functionality")
    print("=" * 40)
    
    # Check for dump files
    vram_file = None
    cgram_file = None
    
    # Look for Cave dumps first
    if Path("Cave.SnesVideoRam.dmp").exists():
        vram_file = "Cave.SnesVideoRam.dmp"
        cgram_file = "Cave.SnesCgRam.dmp"
        print(f"Found Cave dumps")
    elif Path("VRAM.dmp").exists():
        vram_file = "VRAM.dmp"
        cgram_file = "CGRAM.dmp"
        print(f"Found standard dumps")
    else:
        print("No dump files found!")
        return
        
    # Test sprite extraction
    print(f"\n1. Testing Sprite Extraction")
    print(f"   VRAM: {vram_file}")
    
    extractor = SpriteExtractor()
    try:
        img, num_tiles = extractor.extract_sprites_grayscale(
            vram_file,
            "test_sprites.png"
        )
        print(f"   ✓ Extracted {num_tiles} tiles")
        print(f"   ✓ Saved to test_sprites.png")
    except Exception as e:
        print(f"   ✗ Extraction failed: {e}")
        return
        
    # Test palette extraction
    if Path(cgram_file).exists():
        print(f"\n2. Testing Palette Extraction")
        print(f"   CGRAM: {cgram_file}")
        
        palette_manager = PaletteManager()
        try:
            palette_manager.load_cgram(cgram_file)
            sprite_palettes = palette_manager.get_sprite_palettes()
            print(f"   ✓ Loaded {len(sprite_palettes)} sprite palettes")
            
            # Show first few colors of palette 8
            pal8 = palette_manager.get_palette(8)
            print(f"   ✓ Palette 8 (Kirby): {pal8[:4]}...")
            
            # Create a test palette file
            palette_manager.create_palette_json(
                8,
                "test_palette.pal.json",
                "test_sprites.png"
            )
            print(f"   ✓ Created test_palette.pal.json")
            
        except Exception as e:
            print(f"   ✗ Palette extraction failed: {e}")
            
    print("\n✓ Core functionality test complete!")
    print("\nTest files created:")
    print("  - test_sprites.png (grayscale sprite sheet)")
    print("  - test_palette.pal.json (Kirby palette)")
    

if __name__ == "__main__":
    test_extraction()