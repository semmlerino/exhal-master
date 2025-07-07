# Kirby Super Star Sprite Extraction Notes

## Summary
We successfully found and extracted Kirby sprites from Kirby Super Star (SNES) using a combination of ROM analysis, compression tools, and memory dumps from Mesen-S emulator.

## Key Discoveries

### 1. ROM Structure
- **ROM Size**: 4,194,304 bytes (4MB), LoROM format
- **Compression**: HAL Laboratory's proprietary compression (LZ2/LZ3 variant)
- **Decompression Routine**: JSL $00889A
- **Master Sprite Pointer Table**: Located at ROM offset 0x3F0002 (SNES $FF:0002)

### 2. Sprite Data Locations
- **Sprite Banks**: $9C-$B7 and $C0-$DE (as documented)
- **Default Kirby sprites**: Supposedly at PC 0x26B400, but we found different data there
- **Sprite indices**: Each room loads 4 sprite sheets using indices that point to the master table

### 3. Where We Actually Found Kirby
- **VRAM Location**: $6000 (word address) = 0xC000 (byte address)
- **Sprite Index**: 9 (shown in Mesen-S sprite viewer)
- **Tile Numbers**: $00, $02, $03, etc.
- **Successfully extracted from**: VRAM.dmp (Video RAM dump from Mesen-S)

### 4. Tools Used
- **exhal**: Decompresses HAL compressed data from ROM
- **inhal**: Recompresses data for insertion back into ROM
- **snes_tiles_to_png.py**: Converts raw SNES tile data to PNG
- **extract_exact_palette.py**: Applies Kirby's color palette
- **view_sprites_zoomed.py**: Creates zoomed versions for easier viewing
- **Mesen-S**: Emulator with debugging features

### 5. Files Created
- **kirby_full_colored.png**: All Kirby animation frames with correct colors
- **kirby_full_colored_x4.png**: 4x zoomed version for editing
- **VRAM.dmp**: 64KB dump of Video RAM containing decompressed sprites
- **SnesPrgRom.dmp**: Full ROM dump for analysis

### 6. Kirby Sprite Details
- **Format**: 4bpp (16 colors)
- **Tile Size**: 8x8 pixels per tile
- **Character Size**: Typically 2x2 or 3x3 tiles (16x16 or 24x24 pixels)
- **Animations Found**: Standing, walking, running, inhaling, jumping

### 7. Color Palette (Kirby)
```python
kirby_colors = [
    (0, 0, 0),        # 0: Transparent/black
    (248, 224, 248),  # 1: Light pink (highlight)
    (248, 184, 232),  # 2: Pink (main body)
    (248, 144, 200),  # 3: Medium pink
    (240, 96, 152),   # 4: Dark pink (shadow)
    (192, 48, 104),   # 5: Deep pink/red (outline)
    (248, 248, 248),  # 6: White (eyes)
    (216, 216, 216),  # 7: Light gray
    (168, 168, 168),  # 8: Gray
    (120, 120, 120),  # 9: Dark gray
    (248, 144, 144),  # A: Light red/pink (cheeks)
    (248, 80, 80),    # B: Red (feet)
    (216, 0, 0),      # C: Dark red
    (144, 0, 0),      # D: Deep red
    (80, 0, 0),       # E: Very dark red
    (40, 0, 0),       # F: Black-red
]
```

## Workflow for Sprite Editing

### Extraction (Completed)
1. Dump VRAM from emulator when Kirby is on screen
2. Extract bytes from VRAM offset 0xC000 (Kirby's location)
3. Convert to PNG using snes_tiles_to_png.py
4. Apply color palette

### Editing
1. Open kirby_full_colored.png in image editor
2. Keep dimensions: 64 pixels wide (8 tiles)
3. Use only the existing 16 colors in the palette
4. Save as indexed color PNG

### Reinsertion (To Do)
1. Convert edited PNG back to SNES 4bpp format
2. Find the compressed source in ROM (using sprite index 9's pointers)
3. Compress with inhal tool
4. Insert back into ROM at the correct offset

## Challenges Encountered
1. **Compressed vs Decompressed**: ROM contains compressed sprites, but we needed the decompressed versions from VRAM
2. **Address Mapping**: SNES addresses don't directly map to file offsets
3. **Palette Application**: Needed to determine correct colors for Kirby
4. **Sprite Organization**: Sprites are stored as individual tiles that need to be arranged properly

## Additional Findings from Memory Dumps

### CGRAM (Palette) Analysis
- CGRAM.dmp contains 16 palettes of 16 colors each (512 bytes total)
- Palette format: BGR555 (5 bits per color channel)
- Current CGRAM state shows:
  - Palette 0: White/Yellow/Black (possibly UI or effects)
  - Palette 12: Pink tones (closest to Kirby colors but not exact)
  - Palettes 4-7: Various enemy/environment colors
  
### OAM (Sprite) Analysis
- OAM.dmp shows active sprite positions and attributes (544 bytes)
- Confirms Kirby uses sprite index 9 with tile $00 at VRAM $6000

### Save State
- File: Kirby Super Star (USA)_1.mss (197,618 bytes)
- Contains complete game state including decompressed sprites

### Character Locations Found
- **Kirby**: VRAM $6000 (confirmed, full animation set)
- **Other sprites**: VRAM $6800+ (level elements, effects)
- Note: The CGRAM dump appears to be from a different game moment than when Kirby's pink palette is loaded

## Next Steps
1. Find where sprite index 9 points to in the ROM (the compressed source)
2. Create PNG to SNES tile converter for edited sprites
3. Test the complete edit-and-reinsert workflow
4. Extract more characters when proper palettes are available
5. Document the sprite index table for all characters
6. Get CGRAM dump when Kirby is on screen for accurate colors

## Useful Memory Addresses
- ROM Sprite Pointer Table: 0x3F0002
- Kirby in VRAM: $6000.w (0xC000 bytes)
- Decompression routine: JSL $00889A

## Commands for Quick Reference
```bash
# Extract Kirby from VRAM dump
dd if=VRAM.dmp of=kirby_tiles.bin bs=1 skip=$((0x6000 * 2)) count=$((64 * 32))

# Convert to PNG
python3 snes_tiles_to_png.py kirby_tiles.bin kirby.png 8

# Apply colors
python3 extract_exact_palette.py kirby.png kirby_colored.png

# Zoom for editing
python3 view_sprites_zoomed.py kirby_colored.png 4
```

## Credits
- HAL Laboratory compression tools (exhal/inhal) by Devin Acker
- ROM documentation from SuperFamicom Dev Wiki
- Sprite viewer screenshots and memory dumps from Mesen-S emulator