# Comprehensive Kirby Super Star Sprite Editing Guide

## Overview

This guide explains how to extract, edit, and reinsert sprites for Kirby Super Star using the palette-aware workflow tools. With our palette mapping data (43% coverage), you can now edit sprites while maintaining correct colors.

## Prerequisites

1. **Memory Dumps**:
   - VRAM dump (contains sprite graphics)
   - CGRAM dump (contains color palettes)
   - Optional: OAM dump (sprite-to-palette mappings)

2. **Palette Mappings**:
   - `final_palette_mapping.json` (from Mesen tracking)
   - Or use default mappings for unmapped sprites

3. **Image Editor**:
   - Must support indexed PNG format
   - Recommended: Aseprite, GraphicsGale, or GIMP

## Workflow Options

### Option 1: Individual Tile Editing

Best for: Precise edits to specific sprites, testing changes

```bash
# Extract sprites as individual tiles
python sprite_edit_workflow.py extract sync3_vram.dmp sync3_cgram.dmp \
    -m final_palette_mapping.json \
    -o my_sprites \
    --offset 0xC000 \
    --size 0x4000

# Edit PNG files in my_sprites/ folder
# Each tile is saved as tile_XXXX_palY.png

# Validate your edits
python sprite_edit_workflow.py validate my_sprites/

# Reinsert into VRAM
python sprite_edit_workflow.py reinsert my_sprites/
```

### Option 2: Sprite Sheet Editing

Best for: Bulk edits, viewing sprites in context

```bash
# Extract as sprite sheet
python sprite_sheet_editor.py extract sync3_vram.dmp sync3_cgram.dmp \
    -m final_palette_mapping.json \
    -o kirby_sprites.png \
    --guide

# Edit kirby_sprites.png in your image editor
# Use kirby_sprites_editing_guide.png as reference

# Validate edited sheet
python sprite_sheet_editor.py validate kirby_sprites_edited.png

# Convert back to VRAM
python sprite_sheet_editor.py reinsert kirby_sprites_edited.png
```

## SNES Sprite Constraints

### Critical Rules
1. **One Palette Per Tile**: Each 8×8 tile uses exactly ONE palette
2. **15 Colors Maximum**: Each tile can use colors 1-15 from its palette
3. **Color 0 = Transparent**: Always reserved for transparency
4. **Fixed Palettes**: Cannot add new colors, only use existing palette colors

### Technical Details
- **Tile Size**: 8×8 pixels (cannot be changed)
- **Color Depth**: 4bpp (16 colors per palette)
- **Sprite Palettes**: OAM palettes 0-7 map to CGRAM palettes 8-15
- **Large Sprites**: Made of multiple 8×8 tiles, each can use different palettes

## Editing Best Practices

### 1. Maintain Palette Integrity
```
✓ DO: Use only colors from the sprite's assigned palette
✗ DON'T: Add new colors or use colors from other palettes
```

### 2. Preserve Transparency
```
✓ DO: Keep color index 0 transparent
✗ DON'T: Draw with color index 0
```

### 3. Work in Indexed Mode
```
✓ DO: Save as indexed PNG with 16 colors
✗ DON'T: Save as RGB/RGBA without palette
```

### 4. Test Frequently
```
✓ DO: Validate after each major edit
✗ DON'T: Make extensive changes without testing
```

## Common Editing Scenarios

### Changing Kirby's Color
```bash
# Kirby uses palette 0 (CGRAM palette 8)
# Edit tiles 0000-0031 using only palette 0 colors
```

### Editing Enemy Sprites
```bash
# Enemies use various palettes (1, 3, 4)
# Check tile filename for palette: tile_0064_pal1.png
```

### Creating New Animations
```bash
# Must reuse existing tiles or replace unused tiles
# Cannot add new tiles beyond VRAM capacity
```

## Validation Messages

### Success
```
✓ Valid tiles: 120
✓ All colors within palette constraints
✓ Ready for reinsertion
```

