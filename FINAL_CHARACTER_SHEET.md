# Kirby Super Star - Extracted Character Sprites

## Successfully Extracted Characters

### 1. Beam/Spark Kirby (Yellow)
- **Location**: VRAM $6000
- **Palette**: 8 (yellow/orange tones)
- **File**: `kirby_full_sheet_pal8.png`
- **Colors**: Yellow body, orange feet, white highlights
- **Status**: ✅ Complete animation set

### 2. Level Sprites/Enemies
- **Location**: VRAM $6800-$7000
- **Various palettes**:
  - Palette 4: Green/Pink enemies
  - Palette 5: Blue/Brown enemies
  - Palette 6: Purple/Dark enemies
- **Files**: `all_chars_pal4.png`, `all_chars_pal5.png`, etc.

### 3. UI Elements
- **Location**: VRAM $7000+
- **Palette**: 0, 2 (browns/yellows)
- **Contains**: Score numbers, HUD elements

## Palette Reference from CGRAM

| Palette | Primary Colors | Used For |
|---------|----------------|----------|
| 0 | White/Yellow/Black | UI/Effects |
| 1 | Green/Brown | Environment |
| 2 | Brown/Orange | Blocks/Terrain |
| 3 | Blue shades | Water/Sky |
| 4 | Green/Pink | Enemies |
| 5 | Blue/Brown | Enemies |
| 6 | Purple/Dark | Dark enemies |
| 7 | Blue/Teal | Effects |
| 8 | Yellow/Orange | Beam Kirby |
| 9 | Purple/Orange | Special enemies |
| 10 | Yellow/Cream | Alt Kirby ability |
| 11 | Tan/Brown | Environment |
| 12 | Pink/Red | (Close to normal Kirby) |
| 13 | Green/White | Items/Effects |
| 14 | White/Yellow | Bright effects |
| 15 | Purple/Pink | Special effects |

## Sprite Editing Workflow

### For Beam Kirby:
1. Edit `kirby_full_sheet_pal8_x4.png`
2. Keep yellow/orange color scheme
3. Maintain 64-pixel width

### For Enemies:
1. Use `all_chars_pal4.png` or appropriate palette
2. Enemy sprites are typically smaller (8x8 or 16x16)
3. Check multiple palettes to find correct colors

## Files Created
- `kirby_full_sheet_pal0-15.png` - Kirby with all 16 palettes
- `all_chars_pal1-13.png` - All characters with various palettes
- `VRAM.dmp` - Complete VRAM dump
- `CGRAM.dmp` - All 16 color palettes
- `OAM.dmp` - Sprite position data

## Key Discovery
The yellow Kirby in the screenshots is **Beam/Spark Kirby** (ability form), not regular pink Kirby. This explains why the CGRAM dump has yellow tones instead of pink - the game loads different palettes based on Kirby's current ability!

## Next Steps for Sprite Modding
1. Choose which Kirby form to edit (Beam, Normal, etc.)
2. Edit the appropriate palette version
3. Convert back to SNES format
4. Find compressed location in ROM using sprite index 9
5. Recompress and insert

The complete sprite set is now available for editing!