# Kirby Palette Assignment Fix Summary

## Issue Description

When using the indexed pixel editor with grayscale sprite sheets, Kirby appeared **blue** when palette 14 was applied, even though palette 14 was labeled as a "Kirby palette" with pink colors. The purple palette (palette 8) showed Kirby correctly with pink/purple colors.

## Root Cause Analysis

### 1. Incorrect Palette Detection
The `extract_grayscale_sheet.py` script was trying to identify Kirby palettes by looking for pink colors:
```python
has_pink = any(r > 200 and g < 150 and b < 150 for r, g, b in colors)
```

However, palette 14's "pink" colors had green values > 150:
- Color at index 6: RGB(248, 176, 176) - green is 176 > 150
- Color at index 7: RGB(248, 112, 112) - green is 112 < 150

This caused the detection to partially fail.

### 2. Wrong Color Placement
Even when palette 14 was identified as having pink colors, the issue was **where** those colors were located:

**Palette 14 color layout:**
- Indices 0-1: Black and white
- Indices 2-3: **BLUE colors** (128, 224, 232) and (40, 128, 192)
- Indices 4-5: Yellow/green colors
- Indices 6-7: Pink colors

**Palette 8 color layout:**
- Indices 0-7: Various shades of pink/purple throughout

Since Kirby's sprite pixels use indices 2-5 for the main body, applying palette 14 made him appear blue!

### 3. OAM Analysis Revealed the Truth

The OAM (Object Attribute Memory) analysis showed:
- Kirby sprites consistently use **OAM palette 0**
- OAM palette 0 corresponds to **CGRAM palette 8** (OAM + 8 = CGRAM)
- Some power-up states use OAM palette 4 (CGRAM palette 12)

## Solution Implemented

### 1. Created Fix Script
`fix_kirby_palette_assignment.py` that:
- Corrects companion palette files from palette 14 to palette 8
- Backs up the original palette files
- Updates metadata to reflect the correction

### 2. Fixed Affected Files
- `kirby_sprites_grayscale_fixed.pal.json`
- `kirby_focused_test.pal.json`
- Other grayscale sheet companion palettes

### 3. Created OAM-Based Mapping
Generated `oam_based_palette_mapping.json` documenting:
- Kirby normal sprites: OAM palette 0 → CGRAM palette 8
- Kirby power-up sprites: OAM palette 4 → CGRAM palette 12
- Effects/UI: OAM palette 6 → CGRAM palette 14

## Visual Comparison

Created `kirby_palette_issue_comparison.png` showing:
- Why palette 14 makes Kirby blue (blue colors at indices 2-3)
- Why palette 8 makes Kirby pink (pink colors throughout)
- The actual color values in each palette

## Lessons Learned

1. **Trust OAM data over color detection** - The actual palette assignments from the game's OAM are more reliable than trying to guess based on color content.

2. **Color placement matters** - Even if a palette contains the "right" colors, they need to be at the correct indices for the sprite to display properly.

3. **Default assumptions can be wrong** - The script defaulted to the "most used" palette, but for Kirby specifically, palette 8 is correct even if palette 14 is used more overall.

## Workflow Impact

For users:
1. The indexed pixel editor will now automatically load the correct palette 8 for Kirby sprites
2. Kirby will appear with proper pink/purple colors instead of blue
3. The companion .pal.json files now include OAM verification metadata

## Files Modified/Created

- `fix_kirby_palette_assignment.py` - The fix script
- `visualize_palette_issue.py` - Creates visual comparison
- `oam_based_palette_mapping.json` - OAM-based palette reference
- `kirby_palette_issue_comparison.png` - Visual explanation
- Various `.pal.json` files - Corrected companion palettes
- Backup files with `_backup_pal14` suffix

## Verification

To verify the fix works:
1. Open any grayscale Kirby sprite sheet in the indexed pixel editor
2. Load the companion .pal.json file (should auto-prompt)
3. Kirby should now appear pink/purple, not blue

The issue is now resolved!