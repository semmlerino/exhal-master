# ULTRATHINK Workflow - Complete Implementation

## Overview
The "ultrathink" workflow is now fully implemented and working correctly. This workflow allows you to:
1. Extract sprites in grayscale indexed format (preserving palette indices 0-15)
2. View and edit sprites with proper index visibility
3. Toggle between grayscale and color preview modes
4. Save edits back to the game format

## Fixed Issues

### Problem: Pink Sprites in Editor
The sprites were appearing pink even before loading a palette because:
1. The grayscale PNGs were storing gray values (17, 34, 51...) instead of indices (1, 2, 3...)
2. The editor's default palette was set to pink Kirby colors

### Solution
1. Updated `extract_grayscale_sheet.py` to create properly indexed PNGs (pixel values 0-15)
2. Applied a grayscale palette to the indexed image for proper visualization
3. The editor now correctly shows grayscale by default

## Complete Workflow

### 1. Extract Sprites
```bash
python3 extract_grayscale_sheet.py Cave.SnesVideoRam.dmp 0x7000
```

This creates:
- `kirby_sprites_grayscale_ultrathink.png` - Properly indexed grayscale sprite sheet
- `kirby_sprites_grayscale_ultrathink.pal.json` - Companion palette file
- `kirby_sprites_grayscale_ultrathink_metadata.json` - Tile and palette info
- `kirby_sprites_grayscale_ultrathink_editing_guide.png` - Visual reference

### 2. Edit Sprites
```bash
# Auto-detect companion palette
python3 indexed_pixel_editor.py kirby_sprites_grayscale_ultrathink.png

# Or specify palette explicitly
python3 indexed_pixel_editor.py kirby_sprites_grayscale_ultrathink.png -p kirby_palette_14.pal.json
```

### 3. Editor Features
- **Default View**: Grayscale showing index values (0-15)
- **Press 'C'**: Toggle to color preview with loaded palette
- **Pixel Editing**: Maintains indexed format
- **Save**: Preserves 4bpp format for game compatibility

## Technical Details

### Proper Index Mapping
The fixed implementation uses:
- **Pixel values**: 0-15 (actual palette indices)
- **Display palette**: Maps indices to grayscale for visualization
  - Index 0 → Gray 0 (black/transparent)
  - Index 1 → Gray 17
  - Index 2 → Gray 34
  - ...
  - Index 15 → Gray 255 (white)

### Available Palettes
- `kirby_palette_14.pal.json` - Pink Kirby (standard colors)
- `kirby_palette_8.pal.json` - Purple Kirby (special state)
- `kirby_smart_palette_11.pal.json` - Yellow/brown (most used in scene)

## Creating Colored PNGs
To create standard PNG files with colors applied:
```bash
python3 create_colored_pngs.py
```

This properly maps the grayscale indices back to palette colors.

## Summary
The ultrathink workflow now works exactly as envisioned:
- Sprites appear in grayscale by default (not pink)
- Index values are preserved (0-15)
- Color preview works correctly with external palettes
- Full editing capability with proper format preservation