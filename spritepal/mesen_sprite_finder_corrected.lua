-- ===============================================================================
-- SpritePal Sprite Finder for Mesen-S (Corrected API Version)
-- Automated ROM offset discovery for sprite editing
-- ===============================================================================
-- Version: 2.0 - Corrected for actual Mesen-S Lua API
-- ===============================================================================
-- Usage:
-- 1. Load your ROM in Mesen-S
-- 2. Script → Load Script → Select this file
-- 3. Visual overlay appears with instructions
-- 4. Play game and hover over sprites
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
    
    -- Export
    EXPORT_DIR = "sprite_data",    -- Directory for exports
    JSON_FILENAME = "sprite_map.json"  -- Export filename
}

-- Global state
local state = {
    enabled = true,
    tracking = {},          -- DMA tracking data
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
    frame_count = 0
}

-- ===============================================================================
-- ROM Offset Calculation
-- ===============================================================================

local function calculate_rom_offset(bank, address)
    -- Get ROM size to detect header
    local rom_size = emu.getRomSize()
    local has_header = (rom_size % 1024) == 512
    local header_offset = has_header and 512 or 0
    
    -- Try to detect mapping type based on ROM header
    -- Read mapping mode byte from ROM header
    local header_loc = has_header and 0x7FC0 + 512 or 0x7FC0
    local map_mode = emu.read(header_loc + 0x15, "prgRom", false)
    
    local mapping = "lorom"  -- Default to LoROM
    if map_mode and (map_mode & 0x01) == 0x01 then
        mapping = "hirom"
    end
    
    local rom_offset
    
    if mapping == "lorom" then
        -- LoROM: ((bank & 0x7F) << 15) | (address & 0x7FFF)
        rom_offset = ((bank & 0x7F) * 0x8000) + (address & 0x7FFF)
    else
        -- HiROM: ((bank & 0x3F) << 16) | address
        rom_offset = ((bank & 0x3F) * 0x10000) + address
    end
    
    return rom_offset + header_offset, mapping
end

-- ===============================================================================
-- DMA Tracking
-- ===============================================================================

