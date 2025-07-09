#!/usr/bin/env python3
"""
Create multiple test sprite sheets from different dump files
This demonstrates the enhanced workflow with various sprite extractions
"""

import json
import os


def create_kirby_focused_sheet():
    """Create a focused Kirby sprite sheet from the main area"""
    print("=== Creating Kirby Focused Sprite Sheet ===")

    # Extract a focused 8x8 section of Kirby sprites (64 tiles)
    from extract_grayscale_sheet import extract_grayscale_sheet

    if not all(os.path.exists(f) for f in ["Cave.SnesVideoRam.dmp", "Cave.SnesCgRam.dmp"]):
        print("❌ Required dump files not found")
        return False

    try:
        extract_grayscale_sheet(
            "Cave.SnesVideoRam.dmp",
            "Cave.SnesCgRam.dmp",
            offset=0xC000,  # Kirby sprite area
            size=0x800,     # 64 tiles (8x8 grid)
            output_png="kirby_focused_test.png"
        )

        print("✅ Created focused Kirby sheet: kirby_focused_test.png")
        print("✅ Companion palette: kirby_focused_test.pal.json")
        return True

    except Exception as e:
        print(f"❌ Failed to create Kirby focused sheet: {e}")
        return False

def create_small_test_sheets():
    """Create smaller test sheets for quick testing"""
    print("\n=== Creating Small Test Sheets ===")

    from extract_grayscale_sheet import extract_grayscale_sheet

    if not all(os.path.exists(f) for f in ["Cave.SnesVideoRam.dmp", "Cave.SnesCgRam.dmp"]):
        print("❌ Required dump files not found")
        return False

    test_configs = [
        {
            "name": "tiny_test",
            "offset": 0xC000,
            "size": 0x200,  # 16 tiles (4x4 grid)
            "description": "4x4 Kirby sprites"
        },
        {
            "name": "medium_test",
            "offset": 0xC400,
            "size": 0x400,  # 32 tiles (8x4 grid)
            "description": "8x4 sprite section"
        },
        {
            "name": "level_sprites_test",
            "offset": 0xD000,
            "size": 0x600,  # 48 tiles (8x6 grid)
            "description": "Level/environment sprites"
        }
    ]

    created_sheets = []

    for config in test_configs:
        try:
            print(f"Creating {config['description']}...")

            metadata = extract_grayscale_sheet(
                "Cave.SnesVideoRam.dmp",
                "Cave.SnesCgRam.dmp",
                offset=config["offset"],
                size=config["size"],
                output_png=f"{config['name']}.png"
            )

            created_sheets.append({
                "png": f"{config['name']}.png",
                "palette": f"{config['name']}.pal.json",
                "description": config["description"],
                "tiles": config["size"] // 32,
                "size": f"{metadata.get('sheet_dimensions', [0,0])[0]}x{metadata.get('sheet_dimensions', [0,0])[1]}"
            })

            print(f"✅ Created {config['name']}.png + palette")

        except Exception as e:
            print(f"❌ Failed to create {config['name']}: {e}")

    return created_sheets

