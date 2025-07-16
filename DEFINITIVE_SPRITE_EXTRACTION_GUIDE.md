# Definitive Sprite Extraction Guide - Kirby Super Star
## Complete Reference for Correct Palette Mapping

### Executive Summary

This document consolidates all learnings about sprite extraction with correct palette mapping for Kirby Super Star. The key insight is that **each 8x8 tile requires its own palette assignment** based on OAM data, not single-palette application to all tiles.

---

## 1. Technical Background

### SNES Sprite System Architecture

**Memory Layout:**
- **VRAM**: Contains sprite graphics data (tiles)
- **CGRAM**: Contains color palettes (256 colors total)
- **OAM**: Contains sprite-to-palette mappings and positioning

**Palette Mapping:**
- OAM palettes 0-7 map to CGRAM palettes 8-15
- Formula: `CGRAM_palette = OAM_palette + 8`
- Each 8x8 tile uses exactly ONE palette (16 colors)

**Sprite Data Format:**
- 4bpp (4 bits per pixel) = 16 colors per tile
- Each tile: 8x8 pixels = 32 bytes of data
- Color 0 = transparent, colors 1-15 = visible

### OAM Structure (Critical for Palette Mapping)

```
OAM Entry (4 bytes per sprite):
Byte 0: X position (low 8 bits)
Byte 1: Y position
Byte 2: Tile number (low 8 bits)
Byte 3: Attributes
    Bit 0-2: Palette number (0-7)  ← CRITICAL
    Bit 3-4: Priority
    Bit 5: H-flip
    Bit 6: V-flip
    Bit 7: Tile table select
```

---

## 2. Critical Issues with Previous Approaches

### Problem 1: Single Palette Applied to All Tiles

**What was wrong:**
```bash
# INCORRECT - applies one palette to ALL tiles
python3 sprite_extractor.py --palette 8 --output sprites.png
```

**Why it's wrong:**
- Extracts 512 tiles but applies same palette to all
- OAM data shows different tiles use different palettes:
  - Tiles 0-19: Use palette 0 (Kirby)
  - Tiles 32-51: Use palette 4 (UI elements)
  - Tiles 160+: Use palette 6 (enemies)

**Result:** Mixed-up colors, blue Kirby, wrong enemy colors

### Problem 2: OAM Parsing Bugs (Fixed)

**Historical bug:**
```python
# WRONG (old code)
palette = (attrs >> 1) & 0x07  # Incorrect bit shifting

# CORRECT (current code)
palette = attrs & 0x07  # Extract lower 3 bits
```

### Problem 3: Unsynchronized Memory Dumps

**Issue:** Using dumps from different game moments
**Solution:** VRAM, CGRAM, and OAM must be from the same exact frame

---

## 3. Correct Workflow

### Step 1: Obtain Synchronized Dumps

**In Mesen-S emulator:**
1. Pause at desired moment
2. Debug → Save Memory Dump
3. Export all three simultaneously:
   - `VRAM.dmp` (sprite graphics)
   - `CGRAM.dmp` (color palettes)
   - `OAM.dmp` (sprite-to-palette mappings)

### Step 2: Analyze OAM Data

```bash
# Analyze palette mappings
python3 sprite_editor/oam_palette_mapper.py OAM.dmp
```

**Expected output:**
```
Active palettes: [0, 4, 6]
Palette 0: 6 sprites (Kirby)
Palette 4: 5 sprites (UI elements)
Palette 6: 10 sprites (enemies)
```

### Step 3: Extract with Correct Palette Mapping

**Use the synchronized extraction tool:**
```bash
PYTHONPATH=/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master \
python3 archive/experimental/demo_final_synchronized.py
```

**This produces:**
- `cave_sprites_synchronized.png` - Each tile with correct palette
- `cave_character_showcase.png` - Individual character examples

---

## 4. Tools Reference

### 🆕 Recently Restored Tools (January 2025)

**1. `mss_palette_extractor.py`**
- Purpose: Extract VRAM, CGRAM, and OAM from Mesen-S savestate files (.mss)
- Benefits: 
  - No need for separate memory dumps
  - Automatically synchronized data from single savestate
  - Creates visual palette mapping reports
  - Identifies which sprites use which palettes
- Usage: `python3 mss_palette_extractor.py "Kirby Super Star (USA)_2.mss"`
- Outputs:
  - `*_VRAM.dmp`, `*_CGRAM.dmp`, `*_OAM.dmp` - Memory dumps
  - `*_palette_data.json` - Palette mappings in JSON format
  - `*_report.png` - Visual report showing palette usage

**2. `create_sprite_sheets.py`**
- Purpose: Create organized sprite sheets by palette
- Benefits:
  - Automatically groups sprites by their assigned palette
  - Creates both 1x and 4x scaled versions
  - Works with any memory dump set
