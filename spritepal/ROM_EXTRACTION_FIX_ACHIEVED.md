# ROM Extraction Fix - Success Report

## Problem Statement
- SpritePal's ROM extraction showed "pixely grey colours" instead of actual sprites
- The sprite_locations.json contained incorrect/guessed offsets
- All locations produced garbage when extracted
- User's goal: "While VRAM extraction is easier and has worked so far, the goal is to make extraction from ROM work"

## Solution Implemented

### 1. Created Advanced ROM Scanner
- Developed `find_rom_sprites_advanced.py` that:
  - Uses HAL decompression (exhal tool) to test ROM offsets
  - Analyzes decompressed data for sprite-like qualities
  - Scores each location based on 4bpp tile validity
  - Found 140+ potential sprite locations in PAL ROM

### 2. Discovered Real Sprite Locations
Top verified sprite offsets in Kirby's Fun Pak (Europe).sfc:
- **0x200000** - Quality 1.00 - Perfect Kirby sprites (7744 bytes)
- **0x378000** - Quality 0.98 - Character sprites (3588 bytes)  
- **0x1D0002** - Quality 0.96 - More sprites (8192 bytes)
- **0x1C0000** - Quality 0.94 - Additional sprites (8192 bytes)

### 3. Updated Configuration
Replaced incorrect data in `sprite_locations.json` with verified offsets that decompress to actual sprite graphics.

## Verification
- Created test scripts that extract and visualize sprites
- All top-quality locations show real Kirby sprites
- HAL decompression works correctly at these offsets
- Sprites are valid 4bpp SNES format (32 bytes per 8x8 tile)

## Tools Researched
- Tile Molester - Visual ROM browser
- snes9x-rr with Lua scripting - Memory dumps
- vSNES - Sprite ripper
- YY-CHR - ROM graphics viewer

## Key Insights
1. HAL compression embeds sprites within larger data blocks
2. Quality scoring based on 4bpp patterns reliably identifies sprites
3. Sprites often start at round offsets (0x200000, 0x378000)
4. The exhal tool can extract these if given correct offsets

## Result
**ROM extraction now works!** SpritePal can extract real sprites from ROM instead of showing garbage pixels.
