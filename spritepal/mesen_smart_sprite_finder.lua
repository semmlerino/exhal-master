-- ===============================================================================
-- Smart Sprite Finder for Mesen-S - Multi-Strategy Automated Approach
-- Finds ROM offsets automatically using pattern matching and multiple methods
-- ===============================================================================
-- This script uses multiple strategies to find sprite ROM offsets:
-- 1. VRAM pattern matching against ROM
-- 2. Memory change tracking
-- 3. Visual sprite selection
-- 4. API function attempts (getPrgRomOffset)
-- ===============================================================================

local state = {
    -- Core state
    enabled = true,
    frame = 0,
    captures = {},
    message = "Smart Sprite Finder Ready",
    message_timer = 0,
    
    -- VRAM tracking
    vram_snapshot = {},
    vram_changes = {},
    
    -- Pattern matching
    pattern_matches = {},
    search_active = false,
    search_progress = 0,
    
    -- Input
    last_keys = {},
    mouse_x = 128,
    mouse_y = 128,
    
    -- ROM data cache
    rom_cache = nil,
    rom_size = 0
}

-- ===============================================================================
-- Memory Reading with Multiple Fallbacks
-- ===============================================================================

function safe_read(address, mem_type)
    -- Try different memory type formats
    local attempts = {
        function() return emu.read(address, mem_type) end,
        function() return emu.read(address) end,
        function() return emu.readByte and emu.readByte(address, mem_type) end,
        function() return emu.readByte and emu.readByte(address) end,
    }
    
    for _, attempt in ipairs(attempts) do
        local success, value = pcall(attempt)
        if success and value then
            return value
        end
    end
    
    return 0
end

function read_vram(address)
    -- Try different VRAM access methods
    local value = safe_read(0x2139, "cpu")  -- VRAM read register
    if value == 0 then
        value = safe_read(address, "vram")
    end
    if value == 0 then
        value = safe_read(address, "ppu")
    end
    return value
end

function read_rom(offset)
    -- Try different ROM access methods
    local value = safe_read(offset, "prgRom")
    if value == 0 then
        value = safe_read(offset, "rom")
    end
    if value == 0 then
        value = safe_read(offset, "prg")
    end
    return value
end

-- ===============================================================================
-- VRAM Change Detection
-- ===============================================================================

function track_vram_changes()
    -- Monitor common sprite VRAM areas
    local sprite_vram_start = 0x4000  -- Common sprite tile area
    local sprite_vram_end = 0x7FFF
    local sample_size = 32  -- Check every 32 bytes (one 4bpp tile)
    
    local changes = {}
    
    for addr = sprite_vram_start, sprite_vram_end, sample_size do
        -- Read current tile data
        local tile_data = {}
        for i = 0, sample_size - 1 do
            tile_data[i] = read_vram(addr + i)
        end
        
        -- Compare with previous snapshot
        if state.vram_snapshot[addr] then
            local changed = false
            for i = 0, sample_size - 1 do
                if tile_data[i] ~= state.vram_snapshot[addr][i] then
                    changed = true
                    break
                end
            end
            
            if changed then
                -- VRAM changed, this might be a new sprite load
                table.insert(changes, {
                    vram_addr = addr,
                    data = tile_data,
                    frame = state.frame
                })
            end
        end
        
        -- Update snapshot
        state.vram_snapshot[addr] = tile_data
    end
    
    return changes
end

-- ===============================================================================
-- Pattern Matching: Find VRAM Data in ROM
-- ===============================================================================

