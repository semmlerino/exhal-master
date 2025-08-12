# Mesen 2 Lua API Learnings - DO NOT DELETE

## Critical Discovery Date: 2025-08-12

This document captures hard-won knowledge about Mesen 2's Lua API discovered through systematic debugging. The official documentation was incomplete/misleading, requiring empirical testing to discover the actual API.

## Executive Summary

**Key Insight**: Mesen 2's Lua API uses SNES-specific enum names, not generic ones. Documentation may show generic names, but the actual implementation requires platform-specific names.

## The Journey: What Went Wrong

### Initial Attempts (All Failed)
```lua
-- WRONG - These enums don't exist:
emu.CallbackType.CpuWrite      -- ❌ nil
emu.memCallbackType.cpuWrite   -- ❌ nil  
emu.MemoryType.CpuMemory       -- ❌ nil
emu.memType.cpu                -- ❌ nil (exists but wrong for SNES)
emu.memType.oam                -- ❌ nil (not for SNES)
```

### The Diagnostic Process

Created diagnostic scripts to enumerate the actual API:
1. Listed all functions in `emu` namespace
2. Tested callbacks with strings, integers, and different parameter orders
3. Enumerated all enum tables to find actual values
4. Used pcall() to safely test different formats

### The Discovery

**Mesen 2 uses platform-specific enums!** For SNES development:
- Not `emu.memType.cpu` but `emu.memType.snesMemory`
- Not `emu.memType.oam` but `emu.memType.snesSpriteRam`
- Not `emu.memType.vram` but `emu.memType.snesVideoRam`

## Correct Mesen 2 Lua API Reference

### Memory Types (`emu.memType`)

| Purpose | Enum | Value | Usage |
|---------|------|-------|-------|
| CPU Memory | `emu.memType.snesMemory` | 0 | Main CPU address space |
| Program ROM | `emu.memType.snesPrgRom` | 14 | ROM data |
| Work RAM | `emu.memType.snesWorkRam` | 15 | System RAM |
| Video RAM | `emu.memType.snesVideoRam` | 17 | VRAM for tiles/tilemaps |
| Sprite RAM | `emu.memType.snesSpriteRam` | 18 | OAM (Object Attribute Memory) |
| Palette RAM | `emu.memType.snesCgRam` | 19 | Color palette data |
| Save RAM | `emu.memType.snesSaveRam` | 16 | Battery-backed SRAM |

### Event Types (`emu.eventType`)

| Event | Enum | Value |
|-------|------|-------|
| NMI | `emu.eventType.nmi` | 0 |
| IRQ | `emu.eventType.irq` | 1 |
| Start Frame | `emu.eventType.startFrame` | 2 |
| End Frame | `emu.eventType.endFrame` | 3 |
| Reset | `emu.eventType.reset` | 4 |
| Script Ended | `emu.eventType.scriptEnded` | 5 |
| Input Polled | `emu.eventType.inputPolled` | 6 |
| State Loaded | `emu.eventType.stateLoaded` | 7 |
| State Saved | `emu.eventType.stateSaved` | 8 |
| Code Break | `emu.eventType.codeBreak` | 9 |

### Callback Types (`emu.callbackType`) 

⚠️ **CRITICAL: The values are NOT what you'd expect!**

| Type | Enum | ACTUAL Value | Common Mistake |
|------|------|--------------|----------------|
| Read | `emu.callbackType.read` | 0 | ✅ Correct |
| Write | `emu.callbackType.write` | **1** | ❌ Often assumed to be 2 |
| Exec | `emu.callbackType.exec` | 2 | ❌ Often assumed to be 0 |

**What works:**
```lua
-- CORRECT - These work:
emu.addMemoryCallback(callback, emu.callbackType.write, 0x420B, 0x420B)  -- ✅ Best
emu.addMemoryCallback(callback, 1, 0x420B, 0x420B)  -- ✅ Works (write = 1)

-- WRONG - These DON'T work reliably:
emu.addMemoryCallback(callback, "write", 0x420B, 0x420B)  -- ❌ Accepted but doesn't fire!
emu.addMemoryCallback(callback, 2, 0x420B, 0x420B)  -- ❌ Wrong value (2 is exec!)
```

**Discovery:** String values like `"write"` are accepted without error but callbacks don't actually fire! Always use the enum or correct integer value.

