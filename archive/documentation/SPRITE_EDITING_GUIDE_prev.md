# Sprite Editing Guide for Kirby Super Star

## Files Ready for Editing

### 1. Beam Kirby (Yellow)
- **File to edit**: `kirby_full_sheet_pal8_x4.png` (4x zoomed for easy editing)
- **Original size**: `kirby_full_sheet_pal8.png` (64x64 pixels)
- **Colors**: Yellow body, orange feet, white highlights
- **Tiles**: 64 tiles (8x8 arrangement)

### 2. Test Enemy Sprites
- **File to edit**: `all_chars_pal4.png` (has various enemies/objects)
- **Size**: 128x256 pixels
- **Contains**: Multiple characters with green/pink palette

## Quick Editing Steps

### Step 1: Make a Test Edit
```bash
# Make copies for editing
cp kirby_full_sheet_pal8.png kirby_edited.png
cp all_chars_pal4.png enemies_edited.png
```

### Step 2: Edit in Your Favorite Image Editor
- **GIMP** (free): `gimp kirby_edited.png`
- **Paint.NET** (Windows): Open the file
- **Aseprite** (pixel art focused): Great for sprites

**Editing Tips:**
- Keep the image dimensions exactly the same
- Use ONLY the existing colors in the palette
- Save as **Indexed Color PNG** (not RGB)
- For testing, try simple changes like:
  - Give Kirby sunglasses (add black pixels)
  - Change his expression
  - Add a hat or accessory
  - Modify enemy colors within the palette

### Step 3: Convert Back to SNES Format
```bash
# Convert edited PNG back to SNES tiles
python3 png_to_snes.py kirby_edited.png kirby_edited.bin
python3 png_to_snes.py enemies_edited.png enemies_edited.bin
```

### Step 4: Test in Emulator (Quick Method)
Since we extracted from VRAM, we can test quickly by:
1. Replacing the data directly in VRAM while the game is paused
2. Or creating a modified save state

### Step 5: Insert into ROM (Permanent Method)
```bash
# Find where sprite index 9 points in ROM
# Then compress and insert
./inhal kirby_edited.bin "Kirby Super Star (USA).sfc" 0x[offset]
```

## Simple Test Edits to Try

### For Kirby:
1. **Sunglasses**: Add black pixels over eyes
2. **Smile Change**: Modify mouth pixels
3. **Headband**: Add a colored band on top
4. **Star Mark**: Add a small star on his body

### For Enemies:
1. **Color Swap**: Change green to pink within palette
2. **Expression**: Modify eye pixels
3. **Accessories**: Add simple decorations

## Color Palette Reference

### Beam Kirby (Palette 8):
- Color 0: Transparent (keep as-is)
- Color 1: White (highlights)
- Color 2: Light yellow (main body)
- Color 3: Yellow (body shading)
- Color 4: Orange (feet/cheeks)
- Color 5: Dark orange (outlines)
- Colors 6-15: Various shades for effects

## Testing Your Edits

### Quick Preview:
```bash
# View your edited sprites
python3 view_sprites_zoomed.py kirby_edited.png 4
```

### Compare Before/After:
Place original and edited side by side to see changes

## Common Issues

1. **"Wrong colors" after editing**
   - Make sure to save as Indexed PNG, not RGB
   - Don't add new colors outside the palette

2. **"Sprites look corrupted"**
   - Keep exact dimensions (don't resize)
   - Each tile must be exactly 8x8 pixels

3. **"Black squares appear"**
   - Color 0 is transparent - don't change it
   - Check you're using the palette correctly

## Ready to Start!

1. Open `kirby_full_sheet_pal8_x4.png` in your editor
2. Make a simple edit (like adding sunglasses)
3. Save as indexed PNG
4. We'll test it together!

Good luck with your sprite editing!