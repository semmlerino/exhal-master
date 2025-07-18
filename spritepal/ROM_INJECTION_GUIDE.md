# ROM Injection Guide

This guide explains how to use SpritePal's new ROM injection feature to directly patch edited sprites into SNES ROM files.

## Overview

ROM injection allows you to:
- Inject edited sprites directly into ROM files (not just VRAM dumps)
- Automatically compress sprites using HAL compression
- Update ROM checksums automatically
- Select from known sprite locations or specify custom offsets

## Requirements

1. HAL compression tools (exhal/inhal) must be available
   - These are included in `archive/obsolete_test_images/ultrathink/`
   - Or build from source using `make` in the project root

2. A compatible SNES ROM file (tested with Kirby Super Star)

## Usage

### 1. Extract Sprites First

Use SpritePal's normal extraction workflow:
1. Load VRAM, CGRAM, and OAM dumps
2. Extract sprites to PNG format
3. Edit sprites in the pixel editor

### 2. Open Injection Dialog

Click "Inject" button and switch to the "ROM Injection" tab.

### 3. Configure ROM Injection

1. **Sprite File**: Already populated with your edited sprite PNG

2. **Input ROM**: Select the original ROM file to patch
   - Supports .sfc and .smc formats
   - SMC headers are automatically detected

3. **Output ROM**: Choose where to save the patched ROM
   - Auto-suggested based on input ROM name

4. **Sprite Location**: 
   - For Kirby Super Star, known locations are auto-populated
   - Select from dropdown or enter custom hex offset
   - Known locations include:
     - Kirby Normal (0x0C8000)
     - Kirby Beam (0x0C8800)
     - Enemies Set 1 (0x0D0000)

5. **Compression Options**:
   - Normal: Smaller file size, slower compression
   - Fast: Larger file size, faster compression
   - Use fast mode if normal compression exceeds original size

### 4. Inject Sprites

Click OK to start the injection process:
1. Sprite PNG is converted to SNES 4bpp format
2. Data is compressed using HAL compression
3. Compressed data is injected at specified offset
4. ROM checksum is recalculated and updated
5. Modified ROM is saved to output path

## Technical Details

### HAL Compression

- Uses the same compression format as original Kirby games
- Maximum uncompressed size: 64KB
- Supports multiple compression methods:
  - RLE (8-bit, 16-bit, sequence)
  - LZ77-style back references (normal, rotated, reversed)

### ROM Structure

- Automatically detects and handles SMC headers (512 bytes)
- Reads SNES ROM header at 0x7FC0 or 0xFFC0
- Updates checksum and complement fields

### Sprite Locations

The ROM injector includes a database of known sprite locations for Kirby Super Star. These can be extended by modifying `KIRBY_SPRITE_POINTERS` in `rom_injector.py`.

### Error Handling

- Validates sprite dimensions (must be multiples of 8)
- Checks color count (max 16 for 4bpp)
- Ensures compressed data fits in original space
- Verifies ROM header and checksum

## Troubleshooting

### "HAL compression tools not found"
- Ensure exhal/inhal are in the archive directory or system PATH
- Build tools using `make` if needed

### "Compressed sprite too large"
- Enable fast compression mode
- Reduce sprite complexity or colors
- Check that sprite dimensions match original

### "Invalid ROM header"
- Ensure ROM is uncompressed (not zipped)
- Verify ROM is a valid SNES ROM
- Check for corrupted file

## Example Workflow

```python
# Example: Inject edited Kirby sprite into ROM

1. Extract original sprites:
   - Load Cave.SnesVideoRam.dmp
   - Load Cave.SnesCgRam.dmp
   - Extract sprites → kirby_sprites.png

2. Edit in pixel editor:
   - Open kirby_sprites.png
   - Make changes
   - Save

3. Inject to ROM:
   - Open injection dialog
   - Switch to ROM Injection tab
   - Input ROM: "Kirby Super Star (USA).sfc"
   - Output ROM: "Kirby Super Star (USA)_modified.sfc"
   - Select "Kirby Normal" from dropdown
   - Click OK

4. Test in emulator:
   - Load modified ROM
   - Verify sprite changes appear in-game
```

## Safety Notes

- Always work with ROM backups
- The tool creates a new ROM file, never modifies the original
- Test modified ROMs thoroughly before distribution
- Respect copyright laws when sharing modified ROMs