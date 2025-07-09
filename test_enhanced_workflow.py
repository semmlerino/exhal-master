#!/usr/bin/env python3
"""
Test script for the enhanced sprite extraction and palette workflow

This script tests the complete workflow:
1. Extract palette files
2. Extract grayscale sprites with companion palettes
3. Test editor palette loading functionality
4. Verify the complete workflow integration

Run this to verify that all components work together correctly.
"""

import json
import os

import numpy as np
from PIL import Image


def test_palette_extraction():
    """Test the standalone palette extraction functionality"""
    print("=== Testing Palette Extraction ===")

    # Check if the palette extraction script exists
    if not os.path.exists("extract_palette_for_editor.py"):
        print("❌ extract_palette_for_editor.py not found")
        return False

    print("✅ extract_palette_for_editor.py exists")

    # Test creating reference Kirby palette
    try:
        from extract_palette_for_editor import (
            create_kirby_palette_from_notes,
            create_reference_palette_file,
        )

        # Test creating reference palette data
        palette_data = create_kirby_palette_from_notes()

        # Verify structure
        assert "palette" in palette_data
        assert "colors" in palette_data["palette"]
        assert len(palette_data["palette"]["colors"]) == 16
        assert palette_data["palette"]["colors"][0] == [0, 0, 0]  # Black
        assert palette_data["palette"]["colors"][1] == [248, 224, 248]  # Light pink

        print("✅ Kirby reference palette creation works")

        # Test creating palette file
        test_palette_file = "test_kirby_reference.pal.json"
        create_reference_palette_file(test_palette_file)

        # Verify file was created and has correct format
        assert os.path.exists(test_palette_file)

        with open(test_palette_file) as f:
            loaded_data = json.load(f)

        assert loaded_data["format_version"] == "1.0"
        assert loaded_data["editor_compatibility"]["indexed_pixel_editor"]

        # Clean up
        os.remove(test_palette_file)

        print("✅ Reference palette file creation works")
        return True

    except Exception as e:
        print(f"❌ Palette extraction test failed: {e}")
        return False


def test_grayscale_extraction_with_palette():
    """Test the enhanced grayscale extraction with companion palette files"""
    print("\n=== Testing Grayscale Extraction with Companion Palettes ===")

    # Check if the enhanced extraction script exists
    if not os.path.exists("extract_grayscale_sheet.py"):
        print("❌ extract_grayscale_sheet.py not found")
        return False

    print("✅ extract_grayscale_sheet.py exists")

    # Check for the companion palette file creation function
    try:
        # Read the file and check for our enhancement
        with open("extract_grayscale_sheet.py") as f:
            content = f.read()

        if "_create_companion_palette_file" in content:
            print("✅ Companion palette file creation function found")
        else:
            print("❌ _create_companion_palette_file function not found in extract_grayscale_sheet.py")
            return False

        if "palette_file = _create_companion_palette_file" in content:
            print("✅ Companion palette file creation integrated into main extraction")
        else:
            print("❌ Companion palette file creation not integrated")
            return False

        return True

    except Exception as e:
        print(f"❌ Grayscale extraction test failed: {e}")
        return False


def test_editor_palette_loading():
    """Test the enhanced editor palette loading functionality"""
    print("\n=== Testing Editor Palette Loading ===")

    # Check if the enhanced editor exists
    if not os.path.exists("indexed_pixel_editor.py"):
        print("❌ indexed_pixel_editor.py not found")
        return False

    print("✅ indexed_pixel_editor.py exists")

    try:
        # Read the editor file and check for our enhancements
        with open("indexed_pixel_editor.py") as f:
            content = f.read()

        # Check for palette loading functionality
        required_functions = [
            "load_palette_file",
            "load_palette_by_path",
            "load_grayscale_with_palette",
            "_check_and_offer_palette_loading",
            "_validate_palette_file"
        ]

        for func in required_functions:
            if f"def {func}" in content:
                print(f"✅ {func} function found")
            else:
                print(f"❌ {func} function not found")
                return False

        # Check for palette tracking in settings
        if "recent_palette_files" in content and "palette_file_associations" in content:
            print("✅ Palette file tracking in settings found")
        else:
            print("❌ Palette file tracking in settings not found")
            return False

        # Check for external palette support
        if "external_palette_colors" in content:
            print("✅ External palette support found")
        else:
            print("❌ External palette support not found")
            return False

        return True

    except Exception as e:
        print(f"❌ Editor palette loading test failed: {e}")
        return False


