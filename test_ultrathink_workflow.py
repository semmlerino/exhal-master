#!/usr/bin/env python3
"""
Demonstrate the complete ultrathink workflow
"""

import os
import subprocess


def main():
    print("🎆 ULTRATHINK WORKFLOW DEMONSTRATION")
    print("=" * 50)

    # Step 1: Extract grayscale sprites with palette
    print("\n1️⃣  Extracting sprites in grayscale indexed format...")
    cmd = [
        "python3", "extract_grayscale_sheet.py",
        "Cave.SnesVideoRam.dmp", "0x7000",
        "-p", "kirby_palette_14.pal.json",
        "-o", "demo_ultrathink.png"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        print("✅ Extraction successful!")
        print("   - Grayscale PNG: demo_ultrathink.png")
        print("   - Companion palette: demo_ultrathink.pal.json")
    else:
        print("❌ Extraction failed:", result.stderr)
        return

    # Step 2: Show how to load in editor
    print("\n2️⃣  Loading in indexed pixel editor...")
    print("\nTo use the indexed pixel editor with the ultrathink workflow:")
    print("\nOption A - Auto-detection (recommended):")
    print("  python3 indexed_pixel_editor.py demo_ultrathink.png")
    print("  (The editor will auto-detect and offer to load demo_ultrathink.pal.json)")

    print("\nOption B - Explicit palette:")
    print("  python3 indexed_pixel_editor.py demo_ultrathink.png -p demo_ultrathink.pal.json")

    print("\nOption C - Different palette:")
    print("  python3 indexed_pixel_editor.py demo_ultrathink.png -p kirby_palette_8.pal.json")

    print("\n3️⃣  Editor Features:")
    print("  - Press 'C' to toggle between grayscale index view and color preview")
    print("  - In grayscale mode: see the actual index values (0-15)")
    print("  - In color mode: see how sprites will look in-game")
    print("  - Edit pixels and save changes back to the indexed format")

    print("\n4️⃣  Available Palettes:")
    palettes = [
        ("kirby_palette_14.pal.json", "Pink Kirby (standard)"),
        ("kirby_palette_8.pal.json", "Purple Kirby (power-up?)"),
        ("kirby_smart_palette_11.pal.json", "Yellow/Brown (most used)")
    ]

    for pal_file, desc in palettes:
        if os.path.exists(pal_file):
            print(f"  ✅ {pal_file} - {desc}")
        else:
            print(f"  ❌ {pal_file} - Not found")

    print("\n🎆 The ULTRATHINK workflow is ready to use!")
    print("\nThis workflow allows you to:")
    print("1. Extract sprites preserving their indexed format")
    print("2. Edit with full index visibility")
    print("3. Preview colors in real-time")
    print("4. Save changes back to the game format")

if __name__ == "__main__":
    main()
