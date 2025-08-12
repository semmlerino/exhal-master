-- ===============================================================================
-- SpritePal Sprite Finder for Mesen-S v3.0 (Fixed)
-- Automated ROM offset discovery for sprite editing
-- ===============================================================================
-- Usage:
-- 1. Load your ROM in Mesen-S
-- 2. Script → Load Script → Select this file
-- 3. Visual overlay appears with instructions
-- 4. Play game and point at sprites
-- 5. Press F9 to capture sprite data
-- 6. Press S to save sprite map to console log
-- ===============================================================================

-- Configuration
local CONFIG = {
    -- Display
    HIGHLIGHT_COLOR = 0x8000FF00,  -- Semi-transparent green highlight
    INFO_COLOR = 0xFFFFFFFF,       -- White text
    BG_COLOR = 0xCC000000,         -- Semi-transparent black
    YELLOW = 0xFFFFFF00,           -- Yellow for warnings
    RED = 0xFFFF0000,              -- Red for errors
    GRAY = 0xFFAAAAAA,             -- Gray for secondary text
}

-- Global state
local state = {
    enabled = true,
    selected_sprite = nil,  -- Currently selected sprite
    sprite_map = {},       -- Collected sprite data
    mouse_x = 0,
    mouse_y = 0,
    message = "Press F9 to capture sprite",
    message_timer = 0,
    dma_log = {},          -- Recent DMA transfers
    vram_map = {},         -- VRAM to ROM mapping
    last_f9 = false,       -- Key press tracking
    last_s = false,
    last_f10 = false,
    frame_count = 0,
    has_header = false,    -- SMC header detection
    mapping_type = "lorom" -- ROM mapping type
}

-- ===============================================================================
-- ROM Header Detection (without getRomSize)
-- ===============================================================================

local function detect_rom_header()
    -- Try to detect SMC header by checking ROM mapping mode bytes
    -- Check both possible header locations
    local lorom_header = 0x7FC0
    local hirom_header = 0xFFC0
    
    -- Check with potential SMC header offset
    local test_with_header = lorom_header + 512
    local test_map_mode = emu.read(test_with_header + 0x15, "prgRom", false)
    
    if test_map_mode and test_map_mode ~= 0xFF then
        -- Likely has SMC header
        state.has_header = true
        state.mapping_type = (test_map_mode & 0x01) == 0x01 and "hirom" or "lorom"
        return true
    end
    
    -- Check without header
    local map_mode = emu.read(lorom_header + 0x15, "prgRom", false)
    if map_mode and map_mode ~= 0xFF then
        state.has_header = false
        state.mapping_type = (map_mode & 0x01) == 0x01 and "hirom" or "lorom"
        return true
    end
    
    -- Try HiROM location
    map_mode = emu.read(hirom_header + 0x15, "prgRom", false)
    if map_mode and map_mode ~= 0xFF then
        state.has_header = false
        state.mapping_type = "hirom"
        return true
    end
    
    -- Default to LoROM without header
    state.has_header = false
    state.mapping_type = "lorom"
    return false
end

-- ===============================================================================
-- ROM Offset Calculation
-- ===============================================================================

local function calculate_rom_offset(bank, address)
    local header_offset = state.has_header and 512 or 0
    local rom_offset
    
    if state.mapping_type == "lorom" then
        -- LoROM: ((bank & 0x7F) << 15) | (address & 0x7FFF)
        rom_offset = ((bank & 0x7F) * 0x8000) + (address & 0x7FFF)
    else
        -- HiROM: ((bank & 0x3F) << 16) | address
        rom_offset = ((bank & 0x3F) * 0x10000) + address
    end
    
    return rom_offset + header_offset
end

-- ===============================================================================
-- DMA Tracking
-- ===============================================================================

