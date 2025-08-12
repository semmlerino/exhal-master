-- ===============================================================================
-- SpritePal Sprite Finder for Mesen-S
-- Automated ROM offset discovery for sprite editing
-- ===============================================================================
-- Usage:
-- 1. Load your ROM in Mesen-S
-- 2. Script → Load Script → Select this file
-- 3. Visual overlay appears with instructions
-- 4. Play game and hover over sprites
-- 5. Press F9 to capture sprite data
-- 6. Press C to copy offset or S to save sprite map
-- ===============================================================================

-- Configuration
local CONFIG = {
    -- Hotkeys
    CAPTURE_KEY = "F9",        -- Capture sprite under cursor
    COPY_KEY = "C",            -- Copy offset to clipboard
    SAVE_KEY = "S",            -- Save sprite map
    TOGGLE_KEY = "F10",        -- Toggle overlay
    
    -- Display
    OVERLAY_ALPHA = 0.8,      -- Overlay transparency
    HIGHLIGHT_COLOR = 0xFF00FF00,  -- Green highlight for selected sprite
    INFO_COLOR = 0xFFFFFFFF,       -- White text
    BG_COLOR = 0xCC000000,         -- Semi-transparent black
    
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
    vram_map = {}          -- VRAM to ROM mapping
}

-- ===============================================================================
-- ROM Offset Calculation
-- ===============================================================================

local function calculate_rom_offset(bank, address)
    -- Detect ROM mapping type
    local rom_size = emu.getRomSize()
    local has_header = (rom_size % 1024) == 512
    local header_offset = has_header and 512 or 0
    
    -- Try to detect mapping type based on common patterns
    local mapping = "lorom"  -- Default to LoROM
    
    -- Read ROM header to determine mapping
    local header_loc = has_header and 0x7FC0 + 512 or 0x7FC0
    local map_mode = emu.read(header_loc + 0x15, emu.memType.cpuRom)
    
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
        local control = emu.read(base, emu.memType.cpu)
        if control and control ~= 0 then
            local dest = emu.read(base + 0x01, emu.memType.cpu)
            
            -- Check if this is a VRAM transfer (destination $2118/2119)
            if dest == 0x18 or dest == 0x19 then
                -- Get source address
                local src_low = emu.read(base + 0x02, emu.memType.cpu)
                local src_high = emu.read(base + 0x03, emu.memType.cpu)
                local src_bank = emu.read(base + 0x04, emu.memType.cpu)
                local src_addr = (src_high * 256) + src_low
                
                -- Get transfer size
                local size_low = emu.read(base + 0x05, emu.memType.cpu)
                local size_high = emu.read(base + 0x06, emu.memType.cpu)
                local size = (size_high * 256) + size_low
                
                -- Get VRAM destination
                local vram_low = emu.read(0x2116, emu.memType.cpu)
                local vram_high = emu.read(0x2117, emu.memType.cpu)
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
                    frame = emu.getState().ppu.frameCount
                }
                
                -- Add to log (keep last 100 transfers)
                table.insert(state.dma_log, 1, transfer)
                if #state.dma_log > 100 then
                    table.remove(state.dma_log)
                end
                
                -- Map VRAM regions to ROM offsets
                for i = 0, size - 1, 32 do  -- Track every 32 bytes (one 8x8 tile in 4bpp)
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
-- Sprite Detection
-- ===============================================================================