## Working Code Patterns

### Memory Callbacks
```lua
-- CORRECT - Register a write callback
local callback_id = emu.addMemoryCallback(
    function(address, value)
        emu.log(string.format("Write: $%04X = $%02X", address, value))
    end,
    emu.callbackType.write,  -- Use enum (value 1) - NOT string "write"!
    0x420B,   -- start address
    0x420B    -- end address
)

-- Alternative using integer (but enum is clearer):
local callback_id = emu.addMemoryCallback(
    function(address, value)
        -- callback code
    end,
    1,        -- 1 = write (NOT 2!)
    0x420B,
    0x420B
)

-- Remove when done
emu.removeMemoryCallback(callback_id)
```

### Event Callbacks
```lua
-- CORRECT - Register frame callback
local frame_id = emu.addEventCallback(
    function()
        -- Called at end of frame
    end,
    emu.eventType.endFrame  -- or use integer 3
)

-- Remove when done
emu.removeEventCallback(frame_id)
```

### Memory Reads
```lua
-- CORRECT - Read from different memory types
local cpu_value = emu.read(0x420B, emu.memType.snesMemory)     -- CPU memory
local oam_byte = emu.read(0, emu.memType.snesSpriteRam)        -- OAM
local vram_word = emu.read(0x0000, emu.memType.snesVideoRam)   -- VRAM
local palette = emu.read(0, emu.memType.snesCgRam)             -- CGRAM

-- Read 16-bit value
local word = emu.readWord(0x2116, emu.memType.snesMemory)
```

### OAM (Sprite) Access
```lua
-- CORRECT - Read OAM/sprite data
local oam_data = {}
for i = 0, 543 do  -- 544 bytes total (512 sprite + 32 high table)
    oam_data[i] = emu.read(i, emu.memType.snesSpriteRam)
end
```

### VRAM Access
```lua
-- CORRECT - Read VRAM directly
local tile_data = emu.read(0x0000, emu.memType.snesVideoRam)
```

## Common Pitfalls and Solutions

### Pitfall 1: Using Generic Memory Types
```lua
-- WRONG
emu.read(addr, emu.memType.cpu)  -- This exists but wrong for SNES!

-- CORRECT
emu.read(addr, emu.memType.snesMemory)
```

### Pitfall 2: Wrong OAM Access Method
```lua
-- WRONG - Don't use PPU memory space
emu.read(0x2000 + i, emu.memType.ppu)

-- CORRECT - Use sprite RAM directly
emu.read(i, emu.memType.snesSpriteRam)
```

### Pitfall 3: Missing Required Parameters
```lua
-- WRONG - emu.read needs memory type
local value = emu.read(0x420B)  -- Error: too few parameters

-- CORRECT
local value = emu.read(0x420B, emu.memType.snesMemory)
```

### Pitfall 4: Wrong Callback Parameter Order
```lua
-- WRONG - Old parameter order from other emulators
emu.addMemoryCallback(0x420B, 0x420B, "write", callback)

-- CORRECT - Callback first, then type, then addresses
emu.addMemoryCallback(callback, "write", 0x420B, 0x420B)
```

## Diagnostic Script Template

When working with unknown emulator APIs, use this approach:

```lua
-- 1. Enumerate available functions
for k, v in pairs(emu) do
    if type(v) == "function" then
        emu.log("emu." .. k .. "()")
    elseif type(v) == "table" then
        emu.log("emu." .. k .. " = table")
        -- Enumerate table contents
        for k2, v2 in pairs(v) do
            emu.log("  ." .. k2 .. " = " .. tostring(v2))
        end
    end
end

-- 2. Test different parameter formats with pcall
local function safe_test(name, func)
    local success, result = pcall(func)
    emu.log(name .. ": " .. (success and "SUCCESS" or "FAILED"))
    return success, result
end

-- 3. Try different formats systematically
safe_test("String type", function()
    return emu.addMemoryCallback(callback, "write", 0x420B, 0x420B)
end)
safe_test("Integer type", function()
    return emu.addMemoryCallback(callback, 2, 0x420B, 0x420B)
end)
```

## Complete Working Example

