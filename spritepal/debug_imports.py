#!/usr/bin/env python3
"""Debug import issues."""

import sys
import traceback

def test_import(module_name):
    print(f"\nTesting import of {module_name}...")
    try:
        __import__(module_name)
        print(f"  ✓ {module_name} imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ {module_name} failed: {e}")
        traceback.print_exc()
        return False

# Test imports in order
modules = [
    "core.mmap_rom_reader",
    "utils.constants", 
    "core.rom_extractor",
    "core.optimized_rom_extractor",
    "core.managers.base",
    "core.managers.monitoring_manager",
]

for module in modules:
    if not test_import(module):
        print(f"\nStopping at {module} due to import error")
        break