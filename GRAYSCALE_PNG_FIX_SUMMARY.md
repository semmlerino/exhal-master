# Grayscale PNG Pink Sprite Issue - FIXED

## Problem Summary
Sprites appeared pink in the indexed_pixel_editor even before loading a palette. This was caused by two issues:

1. **Incorrect pixel values in grayscale PNGs**: The grayscale PNG files were storing actual gray values (17, 34, 51, etc.) as pixel data instead of palette indices (1, 2, 3, etc.)

2. **Default pink palette in editor**: The ColorPaletteWidget defaulted to a color palette with pink colors for Kirby sprites instead of a grayscale palette

## Root Cause Analysis

### Issue 1: Grayscale PNG Format
The `extract_grayscale_sheet.py` was creating grayscale images incorrectly:
- It used gray values directly as pixel values (e.g., pixel value 17 for index 1)
- This caused the indexed PNG to have pixel values ranging from 0-255 instead of 0-15
- When loaded, the editor would try to look up palette index 17, 34, etc. which were undefined

### Issue 2: Default Editor Palette
The `ColorPaletteWidget` initialized with a color palette containing:
- Index 1: (255, 183, 197) - Kirby pink
- Index 6: (255, 220, 220) - Light pink  
- Index 7: (200, 120, 150) - Dark pink

This caused any sprite using these indices to appear pink by default.

## Solution Implemented

### 1. Created Proper Indexed Grayscale PNGs
- `create_proper_grayscale_png.py` - Converts grayscale PNGs to use proper palette indices (0-15)
- Maps gray values to indices: 0→0, 17→1, 34→2, ..., 255→15
- Maintains the grayscale palette but uses correct indexed format

### 2. Updated ColorPaletteWidget Default Palette
- Added `default_grayscale` palette with proper gray values
- Changed default initialization to use grayscale instead of colors
- Added `set_color_mode()` method to switch between grayscale and color modes

### 3. Improved Canvas Palette Detection
- Canvas now detects if loaded palette is grayscale
- Doesn't override with color palette for grayscale images

## Files Created/Modified

### New Files
- `diagnose_grayscale_palette.py` - Diagnostic tool to inspect PNG palettes
- `fix_grayscale_palette.py` - Fixes palette data in existing PNGs
- `create_proper_grayscale_png.py` - Creates properly indexed grayscale PNGs

### Modified Files
- `pixel_editor_widgets.py` - Updated ColorPaletteWidget with grayscale default

### Fixed PNG Files
- `kirby_sprites_indexed_grayscale.png` - Properly indexed version
- `kirby_sprites_indexed_grayscale_v3.png` - Latest fixed version
- `kirby_sprites_indexed_grayscale_ultra.png` - Ultra version fixed

## Usage Instructions

1. **For existing grayscale PNGs**, convert them using:
   ```bash
   python3 create_proper_grayscale_png.py input.png output.png
   ```

2. **When creating new grayscale sheets**, ensure they use palette indices (0-15) not gray values

3. **In the pixel editor**, grayscale images will now display correctly without pink colors

## Verification
Run the diagnostic tool to verify proper indexing:
```bash
python3 diagnose_grayscale_palette.py kirby_sprites_indexed_grayscale_v3.png
```

Should show:
- Pixel value range: 0-15 (not 0-255)
- Palette: Proper grayscale mapping
- No pink colors in default view