local function get_sprite_at_position(x, y)
    -- Read OAM to find sprites at position
    local sprites = {}
    
    for i = 0, 127 do  -- 128 sprites in OAM
        local oam_addr = i * 4
        
        -- Read sprite data from OAM
        local spr_x = emu.read(oam_addr, emu.memType.oam)
        local spr_y = emu.read(oam_addr + 1, emu.memType.oam)
        local tile = emu.read(oam_addr + 2, emu.memType.oam)
        local attr = emu.read(oam_addr + 3, emu.memType.oam)
        
        -- Read extra X bit and size bit from high table
        local high_table_addr = 0x200 + math.floor(i / 4)
        local high_table_byte = emu.read(high_table_addr, emu.memType.oam)
        local bit_pos = (i % 4) * 2
        local x_high = (high_table_byte >> bit_pos) & 1
        local size_bit = (high_table_byte >> (bit_pos + 1)) & 1
        
        -- Calculate actual position
        spr_x = spr_x + (x_high * 256)
        
        -- Determine sprite size based on registers
        local obj_size = emu.read(0x2101, emu.memType.cpu) >> 5
        local width, height
        
        if size_bit == 0 then
            -- Small sprite
            width = ({8, 8, 8, 16, 16, 32, 16, 16})[obj_size + 1]
            height = ({8, 8, 8, 16, 16, 32, 32, 32})[obj_size + 1]
        else
            -- Large sprite
            width = ({16, 32, 64, 32, 64, 64, 32, 32})[obj_size + 1]
            height = ({16, 32, 64, 32, 64, 64, 64, 32})[obj_size + 1]
        end
        
        -- Check if cursor is over this sprite
        if x >= spr_x and x < spr_x + width and
           y >= spr_y and y < spr_y + height then
            
            -- Get VRAM address for this tile
            local name_base = (emu.read(0x2101, emu.memType.cpu) & 0x07) * 0x2000
            local tile_vram = name_base + (tile * 32)  -- 32 bytes per 4bpp tile
            
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
    
    -- Return the highest priority sprite
    if #sprites > 0 then
        table.sort(sprites, function(a, b) 
            return a.priority > b.priority 
        end)
        return sprites[1]
    end
    
    return nil
end

-- ===============================================================================
-- HAL Compression Detection
-- ===============================================================================