def create_test_summary(created_sheets):
    """Create a summary of all test sheets created"""
    print("\n=== Creating Test Summary ===")

    summary = {
        "test_sprite_sheets": {
            "description": "Test sprite sheets for enhanced palette workflow",
            "created_date": "2025-07-08",
            "extraction_source": {
                "vram": "Cave.SnesVideoRam.dmp",
                "cgram": "Cave.SnesCgRam.dmp"
            },
            "sheets": created_sheets,
            "testing_instructions": {
                "1": "Launch: python3 indexed_pixel_editor.py",
                "2": "Open any .png file from the list below",
                "3": "Editor will auto-detect and offer to load the .pal.json file",
                "4": "Accept to load the palette",
                "5": "Toggle greyscale mode to switch between index and color view",
                "6": "Edit sprites and see real-time color preview"
            },
            "palette_files_available": [
                "kirby_reference.pal.json - Reference Kirby colors",
                "Cave.SnesCgRam_palette_8.pal.json - Extracted palette 8 (Kirby)",
                "Cave.SnesCgRam_palette_9.pal.json - Extracted palette 9",
                "Cave.SnesCgRam_palette_10.pal.json - Extracted palette 10",
                "Cave.SnesCgRam_palette_11.pal.json - Extracted palette 11",
                "Cave.SnesCgRam_palette_12.pal.json - Extracted palette 12",
                "Cave.SnesCgRam_palette_13.pal.json - Extracted palette 13",
                "Cave.SnesCgRam_palette_14.pal.json - Extracted palette 14",
                "Cave.SnesCgRam_palette_15.pal.json - Extracted palette 15"
            ]
        }
    }

    with open("test_sprite_sheets_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("✅ Created test_sprite_sheets_summary.json")

    # Create human-readable summary
    readme_content = """# Test Sprite Sheets for Enhanced Palette Workflow

## Created Sprite Sheets

"""

    for i, sheet in enumerate(created_sheets, 1):
        readme_content += f"""### {i}. {sheet['description']}
- **Image**: `{sheet['png']}`
- **Palette**: `{sheet['palette']}`
- **Size**: {sheet['size']} pixels
- **Tiles**: {sheet['tiles']} tiles

"""

    readme_content += """## How to Test

1. **Launch Editor**: `python3 indexed_pixel_editor.py`
2. **Open Image**: Load any `.png` file above
3. **Auto-Palette**: Editor detects `.pal.json` and offers to load it
4. **Accept**: Click "Yes" to load the companion palette
5. **Toggle Views**:
   - ☑️ **Greyscale Mode**: See index values (0-15) as grayscale
   - ☐ **Greyscale Mode**: See game-accurate colors using external palette

## Visual Indicators

- **Green border** around palette = external palette loaded
- **Green triangle** on first color = external palette indicator
- **Tooltip** shows palette source information
- **Window title** shows current palette name

## Available Palettes

You can also manually load any of these palette files:

- `kirby_reference.pal.json` - Reference Kirby colors from documentation
- `Cave.SnesCgRam_palette_8.pal.json` - Kirby's palette (most common)
- `Cave.SnesCgRam_palette_9.pal.json` - Additional sprite palette
- `Cave.SnesCgRam_palette_10.pal.json` - Additional sprite palette
- `Cave.SnesCgRam_palette_11.pal.json` - Additional sprite palette
- `Cave.SnesCgRam_palette_12.pal.json` - Additional sprite palette
- `Cave.SnesCgRam_palette_13.pal.json` - Additional sprite palette
- `Cave.SnesCgRam_palette_14.pal.json` - Additional sprite palette
- `Cave.SnesCgRam_palette_15.pal.json` - Additional sprite palette

## Testing Different Palettes

Try loading the same sprite sheet with different palettes to see how it affects the color preview:

1. Load a sprite sheet (e.g., `kirby_focused_test.png`)
2. Load its default palette (`kirby_focused_test.pal.json`)
3. Try "File → Load Palette File..." with a different palette (e.g., `Cave.SnesCgRam_palette_9.pal.json`)
4. See how the same sprite indices look with different color palettes!

## Workflow Verification

This tests the complete enhanced workflow:
- ✅ Sprite extraction with companion palettes
- ✅ Auto-detection of paired files
- ✅ External palette loading
- ✅ Greyscale/color mode switching
- ✅ Settings persistence
- ✅ Recent files tracking
"""

    with open("TEST_SPRITE_SHEETS_README.md", "w") as f:
        f.write(readme_content)

    print("✅ Created TEST_SPRITE_SHEETS_README.md")

def check_existing_sheets():
    """Check what sprite sheets already exist"""
    print("=== Checking Existing Sprite Sheets ===")

    existing_sheets = []
    png_files = [f for f in os.listdir(".") if f.endswith(".png") and "test" in f.lower()]

    for png_file in png_files:
        base_name = os.path.splitext(png_file)[0]
        pal_file = f"{base_name}.pal.json"

        if os.path.exists(pal_file):
            # Get image dimensions
            try:
                from PIL import Image
                with Image.open(png_file) as img:
                    width, height = img.size

                existing_sheets.append({
                    "png": png_file,
                    "palette": pal_file,
                    "description": f"Existing {base_name}",
                    "tiles": (width * height) // 64,  # Assuming 8x8 tiles
                    "size": f"{width}x{height}"
                })

                print(f"✅ Found existing: {png_file} + {pal_file}")

            except Exception as e:
                print(f"❌ Error checking {png_file}: {e}")

    return existing_sheets

def main():
    """Create comprehensive test sprite sheets"""
    print("🎨 Creating Test Sprite Sheets for Enhanced Palette Workflow")
    print("=" * 60)

    all_sheets = []

    # Check existing sheets first
    existing = check_existing_sheets()
    all_sheets.extend(existing)

    # Create focused Kirby sheet
    if create_kirby_focused_sheet():
        all_sheets.append({
            "png": "kirby_focused_test.png",
            "palette": "kirby_focused_test.pal.json",
            "description": "Focused Kirby sprites (8x8 grid)",
            "tiles": 64,
            "size": "64x64"
        })

    # Create small test sheets
    small_sheets = create_small_test_sheets()
    all_sheets.extend(small_sheets)

    # Create summary
    create_test_summary(all_sheets)

    print(f"\n🎉 Created {len(all_sheets)} test sprite sheets!")
    print("\n📋 Summary:")
    for sheet in all_sheets:
        print(f"  • {sheet['description']}: {sheet['png']} + {sheet['palette']}")

    print("\n🚀 Ready to test! Run:")
    print("   python3 indexed_pixel_editor.py")
    print("   Then open any of the .png files above")
    print("   The editor will auto-offer to load the companion .pal.json file!")

    print("\n📖 See TEST_SPRITE_SHEETS_README.md for detailed testing instructions")

if __name__ == "__main__":
    main()
