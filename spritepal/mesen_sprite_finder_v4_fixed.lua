-- ===============================================================================
-- SpritePal Sprite Finder for Mesen-S v4.0 (Complete Rewrite)
-- Simplified, robust DMA tracking for ROM offset discovery
-- ===============================================================================
-- This version addresses all compatibility issues found in thorough review:
-- - Uses memory callbacks instead of polling for DMA
-- - Removes non-existent API calls
-- - Adds comprehensive error handling
-- - Focuses on working functionality over complex features
-- ===============================================================================

-- Configuration
local CONFIG = {
    -- Colors (ARGB format for Mesen-S)
    COLOR_WHITE = 0xFFFFFFFF,
    COLOR_GREEN = 0xFF00FF00,
    COLOR_YELLOW = 0xFFFFFF00,
    COLOR_RED = 0xFFFF0000,
    COLOR_BLACK_BG = 0xCC000000,
    COLOR_GRAY = 0xFFAAAAAA,
}

-- Global state with safe defaults
local state = {
    enabled = true,
    dma_log = {},           -- Recent DMA transfers
    capture_list = {},      -- Captured ROM offsets
    message = "Waiting for DMA transfers...",
    message_timer = 0,
    message_color = CONFIG.COLOR_WHITE,
    frame_count = 0,
    last_keys = {},         -- For edge detection
    -- ROM mapping detection
    has_header = false,
    mapping = "lorom",      -- Safe default
    header_checked = false
}

-- ===============================================================================
-- Safe Memory Reading
-- ===============================================================================

local function safe_read(address, mem_type)
    -- Safely read memory with nil checking
    local success, value = pcall(function()
        return emu.read(address, mem_type or "cpu", false)
    end)
    
    if success and value then
        return value
    end
    return 0  -- Safe default
end

-- ===============================================================================
-- ROM Header Detection (Deferred)
-- ===============================================================================

local function detect_rom_mapping()
    if state.header_checked then
        return
    end
    
    -- Try common header locations
    local lorom_header = 0x7FC0
    local hirom_header = 0xFFC0
    
    -- Check for SMC header (512 bytes)
    local with_header = safe_read(lorom_header + 512 + 0x15, "prgRom")
    if with_header ~= 0 and with_header ~= 0xFF then
        state.has_header = true
        state.mapping = (with_header & 0x01) == 0x01 and "hirom" or "lorom"
        state.header_checked = true
        return
    end
    
    -- Check without header
    local without_header = safe_read(lorom_header + 0x15, "prgRom")
    if without_header ~= 0 and without_header ~= 0xFF then
        state.has_header = false
        state.mapping = (without_header & 0x01) == 0x01 and "hirom" or "lorom"
        state.header_checked = true
        return
    end
    
    -- Check HiROM location
    local hirom_check = safe_read(hirom_header + 0x15, "prgRom")
    if hirom_check ~= 0 and hirom_check ~= 0xFF then
        state.has_header = false
        state.mapping = "hirom"
        state.header_checked = true
        return
    end
    
    -- Default to LoROM without header
    state.has_header = false
    state.mapping = "lorom"
    state.header_checked = true
end

-- ===============================================================================
-- ROM Offset Calculation
-- ===============================================================================

local function calculate_rom_offset(bank, address)
    -- Ensure mapping is detected
    if not state.header_checked then
        detect_rom_mapping()
    end
    
    local offset = 0
    
    if state.mapping == "lorom" then
        -- LoROM: ((bank & 0x7F) << 15) | (address & 0x7FFF)
        offset = ((bank & 0x7F) * 0x8000) + (address & 0x7FFF)
    else
        -- HiROM: ((bank & 0x3F) << 16) | address
        offset = ((bank & 0x3F) * 0x10000) + address
    end
    
    -- Add header offset if present
    if state.has_header then
        offset = offset + 512
    end
    
    return offset
end

-- ===============================================================================
-- DMA Tracking via Memory Callback
-- ===============================================================================

