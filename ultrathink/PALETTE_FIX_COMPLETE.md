# Palette Association Fix Complete

## Problem Identified
The user correctly identified that Kirby was appearing blue instead of pink when using the companion palette. Investigation revealed:

1. **Wrong Palette Assignment**: The companion palette was using palette 14 (which has blue colors at indices 2-3)
2. **Correct Palette**: Kirby should use palette 8 (OAM palette 0), which has purple/pink colors

## What Was Fixed

### 1. Companion Palette File
Updated `kirby_sprites.pal.json` to use palette 8 instead of 14:
- **Before**: Palette 14 with blue colors (128,224,232 and 40,128,192 at indices 2-3)
- **After**: Palette 8 with purple/pink colors (248,160,232 and 240,112,224 at indices 2-3)

### 2. Palette Detection Logic
Updated `extract_grayscale_sheet.py` to properly detect Kirby palettes:
```python
# Now checks for purple/magenta colors (high red, low green, high blue)
has_purple = any(r > 200 and g < 100 and b > 200 for r, g, b in colors)
```

### 3. Enhanced Editor Features
Created `indexed_pixel_editor_enhanced.py` with:
- **Palette Switching**: Press 'P' to switch between all available palettes
- **Keyboard Shortcut**: Press 'C' to toggle color mode (as documented)
- **Metadata Support**: Automatically loads all 16 palettes from metadata

## How Palettes Work

### OAM to CGRAM Mapping
- Sprites use OAM palettes 0-7
- These map to CGRAM palettes 8-15
- Kirby uses OAM palette 0 = CGRAM palette 8

### Tile-to-Palette Association
Each tile in the sprite sheet has a palette assignment stored in metadata:
```json
"0": {
  "palette": 0,        // OAM palette
  "cgram_palette": 8,  // CGRAM palette
  "x": 0, "y": 0
}
```

## Usage

### Basic Editor (with corrected companion palette):
```bash
python3 ../indexed_pixel_editor.py sprites/kirby_sprites.png
```

### Enhanced Editor (with palette switching):
```bash
python3 ../indexed_pixel_editor_enhanced.py sprites/kirby_sprites.png
```

## Result
Kirby now appears with proper purple/pink colors in the editor when using the companion palette!