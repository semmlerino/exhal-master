# Grayscale Sprite Editing Guide

## Files Ready for Editing

- **all_chars_edit_2x.png** - 2x zoom (256x512) - Good for overall view
- **all_chars_edit_4x.png** - 4x zoom (512x1024) - Better for detailed pixel work
- **all_chars.png** - Original size (128x256) - Edit this if you prefer 1:1

## How Grayscale Values Work

Each pixel has a value from 0-15:
- **0**: Transparent/Background (usually black)
- **1-3**: Dark shades (outlines, shadows)
- **4-7**: Mid-tones (main sprite colors)
- **8-11**: Light shades (highlights)
- **12-15**: Brightest (special effects, shine)

## Editing Workflow

### 1. Make Your Edits
Edit any of the files above in your image editor. Some ideas:
- Add accessories (hats, glasses, mustaches)
- Change expressions (eyes, mouths)
- Modify poses
- Create new effects

### 2. Convert to SNES Format
```bash
# If you edited the zoomed version, resize back first
# Most image editors can do this, or use ImageMagick:
# convert all_chars_edit_4x.png -resize 128x256 all_chars_edited.png

# Convert to SNES format
python3 png_to_snes.py all_chars_edited.png all_chars_edited.bin
```

### 3. Preview with Different Palettes
```bash
# Convert back to PNG
python3 snes_tiles_to_png.py all_chars_edited.bin preview.png 16

# Apply different palettes to see how it looks
for pal in 0 4 5 6 7 8; do
    python3 extract_all_palettes.py CGRAM.dmp preview.png $pal
done
```

## What Each Sprite Is (By Row)

Looking at the grayscale sprites:

**Rows 0-1**: Kirby animations
- Standing, walking, jumping
- Mouth open (inhaling)
- Various action poses

**Rows 2-3**: Common enemies
- Round enemies (possibly Waddle Dees)
- Flying enemies
- Various creatures

**Rows 4-5**: Effects and items
- Stars (collectibles)
- Sparkle effects
- Power-up items

**Rows 6-7**: More enemies and objects
- Different enemy types
- Platform elements
- Background objects

## Simple Edit Ideas

1. **Kirby Mods**:
   - Add sunglasses (dark pixels over eyes)
   - Give him a cap (pixels on top)
   - Change his shape (make him square?)

2. **Enemy Mods**:
   - Add angry eyebrows
   - Give them accessories
   - Change their expressions

3. **Effect Mods**:
   - Change star shapes
   - Modify sparkle patterns
   - Create new effect designs

## Tips for Good Edits

- **Preserve outlines**: Keep value 1-3 pixels for edges
- **Maintain contrast**: Use full range of values (1-15)
- **Test small changes first**: Edit one sprite before doing many
- **Keep backups**: Copy files before editing

## Ready to Edit!

1. Open `all_chars_edit_2x.png` or `all_chars_edit_4x.png`
2. Make your changes
3. Save the file
4. We'll convert it back to test!

The grayscale approach lets you focus on the pixel art without worrying about color restrictions!