local function detect_hal_compression(rom_offset)
    -- Read bytes at offset to check for HAL compression markers
    local marker1 = emu.read(rom_offset, emu.memType.cpuRom)
    local marker2 = emu.read(rom_offset + 1, emu.memType.cpuRom)
    
    -- HAL compression typically starts with specific patterns
    -- Common markers: 0x00-0x0F followed by size bytes
    if marker1 and marker1 <= 0x0F then
        -- Likely HAL compressed
        local size_low = marker2
        local size_high = emu.read(rom_offset + 2, emu.memType.cpuRom)
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
    emu.drawRectangle(5, panel_y, 250, 80, state.message_timer > 0 and 0xFF00FF00 or CONFIG.BG_COLOR, true)
    emu.drawRectangle(5, panel_y, 250, 80, CONFIG.INFO_COLOR, false)
    
    emu.drawString(10, panel_y + 5, "SpritePal Sprite Finder", CONFIG.INFO_COLOR)
    emu.drawString(10, panel_y + 20, state.message, CONFIG.INFO_COLOR)
    emu.drawString(10, panel_y + 35, "F9: Capture | C: Copy | S: Save", 0xFFAAAAAA)
    emu.drawString(10, panel_y + 50, "F10: Toggle | Mouse: " .. state.mouse_x .. "," .. state.mouse_y, 0xFFAAAAAA)
    
    if state.selected_sprite then
        emu.drawString(10, panel_y + 65, "Sprites captured: " .. #state.sprite_map, 0xFF00FF00)
    end
    
    -- Highlight selected sprite
    if state.selected_sprite then
        local spr = state.selected_sprite
        emu.drawRectangle(spr.x, spr.y, spr.width, spr.height, CONFIG.HIGHLIGHT_COLOR, false)
        emu.drawRectangle(spr.x-1, spr.y-1, spr.width+2, spr.height+2, CONFIG.HIGHLIGHT_COLOR, false)
        
        -- Draw sprite info box
        local info_x = math.min(spr.x + spr.width + 5, 200)
        local info_y = spr.y
        
        emu.drawRectangle(info_x, info_y, 120, 85, CONFIG.BG_COLOR, true)
        emu.drawRectangle(info_x, info_y, 120, 85, CONFIG.HIGHLIGHT_COLOR, false)
        
        emu.drawString(info_x + 3, info_y + 3, "Sprite #" .. spr.index, CONFIG.INFO_COLOR)
        emu.drawString(info_x + 3, info_y + 15, "Tile: $" .. string.format("%02X", spr.tile), CONFIG.INFO_COLOR)
        emu.drawString(info_x + 3, info_y + 27, "Size: " .. spr.width .. "x" .. spr.height, CONFIG.INFO_COLOR)
        
        if spr.rom_source then
            emu.drawString(info_x + 3, info_y + 39, "ROM: " .. string.format("0x%06X", spr.rom_source.rom_offset), 0xFF00FF00)
            emu.drawString(info_x + 3, info_y + 51, "Src: " .. spr.rom_source.source, 0xFFAAAAAA)
            
            -- Check for HAL compression
            local is_hal, comp_size = detect_hal_compression(spr.rom_source.rom_offset)
            if is_hal then
                emu.drawString(info_x + 3, info_y + 63, "HAL: " .. comp_size .. " bytes", 0xFFFFFF00)
            end
        else
            emu.drawString(info_x + 3, info_y + 39, "ROM: Unknown", 0xFFFF0000)
            emu.drawString(info_x + 3, info_y + 51, "Run DMA trace", 0xFFAAAAAA)
        end
    end
    
    -- Draw recent DMA transfers (debug info)
    if #state.dma_log > 0 and emu.getInput().isKeyPressed("Tab") then
        emu.drawRectangle(260, 10, 200, 150, CONFIG.BG_COLOR, true)
        emu.drawString(265, 15, "Recent DMA Transfers:", CONFIG.INFO_COLOR)
        
        for i = 1, math.min(8, #state.dma_log) do
            local dma = state.dma_log[i]
            local y = 30 + (i-1) * 15
            emu.drawString(265, y, dma.source .. "->" .. dma.vram, 0xFFAAAAAA)
            emu.drawString(365, y, dma.rom_offset_hex, 0xFF00FF00)
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
    local input = emu.getInput()
    
    -- Update mouse position
    state.mouse_x = input.getMouseX()
    state.mouse_y = input.getMouseY()
    
    -- Check for sprite under cursor
    local sprite = get_sprite_at_position(state.mouse_x, state.mouse_y)
    if sprite then
        state.selected_sprite = sprite
    end
    
    -- F9: Capture sprite
    if input.isKeyPressed(CONFIG.CAPTURE_KEY) then
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
                frame = emu.getState().ppu.frameCount
            }
            
            -- Check for HAL compression
            local is_hal, comp_size = detect_hal_compression(entry.rom_offset)
            if is_hal then
                entry.hal_compressed = true
                entry.compressed_size = comp_size
            end
            
            table.insert(state.sprite_map, entry)
            
            state.message = "Captured sprite #" .. #state.sprite_map .. " at " .. entry.rom_offset_hex
            state.message_timer = 120
            
            -- Log to console
            emu.log("Sprite captured: " .. entry.rom_offset_hex .. " (" .. entry.size .. ")")
        else
            state.message = "No sprite data - trigger DMA first!"
            state.message_timer = 120
        end
    end
    
    -- C: Copy offset to clipboard
    if input.isKeyPressed(CONFIG.COPY_KEY) then
        if state.selected_sprite and state.selected_sprite.rom_source then
            local offset_text = string.format("0x%06X", state.selected_sprite.rom_source.rom_offset)
            -- Note: Mesen-S doesn't have clipboard API, so we'll log it
            emu.log("ROM Offset: " .. offset_text .. " (copy this value)")
            state.message = "Offset logged: " .. offset_text
            state.message_timer = 120
        end
    end
    
    -- S: Save sprite map
    if input.isKeyPressed(CONFIG.SAVE_KEY) then
        save_sprite_map()
    end
    
    -- F10: Toggle overlay
    if input.isKeyPressed(CONFIG.TOGGLE_KEY) then
        state.enabled = not state.enabled
    end
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
    json = json .. '  "rom": "' .. emu.getRomInfo().name .. '",\n'
    json = json .. '  "captured_at": "' .. os.date() .. '",\n'
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
        json = json .. '      "frame": ' .. sprite.frame
        
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
    emu.log("=== SPRITE MAP JSON ===")
    emu.log(json)
    emu.log("=== END SPRITE MAP ===")
    
    state.message = "Sprite map saved to log (" .. #state.sprite_map .. " sprites)"
    state.message_timer = 180
end

-- ===============================================================================
-- Main Loop
-- ===============================================================================

-- Register callbacks
emu.addEventCallback(function()
    -- Track DMA on every frame
    track_dma_transfer()
end, emu.eventType.startFrame)

emu.addEventCallback(function()
    -- Handle input and draw overlay
    handle_input()
    draw_overlay()
end, emu.eventType.endFrame)

-- Initialize
emu.log("SpritePal Sprite Finder loaded!")
emu.log("F9: Capture sprite | C: Copy offset | S: Save map | F10: Toggle")
state.message = "Sprite Finder ready!"
state.message_timer = 180