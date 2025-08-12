-- ===============================================================================
-- Pattern Finder for Mesen-S - Simple Automated ROM Offset Discovery
-- Finds sprites by matching patterns between VRAM and ROM
-- ===============================================================================
-- How it works:
-- 1. Samples VRAM data from sprite areas
-- 2. Searches ROM for matching byte patterns
-- 3. Reports ROM offsets when patterns match
-- This bypasses DMA tracking entirely!
-- ===============================================================================

local state = {
    frame = 0,
    found_offsets = {},
    message = "Pattern Finder Active - Play game to detect sprites",
    message_timer = 180,
    last_search = 0,
    enabled = true
}

-- ===============================================================================
-- Simple Memory Reading
-- ===============================================================================

function read_byte(address, mem_type)
    -- Try to read a byte with fallbacks
    local ok, val = pcall(emu.read, address, mem_type or "cpu")
    if ok and val then return val end
    
    ok, val = pcall(emu.read, address)
    if ok and val then return val end
    
    return 0
end

-- ===============================================================================
-- Pattern Matching Core
-- ===============================================================================

function get_vram_pattern(vram_addr, size)
    -- Read a pattern from VRAM
    local pattern = {}
    
    -- Set VRAM address
    pcall(emu.write, 0x2116, vram_addr & 0xFF)
    pcall(emu.write, 0x2117, (vram_addr >> 8) & 0xFF)
    
    -- Read from VRAM data register
    for i = 1, size do
        pattern[i] = read_byte(0x2139, "cpu")
        if pattern[i] == 0 then
            -- Fallback: try direct VRAM read
            pattern[i] = read_byte(vram_addr + i - 1, "vram") 
        end
    end
    
    return pattern
end

function search_rom_for_pattern(pattern)
    -- Search ROM for matching pattern
    local matches = {}
    local pattern_size = #pattern
    
    -- Skip if pattern is all zeros or all same value
    local first = pattern[1]
    local all_same = true
    for i = 2, pattern_size do
        if pattern[i] ~= first then
            all_same = false
            break
        end
    end
    if all_same then return matches end
    
    -- Search ROM (up to 4MB)
    local max_offset = 4 * 1024 * 1024
    local step = 256  -- Search every 256 bytes for speed
    
    for offset = 0, max_offset, step do
        -- Check if pattern matches at this offset
        local match = true
        for i = 1, pattern_size do
            local rom_byte = read_byte(offset + i - 1, "prgRom")
            if rom_byte == 0 then
                rom_byte = read_byte(offset + i - 1, "rom")
            end
            
            if rom_byte ~= pattern[i] then
                match = false
                break
            end
        end
        
        if match then
            -- Found a match!
            table.insert(matches, offset)
            
            -- Limit matches
            if #matches >= 5 then
                break
            end
        end
    end
    
    return matches
end

-- ===============================================================================
-- Automated Sprite Detection
-- ===============================================================================

function auto_detect_sprites()
    -- Sample common sprite VRAM locations
    local sprite_areas = {
        0x4000,  -- Common sprite area 1
        0x6000,  -- Common sprite area 2
        0x7000,  -- Common sprite area 3
    }
    
    for _, vram_addr in ipairs(sprite_areas) do
        -- Get a 32-byte pattern (one 4bpp tile)
        local pattern = get_vram_pattern(vram_addr, 32)
        
        -- Search ROM for this pattern
        local matches = search_rom_for_pattern(pattern)
        
        if #matches > 0 then
            for _, offset in ipairs(matches) do
                -- Check if we already found this offset
                local already_found = false
                for _, found in ipairs(state.found_offsets) do
                    if found.offset == offset then
                        already_found = true
                        break
                    end
                end
                
                if not already_found then
                    -- New offset found!
                    local entry = {
                        offset = offset,
                        hex = string.format("0x%06X", offset),
                        vram = string.format("$%04X", vram_addr),
                        frame = state.frame
                    }
                    
                    table.insert(state.found_offsets, entry)
                    
                    -- Log discovery
                    emu.log("PATTERN MATCH: VRAM " .. entry.vram .. " found at ROM " .. entry.hex)
                    
                    state.message = "Found: " .. entry.hex
                    state.message_timer = 120
                end
            end
        end
    end