local function capture_dma_transfer()
    -- This is called when $420B (DMA enable) is written
    local dma_enable = safe_read(0x420B, "cpu")
    
    if dma_enable == 0 then
        return  -- No DMA enabled
    end
    
    -- Check each DMA channel
    for channel = 0, 7 do
        if (dma_enable & (1 << channel)) ~= 0 then
            local base = 0x4300 + (channel * 0x10)
            
            -- Read DMA parameters
            local mode = safe_read(base, "cpu")
            local dest = safe_read(base + 0x01, "cpu")
            
            -- Check if this is a VRAM transfer
            if dest == 0x18 or dest == 0x19 then
                -- Get source address
                local src_low = safe_read(base + 0x02, "cpu")
                local src_high = safe_read(base + 0x03, "cpu")
                local src_bank = safe_read(base + 0x04, "cpu")
                local src_addr = (src_high * 256) + src_low
                
                -- Get size
                local size_low = safe_read(base + 0x05, "cpu")
                local size_high = safe_read(base + 0x06, "cpu")
                local size = (size_high * 256) + size_low
                if size == 0 then size = 0x10000 end  -- 0 means 64KB
                
                -- Get VRAM destination
                local vram_low = safe_read(0x2116, "cpu")
                local vram_high = safe_read(0x2117, "cpu")
                local vram_addr = (vram_high * 256) + vram_low
                
                -- Calculate ROM offset
                local rom_offset = calculate_rom_offset(src_bank, src_addr)
                
                -- Create transfer record
                local transfer = {
                    channel = channel,
                    source = string.format("$%02X:%04X", src_bank, src_addr),
                    vram = string.format("$%04X", vram_addr),
                    size = size,
                    rom_offset = rom_offset,
                    rom_offset_hex = string.format("0x%06X", rom_offset),
                    frame = state.frame_count
                }
                
                -- Add to log (keep last 20)
                table.insert(state.dma_log, 1, transfer)
                if #state.dma_log > 20 then
                    table.remove(state.dma_log)
                end
                
                -- Update message
                state.message = "DMA: " .. transfer.rom_offset_hex .. " (" .. size .. " bytes)"
                state.message_timer = 60
                state.message_color = CONFIG.COLOR_GREEN
                
                -- Log to console for debugging
                emu.log(string.format("DMA Transfer: %s -> VRAM %s, ROM: %s (%d bytes)",
                    transfer.source, transfer.vram, transfer.rom_offset_hex, size))
            end
        end
    end
end

-- ===============================================================================
-- Simplified UI Drawing
-- ===============================================================================

