-- Mesen 2 Enhanced Sprite Finder with Visual Feedback
-- Features: On-screen HUD, hotkey controls, better file management, visual feedback

emu.log("=== Enhanced Sprite Finder Starting ===")
emu.log("Controls: 1=Start/Resume, 2=Pause, 3=Export, 4=Reset, 5=Toggle HUD, 6=Toggle Offsets")

-- Configuration
local config = {
    -- Visual settings
    hud_enabled = true,
    hud_x = 10,
    hud_y = 10,
    hud_bg_color = 0x80000000,  -- Semi-transparent black
    hud_text_color = 0xFFFFFFFF, -- White
    highlight_sprites = true,
    show_offsets = true,  -- Display ROM offsets next to sprites
    offset_text_color = 0xFFFFFF00,  -- Bright yellow text for maximum visibility
    offset_bg_color = 0xFF880088,  -- Solid purple background for contrast
    offset_border_color = 0xFFFFFF00,  -- Yellow border to match text
    offset_line_color = 0xFFFFFF00,  -- Yellow line connecting to sprite
    
    -- Colors for sprite highlighting
    color_captured = 0x8000FF00,   -- Green (captured)
    color_detected = 0x80FFFF00,   -- Yellow (detected)
    color_missing = 0x80FF0000,    -- Red (no DMA)
    
    -- Hotkeys (Number keys to avoid savestate conflicts)
    key_start = "1",
    key_pause = "2", 
    key_export = "3",
    key_reset = "4",
    key_toggle_hud = "5",
    key_toggle_offsets = "6",
    
    -- File settings
    use_timestamp = true,
    max_backups = 5
}

-- Global state
local state = {
    -- Core tracking
    frame_count = 0,
    capture_active = false,
    dma_captures = {},
    active_sprites = {},
    unique_rom_offsets = {},
    sprite_rom_map = {},  -- sprite_id -> rom_offset for highlighting
    
    -- OBSEL config
    obsel_config = nil,
    
    -- Statistics
    stats = {
        total_dma = 0,
        vram_dma = 0,
        sprites_found = 0,
        sprites_captured = 0,
        rom_offsets_found = 0,
        session_start_frame = 0
    },
    
    -- UI state
    messages = {},  -- On-screen messages
    last_export_file = "",
    
    -- Callbacks
    callbacks = {}
}

-- Constants
local DMA_ENABLE = 0x420B
local HDMA_ENABLE = 0x420C  
local DMA_BASE = 0x4300
local OBSEL = 0x2101
local VRAM_ADDR_L = 0x2116
local VRAM_ADDR_H = 0x2117

-- Helper: Get script data folder
local function get_output_path()
    local folder = emu.getScriptDataFolder()
    if not folder or folder == "" then
        folder = "."  -- Fallback to current directory
    end
    return folder
end

-- Helper: Generate filename with timestamp
local function generate_filename(base_name, extension)
    if config.use_timestamp then
        local timestamp = os.date("%Y%m%d_%H%M%S")
        return string.format("%s_%s.%s", base_name, timestamp, extension)
    else
        return string.format("%s.%s", base_name, extension)
    end
end

-- Helper: Add on-screen message
local function add_message(text, duration)
    duration = duration or 180  -- Default 3 seconds
    table.insert(state.messages, {
        text = text,
        frames_left = duration,
        y_offset = 0
    })
    emu.log("MSG: " .. text)
end

-- Helper: Convert CPU address to ROM offset
local function cpu_to_rom_offset(cpu_addr)
    local bank = (cpu_addr >> 16) & 0xFF
    local addr = cpu_addr & 0xFFFF
    
    if addr < 0x8000 then return nil end
    if bank == 0x7E or bank == 0x7F then return nil end
    
    if bank >= 0x80 then
        local rom_offset = ((bank & 0x7F) * 0x8000) + (addr - 0x8000)
        return rom_offset
    end
    
    return nil
end

