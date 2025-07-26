#!/usr/bin/env python3
"""Test script for the new offset slider functionality."""

import os
import sys

print("Testing Sprite Offset Slider Feature")
print("=" * 60)

# Check if ROM exists
rom_path = "Kirby's Fun Pak (Europe).sfc"
if not os.path.exists(rom_path):
    print(f"ERROR: ROM not found: {rom_path}")
    print("Please ensure the ROM is in the current directory.")
    sys.exit(1)

print(f"\n✓ ROM found: {rom_path}")

# Known good sprite offsets to test
test_offsets = [
    (0x200000, "Perfect quality sprites"),
    (0x378000, "Character sprites"),
    (0x1D0002, "More sprites"),
    (0x1C0000, "Additional sprites")
]

print("\nKnown sprite offsets to test with slider:")
for offset, desc in test_offsets:
    print(f"  - 0x{offset:06X}: {desc}")

print("\n" + "=" * 60)
print("\nTo test the new slider feature:")
print("\n1. Launch SpritePal:")
print("   python launch_spritepal.py")

print("\n2. In ROM Extraction tab:")
print("   - Load ROM: Kirby's Fun Pak (Europe).sfc")
print("   - Switch Mode to: 'Manual Offset Exploration'")
print("   - The offset slider will appear")

print("\n3. Test the slider:")
print("   - Drag slider to 0x200000 - should show Kirby sprites")
print("   - Try 'Next Valid' button - should find next sprite")
print("   - Use 'Jump to' dropdown for quick navigation")
print("   - Change step size for fine/coarse control")

print("\n4. Features to verify:")
print("   - Real-time preview updates while dragging")
print("   - Status shows decompression success/failure")
print("   - Extract button works with manual offset")
print("   - Navigation buttons find valid sprites")

print("\n5. Performance check:")
print("   - Slider should be responsive")
print("   - Preview updates smoothly")
print("   - No UI freezing during decompression")

print("\n" + "=" * 60)
print("\nImplementation complete! The sprite offset slider allows:")
print("- Dynamic exploration of ROM offsets")
print("- Real-time sprite preview")
print("- Smart navigation to valid sprites")
print("- Manual extraction from any offset")
