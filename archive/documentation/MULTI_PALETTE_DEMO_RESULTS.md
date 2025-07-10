# Multi-Palette Extraction Demo Results

This demonstration shows how the Kirby sprite editor correctly handles sprites with different palettes in the same sheet.

## Files Created

### 1. `demo_oam_correct_palettes.png`
- **What it shows**: Full sprite sheet (512 tiles) where each tile uses its OAM-assigned palette
- **Key insight**: This is how the sprites actually appear in-game, with correct colors
- **Notable**: Different characters use different palettes (Kirby uses palette 0, enemies use others)

### 2. `demo_palette_0.png` through `demo_palette_7.png`
- **What they show**: The same sprite sheet with uniform palettes applied
- **Purpose**: Shows how sprites would look if forced to use a single palette
- **Key insight**: Many sprites look wrong when using incorrect palettes

### 3. `demo_oam_correct.png`
- **What it shows**: Same as #1 but generated through the multi-palette extraction method
- **Purpose**: Verifies that the multi-palette extraction properly creates OAM-correct versions

### 4. `demo_palette_grid.png`
- **What it shows**: A 4x4 grid displaying sprites with all 16 possible palettes
- **Visual indicators**:
  - Green borders = Active palettes (actually used by sprites per OAM data)
  - Gray borders = Inactive palettes
  - Labels show palette number and sprite count
- **Active palettes found**: 0, 2, 3, 4, 6, 7

### 5. `demo_kirby_only.png` and `demo_kirby_only_4x.png`
- **What they show**: Just the first 64 tiles (Kirby sprites) with correct palettes
- **4x version**: Scaled up for better visibility
- **Key insight**: Kirby primarily uses palette 0

### 6. `demo_palette_comparison.png`
- **What it shows**: Side-by-side grid comparison of different palette versions
- **Purpose**: Makes it easy to see the differences between palettes
- **Green border**: Highlights the OAM-correct version

### 7. `demo_kirby_palette_strip.png`
- **What it shows**: Horizontal strip showing Kirby with each palette
- **Key insight**: Shows clearly that Kirby looks correct with palette 0 (green highlight)

## Key Findings from OAM Analysis

Based on the OAM data analysis:
- **Palette 0**: 8 sprites (primarily Kirby)
- **Palette 2**: 4 sprites
- **Palette 3**: 3 sprites
- **Palette 4**: 18 sprites (most common, likely enemies/objects)
- **Palette 6**: 8 sprites
- **Palette 7**: 3 sprites

## Technical Achievement

The sprite editor successfully:
1. ✅ Reads OAM data to understand sprite-to-palette mappings
2. ✅ Extracts sprites with each tile using its correct palette
3. ✅ Provides multiple viewing modes for palette analysis
4. ✅ Handles the complex case where different sprites in one sheet use different palettes

This demonstrates that the sprite editor properly handles SNES sprite palettes as they work in the actual game!