local function track_dma_transfer()
    -- Monitor all 8 DMA channels
    for channel = 0, 7 do
        local base = 0x4300 + (channel * 0x10)
        
        -- Check if channel is enabled via $420B
        local dma_enable = emu.read(0x420B, "cpu", false)
        if dma_enable and (dma_enable & (1 << channel)) ~= 0 then
            local dest = emu.read(base + 0x01, "cpu", false)
            
            -- Check if this is a VRAM transfer (destination $2118/2119)
            if dest == 0x18 or dest == 0x19 then
                -- Get source address
                local src_low = emu.read(base + 0x02, "cpu", false) or 0
                local src_high = emu.read(base + 0x03, "cpu", false) or 0
                local src_bank = emu.read(base + 0x04, "cpu", false) or 0
                local src_addr = (src_high * 256) + src_low
                
                -- Get transfer size
                local size_low = emu.read(base + 0x05, "cpu", false) or 0
                local size_high = emu.read(base + 0x06, "cpu", false) or 0
                local size = (size_high * 256) + size_low
                
                if size == 0 then size = 0x10000 end -- 0 means 64KB
                
                -- Get VRAM destination
                local vram_low = emu.read(0x2116, "cpu", false) or 0
                local vram_high = emu.read(0x2117, "cpu", false) or 0
                local vram_addr = (vram_high * 256) + vram_low
                
                -- Calculate ROM offset
                local rom_offset = calculate_rom_offset(src_bank, src_addr)
                
                -- Store DMA info
                local transfer = {
                    channel = channel,
                    source = string.format("$%02X:%04X", src_bank, src_addr),
                    vram = string.format("$%04X", vram_addr),
                    size = size,
                    rom_offset = rom_offset,
                    rom_offset_hex = string.format("0x%06X", rom_offset),
                    frame = state.frame_count
                }
                
                -- Add to log (keep last 100 transfers)
                table.insert(state.dma_log, 1, transfer)
                if #state.dma_log > 100 then
                    table.remove(state.dma_log)
                end
                
                -- Map VRAM regions to ROM offsets
                -- Track every 32 bytes (one 8x8 tile in 4bpp)
                for i = 0, math.min(size - 1, 0x2000), 32 do
                    state.vram_map[vram_addr + i] = {
                        rom_offset = rom_offset + i,
                        source = transfer.source,
                        frame = transfer.frame
                    }
                end
            end
        end
    end
end

-- ===============================================================================
-- Simplified Sprite Detection
-- ===============================================================================

local function get_sprite_under_cursor()
    -- For simplicity, just track the most recent DMA transfers
    -- and show info based on mouse position
    
    -- Create a "virtual" sprite based on mouse position
    -- This is simplified since we can't easily correlate OAM with mouse
    local grid_x = math.floor(state.mouse_x / 16) * 16
    local grid_y = math.floor(state.mouse_y / 16) * 16
    
    -- Look for VRAM data at common sprite locations
    local vram_addr = 0x6000 + (grid_y * 16) + grid_x  -- Simplified mapping
    local source_info = state.vram_map[vram_addr & 0x7FFF]
    
    if not source_info and #state.dma_log > 0 then
        -- Use most recent DMA as fallback
        local recent = state.dma_log[1]
        source_info = {
            rom_offset = recent.rom_offset,
            source = recent.source,
            frame = recent.frame
        }
    end
    
    return {
        x = grid_x,
        y = grid_y,
        width = 16,
        height = 16,
        rom_source = source_info
    }
end

-- ===============================================================================
-- HAL Compression Detection
-- ===============================================================================

local function detect_hal_compression(rom_offset)
    -- Read bytes at offset to check for HAL compression markers
    local marker1 = emu.read(rom_offset, "prgRom", false)
    local marker2 = emu.read(rom_offset + 1, "prgRom", false)
    
    if not marker1 or not marker2 then
        return false, 0
    end
    
    -- HAL compression typically starts with specific patterns
    if marker1 <= 0x0F then
        -- Likely HAL compressed
        local size_low = marker2
        local size_high = emu.read(rom_offset + 2, "prgRom", false) or 0
        local compressed_size = (size_high * 256) + size_low
        
        return true, compressed_size
    end
    
    return false, 0