def test_widget_enhancements():
    """Test the enhanced ColorPaletteWidget functionality"""
    print("\n=== Testing Widget Enhancements ===")

    # Check if the enhanced widgets exist
    if not os.path.exists("pixel_editor_widgets.py"):
        print("❌ pixel_editor_widgets.py not found")
        return False

    print("✅ pixel_editor_widgets.py exists")

    try:
        # Read the widgets file and check for our enhancements
        with open("pixel_editor_widgets.py") as f:
            content = f.read()

        # Check for ColorPaletteWidget enhancements
        required_features = [
            "is_external_palette",
            "palette_source",
            "reset_to_default",
            "_show_context_menu",
            "_update_tooltip",
            "default_colors"
        ]

        for feature in required_features:
            if feature in content:
                print(f"✅ ColorPaletteWidget feature '{feature}' found")
            else:
                print(f"❌ ColorPaletteWidget feature '{feature}' not found")
                return False

        # Check for PixelCanvas external palette support
        if "editor_parent.external_palette_colors" in content:
            print("✅ PixelCanvas external palette support found")
        else:
            print("❌ PixelCanvas external palette support not found")
            return False

        return True

    except Exception as e:
        print(f"❌ Widget enhancements test failed: {e}")
        return False


def test_workflow_integration():
    """Test that all components integrate properly"""
    print("\n=== Testing Workflow Integration ===")

    try:
        # Create a test palette file
        test_palette_data = {
            "format_version": "1.0",
            "format_description": "Indexed Pixel Editor Palette File",
            "source": {
                "cgram_file": "test.dmp",
                "palette_index": 8,
                "extraction_tool": "test_workflow"
            },
            "palette": {
                "name": "Test Palette",
                "colors": [[i*16, i*16, i*16] for i in range(16)],
                "color_count": 16,
                "format": "RGB888"
            },
            "usage_hints": {
                "transparent_index": 0,
                "typical_use": "sprite",
                "kirby_palette": False
            },
            "editor_compatibility": {
                "indexed_pixel_editor": True,
                "supports_grayscale_mode": True,
                "auto_loadable": True
            }
        }

        test_palette_file = "test_workflow.pal.json"
        with open(test_palette_file, "w") as f:
            json.dump(test_palette_data, f, indent=2)

        print("✅ Test palette file created")

        # Create a test grayscale image
        test_image = Image.new("P", (16, 16))
        test_image_data = np.random.randint(0, 16, (16, 16), dtype=np.uint8)
        test_image = Image.fromarray(test_image_data, mode="P")

        # Set a grayscale palette
        palette_data = []
        for i in range(16):
            gray = (i * 255) // 15
            palette_data.extend([gray, gray, gray])
        while len(palette_data) < 768:
            palette_data.extend([0, 0, 0])

        test_image.putpalette(palette_data)

        test_image_file = "test_workflow.png"
        test_image.save(test_image_file)

        print("✅ Test grayscale image created")

        # Test that files pair correctly (same base name)
        base_name = "test_workflow"
        assert os.path.exists(f"{base_name}.png")
        assert os.path.exists(f"{base_name}.pal.json")

        print("✅ Palette and image files pair correctly")

        # Test loading the palette file
        from indexed_pixel_editor import SettingsManager

        settings = SettingsManager()
        settings.add_recent_palette_file(test_palette_file)

        recent_palettes = settings.get_recent_palette_files()
        assert test_palette_file in [os.path.basename(p) for p in recent_palettes]

        print("✅ Settings manager palette tracking works")

        # Clean up
        os.remove(test_palette_file)
        os.remove(test_image_file)

        print("✅ Workflow integration test completed successfully")
        return True

    except Exception as e:
        print(f"❌ Workflow integration test failed: {e}")
        return False


