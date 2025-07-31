#!/usr/bin/env python3
"""Debug script to check ROM cache behavior in tests"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.rom_cache import ROMCache, get_rom_cache
from utils.settings_manager import get_settings_manager


def debug_cache_state():
    """Debug the current cache state and settings"""
    print("=== ROM Cache Debug ===")

    # Check settings manager
    settings_manager = get_settings_manager()
    if settings_manager:
        cache_enabled = settings_manager.get_cache_enabled()
        cache_location = settings_manager.get_cache_location()
        cache_expiration = settings_manager.get_cache_expiration_days()

        print("Settings Manager: Found")
        print(f"  Cache enabled: {cache_enabled}")
        print(f"  Cache location: {cache_location or 'default'}")
        print(f"  Cache expiration: {cache_expiration} days")
        print(f"  Settings file: {settings_manager._settings_file}")
        print(f"  App name: {settings_manager.app_name}")

        # Check if cache settings exist in file
        cache_settings = settings_manager.get("cache", "enabled", default=None)
        print(f"  Cache settings exist: {cache_settings is not None}")
    else:
        print("Settings Manager: None")

    # Create cache with test directory
    test_dir = "/tmp/test_rom_cache"
    cache = ROMCache(cache_dir=test_dir)

    print("\nROMCache instance:")
    print(f"  Cache enabled: {cache.cache_enabled}")
    print(f"  Cache directory: {cache.cache_dir}")
    print(f"  Directory exists: {cache.cache_dir.exists()}")

    # Test cache operations
    test_rom = "/tmp/test.sfc"
    sprite_locations = {"test": {"offset": 0x12345}}

    print(f"\nTesting cache operations with: {test_rom}")

    # Try to save
    success = cache.save_sprite_locations(test_rom, sprite_locations)
    print(f"  Save success: {success}")

    # Try to load
    loaded = cache.get_sprite_locations(test_rom)
    print(f"  Load result: {loaded}")

    # Check cache stats
    stats = cache.get_cache_stats()
    print("\nCache stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test singleton instance
    print("\nGlobal cache instance:")
    global_cache = get_rom_cache()
    print(f"  Cache enabled: {global_cache.cache_enabled}")
    print(f"  Cache directory: {global_cache.cache_dir}")
    print(f"  Same instance as local: {global_cache is cache}")

if __name__ == "__main__":
    debug_cache_state()