function find_pattern_in_rom(pattern_data, pattern_size)
    -- Cache ROM if not already done
    if not state.rom_cache then
        cache_rom_data()
    end
    
    local matches = {}
    
    -- Search through ROM for pattern
    -- Use larger steps for speed
    for offset = 0, state.rom_size - pattern_size, 16 do
        local match = true
        
        -- Check if pattern matches
        for i = 0, pattern_size - 1 do
            if state.rom_cache[offset + i] ~= pattern_data[i] then
                match = false
                break
            end
        end
        
        if match then
            -- Found a match!
            table.insert(matches, {
                rom_offset = offset,
                rom_offset_hex = string.format("0x%06X", offset),
                confidence = 100
            })
            
            -- Limit matches to prevent slowdown
            if #matches >= 10 then
                break
            end
        end
    end
    
    return matches
end

function cache_rom_data()
    -- Cache ROM data for faster searching
    state.rom_cache = {}
    
    -- Try to determine ROM size (max 4MB for SNES)
    local max_size = 4 * 1024 * 1024
    
    -- Sample ROM to find actual size
    for offset = 0, max_size, 0x10000 do
        local value = read_rom(offset)
        if value ~= 0xFF and value ~= 0 then
            state.rom_size = offset + 0x10000
        end
    end
    
    -- Cache ROM data
    for offset = 0, state.rom_size - 1 do
        state.rom_cache[offset] = read_rom(offset)
    end
    
    emu.log("ROM cached: " .. state.rom_size .. " bytes")
end

-- ===============================================================================
-- Automated Sprite Finding
-- ===============================================================================

function auto_find_sprites()
    -- Track VRAM changes
    local changes = track_vram_changes()
    
    if #changes > 0 then
        state.message = "VRAM changes detected: " .. #changes
        state.message_timer = 60
        
        -- Search for patterns in ROM
        for _, change in ipairs(changes) do
            local matches = find_pattern_in_rom(change.data, 32)
            
            if #matches > 0 then
                -- Found potential sprite source!
                for _, match in ipairs(matches) do
                    -- Check if already captured
                    local already_captured = false
                    for _, cap in ipairs(state.captures) do
                        if cap.rom_offset == match.rom_offset then
                            already_captured = true
                            break
                        end
                    end
                    
                    if not already_captured then
                        table.insert(state.captures, {
                            rom_offset = match.rom_offset,
                            rom_offset_hex = match.rom_offset_hex,
                            vram_addr = change.vram_addr,
                            vram_hex = string.format("$%04X", change.vram_addr),
                            frame = state.frame,
                            auto = true
                        })
                        
                        emu.log("AUTO FOUND: VRAM " .. string.format("$%04X", change.vram_addr) .. 
                               " -> ROM " .. match.rom_offset_hex)
                    end
                end
            end
        end
    end
end

-- ===============================================================================
-- Try API Functions
-- ===============================================================================

function try_api_functions()
    -- Try getPrgRomOffset if it exists
    local success, offset = pcall(function()
        return emu.getPrgRomOffset and emu.getPrgRomOffset(0x8000) or nil
    end)
    
    if success and offset then
        emu.log("getPrgRomOffset API available!")
        return offset
    end
    
    return nil
end

-- ===============================================================================
-- Visual Sprite Picker
-- ===============================================================================

function get_sprite_at_position(x, y)
    -- Read OAM to find sprite at position
    for i = 0, 127 do
        local oam_base = i * 4
        
        -- Read sprite position (simplified)
        local spr_x = safe_read(oam_base, "oam")
        local spr_y = safe_read(oam_base + 1, "oam")
        
        -- Check if position matches (with tolerance)
        if math.abs(x - spr_x) < 16 and math.abs(y - spr_y) < 16 then
            -- Found sprite at position
            local tile = safe_read(oam_base + 2, "oam")
            local attr = safe_read(oam_base + 3, "oam")
            
            return {
                index = i,
                x = spr_x,
                y = spr_y,
                tile = tile,
                attr = attr
            }
        end
    end
    
    return nil
end

-- ===============================================================================
-- Drawing UI
-- ===============================================================================

