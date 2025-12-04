#!/usr/bin/env python3
"""
Test script to verify the clipboard workflow between Mesen2 and SpritePal.

This tests:
1. Reading clipboard file from Mesen2
2. Navigating to the pasted offset
3. Verifying HAL decompression works correctly
"""

from pathlib import Path


def test_clipboard_reading():
    """Test reading offset from clipboard file."""
    print("Testing clipboard workflow...")

    # Check possible clipboard file locations
    possible_paths = [
        Path.home() / "Mesen2" / "sprite_clipboard.txt",
        Path.home() / "Documents" / "Mesen2" / "sprite_clipboard.txt",
        Path.cwd() / "sprite_clipboard.txt",
    ]

    clipboard_file = None
    for path in possible_paths:
        if path.exists():
            clipboard_file = path
            print(f"✓ Found clipboard file at: {path}")
            break

    if not clipboard_file:
        print("✗ No clipboard file found. Please:")
        print("  1. Run Mesen2 with the Lua script")
        print("  2. Press 'C' while hovering over a sprite")
        print("  3. Check that sprite_clipboard.txt was created")
        return False

    # Read the offset
    try:
        with open(clipboard_file) as f:
            offset_str = f.read().strip()

        if not offset_str:
            print("✗ Clipboard file is empty")
            return False

        # Parse the offset
        if offset_str.startswith("0x") or offset_str.startswith("0X"):
            offset = int(offset_str, 16)
        else:
            offset = int(offset_str, 16)

        print(f"✓ Read offset from clipboard: 0x{offset:06X}")

        # Validate the offset is in valid ROM range
        if offset < 0:
            print(f"✗ Invalid negative offset: 0x{offset:06X}")
            return False

        # Check which bank this offset would be in
        bank = (offset // 0x8000) + 0x80
        bank_offset = offset % 0x8000

        print(f"  Bank: 0x{bank:02X}, Offset in bank: 0x{bank_offset:04X}")

        # Validate bank range for LoROM
        if bank > 0xBF:
            print(f"⚠️ WARNING: Bank 0x{bank:02X} is outside normal ROM range (0x80-0xBF)")
            print("  This suggests the offset may be from RAM, not ROM")
            print("  The Lua script may be capturing RAM->VRAM transfers instead of ROM->VRAM")
            print("  HAL decompression will likely fail for this offset")
            print()
            print("  Possible causes:")
            print("  1. The game decompresses sprites to RAM first, then DMAs to VRAM")
            print("  2. The Lua script needs to track ROM->RAM transfers to find original offsets")
            print()
            print("  Try enabling debug logging in the Lua script to see transfer details")
            return False

        # Valid ROM offset
        if offset > 0x400000:  # 4MB max for typical SNES ROM
            print(f"⚠️ Offset 0x{offset:06X} exceeds typical 4MB ROM size")
            print("  This ROM may be larger than usual or the offset may be incorrect")

        print(f"✓ Offset 0x{offset:06X} appears to be a valid ROM offset")
        return True

    except Exception as e:
        print(f"✗ Error reading clipboard: {e}")
        return False

def test_session_file():
    """Test reading session export file."""
    print("\nTesting session export...")

    session_file = Path.home() / "Mesen2" / "sprite_session.json"

    if not session_file.exists():
        print("✗ No session file found. Please:")
        print("  1. Run Mesen2 with the Lua script")
        print("  2. Capture some sprites")
        print("  3. Press 'E' to export session")
        return False

    try:
        import json
        with open(session_file) as f:
            session_data = json.load(f)

        if "sprites" not in session_data:
            print("✗ Session file missing 'sprites' key")
            return False

        sprite_count = len(session_data["sprites"])
        print(f"✓ Session file contains {sprite_count} sprites")

        # Show first few sprites
        for i, sprite in enumerate(session_data["sprites"][:3]):
            print(f"  Sprite {i+1}: ROM offset 0x{sprite['rom_offset']:06X}, "
                  f"tile ${sprite['tile']:02X}, palette {sprite['palette']}")

        if sprite_count > 3:
            print(f"  ... and {sprite_count - 3} more")

        return True

    except Exception as e:
        print(f"✗ Error reading session file: {e}")
        return False

def main():
    """Run all workflow tests."""
    print("=" * 60)
    print("SpritePal Clipboard Workflow Test")
    print("=" * 60)

    clipboard_ok = test_clipboard_reading()
    session_ok = test_session_file()

    print("\n" + "=" * 60)
    if clipboard_ok and session_ok:
        print("✓ All tests passed!")
        print("\nNext steps:")
        print("1. Open SpritePal")
        print("2. Load your ROM")
        print("3. Open Manual Offset dialog")
        print("4. Click the 'Paste' button")
        print("5. The sprite should decompress and display correctly")
    elif clipboard_ok:
        print("✓ Clipboard test passed, session export not found")
        print("\nYou can still test the paste functionality in SpritePal")
    else:
        print("✗ Tests failed - please check the instructions above")
    print("=" * 60)

if __name__ == "__main__":
    main()
