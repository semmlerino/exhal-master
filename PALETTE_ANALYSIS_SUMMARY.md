# Kirby Sprite Palette Analysis Summary

## Issue Identified
The original `extract_grayscale_sheet.py` was using a simplistic "most common palette" approach based on tile counts in metadata, which incorrectly selected palette 8. This didn't match the actual sprite assignments in the OAM (Object Attribute Memory) data.

## Analysis Results

### OAM Palette Usage (from actual sprite data)
- **OAM Palette 0** (CGRAM 8): 6 sprites - Has Kirby colors (pink/purple)
- **OAM Palette 3** (CGRAM 11): 23 sprites - No Kirby colors (yellow/brown tones)
- **OAM Palette 4** (CGRAM 12): 5 sprites - Has Kirby colors (orange tones)
- **OAM Palette 6** (CGRAM 14): 10 sprites - Has Kirby colors (red/pink) ✅ **RECOMMENDED**
- **OAM Palette 7** (CGRAM 15): 2 sprites - No Kirby colors (blue tones)

### Metadata Tile Counts (less reliable)
- CGRAM Palette 8: 327 tiles
- CGRAM Palette 9: 126 tiles
- CGRAM Palette 10: 15 tiles
- CGRAM Palette 11: 19 tiles
- CGRAM Palette 12: 23 tiles

### Key Findings
1. **Discrepancy**: The metadata shows palette 8 as most common (327 tiles), but OAM shows only 6 sprites actually use it
2. **Palette 14 is optimal**: It has both Kirby colors AND significant OAM usage (10 sprites)
3. **OAM data is more reliable**: It reflects actual sprite rendering assignments

## Solution Implemented

### 1. Enhanced Palette Selection Logic
Updated `extract_grayscale_sheet.py` to:
- Load OAM data when available
- Use OAM palette assignments for tiles
- Select companion palette based on:
  - Presence of Kirby colors (pink/red detection)
  - Actual sprite usage in OAM data
  - Fallback to tile counts only if OAM unavailable

### 2. Test Script Created
`test_palette_analysis.py` - Comprehensive analysis tool that:
- Applies all palettes (8-15) to grayscale sprites
- Saves test images for visual comparison
- Analyzes color content for Kirby-specific colors
- Compares OAM vs metadata assignments
- Generates recommendations

### 3. Visual Comparison Tools
- `kirby_palette_comparison.png` - Grid view of all palette options
- `kirby_palette_focused.png` - Focused view of top candidates
- `palette_tests/` directory - Individual test images for each palette

## Usage

### For Sprite Extraction with Correct Palette:
```bash
python3 extract_grayscale_sheet.py
```
This will now automatically use OAM data to select the correct palette.

### For Palette Analysis:
```bash
python3 test_palette_analysis.py
```
This generates test images and analysis to verify palette selection.

### For Manual Palette Testing:
```bash
python3 fix_palette_selection.py
```
This creates a grayscale sheet with improved OAM-based palette selection.

## Files Modified
- `extract_grayscale_sheet.py` - Added OAM support and smart palette selection
- Created `test_palette_analysis.py` - Comprehensive palette testing tool
- Created `fix_palette_selection.py` - Standalone fix with enhanced logic
- Created `create_palette_comparison.py` - Visual comparison generator

## Verification
The generated `.pal.json` companion files now correctly specify palette 14 for Kirby sprites based on:
- OAM sprite usage data
- Presence of characteristic Kirby colors (reds/pinks)
- Actual in-game sprite rendering assignments