- Usage: 
  ```bash
  python3 create_sprite_sheets.py  # Auto-detects dumps
  python3 create_sprite_sheets.py "Kirby Super Star (USA)_2"  # Specific prefix
  ```

**3. `extract_palettes.py`**
- Purpose: Extract and visualize all palettes from CGRAM
- Creates:
  - `cave_palettes_reference.png` - Visual chart of all 16 palettes
  - `cave_palette_*_indexed.png` - Individual palette files for editing
- Usage: `python3 extract_palettes.py`

**4. `prepare_sprite_for_editing.py`**
- Purpose: Prepare sprites for indexed color editing
- Creates:
  - Grayscale sprites with specific palettes applied
  - Editing templates with selected tiles at 4x scale
  - Grid references for precise editing
- Usage: `python3 prepare_sprite_for_editing.py`

### ✅ Correct Tools (Use These)

**1. `demo_final_synchronized.py`**
- Location: `archive/experimental/`
- Purpose: Extracts sprites with per-tile palette mapping
- Uses: OAM data to apply correct palette to each tile

**2. `oam_palette_mapper.py`**
- Location: `sprite_editor/`
- Purpose: Analyzes OAM data for palette assignments
- Usage: `python3 sprite_editor/oam_palette_mapper.py OAM.dmp`

### ❌ Incorrect Tools (Avoid)

**1. `sprite_extractor.py`**
- Problem: Only applies single palette to all tiles
- Limited use: Only for extracting grayscale versions

**2. `sprite_workflow.py`**
- Problem: Wrapper around single-palette extraction
- Limited use: Basic extraction only

---

## 5. Verified Examples

### Cave Area (Known Working Example)

**Files:**
- `Cave.SnesVideoRam.dmp`
- `Cave.SnesCgRam.dmp`
- `Cave.SnesSpriteRam.dmp`

**OAM Analysis Results:**
```
OAM Palette 0: 6 sprites, tiles [0, 2, 3, 4, 18, 19]
OAM Palette 4: 6 sprites, tiles [32, 34, 35, 36, 50, 51]
OAM Palette 6: 6 sprites, tiles [160, 162, 176, 178]
```

**Color Palettes:**
- Palette 0: Pink Kirby colors `[224,56,248], [248,160,232], [240,112,224]`
- Palette 4: UI colors `[248,248,248], [248,152,0], [248,88,0]`
- Palette 6: Cave enemy colors `[248,248,248], [128,224,232], [40,128,192]`

### Results Comparison

**Wrong approach (single palette):**
- `kirby_sprites_colored_pal8.png` - Mixed colors, blue areas where shouldn't be
- `kirby_sprites_colored_pal12.png` - Everything pink/magenta
- `kirby_sprites_colored_pal14.png` - Everything yellow/brown

**Correct approach (per-tile palette):**
- `cave_sprites_synchronized.png` - Proper colors per character type
- `cave_character_showcase.png` - Individual character examples

### Indexed Color Editing Approach (New)

**Benefits of separating sprites and palettes:**
- Edit sprites in grayscale preserving index values
- Apply different palettes without re-editing
- Maintain SNES 4bpp constraints automatically
- Easier to see pixel boundaries in grayscale

**Files created for editing:**
- `cave_sprites_grayscale.png` - Base grayscale sprites
- `cave_palette_*_indexed.png` - Individual palette references
- `*_edit_tiles_*_pal*.png` - Pre-scaled editing templates

---

## 6. Troubleshooting Guide

### "Palette did not match" Error

**Root cause:** Using wrong extraction method
**Solution:** Use synchronized extraction with OAM-based palette mapping

### "Sprites appear blue instead of pink"

**Root cause:** Using palette 14 instead of palette 8 for Kirby
**Solution:** Check OAM data - Kirby uses OAM palette 0 → CGRAM palette 8

### "Colors look completely wrong"

**Root cause:** Applying single palette to all tiles
**Solution:** Use per-tile palette mapping based on OAM data

### "Missing sprites or corrupted data"

**Root cause:** Unsynchronized memory dumps
**Solution:** Ensure VRAM, CGRAM, OAM are from same frame

---

## 7. File Format Reference

### Memory Dump Sizes
- **VRAM.dmp**: 65,536 bytes (64KB)
- **CGRAM.dmp**: 512 bytes (256 colors × 2 bytes)
- **OAM.dmp**: 544 bytes (512 + 32 bytes)

### Important Memory Addresses
- **Sprite data in VRAM**: 0xC000 (word address 0x6000)
- **Kirby tiles**: 0-31 (typically first 32 tiles)
- **OAM sprite palettes**: 0-7 (map to CGRAM 8-15)

### Palette Data Format
```
CGRAM Color Format (BGR555):
- 2 bytes per color
- 5 bits each: Blue, Green, Red
- Conversion: RGB = (component & 0x1F) * 8
```

---

## 8. Key Algorithms

