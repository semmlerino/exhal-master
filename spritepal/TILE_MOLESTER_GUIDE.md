# Using Tile Molester for Kirby Super Star Sprite Viewing

## Overview
Tile Molester is a multi-platform tile graphics viewer/editor that can help visualize sprites in ROM files and memory dumps. This guide explains how to use it with Kirby Super Star.

## Setup

### 1. Download Tile Molester
- Original (v0.16): Available on RHDN
- **Recommended**: Tile Molester Mod v0.19 (fixes many issues)
- Requires Java to run

### 2. Key Settings for SNES Sprites
- **Codec**: 4bpp planar, composite (2x2bpp)
- **Mode**: 2-Dimensional
- **Block Size**: 8x8 (standard SNES tile size)

## Viewing Kirby Sprites

### Option 1: View VRAM Dumps (Recommended)
This is the cleanest way since VRAM contains decompressed sprites.

1. Open Tile Molester
2. File → Open → Select your VRAM dump (e.g., `vram_Kirby Super Star (USA)_2_VRAM.dmp`)
3. View → Codec → 4bpp planar, composite (2x2bpp)
4. Navigate to sprite offsets:
   - **0x4000**: Primary sprite area
   - **0x6000**: Secondary sprite area (often Kirby)
   - **0x8000**: Additional sprites
   - **0xC000**: More sprite data

### Option 2: View ROM Directly
More challenging due to HAL compression, but useful for finding compressed data.

1. Open your ROM file (`.sfc` or `.smc`)
2. View → Codec → 4bpp planar, composite (2x2bpp)
3. Use Page Down/Page Up to browse through ROM
4. Look for sprite patterns (they'll appear as recognizable graphics when you find them)

### Option 3: View Extracted Sprite Regions
Use the binary files we extracted earlier.

1. Open files like `vram_*_4000.bin` or `vram_*_6000.bin`
2. These contain specific sprite regions already isolated
3. Should immediately show sprite tiles

## Palette Setup

### Import CGRAM Palette Data
1. Palette → Import From → This File... (if viewing VRAM with CGRAM)
2. Or Palette → Import From → Another File... (to use separate CGRAM dump)
3. Settings for SNES palettes:
   - **Format**: 15bpp BGR (555)
   - **Byte Order**: Intel
   - **Size**: 512 bytes (256 colors)
   - **Offset**: 0 (for CGRAM dumps)

### Finding Palettes in ROM
- Palettes are often near graphics data
- Look for patterns of 512 bytes with BGR555 format
- Common locations: Before or after sprite data

## Navigation Tips

### Keyboard Shortcuts
- **Page Up/Down**: Move through file by one screen
- **+/-**: Increase/decrease columns
- **Shift + +/-**: Increase/decrease rows
- **Arrow keys**: Fine navigation

### Finding Sprites
1. Start at known good offsets (0x4000, 0x6000 for VRAM)
2. Look for organized tile patterns
3. Sprites often appear as:
   - Character parts (head, body, limbs)
   - Animation frames in sequence
   - Power-up variations

## Specific Kirby Locations

### From Our VRAM Analysis
- **Kirby sprites**: VRAM offset 0x6000 (shows at 0xC000 in byte addressing)
- **Beam Kirby**: Various poses and animations
- **Enemy sprites**: Scattered throughout 0x4000-0x8000

### Expected Patterns
- Kirby idle: Round body with simple face
- Kirby walking: Multiple frames showing movement
- Kirby inhaling: Expanded mouth frames
- Copy abilities: Hat variations on standard Kirby base

## Troubleshooting

### "Can't see sprites, only garbage"
1. Check codec is set to 4bpp planar
2. Try different offsets (use Page Down)
3. Adjust grid size (+ and - keys)
4. For ROM viewing, remember data is compressed

### "Colors look wrong"
1. Import correct palette (CGRAM dump)
2. Check palette offset
3. Try different palette slots (SNES has 16 palettes)

### "Sprites look scrambled"
1. Adjust block dimensions
2. Check if viewing compressed data (use VRAM dumps instead)
3. Try different starting offsets

## Integration with SpritePal

### Export from Tile Molester
1. Edit → Copy (to copy visible tiles)
2. Edit → Paste To → New Image
3. Save as PNG
4. Use with SpritePal for palette management

### Use Tile Molester for Discovery
1. Find sprites in ROM/VRAM with Tile Molester
2. Note the offsets
3. Use those offsets in SpritePal for extraction
4. SpritePal handles proper palette assignment

## Advanced Tips

### Creating Sprite Sheets
1. Navigate to sprite location
2. Adjust grid to show all frames
3. Edit → Select All
4. Edit → Copy
5. Paste into image editor
6. Save as reference sheet

### Comparing ROM Versions
1. Open multiple instances of Tile Molester
2. Load different ROM versions
3. Navigate to same offset
4. Compare sprite differences

### Finding Compressed Sprites in ROM
1. Compressed data looks like noise/static
2. Use exhal to decompress suspected areas
3. View decompressed data in Tile Molester
4. If sprites appear, you found a compressed block

## Example Workflow

1. **Quick Sprite Viewing**:
   ```
   Open vram_Kirby Super Star (USA)_2_VRAM.dmp
   Set codec to 4bpp planar
   Jump to offset 0x6000
   Import CGRAM for colors
   ```

2. **Finding New Sprites**:
   ```
   Open ROM file
   Set codec to 4bpp planar
   Browse with Page Down
   When you see sprite patterns, note offset
   Extract with exhal if compressed
   ```

3. **Creating Reference Sheets**:
   ```
   Load VRAM dump
   Navigate to sprite area
   Adjust grid to frame sprites nicely
   Copy all tiles
   Paste to new image
   Save as PNG
   ```

## Conclusion

Tile Molester is excellent for:
- Quick sprite viewing without coding
- Finding sprite locations in ROM/VRAM
- Understanding sprite organization
- Creating visual references

Use it alongside SpritePal for a complete sprite extraction workflow!