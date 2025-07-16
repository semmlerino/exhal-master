# Pixel Editor Interactive Workflow

## Overview

This workflow allows you to edit grayscale sprites while seeing real-time color previews using different palettes.

## Files Created

### Main Files
- **`cave_sprites_editor.png`** - Grayscale sprite sheet (512 tiles, 16x32 layout)
- **`cave_sprites_editor_pal*.pal.json`** - Individual palette files (palettes 8-15)
- **`cave_sprites_editor_all_palettes.json`** - Combined palette data
- **`edit_cave_sprites.py`** - Launcher script

### Palette Files
- `cave_sprites_editor_pal8.pal.json` - Kirby (Pink) - Main character palette
- `cave_sprites_editor_pal9.pal.json` - Kirby Alt - Alternative Kirby palette
- `cave_sprites_editor_pal10.pal.json` - Helper - Helper character palette
- `cave_sprites_editor_pal11.pal.json` - Enemy 1 - Common enemy palette
- `cave_sprites_editor_pal12.pal.json` - UI/HUD - User interface elements
- `cave_sprites_editor_pal13.pal.json` - Enemy 2 - Special enemy palette
- `cave_sprites_editor_pal14.pal.json` - Boss/Enemy - Boss and large enemy palette
- `cave_sprites_editor_pal15.pal.json` - Effects - Special effects palette

## How to Use

### Method 1: Quick Launch
```bash
python3 edit_cave_sprites.py
```

### Method 2: Manual Launch
```bash
python3 launch_pixel_editor.py cave_sprites_editor.png
```

### Method 3: With Specific Palette
```bash
python3 launch_pixel_editor.py cave_sprites_editor.png --palette cave_sprites_editor_pal8.pal.json
```

## Pixel Editor Features

### Interactive Palette Switching
- **Number Keys 0-7**: Switch between palettes 8-15 in real-time
- **Tab**: Toggle between grayscale and color preview
- **Shift+Tab**: Cycle through available palettes

### Editing Tools
- **Left Click**: Draw with selected color
- **Right Click**: Pick color from canvas
- **Middle Click**: Pan the view
- **Scroll**: Zoom in/out
- **G**: Toggle grid
- **1-9, 0, A-F**: Select color index (0-15)

### View Modes
- **Grayscale Mode**: Edit the actual pixel indices
- **Color Preview**: See how sprites look with current palette
- **Split View**: See both modes side-by-side

## Workflow Steps

1. **Extract Sprites**
   ```bash
   python3 extract_for_pixel_editor.py
   ```

2. **Launch Editor**
   ```bash
   python3 edit_cave_sprites.py
   ```

3. **Edit Sprites**
   - Work in grayscale to see pixel indices clearly
   - Press Tab to preview with colors
   - Use number keys to test different palettes
   - Save regularly (Ctrl+S)

4. **Reinsert Sprites**
   ```bash
   python3 sprite_editor/sprite_injector.py \
       --input cave_sprites_editor.png \
       --vram Cave.SnesVideoRam.dmp \
       --output VRAM_modified.dmp
   ```

## Tips

- **Color 0 is Transparent**: Always leave as background
- **Test Multiple Palettes**: Sprites may look different with each palette
- **Use Grid**: Enable grid (G key) for precise 8x8 tile editing
- **Zoom for Detail**: Use scroll wheel to zoom in for pixel-perfect editing
- **Save Often**: The editor auto-saves to backup files

## Advanced Features

### Palette Info Display
The editor shows:
- Current palette name
- Color index under cursor
- RGB values of current color
- Zoom level and coordinates

### History
- **Ctrl+Z**: Undo
- **Ctrl+Y**: Redo
- **Ctrl+Shift+Z**: Alternative redo

### Export Options
- **Ctrl+E**: Export with current palette applied
- **Ctrl+Shift+E**: Export as indexed PNG

## Extracting from Different Sources

### From Mesen-S Savestate
```bash
python3 extract_for_pixel_editor.py "Kirby Super Star (USA)_2"
```

### From Custom Dumps
```bash
python3 extract_for_pixel_editor.py my_custom_prefix
```

## Next Steps

After editing:
1. Save your edited sprite sheet
2. Use `sprite_injector.py` to reinsert into VRAM
3. Test in emulator
4. Iterate as needed

The grayscale + palette separation allows for non-destructive editing and easy palette experimentation!