### OAM Palette Extraction
```python
def extract_oam_palette(oam_data, sprite_index):
    offset = sprite_index * 4
    attrs = oam_data[offset + 3]
    oam_palette = attrs & 0x07  # Bits 0-2
    cgram_palette = oam_palette + 8  # OAM offset
    return cgram_palette
```

### Per-Tile Palette Mapping
```python
def apply_correct_palettes(vram_data, cgram_data, oam_data):
    # Parse OAM to get tile→palette mapping
    tile_to_palette = {}
    for sprite in parse_oam(oam_data):
        if sprite['visible']:
            tile_to_palette[sprite['tile']] = sprite['palette']
    
    # Apply correct palette to each tile
    for tile_num in range(total_tiles):
        palette = tile_to_palette.get(tile_num, 0)  # Default to 0
        apply_palette_to_tile(tile_num, palette)
```

---

## 9. Workflow Commands

### Complete Extraction Workflow
```bash
# 1. Analyze OAM data
python3 sprite_editor/oam_palette_mapper.py Cave.SnesSpriteRam.dmp

# 2. Extract with correct palette mapping
PYTHONPATH=/mnt/c/CustomScripts/KirbyMax/workshop/exhal-master \
python3 archive/experimental/demo_final_synchronized.py

# 3. Results:
# - cave_sprites_synchronized.png (correct extraction)
# - cave_character_showcase.png (individual examples)
```

### For Grayscale Extraction Only
```bash
# Only use this for grayscale versions
python3 sprite_editor/sprite_extractor.py \
    --vram VRAM.dmp \
    --offset 0xC000 \
    --size 0x4000 \
    --output sprites_grayscale.png
```

### MSS Savestate Extraction Workflow
```bash
# 1. Extract everything from Mesen-S savestate
python3 mss_palette_extractor.py "Kirby Super Star (USA)_2.mss"

# This creates:
# - Kirby Super Star (USA)_2_VRAM.dmp
# - Kirby Super Star (USA)_2_CGRAM.dmp  
# - Kirby Super Star (USA)_2_OAM.dmp
# - Kirby Super Star (USA)_2_palette_data.json
# - Kirby Super Star (USA)_2_report.png

# 2. Create sprite sheets by palette
python3 create_sprite_sheets.py "Kirby Super Star (USA)_2"
```

### Grayscale Editing Workflow
```bash
# 1. Extract sprites in grayscale
python3 sprite_editor/sprite_extractor.py \
    --vram Cave.SnesVideoRam.dmp \
    --output cave_sprites_grayscale.png

# 2. Extract and visualize palettes
python3 extract_palettes.py

# 3. Prepare indexed color versions for editing
python3 prepare_sprite_for_editing.py

# This creates:
# - cave_sprites_kirby_pal8.png (Kirby palette applied)
# - cave_sprites_ui_pal12.png (UI palette applied)
# - cave_sprites_enemy_pal14.png (Enemy palette applied)
# - kirby_edit_tiles_*_pal8.png (Editing templates)
```

---

## 10. Success Criteria

### Correct Extraction Should Show:
- **Kirby sprites**: Pink/purple colors (palette 8)
- **UI elements**: White/orange colors (palette 12)
- **Enemy sprites**: Character-appropriate colors (various palettes)
- **Each tile**: Using its OAM-assigned palette

### Verification:
1. Check `cave_character_showcase.png` for proper character colors
2. Verify OAM analysis shows expected palette assignments
3. Ensure no "mixed" colors in single character tiles

---

## 11. Additional Restored Tools

### Analysis Tools
- **`analyze_oam_dumps.py`** - Detailed OAM data analysis
- **`rom_analyzer.py`** - Find sprite data in ROM files
- **`analyze_palettes.py`** - Palette analysis and visualization

### Extraction Utilities  
- **`extract_4bpp_section.py`** - Extract focused sprite sections
- **`create_grayscale_with_palette.py`** - Create grayscale with palette info
- **`extract_palette_for_editor.py`** - Extract palettes for pixel editor

### Demo Scripts (in restored_demos/)
- **`demo_edit_and_reinsert.py`** - Complete editing workflow example
- **`demo_unified_workflow.py`** - Unified workflow with validation
- **`demo_all_characters.py`** - Showcase all character sprites

## 12. Conclusion

**The fundamental insight:** SNES sprite extraction requires **per-tile palette mapping** based on OAM data, not single-palette application to all tiles.

**Use this workflow:**
1. Synchronized memory dumps (VRAM+CGRAM+OAM)
2. OAM analysis for palette assignments
3. Per-tile palette application
4. Verification against expected results

**Key files:**
- `DEFINITIVE_SPRITE_EXTRACTION_GUIDE.md` ← This document
- `archive/experimental/demo_final_synchronized.py` ← Correct extraction tool
- `sprite_editor/oam_palette_mapper.py` ← OAM analysis tool

This approach resolves all "palette did not match" errors and produces correctly colored sprite extractions.