# LEARNINGS - DO NOT DELETE

## Mesen2 Sprite Offset Discovery Project
*Critical technical learnings from connecting visible sprites to ROM offsets*

---

## 1. Mesen2 Lua API Critical Discoveries

### 1.1 Platform-Specific Enums (CRITICAL)
```lua
-- WRONG - Generic enums don't work
emu.read(address, emu.memType.cpuMemory)  -- FAILS
emu.addMemoryCallback(func, emu.callbackType.cpuWrite, ...)  -- FAILS

-- CORRECT - Use SNES-specific enums
emu.read(address, emu.memType.snesMemory)  -- WORKS
emu.addMemoryCallback(func, emu.callbackType.write, ...)  -- WORKS
```

### 1.2 Savestate Loading MUST Use Exec Callback (CRITICAL)
**This is the most important discovery - emu.loadSavestate() can ONLY be called from exec callbacks!**

```lua
-- WRONG - Will silently fail or crash
emu.addEventCallback(function()
    emu.loadSavestate(state_bytes)  -- DOES NOT WORK
end, emu.eventType.startFrame)

-- CORRECT - Must use exec callback
local load_ref
load_ref = emu.addMemoryCallback(function(address, value)
    if not state_loaded then
        state_loaded = true
        emu.loadSavestate(state_bytes)  -- WORKS!
        emu.removeMemoryCallback(load_ref, emu.callbackType.exec, 0x8000, 0xFFFF)
    end
end, emu.callbackType.exec, 0x8000, 0xFFFF)  -- Monitor ROM execution range
```

### 1.3 Command Line Behavior
- `--testrunner script.lua` runs headless, exits when script calls emu.stop()
- `--loadstate file.mss` loads savestate BEFORE script execution
- Scripts can load savestates internally using exec callbacks (see above)

---

## 2. Savestate Format (MSS Files)

### 2.1 File Structure
```
Offset 0x00-0x02: "MSS" header (3 bytes)
Offset 0x03: Version byte (usually 0x01)
Offset 0x04-0x22: Header/metadata (exact structure unknown)
Offset 0x23: Start of zlib compressed data (look for 0x78 byte)
```

### 2.2 Decompression Code
```python
def decompress_savestate(path):
    with open(path, 'rb') as f:
        data = f.read()
    
    # Find zlib start (usually at offset 35/0x23)
    zlib_start = None
    for i in range(4, min(100, len(data))):
        if data[i] == 0x78 and data[i+1] in [0x01, 0x5E, 0x9C, 0xDA]:
            zlib_start = i
            break
    
    # Decompress
    decompressed = zlib.decompress(data[zlib_start:])
    return decompressed
```

### 2.3 VRAM Location in Savestate
- VRAM data found at offset 0x6A00 in decompressed savestate
- 64KB total VRAM size in SNES
- Target mushroom sprite at VRAM $6A00-$6A80

---

## 3. Address Translation Formula

### 3.1 Mesen2 Runtime to ROM Offset
```
ROM Offset = Mesen2 Address - 0x300000
```

Examples:
- Mesen2 $3D2238 → ROM $0D2238
- Mesen2 $57D800 → ROM $27D800
- Mesen2 $580000 → ROM $280000

### 3.2 Validation Method
Used exhal tool to confirm sprites exist at calculated ROM offsets

---

## 4. DMA Monitoring Challenges

### 4.1 VRAM Address Reading Issue
**Problem**: Reading VRAM address from $2116/$2117 during DMA always returned $0000

```lua
-- This approach FAILED - always got VRAM $0000
function on_dma_enable_write(address, value)
    local vram_addr_low = emu.read(0x2116, emu.memType.snesMemory)
    local vram_addr_high = emu.read(0x2117, emu.memType.snesMemory)
    local vram_addr = (vram_addr_low | (vram_addr_high << 8)) * 2
    -- vram_addr was always 0!
end
```

### 4.2 Possible Reasons
1. VRAM address registers cleared after DMA
2. Timing issue - need to read before DMA executes
3. DMA might use different addressing mechanism

---

## 5. Mushroom Sprite Findings

### 5.1 Location Confirmed
- **VRAM Address**: $6A00-$6A80
- **Sprite Size**: 16x16 pixels
- **Tile Index**: $A0
- **Palette**: 3

### 5.2 Savestate Comparison Results
```
Before.mss (no mushroom) vs Sprite.mss (mushroom visible):
- 120 bytes differ at VRAM $6A00
- Pattern found: 87 7E 87 7E... (repeating)
- This appears to be fill/initialization data, not actual sprite graphics
```