local function draw_ui()
    if not state.enabled then
        return
    end
    
    -- Main info panel
    local y = 10
    emu.drawRectangle(5, y, 260, 100, CONFIG.COLOR_BLACK_BG, true)
    emu.drawRectangle(5, y, 260, 100, CONFIG.COLOR_WHITE, false)
    
    -- Title
    emu.drawString(10, y + 5, "SpritePal Sprite Finder v4.0", CONFIG.COLOR_WHITE)
    
    -- Status message
    emu.drawString(10, y + 20, state.message, state.message_color)
    
    -- Controls
    emu.drawString(10, y + 35, "F9: Capture Latest | S: Save All | F10: Toggle", CONFIG.COLOR_GRAY)
    
    -- Mapping info
    local mapping_text = "ROM: " .. state.mapping
    if state.has_header then
        mapping_text = mapping_text .. " (+header)"
    end
    emu.drawString(10, y + 50, mapping_text, CONFIG.COLOR_GRAY)
    
    -- Capture count
    if #state.capture_list > 0 then
        emu.drawString(10, y + 65, "Captured: " .. #state.capture_list .. " offsets", CONFIG.COLOR_GREEN)
    end
    
    -- DMA count
    emu.drawString(10, y + 80, "DMA Log: " .. #state.dma_log .. " transfers", CONFIG.COLOR_GRAY)
    
    -- Show recent DMA transfers
    if #state.dma_log > 0 then
        y = 120
        emu.drawRectangle(5, y, 260, math.min(#state.dma_log * 15 + 20, 150), CONFIG.COLOR_BLACK_BG, true)
        emu.drawRectangle(5, y, 260, math.min(#state.dma_log * 15 + 20, 150), CONFIG.COLOR_YELLOW, false)
        
        emu.drawString(10, y + 5, "Recent DMA Transfers:", CONFIG.COLOR_YELLOW)
        
        for i = 1, math.min(#state.dma_log, 8) do
            local dma = state.dma_log[i]
            local text = string.format("%s -> %s [%s]", 
                dma.source, dma.vram, dma.rom_offset_hex)
            emu.drawString(10, y + 5 + (i * 15), text, CONFIG.COLOR_WHITE)
        end
    end
    
    -- Update message timer
    if state.message_timer > 0 then
        state.message_timer = state.message_timer - 1
        if state.message_timer == 0 then
            state.message = "Waiting for DMA transfers..."
            state.message_color = CONFIG.COLOR_WHITE
        end
    end
end

-- ===============================================================================
-- Input Handling with Edge Detection
-- ===============================================================================

local function handle_input()
    -- Check F9 key (Capture)
    local f9_pressed = emu.isKeyPressed("F9")
    if f9_pressed and not state.last_keys["F9"] then
        if #state.dma_log > 0 then
            -- Capture the most recent DMA transfer
            local latest = state.dma_log[1]
            
            -- Check if already captured
            local already_captured = false
            for _, capture in ipairs(state.capture_list) do
                if capture.rom_offset == latest.rom_offset then
                    already_captured = true
                    break
                end
            end
            
            if not already_captured then
                table.insert(state.capture_list, {
                    rom_offset = latest.rom_offset,
                    rom_offset_hex = latest.rom_offset_hex,
                    size = latest.size,
                    source = latest.source,
                    vram = latest.vram
                })
                
                state.message = "Captured: " .. latest.rom_offset_hex
                state.message_timer = 60
                state.message_color = CONFIG.COLOR_GREEN
                
                emu.log("Captured ROM offset: " .. latest.rom_offset_hex)
            else
                state.message = "Already captured: " .. latest.rom_offset_hex
                state.message_timer = 60
                state.message_color = CONFIG.COLOR_YELLOW
            end
        else
            state.message = "No DMA transfers to capture!"
            state.message_timer = 60
            state.message_color = CONFIG.COLOR_RED
        end
    end
    state.last_keys["F9"] = f9_pressed
    
    -- Check S key (Save)
    local s_pressed = emu.isKeyPressed("S")
    if s_pressed and not state.last_keys["S"] then
        save_captures()
    end
    state.last_keys["S"] = s_pressed
    
    -- Check F10 key (Toggle)
    local f10_pressed = emu.isKeyPressed("F10")
    if f10_pressed and not state.last_keys["F10"] then
        state.enabled = not state.enabled
        local status = state.enabled and "enabled" or "disabled"
        emu.log("Sprite Finder " .. status)
    end
    state.last_keys["F10"] = f10_pressed
end

-- ===============================================================================
-- Save Captured Offsets
-- ===============================================================================

function save_captures()
    if #state.capture_list == 0 then
        state.message = "Nothing captured yet!"
        state.message_timer = 60
        state.message_color = CONFIG.COLOR_RED
        return
    end
    
    -- Output to console
    emu.log("================================================================================")
    emu.log("SPRITE FINDER CAPTURE LIST")
    emu.log("ROM Mapping: " .. state.mapping .. (state.has_header and " (with SMC header)" or ""))
    emu.log("Total Captures: " .. #state.capture_list)
    emu.log("================================================================================")
    
    -- Detailed list
    for i, capture in ipairs(state.capture_list) do
        emu.log(string.format("%d. ROM Offset: %s", i, capture.rom_offset_hex))
        emu.log(string.format("   Size: %d bytes", capture.size))
        emu.log(string.format("   Source: %s -> VRAM %s", capture.source, capture.vram))
        emu.log("")
    end
    
    -- Quick copy list
    emu.log("Quick Copy List (for SpritePal):")
    emu.log("--------------------------------")
    for _, capture in ipairs(state.capture_list) do
        emu.log(capture.rom_offset_hex)
    end
    emu.log("================================================================================")
    
    state.message = "Saved " .. #state.capture_list .. " captures to console"
    state.message_timer = 120
    state.message_color = CONFIG.COLOR_GREEN
end

-- ===============================================================================
-- Initialization and Callbacks
-- ===============================================================================

-- Register memory callback for DMA trigger
local function init_dma_callback()
    -- Try to add memory write callback for $420B (DMA enable register)
    local success, result = pcall(function()
        emu.addMemoryCallback(function(address, value)
            if address == 0x420B then
                capture_dma_transfer()
            end
        end, "write", 0x420B)
    end)
    
    if success then
        emu.log("DMA callback registered successfully")
    else
        emu.log("Warning: Could not register DMA callback, using frame polling instead")
        -- Fallback: check DMA in frame callback
        state.use_polling = true
    end
end

-- Frame callback
emu.addEventCallback(function()
    state.frame_count = state.frame_count + 1
    
    -- Fallback DMA checking if callback failed
    if state.use_polling and (state.frame_count % 2) == 0 then
        -- Check DMA enable register periodically
        local dma_enable = safe_read(0x420B, "cpu")
        if dma_enable ~= 0 then
            capture_dma_transfer()
        end
    end
    
    -- Handle input
    handle_input()
end, "startFrame")

-- Drawing callback
emu.addEventCallback(function()
    draw_ui()
end, "endFrame")

-- Initialize
init_dma_callback()

-- Initial message
emu.log("================================================================================")
emu.log("SpritePal Sprite Finder v4.0 - Robust Edition")
emu.log("================================================================================")
emu.log("This version uses memory callbacks to track DMA transfers reliably.")
emu.log("")
emu.log("Instructions:")
emu.log("1. Play your game - DMA transfers are tracked automatically")
emu.log("2. Press F9 to capture the latest DMA transfer")
emu.log("3. Press S to save all captured offsets")
emu.log("4. Press F10 to toggle the overlay")
emu.log("")
emu.log("The overlay shows recent DMA transfers with their ROM offsets.")
emu.log("Use these offsets in SpritePal to edit the sprites.")
emu.log("================================================================================")

state.message = "Sprite Finder ready!"
state.message_timer = 180
state.message_color = CONFIG.COLOR_GREEN