end

-- ===============================================================================
-- UI Drawing
-- ===============================================================================

function draw_ui()
    if not state.enabled then return end
    
    -- Simple overlay
    emu.drawRectangle(5, 10, 350, 90, 0xCC000000, true)
    emu.drawRectangle(5, 10, 350, 90, 0xFFFFFFFF, false)
    
    emu.drawString(10, 15, "PATTERN FINDER - Automated", 0xFFFFFFFF)
    emu.drawString(10, 30, state.message, 0xFFFFFF00)
    emu.drawString(10, 45, "Found Offsets: " .. #state.found_offsets, 0xFF00FF00)
    emu.drawString(10, 60, "Frame: " .. state.frame .. " | Next scan: " .. (30 - (state.frame % 30)), 0xFFAAAAAA)
    emu.drawString(10, 75, "Press S to save | F10 to toggle", 0xFFAAAAAA)
    
    -- Show recent finds
    if #state.found_offsets > 0 then
        local y = 105
        emu.drawRectangle(5, y, 350, math.min(#state.found_offsets * 15 + 20, 90), 0xCC000000, true)
        emu.drawString(10, y + 5, "Recent Discoveries:", 0xFF00FF00)
        
        for i = math.max(1, #state.found_offsets - 4), #state.found_offsets do
            local found = state.found_offsets[i]
            if found then
                emu.drawString(10, y + 5 + ((i - math.max(1, #state.found_offsets - 4) + 1) * 15),
                    found.vram .. " -> " .. found.hex, 0xFFFFFFFF)
            end
        end
    end
    
    if state.message_timer > 0 then
        state.message_timer = state.message_timer - 1
    end
end

-- ===============================================================================
-- Input and Save
-- ===============================================================================

function save_results()
    if #state.found_offsets == 0 then
        state.message = "No offsets found yet"
        state.message_timer = 60
        return
    end
    
    emu.log("========================================")
    emu.log("PATTERN FINDER RESULTS")
    emu.log("========================================")
    emu.log("Found " .. #state.found_offsets .. " ROM offsets")
    emu.log("")
    
    for i, found in ipairs(state.found_offsets) do
        emu.log(i .. ". " .. found.hex .. " (from VRAM " .. found.vram .. ")")
    end
    
    emu.log("")
    emu.log("QUICK COPY LIST:")
    for _, found in ipairs(state.found_offsets) do
        emu.log(found.hex)
    end
    emu.log("========================================")
    
    state.message = "Saved " .. #state.found_offsets .. " offsets"
    state.message_timer = 120
end

-- ===============================================================================
-- Main Callbacks
-- ===============================================================================

emu.addEventCallback(function()
    state.frame = state.frame + 1
    
    -- Run pattern search every 30 frames
    if state.frame % 30 == 0 then
        auto_detect_sprites()
    end
    
    -- Handle input
    if emu.isKeyPressed and emu.isKeyPressed("S") then
        save_results()
    end
    
    if emu.isKeyPressed and emu.isKeyPressed("F10") then
        state.enabled = not state.enabled
    end
end, "startFrame")

emu.addEventCallback(function()
    draw_ui()
end, "endFrame")

-- Initial log
emu.log("========================================")
emu.log("PATTERN FINDER - Simple Automated")
emu.log("========================================")
emu.log("This script automatically finds sprite")
emu.log("ROM offsets by pattern matching!")
emu.log("")
emu.log("Just play the game normally.")
emu.log("Sprites are detected automatically.")
emu.log("")
emu.log("Press S to save results")
emu.log("Press F10 to toggle overlay")
emu.log("========================================")