### 5.3 ROM Search Results
- Searched for 87 7E pattern - not found as graphics data
- Found potential compressed sprite at ROM $3033C4 (131 bytes)
- When extracted with exhal, doesn't match mushroom appearance

---

## 6. Working Code Patterns

### 6.1 Successful Savestate Loading in Lua
```lua
-- Read savestate file
local f = io.open(SAVESTATE_PATH, "rb")
local state_bytes = f:read("*a")
f:close()

-- Load from exec callback
local load_ref
load_ref = emu.addMemoryCallback(function(address, value)
    if not state_loaded then
        state_loaded = true
        emu.loadSavestate(state_bytes)
        emu.removeMemoryCallback(load_ref, emu.callbackType.exec, 0x8000, 0xFFFF)
    end
end, emu.callbackType.exec, 0x8000, 0xFFFF)
```

### 6.2 Successful Sprite Extraction
```bash
# Using exhal tool (path may vary)
./archive/obsolete_test_images/ultrathink/exhal "Kirby Super Star (USA).sfc" 0x280000 sprite.bin
```

### 6.3 Sprite Visualization (4bpp SNES format)
```python
def decode_4bpp_tile(tile_data):
    # Each tile is 8x8 pixels, 32 bytes
    pixels = []
    for y in range(8):
        row_offset = y * 2
        byte1 = tile_data[row_offset]
        byte2 = tile_data[row_offset + 1]
        byte3 = tile_data[row_offset + 16]
        byte4 = tile_data[row_offset + 17]
        
        for x in range(8):
            bit = 7 - x
            pixel = ((byte1 >> bit) & 1) | \
                    (((byte2 >> bit) & 1) << 1) | \
                    (((byte3 >> bit) & 1) << 2) | \
                    (((byte4 >> bit) & 1) << 3)
            pixels.append(pixel)
    return pixels
```

---

## 7. Key Files Created

1. **Lua Scripts**:
   - `mushroom_entering_monitor.lua` - Monitors room transition for sprite loading
   - `mushroom_monitor_sprite_state.lua` - Monitors sprite when already visible
   - `vram_write_monitor.lua` - Direct VRAM write monitoring

2. **Python Scripts**:
   - `find_mushroom_in_savestate.py` - Compares savestates to find sprite data
   - `search_rom_for_mushroom.py` - Searches ROM for sprite patterns
   - `visualize_sprite.py` - Converts binary to PNG

3. **Data Files**:
   - `mushroom_sprite_candidate_006A00.bin` - Extracted VRAM data
   - Savestates: `Before.mss`, `Entering.mss`, `Sprite.mss`

---

## 8. Unresolved Challenges

### 8.1 Sprite Loading Mechanism
- The 87 7E pattern suggests we're seeing initialized/cleared VRAM, not the actual sprite
- Need to catch the exact moment when real sprite data is written
- Sprite might be cached elsewhere and copied during screen refresh

### 8.2 DMA Monitoring
- Cannot reliably read VRAM destination address during DMA
- Need alternative approach to track sprite transfers

### 8.3 Compression
- Mushroom sprite likely HAL compressed in ROM
- Need to identify correct compression markers and offsets

---

## 9. Next Steps Recommendations

1. **Try Different Savestate Timing**:
   - Create savestate during sprite animation frame
   - Capture at different points in room transition

2. **Monitor Different Memory Regions**:
   - WRAM where sprites might be cached
   - OAM (Object Attribute Memory) for sprite metadata

3. **Pattern Matching Approach**:
   - Extract actual mushroom pixels from screenshot
   - Search ROM for those specific patterns
   - Consider different compression methods

4. **Manual Analysis**:
   - Use Mesen2 debugger GUI to manually trace sprite loading
   - Set breakpoints on VRAM writes to $6A00

5. **Alternative Extraction**:
   - Try extracting all potential sprites in $300000-$310000 range
   - Visually compare to find mushroom

---

## 10. Critical Insights

1. **The Bridge Problem**: User correctly identified the core issue - "focusing too much on cataloging, and not enough on the bridge between sprite you can see and rom position"

2. **Savestate Approach Works**: Comparing savestates successfully identified where sprite should be in VRAM

3. **Timing is Everything**: Sprite loading happens at specific moments (room transitions, spawn events) - must catch exact timing

4. **Tool Limitations**: Mesen2 Lua API has specific requirements (exec callbacks for savestate loading) not documented publicly

5. **Address Translation Works**: The Mesen2 - 0x300000 formula successfully maps runtime addresses to ROM offsets

---

*Last Updated: Session ending after discovering mushroom sprite location at VRAM $6A00 with 87 7E fill pattern*

**DO NOT DELETE - This document contains critical technical discoveries essential for the sprite discovery workflow**