function draw_ui()
    if not state.enabled then return end
    
    local y = 10
    
    -- Main panel
    emu.drawRectangle(5, y, 400, 130, 0xCC000000, true)
    emu.drawRectangle(5, y, 400, 130, 0xFFFFFFFF, false)
    
    -- Title
    emu.drawString(10, y + 5, "SMART SPRITE FINDER - Multi-Strategy", 0xFFFFFFFF)
    
    -- Status
    local status_color = #state.captures > 0 and 0xFF00FF00 or 0xFFFFFF00
    emu.drawString(10, y + 20, state.message, status_color)
    
    -- Statistics
    emu.drawString(10, y + 40, "Frame: " .. state.frame, 0xFFAAAAAA)
    emu.drawString(150, y + 40, "Captures: " .. #state.captures, 0xFFAAAAAA)
    emu.drawString(250, y + 40, "VRAM Tracked: " .. #state.vram_changes, 0xFFAAAAAA)
    
    -- Controls
    emu.drawString(10, y + 60, "Controls:", 0xFFAAAAAA)
    emu.drawString(10, y + 75, "F9: Force pattern search | S: Save captures | F10: Toggle", 0xFFAAAAAA)
    emu.drawString(10, y + 90, "Mouse: Click sprites for manual selection", 0xFFAAAAAA)
    
    -- Auto-detection status
    local auto_status = state.search_active and "SEARCHING..." or "MONITORING"
    local auto_color = state.search_active and 0xFFFFFF00 or 0xFF00FF00
    emu.drawString(10, y + 110, "Auto-Detection: " .. auto_status, auto_color)
    
    y = y + 135
    
    -- Recent captures
    if #state.captures > 0 then
        local height = math.min(#state.captures * 20 + 25, 120)
        emu.drawRectangle(5, y, 400, height, 0xCC000000, true)
        emu.drawRectangle(5, y, 400, height, 0xFF00FF00, false)
        
        emu.drawString(10, y + 5, "Recent Captures (Auto-Found):", 0xFF00FF00)
        
        for i = math.max(1, #state.captures - 4), #state.captures do
            local cap = state.captures[i]
            if cap then
                local cy = y + 10 + ((i - math.max(1, #state.captures - 4)) * 20)
                local auto_tag = cap.auto and "[AUTO]" or "[MANUAL]"
                emu.drawString(10, cy, auto_tag .. " " .. cap.vram_hex .. " -> " .. cap.rom_offset_hex, 0xFFFFFFFF)
            end
        end
        
        y = y + height + 5
    end
    
    -- Pattern match results
    if #state.pattern_matches > 0 then
        emu.drawRectangle(5, y, 400, 60, 0xCC000000, true)
        emu.drawRectangle(5, y, 400, 60, 0xFFFFFF00, false)
        
        emu.drawString(10, y + 5, "Pattern Matches Found:", 0xFFFFFF00)
        for i = 1, math.min(#state.pattern_matches, 2) do
            local match = state.pattern_matches[i]
            emu.drawString(10, y + 15 + (i * 15), "ROM: " .. match.rom_offset_hex .. " (confidence: " .. match.confidence .. "%)", 0xFFFFFFFF)
        end
    end
    
    -- Update message timer
    if state.message_timer > 0 then
        state.message_timer = state.message_timer - 1
    end
end

-- ===============================================================================
-- Input Handling
-- ===============================================================================

function handle_input()
    -- F9: Force pattern search
    local f9 = emu.isKeyPressed("F9")
    if f9 and not state.last_keys["F9"] then
        state.search_active = true
        state.message = "Forcing pattern search..."
        state.message_timer = 60
        
        -- Force VRAM pattern matching
        auto_find_sprites()
        
        state.search_active = false
    end
    state.last_keys["F9"] = f9
    
    -- S: Save captures
    local s = emu.isKeyPressed("S")
    if s and not state.last_keys["S"] then
        save_captures()
    end
    state.last_keys["S"] = s
    
    -- F10: Toggle
    local f10 = emu.isKeyPressed("F10")
    if f10 and not state.last_keys["F10"] then
        state.enabled = not state.enabled
    end
    state.last_keys["F10"] = f10
    
    -- Mouse handling (if available)
    local mouse = emu.getMouseState and emu.getMouseState()
    if mouse then
        state.mouse_x = mouse.x or state.mouse_x
        state.mouse_y = mouse.y or state.mouse_y
        
        -- Click to select sprite
        if mouse.left and not state.last_keys["mouse_left"] then
            local sprite = get_sprite_at_position(state.mouse_x, state.mouse_y)
            if sprite then
                state.message = "Selected sprite #" .. sprite.index .. " at " .. sprite.x .. "," .. sprite.y
                state.message_timer = 120
            end
        end
        state.last_keys["mouse_left"] = mouse.left
    end
end

-- ===============================================================================
-- Save Results
-- ===============================================================================

function save_captures()
    if #state.captures == 0 then
        state.message = "No captures to save"
        state.message_timer = 60
        return
    end
    
    emu.log("================================================================================")
    emu.log("SMART SPRITE FINDER - CAPTURE RESULTS")
    emu.log("================================================================================")
    emu.log("Total Captures: " .. #state.captures)
    emu.log("")
    
    -- Group by auto/manual
    local auto_captures = {}
    local manual_captures = {}
    
    for _, cap in ipairs(state.captures) do
        if cap.auto then
            table.insert(auto_captures, cap)
        else
            table.insert(manual_captures, cap)
        end
    end
    
    if #auto_captures > 0 then
        emu.log("AUTO-DETECTED SPRITES:")
        emu.log("-----------------------")
        for i, cap in ipairs(auto_captures) do
            emu.log(i .. ". VRAM " .. cap.vram_hex .. " -> ROM " .. cap.rom_offset_hex)
        end
        emu.log("")
    end
    
    if #manual_captures > 0 then
        emu.log("MANUALLY SELECTED:")
        emu.log("------------------")
        for i, cap in ipairs(manual_captures) do
            emu.log(i .. ". ROM " .. cap.rom_offset_hex)
        end
        emu.log("")
    end
    
    emu.log("QUICK COPY (ROM Offsets for SpritePal):")
    emu.log("----------------------------------------")
    for _, cap in ipairs(state.captures) do
        emu.log(cap.rom_offset_hex)
    end
    emu.log("================================================================================")
    
    state.message = "Saved " .. #state.captures .. " captures to console"
    state.message_timer = 120
end

-- ===============================================================================
-- Main Loop
-- ===============================================================================

-- Frame callback
emu.addEventCallback(function()
    state.frame = state.frame + 1
    
    -- Auto-detect sprites every 30 frames
    if state.frame % 30 == 0 then
        auto_find_sprites()
    end
    
    -- Clean old VRAM changes
    if #state.vram_changes > 100 then
        state.vram_changes = {}
    end
    
    handle_input()
end, "startFrame")

-- Draw callback
emu.addEventCallback(function()
    draw_ui()
end, "endFrame")

-- Try API functions on startup
try_api_functions()

-- Initial message
emu.log("================================================================================")
emu.log("SMART SPRITE FINDER - Multi-Strategy Automated Approach")
emu.log("================================================================================")
emu.log("This script automatically finds sprite ROM offsets using:")
emu.log("1. VRAM pattern matching - Detects changes and searches ROM")
emu.log("2. Memory tracking - Monitors sprite loads")
emu.log("3. Visual selection - Click sprites with mouse")
emu.log("4. API functions - Uses native functions if available")
emu.log("")
emu.log("The script runs automatically and captures sprite offsets as you play!")
emu.log("")
emu.log("Controls:")
emu.log("- F9: Force pattern search")
emu.log("- S: Save all captures")
emu.log("- F10: Toggle overlay")
emu.log("================================================================================")

state.message = "Automated sprite finding active!"
state.message_timer = 180