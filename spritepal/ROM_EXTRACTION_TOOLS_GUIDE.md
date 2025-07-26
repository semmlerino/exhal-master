# ROM Extraction Tools & Solutions Guide

## Overview
This guide documents various tools and approaches to fix ROM sprite extraction for SpritePal, focusing on finding correct sprite locations in compressed ROM data.

## Problem Summary
- SpritePal's ROM extraction shows "pixely grey colours" instead of sprites
- Sprite locations in sprite_locations.json are incorrect/guessed
- HAL compression mixes sprites with other data
- Need to find actual sprite offsets in ROM

## Tool Options

### 1. Snes9x-rr with Lua Scripting
**Purpose**: Programmatic memory dumping and sprite location discovery

**Features**:
- Lua API with memory access functions
- Can dump specific memory regions
- Scriptable for automation
- Command-line support (Linux)

**Setup**:
```bash
# Linux command line
snes9x "Kirby Super Star (USA).sfc" -loadlua dump_sprites.lua

# Example Lua script
memory.writefile("vram_dump.bin", 0x7E0000, 0x10000)  -- Dump VRAM
memory.writefile("cgram_dump.bin", 0x7E2100, 0x200)   -- Dump CGRAM
```

**Advantages**:
- Automated memory dumping
- Can trigger at specific game states
- Scriptable pattern searching

### 2. vSNES (Visual SNES)
**Purpose**: Established sprite ripper with visual interface

**Features**:
- SceneViewer shows all sprites/backgrounds
- Isolates individual sprites
- Works with ZSNES savestates
- Visual sprite identification

**Workflow**:
1. Create ZSNES savestate at desired game moment
2. Open in vSNES SceneViewer
3. Identify sprite tiles and their arrangements
4. Note tile numbers and positions
5. Cross-reference with ROM data

**Note**: Requires older ZSNES versions (pre-2007)

### 3. YY-CHR
**Purpose**: ROM graphics viewer with palette support

**Features**:
- Direct ROM viewing
- Savestate palette import
- Multiple format support
- Tile arrangement visualization

**Usage for Kirby**:
1. Open Kirby ROM in YY-CHR
2. Load savestate for correct palettes
3. Browse ROM to find sprite patterns
4. Note offsets where sprites appear
5. Test if those offsets decompress correctly

### 4. SPEZ (SNES Sprite Editor)
**Purpose**: Modern SNES sprite editor

**GitHub**: https://github.com/nesdoug/SPEZ

**Features**:
- YY-CHR palette compatibility
- 4bpp sprite support
- Modern interface

### 5. Command-Line Memory Dumping

#### Using bsnes-plus
```bash
# While bsnes-plus is GUI-based, it can:
# - Save memory usage tables to disk
# - Log trace data for analysis
# - Export memory regions
```

#### Using Mesen-S
- Memory viewer with export functionality
- Sprite viewer tool
- Debug logging capabilities

## Proposed Solution Workflow

### Step 1: Create Reference VRAM Dumps
```lua
-- snes9x-rr Lua script: dump_at_sprite_test.lua
function dump_memory()
    -- Wait for sprite test mode or specific scene
    if memory.readbyte(0x7E0100) == 0x07 then  -- Example condition
        memory.writefile("vram_sprite_test.bin", 0x7E0000, 0x10000)
        memory.writefile("cgram_sprite_test.bin", 0x7E2100, 0x200)
        print("Dumped memory at sprite test mode")
    end
end

memory.registerexec(0x00740B, dump_memory)  -- Hook sprite test routine
```

### Step 2: Find Sprites in ROM with YY-CHR
1. Open PAL ROM in YY-CHR
2. Set to 4bpp SNES format
3. Scroll through ROM looking for sprite patterns
4. When found, note the offset
5. Check if HAL compressed at that location

### Step 3: Cross-Reference with vSNES
1. Create ZSNES savestates at key moments
2. Use vSNES to identify exact sprite tiles
3. Note tile arrangements and sizes
4. Search ROM for these patterns

### Step 4: Automated Pattern Search
```python
# Python script to search ROM using multiple methods
def search_with_patterns():
    # 1. Load VRAM dumps from various tools
    vram_snes9x = load_dump("vram_sprite_test.bin")
    vram_vsnes = load_vsnes_export("sprites.dat")
    
    # 2. Extract sprite patterns
    patterns = extract_unique_patterns(vram_snes9x, vram_vsnes)
    
    # 3. Search ROM for compressed versions
    for offset in range(0, rom_size, 1):
        decompressed = decompress_hal(rom_data, offset)
        if matches_patterns(decompressed, patterns):
            print(f"Found sprites at 0x{offset:06X}")
```

### Step 5: Update SpritePal Configuration
```json
{
  "sprites": [
    {
      "name": "Kirby_Normal",
      "offset": "0xC8000",  // Found via YY-CHR
      "expected_size": 8192,
      "notes": "Verified with vSNES, matches VRAM 0x6000"
    },
    {
      "name": "Beam_Kirby",
      "offset": "0xCA000",  // Found via pattern search
      "expected_size": 8192,
      "embedded_offset": 512  // Sprite starts 512 bytes into block
    }
  ]
}
```

## Quick Test Commands

### Test with Real Tools
```bash
# 1. Use YY-CHR to find sprite offsets visually
# 2. Test extraction with found offset
./exhal "Kirby's Fun Pak (Europe).sfc" 0xC8000 test_sprite.bin

# 3. Visualize with Tile Molester
java -jar TileMolester.jar test_sprite.bin
# Set to 4bpp planar, 8x8 tiles

# 4. If successful, update sprite_locations.json
```

### Verify with SpritePal
```python
# Test extraction with new offsets
python launch_spritepal.py
# 1. Load PAL ROM
# 2. Go to ROM Extraction tab
# 3. Select newly added sprite
# 4. Preview should show correct sprite
```

## Tool Download Links
- **snes9x-rr**: GitHub releases or TASVideos
- **vSNES**: ROMhacking.net utilities
- **YY-CHR**: https://www.romhacking.net/utilities/119/
- **ZSNES** (for vSNES): Old versions archive
- **SPEZ**: https://github.com/nesdoug/SPEZ
- **Tile Molester**: https://github.com/toruzz/TileMolester

## Expected Outcomes
1. Find correct sprite offsets in PAL ROM
2. Update sprite_locations.json with verified data
3. ROM extraction in SpritePal works properly
4. No more "pixely grey colours"

## Next Steps
1. Download and test these tools
2. Create Lua scripts for automated dumping
3. Use visual tools to find sprite patterns
4. Update configuration with findings
5. Verify ROM extraction works