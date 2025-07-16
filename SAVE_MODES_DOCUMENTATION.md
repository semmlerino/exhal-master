# Pixel Editor Save Modes

## Overview

The pixel editor now supports two save modes to accommodate different workflows:

1. **Default Save** - Saves as indexed grayscale PNG (preserves sprite format)
2. **Save with Color Palette** - Saves as indexed PNG with color palette applied

## Usage

### Default Save (Grayscale)

The standard save operations now save with a grayscale palette by default:

- **File > Save** (Ctrl+S)
- **File > Save As...** (Ctrl+Shift+S)

This preserves the indexed format and saves with grayscale values (0-255 in steps of 17).

### Save with Color Palette

To save with the current color palette applied:

- **File > Save with Color Palette...**

This saves the image with the currently loaded color palette (e.g., Kirby pink, enemy blue, etc.)

## Technical Details

### Implementation

- `FileManager.save_file()` now accepts `use_grayscale_palette` parameter (default: True)
- When True: Uses `DEFAULT_GRAYSCALE_PALETTE` from constants
- When False: Uses the current `palette_model` colors

### File Format

Both modes save as:
- **Format**: PNG
- **Color Mode**: Indexed (P mode)
- **Bit Depth**: 8-bit palette indices
- **Palette**: 256 colors (16 used for 4bpp sprites)

### Workflow Benefits

1. **Sprite Editing**: Default grayscale save maintains compatibility with sprite tools
2. **Preview Export**: Color save allows exporting sprites with final colors
3. **No Data Loss**: Both modes preserve the indexed nature of the image

## Testing

```bash
# Test with a Kirby sprite
python launch_pixel_editor.py kirby_test_sprites/kirby_main.png

# Make an edit, then:
# 1. Save As... → creates grayscale indexed PNG
# 2. Save with Color Palette... → creates colored indexed PNG
```

## Verification

Use the provided test scripts:

```bash
# Check implementation
python verify_save_implementation.py

# Test save modes
python test_save_modes.py
```