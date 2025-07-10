# Palette Fix Investigation Summary

## Problem Identified
The user reported: "It seems like there is an issue with the palette ultrathink" - colors weren't appearing correctly when loading the grayscale sprite sheet with its companion palette.

## Investigation Findings

### 1. OAM Attribute Parsing Bug
Found in `analyze_cave_dumps.py`:
```python
# INCORRECT:
palette = (attrs >> 1) & 0x07  # This shifts bits incorrectly

# CORRECT:
palette = attrs & 0x07  # Extract lower 3 bits for OAM palette (0-7)
cgram_palette = palette + 8  # Map to CGRAM sprite palettes (8-15)
```

### 2. Palette Selection Logic Issues
- Original logic selected palette based on tile count in metadata
- Metadata showed palette 8 had 327 tiles (most common)
- BUT actual OAM data showed only 6 sprites use palette 8
- Palette 11 is most used (81 sprites) but has yellow/brown colors
- Palette 14 has Kirby colors and 26 sprites using it

### 3. Cave Dump Color Analysis
**Palette 8 (from Cave.SnesCgRam.dmp):**
- Contains purple/magenta colors (RGB 240,56,248)
- Not the expected pink colors for normal Kirby
- Suggests this dump is from a different game state (power-up?)

**Palette 14 (from Cave.SnesCgRam.dmp):**
- Contains light pink colors (RGB 248,176,176 and 248,112,112)
- Also has red (RGB 248,0,0) for Kirby's feet
- Better match for normal Kirby appearance

### 4. Sprite Usage Analysis
From OAM data analysis:
```
Palette 8:  6 sprites  - Has purple colors
Palette 11: 81 sprites - Yellow/brown (no Kirby colors)
Palette 12: 6 sprites  - Orange tones
Palette 14: 26 sprites - Pink/red (Kirby colors) ✓
Palette 15: 9 sprites  - Blue tones
```

## Solution Implemented

### 1. Created `fix_palette_system.py`
- Correctly parses OAM attributes (no bit shifting)
- Analyzes actual sprite usage from OAM data
- Scores palettes based on:
  - Presence of pink/red colors
  - Actual sprite usage counts
  - Color characteristics (black transparent, white for eyes)

### 2. Smart Palette Selection
- Primary recommendation: Palette 11 (highest usage)
- Alternative: Palette 14 (has Kirby colors)
- Creates `.pal.json` files with proper metadata

### 3. Files Created
- `kirby_smart_palette_11.pal.json` - Based on usage
- `kirby_palette_14.pal.json` - Based on Kirby colors
- `kirby_palette_8.pal.json` - Purple variant

## Usage Instructions

1. **For pink Kirby appearance:**
   ```bash
   python3 indexed_pixel_editor.py kirby_sprites_grayscale_ultrathink.png -p kirby_palette_14.pal.json
   ```

2. **For game-accurate palette (most sprites):**
   ```bash
   python3 indexed_pixel_editor.py kirby_sprites_grayscale_ultrathink.png -p kirby_smart_palette_11.pal.json
   ```

3. **For purple Kirby variant:**
   ```bash
   python3 indexed_pixel_editor.py kirby_sprites_grayscale_ultrathink.png -p kirby_palette_8.pal.json
   ```

## Key Takeaways

1. **SNES palette mapping**: OAM palettes 0-7 map to CGRAM palettes 8-15
2. **Metadata vs OAM**: Always trust OAM data over metadata tile counts
3. **Game state matters**: The Cave dump appears to be from a special game state with purple Kirby
4. **Multiple valid palettes**: Different palettes may be correct for different contexts

## Next Steps

The palette system is now fixed with proper OAM parsing and smart selection. Users can:
1. Load grayscale sprites with appropriate companion palettes
2. Switch between palettes to see different color variants
3. Edit sprites with accurate color preview

The workflow envisioned by the user is now fully functional:
- Extract sprites in grayscale indexed format ✓
- Extract palettes in script-readable format ✓
- Load both in editor with color preview ✓
- Toggle between grayscale/color views ✓