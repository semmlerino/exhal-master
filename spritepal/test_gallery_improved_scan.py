#!/usr/bin/env python3
"""
Test script to verify gallery loads more sprites with improved scanning.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from core.sprite_finder import SpriteFinder
from utils.logging_config import get_logger

logger = get_logger(__name__)


def test_improved_scanning():
    """Test that improved scanning finds more sprites."""
    
    # Use the preloaded ROM if available
    rom_path = Path("/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master/kss.sfc")
    
    if not rom_path.exists():
        logger.warning("ROM file not found. Please ensure kss.sfc is in the expected location.")
        return
    
    logger.info(f"Testing sprite scanning on: {rom_path}")
    
    # Read ROM data
    with open(rom_path, 'rb') as f:
        rom_data = f.read()
    
    # Initialize finder
    finder = SpriteFinder()
    
    # Test quick scan (similar to old behavior)
    logger.info("\n=== Testing Quick Scan (larger steps) ===")
    quick_ranges = [
        (0x200000, 0x280000, 0x800),  # Main sprite area - scan every 2048 bytes
        (0x100000, 0x180000, 0x1000),  # Secondary area - scan every 4096 bytes
    ]
    
    quick_sprites = []
    for start, end, step in quick_ranges:
        for offset in range(start, min(end, len(rom_data)), step):
            sprite_info = finder.find_sprite_at_offset(rom_data, offset)
            if sprite_info:
                quick_sprites.append(sprite_info)
            if len(quick_sprites) >= 200:
                break
        if len(quick_sprites) >= 200:
            break
    
    logger.info(f"Quick scan found: {len(quick_sprites)} sprites")
    
    # Test thorough scan (new improved behavior)
    logger.info("\n=== Testing Thorough Scan (smaller steps) ===")
    thorough_ranges = [
        (0x200000, 0x280000, 0x100),  # Main sprite area - scan every 256 bytes
        (0x280000, 0x300000, 0x200),  # Extended main area - scan every 512 bytes
        (0x100000, 0x180000, 0x200),  # Secondary area - scan every 512 bytes
        (0x180000, 0x200000, 0x400),  # Extended secondary - scan every 1024 bytes
        (0x300000, 0x380000, 0x400),  # Additional area - scan every 1024 bytes
    ]
    
    thorough_sprites = []
    for start, end, step in thorough_ranges:
        for offset in range(start, min(end, len(rom_data)), step):
            sprite_info = finder.find_sprite_at_offset(rom_data, offset)
            if sprite_info:
                thorough_sprites.append(sprite_info)
            if len(thorough_sprites) >= 200:
                break
        if len(thorough_sprites) >= 200:
            break
    
    logger.info(f"Thorough scan found: {len(thorough_sprites)} sprites")
    
    # Compare results
    logger.info("\n=== Results Comparison ===")
    logger.info(f"Quick scan:    {len(quick_sprites)} sprites")
    logger.info(f"Thorough scan: {len(thorough_sprites)} sprites")
    logger.info(f"Improvement:   {len(thorough_sprites) - len(quick_sprites)} more sprites found")
    
    if len(thorough_sprites) > len(quick_sprites):
        logger.info("✓ SUCCESS: Thorough scan finds more sprites than quick scan")
    else:
        logger.warning("⚠ WARNING: Thorough scan did not find more sprites")
    
    # Show first few sprite offsets from each scan
    logger.info("\nFirst 10 sprites from quick scan:")
    for i, sprite in enumerate(quick_sprites[:10]):
        logger.info(f"  {i+1}. Offset: 0x{sprite['offset']:06X}, Tiles: {sprite['tile_count']}")
    
    logger.info("\nFirst 10 sprites from thorough scan:")
    for i, sprite in enumerate(thorough_sprites[:10]):
        logger.info(f"  {i+1}. Offset: 0x{sprite['offset']:06X}, Tiles: {sprite['tile_count']}")
    
    return len(quick_sprites), len(thorough_sprites)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    try:
        quick_count, thorough_count = test_improved_scanning()
        
        print("\n" + "="*50)
        print("Gallery Sprite Loading Test Complete")
        print("="*50)
        print(f"Quick Scan:    {quick_count} sprites")
        print(f"Thorough Scan: {thorough_count} sprites")
        print(f"Improvement:   +{thorough_count - quick_count} sprites")
        
        if thorough_count > 21:
            print("\n✓ SUCCESS: Gallery can now load more than 21 sprites!")
        else:
            print("\n⚠ More investigation needed - still finding limited sprites")
            
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)