```lua
-- Mesen 2 SNES DMA Monitor (Working)
local function monitor_dma()
    local callback_id = emu.addMemoryCallback(
        function(address, value)
            if value ~= 0 then
                emu.log(string.format("DMA triggered: $%02X", value))
                -- Read DMA parameters
                for ch = 0, 7 do
                    if (value & (1 << ch)) ~= 0 then
                        local base = 0x4300 + (ch * 0x10)
                        local dest = emu.read(base + 1, emu.memType.snesMemory)
                        emu.log(string.format("  Channel %d -> $21%02X", ch, dest))
                    end
                end
            end
        end,
        emu.callbackType.write,  -- or integer 1 (NOT 2!)
        0x420B,   -- DMA enable register
        0x420B
    )
    
    return callback_id
end

-- Start monitoring
local id = monitor_dma()
emu.log("DMA monitoring active, callback ID: " .. id)
```

## Other Platforms

Mesen 2 supports multiple systems. Each has its own memory type enums:
- NES: `emu.memType.nesMemory`, `emu.memType.nesPrgRom`, etc.
- Game Boy: `emu.memType.gameboyMemory`, `emu.memType.gbPrgRom`, etc.
- PC Engine: `emu.memType.pceMemory`, `emu.memType.pcePrgRom`, etc.

Always check which platform-specific enums are needed!

## Key Takeaways

1. **Always enumerate the actual API** - Don't trust documentation blindly
2. **Use platform-specific enums** - SNES uses `snes*` prefixes
3. **Both strings and integers work** for callback types
4. **Memory reads require type parameter** - No default
5. **Callback goes first** in parameter order
6. **Test with pcall()** to avoid crashes during development

## Critical Debugging Session: The Callback Type Value Bug

### The Problem
Script was detecting sprites but capturing 0 DMA transfers despite DMA clearly happening in the game.

### The Investigation
Created multiple diagnostic scripts to test all callback registration methods:
- `mesen2_dma_test_all_methods.lua` - Tested 5 different callback formats
- `mesen2_aggressive_dma_monitor.lua` - Monitored all DMA registers

### The Discovery
```
ENUM_WRITE: $420B = $01    ✅ Working (emu.callbackType.write)
INT_1: $420B = $01          ✅ Working (integer 1)
STRING_WRITE: (nothing)     ❌ Silent failure!
INT_2: (nothing)            ❌ Wrong value!
```

**The Bug:** We assumed `write = 2` based on common emulator patterns, but in Mesen 2:
- `emu.callbackType.write = 1` (not 2!)
- `emu.callbackType.exec = 2` (not 0!)
- String `"write"` is accepted but **callbacks never fire!**

### The Fix
Changed from:
```lua
emu.addMemoryCallback(callback, "write", ...)  -- ❌ Silent failure
emu.addMemoryCallback(callback, 2, ...)        -- ❌ Wrong value
```

To:
```lua
emu.addMemoryCallback(callback, emu.callbackType.write, ...)  -- ✅ Works!
emu.addMemoryCallback(callback, 1, ...)                        -- ✅ Works!
```

### Lesson Learned
**Always test enum values empirically!** What seems logical may not match the implementation.

## Files Created During Discovery

### Initial API Discovery
1. `mesen2_api_diagnostic.lua` - Comprehensive API enumeration
2. `mesen2_simple_test.lua` - Tests common patterns
3. `mesen2_minimal.lua` - Bare minimum test
4. `check_callback_type.lua` - Enum value checker

### Callback Type Debugging
5. `mesen2_dma_test_all_methods.lua` - Tests 5 callback registration methods
6. `mesen2_aggressive_dma_monitor.lua` - Aggressive DMA monitoring
7. `SPRITE_FINDER_USAGE_GUIDE.md` - Usage instructions

### Final Working Versions
8. `mesen2_sprite_finder_working.lua` - Initial "working" version (had wrong callback type!)
9. `mesen2_sprite_finder_CORRECTED.lua` - Actually working version with correct callback type

---

**Last Updated**: 2025-08-12
**Time Invested**: ~5 hours of debugging (3 hours API discovery + 2 hours callback bug)
**Pain Level**: 🔥🔥🔥🔥🔥 (5/5 - Silent failures with accepted parameters is maximum pain)
**Value**: 💎💎💎💎💎 (5/5 - Essential for any Mesen 2 Lua development)

## DO NOT DELETE THIS FILE
This knowledge was hard-won through systematic debugging. Future developers will need this information as the official documentation is incomplete or misleading regarding the actual API implementation.