end

-- ===============================================================================
-- UI Overlay
-- ===============================================================================

local function draw_overlay()
    if not state.enabled then return end
    
    -- Draw info panel
    local panel_y = 10
    local bg_color = state.message_timer > 0 and 0x8000FF00 or CONFIG.BG_COLOR
    emu.drawRectangle(5, panel_y, 250, 110, bg_color, true)
    emu.drawRectangle(5, panel_y, 250, 110, CONFIG.INFO_COLOR, false)
    
    emu.drawString(10, panel_y + 5, "SpritePal Sprite Finder v3.0", CONFIG.INFO_COLOR)
    emu.drawString(10, panel_y + 20, state.message, CONFIG.INFO_COLOR)
    emu.drawString(10, panel_y + 35, "F9: Capture | S: Save | F10: Toggle", CONFIG.GRAY)
    emu.drawString(10, panel_y + 50, "Mouse: " .. state.mouse_x .. "," .. state.mouse_y, CONFIG.GRAY)
    emu.drawString(10, panel_y + 65, "Mapping: " .. state.mapping_type .. (state.has_header and " (+header)" or ""), CONFIG.GRAY)
    
    if #state.sprite_map > 0 then
        emu.drawString(10, panel_y + 80, "Captured: " .. #state.sprite_map .. " sprites", CONFIG.HIGHLIGHT_COLOR)
    end
    
    -- Show DMA transfers
    emu.drawString(10, panel_y + 95, "DMA tracked: " .. #state.dma_log, CONFIG.GRAY)
    
    -- Show most recent DMA info if available
    if #state.dma_log > 0 then
        local recent = state.dma_log[1]
        local info_y = panel_y + 120
        
        emu.drawRectangle(5, info_y, 250, 50, CONFIG.BG_COLOR, true)
        emu.drawRectangle(5, info_y, 250, 50, CONFIG.YELLOW, false)
        
        emu.drawString(10, info_y + 5, "Recent DMA Transfer:", CONFIG.YELLOW)
        emu.drawString(10, info_y + 20, recent.source .. " -> " .. recent.vram, CONFIG.INFO_COLOR)
        emu.drawString(10, info_y + 35, "ROM: " .. recent.rom_offset_hex .. " (" .. recent.size .. " bytes)", CONFIG.HIGHLIGHT_COLOR)
    end
    
    -- Highlight area under cursor
    if state.selected_sprite then
        local spr = state.selected_sprite
        emu.drawRectangle(spr.x, spr.y, spr.width, spr.height, CONFIG.HIGHLIGHT_COLOR, false)
        
        if spr.rom_source then
            -- Draw ROM offset near cursor
            local text = string.format("0x%06X", spr.rom_source.rom_offset)
            emu.drawString(spr.x, spr.y - 10, text, CONFIG.HIGHLIGHT_COLOR)
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

local function handle_input()
    -- Get mouse state
    local mouseState = emu.getMouseState()
    if mouseState then
        state.mouse_x = mouseState.x or state.mouse_x
        state.mouse_y = mouseState.y or state.mouse_y
    end
    
    -- Update selected sprite
    state.selected_sprite = get_sprite_under_cursor()
    
    -- Handle keyboard input with edge detection
    local f9_pressed = emu.isKeyPressed("F9")
    local s_pressed = emu.isKeyPressed("S")
    local f10_pressed = emu.isKeyPressed("F10")
    
    -- F9: Capture sprite (edge detection)
    if f9_pressed and not state.last_f9 then
        if #state.dma_log > 0 then
            -- Use most recent DMA transfer
            local recent = state.dma_log[1]
            
            -- Add to sprite map
            local entry = {
                index = #state.sprite_map + 1,
                rom_offset = recent.rom_offset,
                rom_offset_hex = recent.rom_offset_hex,
                size = recent.size,
                vram = recent.vram,
                source = recent.source,
                frame_captured = state.frame_count
            }
            
            -- Check for HAL compression
            local is_hal, comp_size = detect_hal_compression(entry.rom_offset)
            if is_hal then
                entry.hal_compressed = true
                entry.compressed_size = comp_size
            end
            
            table.insert(state.sprite_map, entry)
            
            state.message = "Captured #" .. #state.sprite_map .. " at " .. entry.rom_offset_hex
            state.message_timer = 120
            
            -- Log to console
            emu.log("Sprite captured: " .. entry.rom_offset_hex .. " (" .. entry.size .. " bytes)")
        else
            state.message = "No DMA transfers detected yet!"
            state.message_timer = 120
        end
    end
    
    -- S: Save sprite map (edge detection)
    if s_pressed and not state.last_s then
        save_sprite_map()
    end
    
    -- F10: Toggle overlay (edge detection)
    if f10_pressed and not state.last_f10 then
        state.enabled = not state.enabled
        state.message = state.enabled and "Overlay enabled" or "Overlay disabled"
        state.message_timer = 60
    end
    
    -- Update key states for edge detection
    state.last_f9 = f9_pressed
    state.last_s = s_pressed
    state.last_f10 = f10_pressed
end

-- ===============================================================================
-- Export Functions
-- ===============================================================================

function save_sprite_map()
    if #state.sprite_map == 0 then
        state.message = "No sprites captured!"
        state.message_timer = 120
        return
    end
    
    -- Log the captures
    emu.log("=== SPRITE MAP ===")
    emu.log("Mapping: " .. state.mapping_type .. (state.has_header and " (with SMC header)" or ""))
    emu.log("Total captures: " .. #state.sprite_map)
    emu.log("")
    
    for i, sprite in ipairs(state.sprite_map) do
        local hal_note = sprite.hal_compressed and " [HAL compressed]" or ""
        emu.log(string.format("%d. %s - %d bytes%s", 
            i, sprite.rom_offset_hex, sprite.size, hal_note))
        emu.log("   Source: " .. sprite.source .. " -> " .. sprite.vram)
        if sprite.hal_compressed then
            emu.log("   Compressed size: " .. sprite.compressed_size .. " bytes")
        end
        emu.log("")
    end
    
    emu.log("=== END SPRITE MAP ===")
    
    -- Create simple offset list for easy copying
    emu.log("")
    emu.log("=== QUICK COPY LIST ===")
    for i, sprite in ipairs(state.sprite_map) do
        emu.log(sprite.rom_offset_hex)
    end
    emu.log("=== END LIST ===")
    
    state.message = "Saved " .. #state.sprite_map .. " sprites to console"
    state.message_timer = 180
end

-- ===============================================================================
-- Main Loop and Initialization
-- ===============================================================================

-- Initialize ROM header detection
detect_rom_header()

-- Frame counter callback
emu.addEventCallback(function()
    state.frame_count = state.frame_count + 1
    -- Track DMA on every frame
    track_dma_transfer()
end, "startFrame")

-- Rendering callback
emu.addEventCallback(function()
    -- Handle input and draw overlay
    handle_input()
    draw_overlay()
end, "endFrame")

-- Initialize
emu.log("================================================================================")
emu.log("SpritePal Sprite Finder v3.0 loaded!")
emu.log("================================================================================")
emu.log("ROM Mapping detected: " .. state.mapping_type)
emu.log("SMC Header: " .. (state.has_header and "Yes (+512 bytes)" or "No"))
emu.log("")
emu.log("INSTRUCTIONS:")
emu.log("1. Play your game to load sprites")
emu.log("2. Watch for DMA transfers (shown on screen)")
emu.log("3. Press F9 to capture the latest transfer")
emu.log("4. Press S to save all captured offsets")
emu.log("5. Press F10 to toggle overlay")
emu.log("")
emu.log("The script tracks DMA transfers to VRAM automatically.")
emu.log("Each capture records the ROM source offset for SpritePal.")
emu.log("================================================================================")

state.message = "Sprite Finder ready!"
state.message_timer = 180