### Common Errors
```
ERROR: Tile 64 has too many colors: 17 (max 15 + transparent)
Solution: Reduce color count in that tile

WARNING: Color (255,128,0) not in original palette 1
Solution: Use color picker from palette reference

ERROR: Invalid dimensions: (16, 16), expected (8, 8)
Solution: Edit must maintain 8×8 tile boundaries
```

## Testing Your Edits

1. **Create Backup**:
   ```bash
   cp sync3_vram.dmp sync3_vram.backup.dmp
   ```

2. **Apply Edits**:
   ```bash
   # Creates sync3_vram_edited.dmp
   python sprite_edit_workflow.py reinsert my_sprites/
   ```

3. **Test in Emulator**:
   - Load savestate with edited VRAM
   - Or use memory viewer to inject at runtime
   - Verify sprites display correctly

## Advanced Features

### Batch Processing
```python
from sprite_edit_workflow import SpriteEditWorkflow

workflow = SpriteEditWorkflow("final_palette_mapping.json")

# Extract specific region
workflow.extract_for_editing(
    "vram.dmp", "cgram.dmp",
    offset=0xC000,  # Sprite area start
    size=0x0800,    # First 64 tiles
    output_dir="kirby_only"
)
```

### Custom Validation
```python
# Set strict mode for palette matching
validation = workflow.validate_edited_sprites(
    "my_sprites/",
    strict_palette_check=True
)
```

### Palette Remapping
```python
# For sprites without known mappings
editor.set_default_palette(4)  # Use palette 4 for unknowns
```

## Troubleshooting

### "No palette mapping found"
- Sprite hasn't been mapped yet (57% are unmapped)
- Solution: Use default palette or manually assign

### "Colors look wrong after reinsertion"
- Check if using correct palette
- Verify OAM offset (+8) is applied
- Ensure edited with indexed color mode

### "Validation passes but sprites corrupted"
- Verify tile boundaries (8×8)
- Check for off-by-one errors in positioning
- Ensure no tiles overlap

## File Formats

### Input Files
- **VRAM dump**: Raw binary, typically 64KB
- **CGRAM dump**: 512 bytes (256 colors)
- **Palette mappings**: JSON with tile→palette data

### Output Files
- **Edited VRAM**: Modified binary dump
- **Preview PNG**: Visual verification
- **Validation report**: JSON with detailed results

## Example: Changing Kirby's Hat Color

1. Extract Kirby sprites:
   ```bash
   python sprite_edit_workflow.py extract vram.dmp cgram.dmp \
       -m final_palette_mapping.json \
       --offset 0xC000 --size 0x0400 \
       -o kirby_tiles
   ```

2. Edit hat pixels in tiles 0-3 (maintain palette 0 colors)

3. Validate:
   ```bash
   python sprite_edit_workflow.py validate kirby_tiles/
   ```

4. Reinsert:
   ```bash
   python sprite_edit_workflow.py reinsert kirby_tiles/
   ```

## Complete Workflow Summary

### Extract → Edit → Validate → Reinsert

1. **Extract with Correct Palettes**:
   - Uses your 43% coverage mapping data
   - Each sprite labeled with its palette
   - Reference sheet for context

2. **Edit with Constraints**:
   - Maintain 8×8 tile boundaries
   - Use only assigned palette colors
   - Preserve transparency (index 0)

3. **Validate Automatically**:
   - Checks color count per tile
   - Verifies palette constraints
   - Reports specific issues

4. **Reinsert Safely**:
   - Creates backups by default
   - Generates preview images
   - Maintains SNES format

## Integration with ROM Hacking

The edited VRAM dumps can be:
- Loaded via savestate editing
- Injected at runtime via emulator
- Compressed and inserted into ROM
- Used with existing sprite editors

## Next Steps

1. **Run Demo**: `python demo_complete_workflow.py`
2. **Extract Your Sprites**: Start with small batches
3. **Make Simple Edits**: Test the workflow
4. **Build Your Sprite Collection**: Share with community

---

With these tools, you can now edit Kirby Super Star sprites while maintaining perfect palette accuracy!