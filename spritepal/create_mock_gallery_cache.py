#!/usr/bin/env python3
"""
Create mock sprite scan data for the Gallery tab.
This simulates what a real ROM scan would produce.
"""

import json
from pathlib import Path

def create_mock_sprite_data():
    """Create realistic mock sprite data."""
    sprites = []
    
    # Create various sprites with different characteristics
    sprite_names = [
        "Kirby_Idle", "Kirby_Walk_1", "Kirby_Walk_2", "Kirby_Jump",
        "Kirby_Float", "Kirby_Inhale", "Kirby_Fire", "Kirby_Ice",
        "Waddle_Dee", "Waddle_Doo", "King_Dedede", "Meta_Knight",
        "Whispy_Woods", "Kracko", "Lololo", "Lalala",
        "Enemy_Star", "Enemy_Sword", "Enemy_Hammer", "Enemy_Parasol",
        "Item_Cherry", "Item_Cake", "Item_1UP", "Item_Invincible",
        "Block_Star", "Block_Stone", "Block_Ice", "Block_Bomb",
        "Background_Tree", "Background_Cloud", "Background_Hill", "Background_Castle"
    ]
    
    # Common sprite sizes (width x height in pixels)
    sizes = [
        (32, 32), (64, 64), (128, 128), (256, 256),
        (32, 64), (64, 32), (128, 64), (64, 128)
    ]
    
    # Generate sprite entries
    base_offset = 0x40000  # Start at a reasonable ROM offset
    
    for i, name in enumerate(sprite_names):
        size = sizes[i % len(sizes)]
        width, height = size
        
        sprite = {
            'offset': base_offset + (i * 0x1000),  # Space them out in ROM
            'offset_hex': f"0x{base_offset + (i * 0x1000):06X}",
            'size': width * height // 2,  # 4bpp sprite data
            'width': width,
            'height': height,
            'name': name,
            'compressed': True,
            'palette_index': i % 8,  # Cycle through 8 palettes
            'tile_count': (width // 8) * (height // 8),  # 8x8 tiles
            'format': '4bpp',
            'compression': 'HAL'
        }
        sprites.append(sprite)
    
    return sprites

def save_gallery_cache(sprites):
    """Save sprite data to the gallery cache file."""
    cache_path = Path.home() / ".spritepal" / "gallery_scan_cache.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    cache_data = {
        'version': 1,
        'rom_path': str(Path.cwd() / "Kirby Super Star (USA).sfc"),
        'rom_size': 4194304,  # 4MB ROM
        'sprite_count': len(sprites),
        'sprites': sprites
    }
    
    with open(cache_path, 'w') as f:
        json.dump(cache_data, f, indent=2)
    
    print(f"✓ Created gallery cache with {len(sprites)} sprites")
    print(f"  Saved to: {cache_path}")
    return cache_path

def main():
    """Create and save mock gallery data."""
    sprites = create_mock_sprite_data()
    
    # Print summary
    print(f"Generated {len(sprites)} mock sprites:")
    for i, sprite in enumerate(sprites[:5]):
        print(f"  {i+1}. {sprite['name']} at {sprite['offset_hex']} ({sprite['width']}x{sprite['height']})")
    if len(sprites) > 5:
        print(f"  ... and {len(sprites) - 5} more")
    
    # Save to cache
    cache_path = save_gallery_cache(sprites)
    
    # Verify it was saved
    with open(cache_path, 'r') as f:
        loaded = json.load(f)
    
    print(f"✓ Verified cache contains {loaded['sprite_count']} sprites")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())