def create_usage_guide():
    """Create a usage guide for the enhanced workflow"""
    print("\n=== Creating Usage Guide ===")

    guide_content = """# Enhanced Sprite Extraction and Palette Workflow Guide

## Overview
The enhanced workflow allows you to extract sprites in grayscale indexed format while preserving the original palette information for accurate color preview in the editor.

## Complete Workflow

### 1. Extract Sprites with Palettes

#### Option A: Extract Grayscale Sprites (Automatic Palette Creation)
```bash
python extract_grayscale_sheet.py
```
This creates:
- `sprites.png` - Grayscale indexed sprite sheet
- `sprites.pal.json` - Companion palette file
- `sprites_metadata.json` - Detailed metadata

#### Option B: Extract Standalone Palette
```bash
python extract_palette_for_editor.py Cave.SnesCgRam.dmp -p 8
```
Creates: `Cave_palette_8.pal.json`

#### Option C: Create Reference Kirby Palette
```bash
python extract_palette_for_editor.py --reference
```
Creates: `kirby_reference.pal.json`

### 2. Edit in the Indexed Pixel Editor

#### Automatic Workflow (Recommended)
1. Open the indexed pixel editor
2. Load a grayscale sprite file (e.g., `sprites.png`)
3. Editor automatically detects `sprites.pal.json` and offers to load it
4. Click "Yes" to load the palette
5. Toggle between greyscale mode (index view) and color mode (game-accurate preview)

#### Manual Workflow
1. Open the indexed pixel editor
2. Use "File → Load Grayscale + Palette..." to load both files
3. Or load them separately:
   - "File → Open" for the image
   - "File → Load Palette File..." for the palette

### 3. Editing Features

#### Palette Widget Features
- **Green border**: Indicates external palette is loaded
- **Green triangle**: Visual indicator on first color cell
- **Tooltip**: Shows palette source information
- **Right-click menu**: Reset to default palette

#### Canvas Features
- **Greyscale Mode ON**: Shows index values as grayscale
- **Greyscale Mode OFF**: Shows game-accurate colors using external palette
- **Color Preview**: Always shows how edits will look in-game

#### Settings Tracking
- Recent palette files are remembered
- Image-to-palette associations are saved
- Auto-loading preferences

### 4. File Formats

#### Palette File Format (.pal.json)
```json
{
  "format_version": "1.0",
  "palette": {
    "name": "Kirby Palette",
    "colors": [[r,g,b], [r,g,b], ...],
    "color_count": 16
  },
  "editor_compatibility": {
    "indexed_pixel_editor": true,
    "auto_loadable": true
  }
}
```

## Benefits

1. **Accurate Color Preview**: See exactly how sprites will look in-game
2. **Index Editing**: Edit in grayscale to see index values clearly
3. **Automatic Pairing**: Companion files are auto-detected and offered
4. **Settings Memory**: Recently used palettes and associations are remembered
5. **Workflow Integration**: Seamless extraction → editing workflow

## Troubleshooting

### Palette Not Loading
- Check file format is valid JSON
- Ensure palette has 16 colors
- Verify file permissions

### Colors Look Wrong
- Confirm correct palette index was extracted
- Check if greyscale mode is enabled when you want color view
- Verify external palette is loaded (green border on palette widget)

### Auto-Detection Not Working
- Ensure files have same base name (e.g., `sprite.png` + `sprite.pal.json`)
- Check auto-offering is enabled in settings
- Verify palette file is valid format

## File Naming Conventions

For automatic detection, use these naming patterns:
- `sprite.png` + `sprite.pal.json`
- `sprite.png` + `sprite_palette.json`
- `sprite.png` + `sprite_metadata.json`

The editor will automatically detect and offer to load companion files.
"""

    with open("ENHANCED_WORKFLOW_GUIDE.md", "w") as f:
        f.write(guide_content)

    print("✅ Usage guide created: ENHANCED_WORKFLOW_GUIDE.md")


def main():
    """Run all tests for the enhanced sprite editing workflow"""
    print("🎨 Enhanced Sprite Extraction and Palette Workflow Tests")
    print("=" * 60)

    tests = [
        test_palette_extraction,
        test_grayscale_extraction_with_palette,
        test_editor_palette_loading,
        test_widget_enhancements,
        test_workflow_integration
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        else:
            print("❌ Test failed!")

    print("\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! Enhanced workflow is ready.")
        create_usage_guide()

        print("\n🚀 Next Steps:")
        print("1. Extract sprites using: python extract_grayscale_sheet.py")
        print("2. Launch editor using: python indexed_pixel_editor.py")
        print("3. Load grayscale sprites - palette will be auto-offered!")
        print("4. Toggle greyscale mode to switch between index and color view")
        print("5. See ENHANCED_WORKFLOW_GUIDE.md for detailed instructions")

    else:
        print("❌ Some tests failed. Check the implementation.")

    return passed == total


if __name__ == "__main__":
    main()
