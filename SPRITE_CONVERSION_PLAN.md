# Sprite Conversion Plan: Convert Pixel Art Sprite for Pixel Editor and VRAM Integration

## Overview
This plan outlines the complete workflow for converting your pixel art sprite to work with the pixel editor and integrate it into the VRAM workflow for Kirby Super Star sprite replacement.

## 1. Prepare Your Sprite

### Format Requirements
- **Bit depth**: 4bpp (16 colors maximum)
- **Tile size**: 8x8 pixels (32 bytes in SNES format)
- **Dimensions**: Must be multiples of 8 pixels (SNES uses 8x8 tiles)
- **Color index 0**: Should be transparent
- **File format**: PNG in indexed color mode

### Steps
1. Convert your sprite to indexed color mode (max 16 colors)
2. Ensure dimensions are multiples of 8 pixels
3. Make sure color index 0 is transparent
4. Save as PNG file

## 2. Convert to Grayscale Format for Pixel Editor

The pixel editor works best with grayscale sprites and separate palette files for color preview.

### What you need to create:
- Grayscale version of your sprite (for editing)
- `.pal.json` palette file(s) (for color preview)

### Example workflow:
```bash
# Convert your colored sprite to grayscale + palette
python extract_for_pixel_editor.py your_sprite.png --create-palette
```

## 3. Extract Current Kirby Sprites (for reference/replacement)

Extract existing Kirby sprites to understand the format and positioning:

```bash
python extract_for_pixel_editor.py VRAM.dmp CGRAM.dmp kirby_sprites_editor.png \
  --offset 0xC000 --width 16 --palettes 8,9,10,11
```

This creates:
- `kirby_sprites_editor.png` (grayscale sprite sheet)
- `kirby_sprites_editor_pal8.pal.json` (palette 8)
- `kirby_sprites_editor_pal9.pal.json` (palette 9)
- etc.

## 4. Edit in Pixel Editor

### Launch the pixel editor:
```bash
python pixel_editor/core/indexed_pixel_editor_v3.py your_sprite_grayscale.png
```

### Editing workflow:
1. Load the grayscale sprite
2. Load the appropriate `.pal.json` palette file (File → Load Palette File)
3. Use grid view (G key) to align with 8x8 tiles
4. Position/edit your sprite to replace Kirby sprites
5. Use different palette files to preview how it looks with different colors
6. Save the edited grayscale PNG

### Key shortcuts:
- **G**: Toggle grid visibility
- **C**: Toggle color/grayscale mode
- **I**: Switch to color picker tool
- **P**: Switch palettes (if multiple loaded)

## 5. Convert PNG to SNES 4bpp Format

Once you're satisfied with your edits:

```bash
python sprite_editor/png_to_snes.py your_edited_sprite.png sprite_data.bin
```

This converts your indexed PNG to SNES 4bpp tile format.

## 6. Inject into VRAM

Replace the original sprites in VRAM:

```bash
python sprite_editor/sprite_injector.py your_edited_sprite.png \
  --vram VRAM.dmp --offset 0xC000 --output VRAM_modified.dmp
```

### Parameters:
- `--vram`: Input VRAM dump file
- `--offset`: VRAM offset (0xC000 = $6000 for sprites)
- `--output`: Output VRAM file with your changes

## 7. Test in Emulator

1. Load the modified `VRAM_modified.dmp` in your emulator
2. Verify the sprites display correctly with proper palettes
3. Test gameplay to ensure sprites work in all contexts

## Important Technical Details

### VRAM Layout
- **Default sprite offset**: 0xC000 (VRAM address $6000)
- **Sprite data size**: 0x4000 (16KB = 512 tiles)
- **Format**: 4bpp (4 bits per pixel, 16 colors max)

### Palette Information
- **Palettes 8-15**: Used for sprites
- **Palettes 0-7**: Used for backgrounds
- **Each palette**: 16 colors (including transparent)
- **Format**: 15-bit RGB (5 bits per channel)

### Palette Descriptions (from cave_sprites_editor.metadata.json):
- **Palette 8**: Main character palette
- **Palette 9**: Alternative Kirby palette
- **Palette 10**: Helper character palette
- **Palette 11**: Common enemy palette
- **Palette 12**: User interface elements
- **Palette 13**: Special enemy palette
- **Palette 14**: Boss and large enemy palette
- **Palette 15**: Special effects palette

## Example Files in Codebase

Reference these existing files to understand the format:

### Example sprite files:
- `kirby_sprites_grayscale_for_editor.png` (grayscale sprite sheet)
- `cave_sprites_editor.png` (another example)

### Example palette files:
- `kirby_sprites_grayscale_for_editor.pal.json`
- `cave_sprites_editor_pal8.pal.json` through `cave_sprites_editor_pal15.pal.json`

### Example metadata:
- `cave_sprites_editor.metadata.json`

## Tools Available

### Conversion Tools:
- `extract_for_pixel_editor.py` - Extract sprites from VRAM to grayscale+palette
- `sprite_editor/png_to_snes.py` - Convert PNG to SNES 4bpp format
- `sprite_editor/snes_tiles_to_png.py` - Convert SNES tiles to PNG
- `sprite_editor/sprite_injector.py` - Inject edited sprites back to VRAM

### Pixel Editor:
- `pixel_editor/core/indexed_pixel_editor_v3.py` - Main pixel editor application

## Troubleshooting

### Common Issues:
1. **Sprite dimensions**: Must be multiples of 8 pixels
2. **Color count**: Maximum 16 colors (including transparent)
3. **Transparency**: Color index 0 must be transparent
4. **Tile alignment**: Use grid view to ensure proper 8x8 tile alignment

### Testing:
- Always test in emulator after injection
- Check that sprites work with all intended palettes
- Verify transparency works correctly
- Test sprite animations if applicable

## Next Steps

Choose your approach:
1. **Create conversion script**: For your specific sprite format
2. **Manual conversion**: Follow the steps above manually
3. **Guided walkthrough**: Step-by-step assistance with your specific sprite