local function track_dma_transfer()
    -- Monitor all 8 DMA channels
    for channel = 0, 7 do
        local base = 0x4300 + (channel * 0x10)
        
        -- Check if channel is active
        local control = emu.read(base, "cpu", false)
        if control and control ~= 0 then
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
                
                -- Get VRAM destination
                local vram_low = emu.read(0x2116, "cpu", false) or 0
                local vram_high = emu.read(0x2117, "cpu", false) or 0
                local vram_addr = (vram_high * 256) + vram_low
                
                -- Calculate ROM offset
                local rom_offset, mapping = calculate_rom_offset(src_bank, src_addr)
                
                -- Store DMA info
                local transfer = {
                    channel = channel,
                    source = string.format("$%02X:%04X", src_bank, src_addr),
                    vram = string.format("$%04X", vram_addr),
                    size = size,
                    rom_offset = rom_offset,
                    rom_offset_hex = string.format("0x%06X", rom_offset),
                    mapping = mapping,
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
-- Sprite Detection (Simplified)
-- ===============================================================================

local function get_sprite_at_position(x, y)
    -- Read OAM to find sprites at position
    local sprites = {}
    
    for i = 0, 127 do  -- 128 sprites in OAM
        local oam_addr = i * 4
        
        -- Read sprite data from OAM
        local spr_x = emu.read(oam_addr, "oam", false) or 0
        local spr_y = emu.read(oam_addr + 1, "oam", false) or 0
        local tile = emu.read(oam_addr + 2, "oam", false) or 0
        local attr = emu.read(oam_addr + 3, "oam", false) or 0
        
        -- Read extra X bit and size bit from high table
        local high_table_addr = 0x200 + math.floor(i / 4)
        local high_table_byte = emu.read(high_table_addr, "oam", false) or 0
        local bit_pos = (i % 4) * 2
        local x_high = (high_table_byte >> bit_pos) & 1
        local size_bit = (high_table_byte >> (bit_pos + 1)) & 1
        
        -- Calculate actual position
        spr_x = spr_x + (x_high * 256)
        
        -- Simplified size calculation (8x8 or 16x16 for now)
        local width = size_bit == 0 and 8 or 16
        local height = width
        
        -- Check if cursor is over this sprite (with some tolerance)
        if x >= spr_x - 4 and x < spr_x + width + 4 and
           y >= spr_y - 4 and y < spr_y + height + 4 then
            
            -- Get VRAM address for this tile (simplified)
            local name_base = (emu.read(0x2101, "cpu", false) or 0) & 0x07
            local tile_vram = (name_base * 0x2000) + (tile * 32)  -- 32 bytes per 4bpp tile
            
            -- Look up ROM source from VRAM map
            local source_info = state.vram_map[tile_vram]
            
            table.insert(sprites, {
                index = i,
                x = spr_x,
                y = spr_y,
                width = width,
                height = height,
                tile = tile,
                tile_vram = tile_vram,
                palette = (attr >> 1) & 0x07,
                priority = (attr >> 4) & 0x03,
                flip_h = (attr & 0x40) ~= 0,
                flip_v = (attr & 0x80) ~= 0,
                rom_source = source_info
            })
        end
    end
    
    -- Return the first sprite found
    if #sprites > 0 then
        return sprites[1]
    end
    
    return nil
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
    -- Common markers: 0x00-0x0F followed by size bytes
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
    emu.drawRectangle(5, panel_y, 250, 95, bg_color, true)
    emu.drawRectangle(5, panel_y, 250, 95, CONFIG.INFO_COLOR, false)
    
    emu.drawString(10, panel_y + 5, "SpritePal Sprite Finder v2.0", CONFIG.INFO_COLOR)
    emu.drawString(10, panel_y + 20, state.message, CONFIG.INFO_COLOR)
    emu.drawString(10, panel_y + 35, "F9: Capture | S: Save | F10: Toggle", CONFIG.GRAY)
    emu.drawString(10, panel_y + 50, "Mouse: " .. state.mouse_x .. "," .. state.mouse_y, CONFIG.GRAY)
    
    if #state.sprite_map > 0 then
        emu.drawString(10, panel_y + 65, "Sprites captured: " .. #state.sprite_map, CONFIG.HIGHLIGHT_COLOR)
    end
    
    -- Show DMA log count
    emu.drawString(10, panel_y + 80, "DMA transfers tracked: " .. #state.dma_log, CONFIG.GRAY)
    
    -- Highlight selected sprite
    if state.selected_sprite then
        local spr = state.selected_sprite
        emu.drawRectangle(spr.x, spr.y, spr.width, spr.height, CONFIG.HIGHLIGHT_COLOR, false)
        emu.drawRectangle(spr.x-1, spr.y-1, spr.width+2, spr.height+2, CONFIG.HIGHLIGHT_COLOR, false)
        
        -- Draw sprite info box
        local info_x = math.min(spr.x + spr.width + 5, 200)
        local info_y = spr.y
        
        emu.drawRectangle(info_x, info_y, 120, 100, CONFIG.BG_COLOR, true)
        emu.drawRectangle(info_x, info_y, 120, 100, CONFIG.HIGHLIGHT_COLOR, false)
        
        emu.drawString(info_x + 3, info_y + 3, "Sprite #" .. spr.index, CONFIG.INFO_COLOR)
        emu.drawString(info_x + 3, info_y + 15, "Tile: $" .. string.format("%02X", spr.tile), CONFIG.INFO_COLOR)
        emu.drawString(info_x + 3, info_y + 27, "Size: " .. spr.width .. "x" .. spr.height, CONFIG.INFO_COLOR)
        emu.drawString(info_x + 3, info_y + 39, "VRAM: $" .. string.format("%04X", spr.tile_vram), CONFIG.GRAY)
        
        if spr.rom_source then
            emu.drawString(info_x + 3, info_y + 51, "ROM: " .. string.format("0x%06X", spr.rom_source.rom_offset), CONFIG.HIGHLIGHT_COLOR)
            emu.drawString(info_x + 3, info_y + 63, "Src: " .. spr.rom_source.source, CONFIG.GRAY)
            
            -- Check for HAL compression
            local is_hal, comp_size = detect_hal_compression(spr.rom_source.rom_offset)
            if is_hal then
                emu.drawString(info_x + 3, info_y + 75, "HAL: " .. comp_size .. " bytes", CONFIG.YELLOW)
            end
            
            emu.drawString(info_x + 3, info_y + 87, "Frame: " .. spr.rom_source.frame, CONFIG.GRAY)
        else
            emu.drawString(info_x + 3, info_y + 51, "ROM: Unknown", CONFIG.RED)
            emu.drawString(info_x + 3, info_y + 63, "Trigger DMA first", CONFIG.GRAY)
            emu.drawString(info_x + 3, info_y + 75, "Play animation", CONFIG.GRAY)
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
    
    -- Check for sprite under cursor
    local sprite = get_sprite_at_position(state.mouse_x, state.mouse_y)
    if sprite then
        state.selected_sprite = sprite
    end
    
    -- Handle keyboard input with edge detection
    local f9_pressed = emu.isKeyPressed("F9")
    local s_pressed = emu.isKeyPressed("S")
    local f10_pressed = emu.isKeyPressed("F10")
    
    -- F9: Capture sprite (edge detection)
    if f9_pressed and not state.last_f9 then
        if state.selected_sprite and state.selected_sprite.rom_source then
            -- Add to sprite map
            local entry = {
                index = #state.sprite_map + 1,
                rom_offset = state.selected_sprite.rom_source.rom_offset,
                rom_offset_hex = string.format("0x%06X", state.selected_sprite.rom_source.rom_offset),
                tile = state.selected_sprite.tile,
                size = state.selected_sprite.width .. "x" .. state.selected_sprite.height,
                vram = string.format("$%04X", state.selected_sprite.tile_vram),
                source = state.selected_sprite.rom_source.source,
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
            emu.log("Sprite captured: " .. entry.rom_offset_hex .. " (" .. entry.size .. ")")
        else
            state.message = "No sprite data - trigger DMA first!"
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
        if state.enabled then
            state.message = "Overlay enabled"
        else
            state.message = "Overlay disabled"
        end
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
    
    -- Create JSON output
    local json = "{\n"
    json = json .. '  "rom": "' .. (emu.getRomInfo().name or "unknown") .. '",\n'
    json = json .. '  "captured_at": "' .. os.date() .. '",\n'
    json = json .. '  "total_sprites": ' .. #state.sprite_map .. ',\n'
    json = json .. '  "sprites": [\n'
    
    for i, sprite in ipairs(state.sprite_map) do
        json = json .. '    {\n'
        json = json .. '      "index": ' .. sprite.index .. ',\n'
        json = json .. '      "rom_offset": ' .. sprite.rom_offset .. ',\n'
        json = json .. '      "rom_offset_hex": "' .. sprite.rom_offset_hex .. '",\n'
        json = json .. '      "tile": ' .. sprite.tile .. ',\n'
        json = json .. '      "size": "' .. sprite.size .. '",\n'
        json = json .. '      "vram": "' .. sprite.vram .. '",\n'
        json = json .. '      "source": "' .. sprite.source .. '",\n'
        json = json .. '      "frame_captured": ' .. sprite.frame_captured
        
        if sprite.hal_compressed then
            json = json .. ',\n'
            json = json .. '      "hal_compressed": true,\n'
            json = json .. '      "compressed_size": ' .. sprite.compressed_size
        end
        
        json = json .. '\n    }'
        if i < #state.sprite_map then
            json = json .. ','
        end
        json = json .. '\n'
    end
    
    json = json .. '  ]\n'
    json = json .. '}\n'
    
    -- Log the JSON (user can copy from log)
    emu.log("=== SPRITE MAP JSON START ===")
    emu.log(json)
    emu.log("=== SPRITE MAP JSON END ===")
    
    -- Also create a simple text summary
    emu.log("=== QUICK OFFSET LIST ===")
    for i, sprite in ipairs(state.sprite_map) do
        local hal_note = sprite.hal_compressed and " [HAL]" or ""
        emu.log(string.format("%d. %s - %s%s", i, sprite.rom_offset_hex, sprite.size, hal_note))
    end
    emu.log("=== END OFFSET LIST ===")
    
    state.message = "Saved " .. #state.sprite_map .. " sprites to console log"
    state.message_timer = 180
end

-- ===============================================================================
-- Main Loop and Initialization
-- ===============================================================================

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
emu.log("SpritePal Sprite Finder v2.0 loaded!")
emu.log("================================================================================")
emu.log("INSTRUCTIONS:")
emu.log("1. Play your game until sprites appear")
emu.log("2. Move mouse over desired sprite")
emu.log("3. Press F9 to capture sprite offset")
emu.log("4. Press S to save all captured sprites")
emu.log("5. Press F10 to toggle overlay")
emu.log("")
emu.log("IMPORTANT: Sprites must be loaded via DMA first!")
emu.log("If no ROM offset shown, trigger sprite animation.")
emu.log("================================================================================")

state.message = "Sprite Finder ready!"
state.message_timer = 180