-- Helper: Read DMA channel
local function read_dma_channel(channel)
    local base = DMA_BASE + (channel * 0x10)
    
    local control = emu.read(base + 0x00, emu.memType.snesMemory)
    local dest_reg = emu.read(base + 0x01, emu.memType.snesMemory)
    local src_low = emu.read(base + 0x02, emu.memType.snesMemory)
    local src_mid = emu.read(base + 0x03, emu.memType.snesMemory)
    local src_bank = emu.read(base + 0x04, emu.memType.snesMemory)
    local size_low = emu.read(base + 0x05, emu.memType.snesMemory)
    local size_high = emu.read(base + 0x06, emu.memType.snesMemory)
    
    local source_addr = (src_bank << 16) | (src_mid << 8) | src_low
    local transfer_size = (size_high << 8) | size_low
    if transfer_size == 0 then
        transfer_size = 0x10000
    end
    
    return {
        control = control,
        dest_reg = dest_reg,
        source_addr = source_addr,
        source_bank = src_bank,
        transfer_size = transfer_size
    }
end

-- Update OBSEL
local function update_obsel()
    local obsel = emu.read(OBSEL, emu.memType.snesMemory)
    state.obsel_config = {
        name_base = obsel & 0x07,
        name_select = (obsel >> 3) & 0x03,
        size_select = (obsel >> 5) & 0x07,
        raw = obsel
    }
end

-- DMA callback
local function on_dma_enable_write(address, value)
    if value == 0 or not state.capture_active then return end
    
    state.stats.total_dma = state.stats.total_dma + 1
    
    local vram_low = emu.read(VRAM_ADDR_L, emu.memType.snesMemory)
    local vram_high = emu.read(VRAM_ADDR_H, emu.memType.snesMemory)
    local vram_addr = (vram_high << 8) | vram_low
    
    for channel = 0, 7 do
        if (value & (1 << channel)) ~= 0 then
            local dma = read_dma_channel(channel)
            
            -- Process VRAM transfers
            if dma.dest_reg == 0x18 or dma.dest_reg == 0x19 then
                if dma.source_bank >= 0x80 then
                    local rom_offset = cpu_to_rom_offset(dma.source_addr)
                    
                    if rom_offset then
                        state.stats.vram_dma = state.stats.vram_dma + 1
                        
                        -- Track capture
                        local capture = {
                            frame = state.frame_count,
                            vram_addr = vram_addr * 2,
                            rom_offset = rom_offset,
                            size = dma.transfer_size
                        }
                        table.insert(state.dma_captures, capture)
                        
                        -- Track unique offsets
                        if not state.unique_rom_offsets[rom_offset] then
                            state.unique_rom_offsets[rom_offset] = {
                                first_frame = state.frame_count,
                                hit_count = 0
                            }
                            state.stats.rom_offsets_found = state.stats.rom_offsets_found + 1
                            
                            -- Milestone messages
                            if state.stats.rom_offsets_found % 10 == 0 then
                                add_message(string.format("%d ROM offsets found!", 
                                    state.stats.rom_offsets_found))
                            end
                        end
                        
                        state.unique_rom_offsets[rom_offset].hit_count = 
                            state.unique_rom_offsets[rom_offset].hit_count + 1
                    end
                end
            end
        end
    end
end

