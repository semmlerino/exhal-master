# Lessons Learned - Kirby Super Star Sprite Editing Project

## Overview
We successfully extracted, edited, and re-inserted sprites from Kirby Super Star (SNES) using memory dumps and custom tools. This document captures key learnings and gotchas.

## What Worked

### 1. Extracting Sprites from VRAM
- **Best approach**: Dump VRAM from emulator when sprites are visible
- **Key location**: Kirby sprites at VRAM $6000 (byte offset 0xC000)
- **Tools**: Mesen-S Debug → Memory Tools → Export VRAM
- **Result**: Clean, decompressed sprites ready for editing

### 2. Identifying Sprites and Palettes
- Used sprite viewer to identify sprite index (Kirby = index 9)
- CGRAM dump provided all 16 palettes
- Different palettes for different Kirby abilities (yellow = Beam/Spark)

### 3. Creating Editing Tools
- `snes_tiles_to_png.py` - Convert SNES tiles to PNG
- `png_to_snes.py` - Convert PNG back to SNES format
- `extract_all_palettes.py` - Apply CGRAM palettes to sprites

## What Didn't Work

### 1. ROM Insertion Complexity
- **Problem**: VRAM contains sprites from multiple compressed sources in ROM
- **Why it failed**: Sprites are assembled at runtime from various locations
- **Lesson**: Can't simply put 16KB back into one ROM location

### 2. Sprite Pointer Confusion
- **Problem**: Sprite index pointers didn't lead to expected graphics
- **Reality**: The pointer table points to metadata, not always direct graphics
- **Lesson**: VRAM extraction is simpler than ROM modification

### 3. Image Format Issues
- **Problem**: Edited sprites showed artifacts/corruption
- **Cause**: Image saved as RGBA instead of indexed color
- **Fix**: Must save as indexed PNG with ≤16 colors

## Critical Technical Details

### SNES Sprite Format
- **4bpp**: 4 bits per pixel = 16 colors max
- **Tile size**: 8x8 pixels = 32 bytes
- **Planar format**: Bitplanes stored separately (not linear)

### Color Modes Matter
```
❌ WRONG: RGBA mode (millions of colors)
✅ RIGHT: Indexed mode (16 colors max)
```

### VRAM vs ROM
- **VRAM**: Runtime memory, sprites decompressed and ready
- **ROM**: Compressed data, complex organization
- **Best practice**: Edit via VRAM for testing, ROM for permanent

## Successful Workflow

### 1. Extract
```bash
# From emulator: Export VRAM.dmp
# Extract sprite region
dd if=VRAM.dmp of=sprites.bin bs=1 skip=$((0x6000 * 2)) count=16384
```

### 2. Convert to PNG
```bash
python3 snes_tiles_to_png.py sprites.bin sprites.png 16
python3 extract_all_palettes.py CGRAM.dmp sprites.png [palette_num]
```

### 3. Edit
- Use any image editor
- **CRITICAL**: Save as indexed color PNG (not RGB!)
- Keep to 16 colors or less
- Maintain exact dimensions

### 4. Convert Back
```bash
# Fix color mode if needed
python3 png_to_snes.py edited.png edited.bin

# Inject into VRAM
dd if=edited.bin of=VRAM_modded.dmp bs=1 seek=$((0x6000 * 2)) conv=notrunc
```

### 5. Test
- Import VRAM_modded.dmp in emulator
- See changes immediately!

## Key Discoveries

### 1. Kirby's Multiple Forms
- Pink Kirby = Normal (not in our CGRAM dump)
- Yellow Kirby = Beam/Spark ability (palette 8)
- Different abilities = Different palettes

### 2. Sprite Organization
- Kirby animations: First ~64 tiles
- Enemies: Following sections
- Effects/UI: Mixed throughout

### 3. Compression
- HAL's custom LZ compression (exhal/inhal tools)
- Compression ratio typically 1.5:1 to 3:1
- 64KB size limit per compressed block

## Common Pitfalls

### 1. Save Format
- **Always** save as indexed PNG
- Check image mode before converting
- Use Image → Mode → Indexed in most editors

### 2. Palette Confusion
- CGRAM state depends on current game screen
- Different areas load different palettes
- May need multiple dumps for all palettes

### 3. Size Mismatches
- VRAM sprites often combine multiple ROM sources
- Can't always trace back to single ROM location
- Editing via VRAM is more reliable

## Tools Created

1. **snes_tiles_to_png.py** - SNES tile data → PNG
2. **png_to_snes.py** - PNG → SNES tile data  
3. **extract_all_palettes.py** - Apply CGRAM palettes
4. **view_sprites_zoomed.py** - Create zoomed versions
5. **create_character_sheet.py** - Organize sprites by type

## Future Improvements

1. **Automatic format checking** - Warn if PNG isn't indexed
2. **Palette management** - Better tools for managing multiple palettes
3. **ROM patching** - Find proper way to insert into ROM permanently
4. **Sprite mapping** - Document which ROM locations map to which VRAM addresses

## Summary

The project succeeded in editing Kirby sprites through VRAM manipulation. Key insight: Working with runtime memory (VRAM) is much simpler than dealing with compressed ROM data. Always verify image format before conversion!

## Quick Reference

```bash
# Extract from VRAM
dd if=VRAM.dmp of=sprites.bin bs=1 skip=$((0x6000 * 2)) count=16384

# Convert to editable format
python3 snes_tiles_to_png.py sprites.bin sprites.png 16

# After editing (MUST be indexed PNG!)
python3 png_to_snes.py edited.png edited.bin

# Inject back
dd if=edited.bin of=VRAM_modded.dmp bs=1 seek=$((0x6000 * 2)) conv=notrunc

# Load VRAM_modded.dmp in emulator
```

Remember: INDEXED COLOR MODE IS CRITICAL!