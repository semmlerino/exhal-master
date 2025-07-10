# Enhanced Sprite Extraction and Palette Workflow Guide

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
