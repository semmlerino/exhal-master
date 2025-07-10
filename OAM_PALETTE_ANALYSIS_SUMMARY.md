# OAM Palette Analysis Summary

## Overview
Analysis of multiple OAM (Object Attribute Memory) dump files from Kirby Super Star to understand sprite palette assignments and identify Kirby sprites.

## Key Findings

### 1. Palette Usage Distribution
- **Palette 0**: Most commonly used (19 unique tiles), primary palette for Kirby sprites
- **Palette 6**: Secondary palette (16 unique tiles), used for effects/UI elements
- **Palette 4**: Common for enemies/objects (14 unique tiles)
- **Palette 1-3**: Character variations and special sprites
- **Palette 5**: Effects and special objects
- **Palette 7**: Rarely used (5 unique tiles)

### 2. Identified Kirby Sprite Clusters

#### High-Confidence Kirby Sprites (Score 8-10/10):
1. **OAM.dmp** - Perfect Kirby cluster:
   - Position: (108, 102), Size: 32x31 pixels
   - 8 sprites using Palette 0 exclusively
   - Tiles: 0x02, 0x03, 0x04, 0x0C, 0x0D, 0x12, 0x13, 0x1D

2. **Cave.SnesSpriteRam.dmp** - Mixed palette Kirby:
   - Position: (11, 83), Size: 37x24 pixels
   - Uses both Palette 0 (5 sprites) and Palette 4 (3 sprites)
   - Suggests Kirby with power-up or special state

3. **SnesSpriteRam.OAM.dmp** - Standard Kirby:
   - Position: (181, 37), Size: 24x24 pixels
   - 5 sprites using Palette 0
   - Tiles: 0x64-0x67, 0x74

### 3. Kirby Tile-to-Palette Mapping

#### Consistent Palette 0 Tiles (Always Kirby):
- Body tiles: 0x02, 0x03, 0x04, 0x0C, 0x0D, 0x12, 0x13, 0x1B, 0x1D
- Additional tiles: 0x64-0x67, 0x74

#### Variable Palette Tiles:
- Tile 0x04: Usually Palette 0, sometimes Palette 5 (power-up state?)
- Tile 0x03: Can use Palette 0 or 1
- Tiles 0x23, 0x24, 0x33: Palette 4 (transformed Kirby parts?)

### 4. Sprite Organization Patterns

Kirby sprites typically:
- Use 4-8 sprites arranged in a 16x16 to 32x32 pixel area
- Primarily use Palette 0 for normal form
- May incorporate Palette 4 sprites when transformed
- Are positioned with consistent tile arrangements

### 5. Palette Assignment Rules

Based on the OAM analysis:
1. **Palette 0**: Default Kirby palette (pink/normal)
2. **Palette 1**: Alternate Kirby state or player 2
3. **Palette 2**: Special effects or UI elements
4. **Palette 3**: Rare usage, specific enemies
5. **Palette 4**: Power-up states, transformed Kirby parts
6. **Palette 5**: Effects, special objects
7. **Palette 6**: UI elements, background objects
8. **Palette 7**: Rarely used, special effects

## Implementation Recommendations

For the sprite editor:
1. **Default Assignment**: Tiles 0x00-0x1F should default to Palette 0
2. **Power-up Handling**: Allow tiles to switch between Palette 0 and 4
3. **Multi-Palette Support**: Some tiles legitimately use multiple palettes
4. **Validation**: Warn if Kirby tiles are assigned unusual palettes (5-7)

## Files Generated
- `oam_palette_mapping.txt`: Complete tile-to-palette mapping
- `kirby_palette_assignments.txt`: Detailed Kirby sprite analysis
- Analysis scripts: `analyze_oam_dumps.py`, `identify_kirby_in_oam.py`