-- Analyze OAM
local function analyze_oam()
    local oam_data = {}
    for i = 0, 543 do
        oam_data[i] = emu.read(i, emu.memType.snesSpriteRam)
    end
    
    state.active_sprites = {}
    for i = 0, 127 do
        local base = i * 4
        local x = oam_data[base]
        local y = oam_data[base + 1]
        local tile = oam_data[base + 2]
        local attr = oam_data[base + 3]
        
        -- Get X MSB and size
        local high_byte_index = 512 + math.floor(i / 4)
        local high_bit_index = (i % 4) * 2
        local high_byte = oam_data[high_byte_index]
        local x_msb = (high_byte >> high_bit_index) & 0x01
        local size_bit = (high_byte >> (high_bit_index + 1)) & 0x01
        
        x = x | (x_msb * 256)
        
        if y < 224 or y >= 240 then
            local sprite = {
                id = i,
                x = x,
                y = y,
                tile = tile,
                attr = attr,
                size_bit = size_bit
            }
            
            if state.obsel_config then
                local name_base = state.obsel_config.name_base * 0x2000
                sprite.vram_addr = name_base + (tile * 32)
                
                -- Sprite size
                local size_select = state.obsel_config.size_select
                local sizes = {
                    [0] = {8, 16}, [1] = {8, 32}, [2] = {8, 64},
                    [3] = {16, 32}, [4] = {16, 64}, [5] = {32, 64},
                    [6] = {16, 32}, [7] = {16, 32}
                }
                local size_pair = sizes[size_select] or {8, 16}
                sprite.width = size_pair[size_bit + 1]
                sprite.height = sprite.width
            end
            
            table.insert(state.active_sprites, sprite)
        end
    end
    
    state.stats.sprites_found = math.max(state.stats.sprites_found, #state.active_sprites)
end

-- Correlate sprites with DMA
local function correlate_sprites_and_dma()
    if not state.obsel_config or #state.dma_captures == 0 then return end
    
    for _, sprite in ipairs(state.active_sprites) do
        if sprite.vram_addr then
            local sprite_vram_start = sprite.vram_addr
            local sprite_vram_end = sprite_vram_start + ((sprite.width / 8) * (sprite.height / 8) * 32)
            
            -- Check recent DMA captures
            for i = #state.dma_captures, math.max(1, #state.dma_captures - 100), -1 do
                local capture = state.dma_captures[i]
                
                if capture.vram_addr and capture.rom_offset then
                    local dma_start = capture.vram_addr
                    local dma_end = dma_start + capture.size
                    
                    -- Check overlap
                    if dma_start < sprite_vram_end and dma_end > sprite_vram_start then
                        -- Map sprite to ROM offset
                        if not state.sprite_rom_map[sprite.id] then
                            state.sprite_rom_map[sprite.id] = capture.rom_offset
                            state.stats.sprites_captured = state.stats.sprites_captured + 1
                            
                            -- Milestone message
                            if state.stats.sprites_captured % 25 == 0 then
                                add_message(string.format("%d sprites captured!", 
                                    state.stats.sprites_captured))
                            end
                        end
                        break
                    end
                end
            end
        end
    end
end

-- Draw HUD
local function draw_hud()
    if not config.hud_enabled then return end
    
    local x = config.hud_x
    local y = config.hud_y
    
    -- Background box
    emu.drawRectangle(x - 2, y - 2, 200, 80, config.hud_bg_color, true)
    
    -- Title
    emu.drawString(x, y, "SPRITE CAPTURE", config.hud_text_color, 0xFF000000)
    y = y + 10
    
    -- Status
    local status_text = state.capture_active and "ACTIVE" or "PAUSED"
    local status_color = state.capture_active and 0xFF00FF00 or 0xFFFFFF00
    emu.drawString(x, y, "Status: " .. status_text, status_color, 0xFF000000)
    y = y + 10
    
    -- Statistics
    emu.drawString(x, y, string.format("Sprites: %d/%d", 
        state.stats.sprites_captured, state.stats.sprites_found), 
        config.hud_text_color, 0xFF000000)
    y = y + 10
    
    emu.drawString(x, y, string.format("ROM Offsets: %d", 
        state.stats.rom_offsets_found), 
        config.hud_text_color, 0xFF000000)
    y = y + 10
    
    emu.drawString(x, y, string.format("DMA Captures: %d", 
        state.stats.vram_dma), 
        config.hud_text_color, 0xFF000000)
    y = y + 10
    
    -- Time running
    local seconds = (state.frame_count - state.stats.session_start_frame) / 60
    emu.drawString(x, y, string.format("Time: %.1fs", seconds), 
        config.hud_text_color, 0xFF000000)
end

-- Draw sprite highlights
local function draw_sprite_highlights()
    if not config.highlight_sprites then return end
    
    for _, sprite in ipairs(state.active_sprites) do
        local color = config.color_missing  -- Default red
        local rom_offset = state.sprite_rom_map[sprite.id]
        
        if rom_offset then
            color = config.color_captured  -- Green if captured
        elseif sprite.vram_addr then
            color = config.color_detected  -- Yellow if detected
        end
        
        -- Adjust for screen position
        if sprite.x < 256 and sprite.y < 224 then
            emu.drawRectangle(sprite.x, sprite.y, 
                sprite.width or 8, sprite.height or 8, 
                color, false)
            
            -- Draw ROM offset above captured sprites with prominent label
            if config.show_offsets and rom_offset then
                local offset_text = string.format("$%06X", rom_offset)
                
                -- Position label above sprite
                local label_width = 56
                local label_height = 16
                local text_x = sprite.x + ((sprite.width or 8) / 2) - (label_width / 2)
                local text_y = sprite.y - label_height - 8
                
                -- Ensure label stays on screen
                if text_x < 2 then
                    text_x = 2
                elseif text_x + label_width > 254 then
                    text_x = 254 - label_width
                end
                
                if text_y < 2 then
                    text_y = sprite.y + (sprite.height or 8) + 4
                end
                
                -- Draw connecting line from sprite to label
                local sprite_center_x = sprite.x + ((sprite.width or 8) / 2)
                local sprite_top_y = sprite.y
                local label_center_x = text_x + (label_width / 2)
                local label_bottom_y = text_y + label_height
                
                if text_y < sprite.y then
                    -- Label is above sprite
                    emu.drawLine(sprite_center_x, sprite_top_y, label_center_x, label_bottom_y, 
                        config.offset_line_color)
                end
                
                -- Draw large bordered box with thick border
                -- Outer border (3 pixels thick)
                emu.drawRectangle(text_x - 3, text_y - 3, label_width + 6, label_height + 6, 
                    config.offset_border_color, true)
                -- Inner background
                emu.drawRectangle(text_x, text_y, label_width, label_height, 
                    config.offset_bg_color, true)
                
                -- Draw the offset text centered in the box
                emu.drawString(text_x + 4, text_y + 4, offset_text, 
                    config.offset_text_color, 0x00000000)
            end
        end
    end
end

-- Draw messages
local function draw_messages()
    local y = 200
    
    for i = #state.messages, 1, -1 do
        local msg = state.messages[i]
        if msg.frames_left > 0 then
            -- Fade effect
            local alpha = math.min(msg.frames_left, 60) / 60
            local color = (math.floor(alpha * 255) << 24) | 0xFFFFFF
            
            emu.drawString(10, y - msg.y_offset, msg.text, color, 0x80000000)
            
            msg.frames_left = msg.frames_left - 1
            msg.y_offset = msg.y_offset + 0.5  -- Slide up
            y = y - 12
        else
            table.remove(state.messages, i)
        end
    end
end

-- Export data
function export_data()
    local output_dir = get_output_path()
    local filename = generate_filename("sprite_capture", "txt")
    local filepath = output_dir .. "/" .. filename
    
    -- Text output
    local output = "=== Enhanced Sprite Finder Results ===\n"
    output = output .. string.format("Capture Time: %.1f seconds\n", 
        (state.frame_count - state.stats.session_start_frame) / 60)
    output = output .. string.format("Sprites Captured: %d/%d\n",
        state.stats.sprites_captured, state.stats.sprites_found)
    output = output .. string.format("ROM Offsets Found: %d\n",
        state.stats.rom_offsets_found)
    output = output .. "\n--- ROM Offsets ---\n"
    
    local sorted = {}
    for offset, data in pairs(state.unique_rom_offsets) do
        table.insert(sorted, {offset = offset, hits = data.hit_count})
    end
    table.sort(sorted, function(a, b) return a.hits > b.hits end)
    
    for i, entry in ipairs(sorted) do
        if i > 50 then break end
        output = output .. string.format("$%06X: %d hits\n", 
            entry.offset, entry.hits)
    end
    
    local file = io.open(filepath, "w")
    if file then
        file:write(output)
        file:close()
        state.last_export_file = filename
        add_message("Exported: " .. filename, 240)
        emu.log("Exported to: " .. filepath)
    end
    
    -- JSON export
    local json_file = generate_filename("sprite_capture", "json")
    local json_path = output_dir .. "/" .. json_file
    export_json(json_path)
end

-- Export JSON
function export_json(filepath)
    local json_data = {
        metadata = {
            capture_time = (state.frame_count - state.stats.session_start_frame) / 60,
            sprites_captured = state.stats.sprites_captured,
            rom_offsets_found = state.stats.rom_offsets_found
        },
        rom_offsets = {}
    }
    
    for offset, data in pairs(state.unique_rom_offsets) do
        table.insert(json_data.rom_offsets, {
            offset = offset,
            hits = data.hit_count
        })
    end
    
    -- Simple JSON serialization
    local function to_json(t, indent)
        indent = indent or 0
        local spaces = string.rep("  ", indent)
        
        if type(t) == "table" then
            local is_array = #t > 0
            local result = is_array and "[\n" or "{\n"
            local first = true
            
            if is_array then
                for i, v in ipairs(t) do
                    if not first then result = result .. ",\n" end
                    result = result .. spaces .. "  " .. to_json(v, indent + 1)
                    first = false
                end
            else
                for k, v in pairs(t) do
                    if not first then result = result .. ",\n" end
                    result = result .. spaces .. '  "' .. k .. '": ' .. to_json(v, indent + 1)
                    first = false
                end
            end
            
            result = result .. "\n" .. spaces .. (is_array and "]" or "}")
            return result
        elseif type(t) == "string" then
            return '"' .. t .. '"'
        else
            return tostring(t)
        end
    end
    
    local file = io.open(filepath, "w")
    if file then
        file:write(to_json(json_data))
        file:close()
    end
end

-- Handle hotkeys
local function handle_hotkeys()
    -- 1: Start/Resume
    if emu.isKeyPressed(config.key_start) then
        if not state.capture_active then
            state.capture_active = true
            state.stats.session_start_frame = state.frame_count
            add_message("Capture STARTED")
        end
    end
    
    -- 2: Pause
    if emu.isKeyPressed(config.key_pause) then
        if state.capture_active then
            state.capture_active = false
            add_message("Capture PAUSED")
        end
    end
    
    -- 3: Export
    if emu.isKeyPressed(config.key_export) then
        export_data()
    end
    
    -- 4: Reset
    if emu.isKeyPressed(config.key_reset) then
        state.dma_captures = {}
        state.unique_rom_offsets = {}
        state.sprite_rom_map = {}
        state.stats.sprites_captured = 0
        state.stats.rom_offsets_found = 0
        state.stats.vram_dma = 0
        add_message("Capture data RESET")
    end
    
    -- 5: Toggle HUD
    if emu.isKeyPressed(config.key_toggle_hud) then
        config.hud_enabled = not config.hud_enabled
        add_message(config.hud_enabled and "HUD ON" or "HUD OFF")
    end
    
    -- 6: Toggle Offset Display
    if emu.isKeyPressed(config.key_toggle_offsets) then
        config.show_offsets = not config.show_offsets
        add_message(config.show_offsets and "Offsets ON" or "Offsets OFF")
    end
end

-- Frame callback
local function on_frame_end()
    state.frame_count = state.frame_count + 1
    
    -- Handle input
    handle_hotkeys()
    
    -- Update OBSEL
    update_obsel()
    
    -- Analyze sprites
    analyze_oam()
    
    -- Correlate if capturing
    if state.capture_active then
        correlate_sprites_and_dma()
    end
    
    -- Draw visual elements
    draw_sprite_highlights()
    draw_hud()
    draw_messages()
    
    -- Auto-export every 30 seconds
    if state.capture_active and state.frame_count % 1800 == 0 then
        export_data()
    end
end

-- Initialize
function init()
    emu.log("Enhanced Sprite Finder initialized!")
    emu.log("Press 1 to start capture")
    
    -- DMA callback
    state.callbacks.dma = emu.addMemoryCallback(
        on_dma_enable_write,
        emu.callbackType.write,
        DMA_ENABLE,
        DMA_ENABLE
    )
    
    -- Frame callback
    state.callbacks.frame = emu.addEventCallback(
        on_frame_end,
        emu.eventType.endFrame
    )
    
    update_obsel()
    
    add_message("Enhanced Sprite Finder Ready!", 300)
    add_message("1=Start 2=Pause 3=Export 6=Offsets", 300)
end

-- Start
init()