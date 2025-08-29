-- Mesen 2 Enhanced Sprite Finder with PRECISE ROM Offset Calculation
-- Features: Calculates exact ROM offset for each sprite's specific tiles
-- FIX: Shows unique ROM offsets for each sprite based on their tile position

emu.log("=== Sprite Finder with Precise Offsets ===")
emu.log("ALWAYS ACTIVE MODE - Capture & Debug permanently enabled")
emu.log("Controls: 3=Export, 4=Reset, 5=HUD, 6=Show Offsets, S=Display, C=Copy, E=Session")

-- Configuration
local config = {
    -- Visual settings
    hud_enabled = true,
    hud_x = 10,
    hud_y = 10,
    hud_bg_color = 0x80000000,  -- Semi-transparent black (80 = half transparent)
    hud_text_color = 0x00FFFFFF, -- Opaque white
    highlight_sprites = true,
    show_offsets = false,  -- Display ROM offsets continuously (off by default to prevent accumulation)
    offset_text_color = 0xFF000000,  -- Black text (0xFF = opaque)
    offset_bg_color = 0xFFFFFF00,  -- Yellow background (0xFF = opaque)
    offset_border_color = 0xFFFF0000,  -- Red border (0xFF = opaque)
    offset_line_color = 0xFFFF0000,  -- Red line connecting to sprite
    offset_shadow_color = 0xFFFFFFFF, -- White shadow (not currently used)
    debug_logging = true,  -- DEBUG ENABLED BY DEFAULT for offset calculations
    
    -- Colors for sprite highlighting
    color_captured = 0x8000FF00,   -- Semi-transparent green (captured)
    color_detected = 0x80FFFF00,   -- Semi-transparent yellow (detected)
    color_missing = 0x80FF0000,    -- Semi-transparent red (no DMA)
    
    -- Hotkeys (Number keys to avoid savestate conflicts)
    key_start = "1",
    key_pause = "2", 
    key_export = "3",
    key_reset = "4",
    key_toggle_hud = "5",
    key_toggle_offsets = "6",
    key_toggle_debug = "7",  -- Toggle debug logging
    
    -- File settings
    use_timestamp = true,
    max_backups = 5
}

-- Global state
local state = {
    -- Core tracking
    frame_count = 0,
    capture_active = true,  -- AUTO-CAPTURE ENABLED
    dma_captures = {},
    active_sprites = {},
    unique_rom_offsets = {},
    sprite_rom_map = {},  -- sprite_id -> rom_offset for highlighting
    persistent_rom_map = {},  -- Persistent mapping by tile+palette key to avoid duplicate offsets
    
    -- ROM->RAM decompression tracking
    rom_to_ram_map = {},  -- Maps RAM addresses to their ROM sources
    recent_decompressions = {},  -- Track recent decompression operations
    
    -- OBSEL config
    obsel_config = nil,
    
    -- Statistics
    stats = {
        total_dma = 0,
        vram_dma = 0,
        sprites_found = 0,
        sprites_captured = 0,
        rom_offsets_found = 0,
        unique_sprite_offsets = {},  -- Track unique sprite-specific offsets
        session_start_frame = 0,  -- Will be set on first frame
        ram_transfers_tracked = 0,
        ram_to_vram_resolved = 0
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
    
    -- Must be in ROM address range ($8000-$FFFF)
    if addr < 0x8000 then return nil end
    
    -- Exclude RAM banks
    if bank == 0x7E or bank == 0x7F then return nil end
    
    -- CRITICAL FIX: Only accept valid ROM banks!
    -- Banks 0x00-0x3F and 0x80-0xBF are ROM in LoROM
    -- Banks 0xC0-0xFF are NOT ROM (typically RAM or unmapped)
    if bank >= 0x80 and bank <= 0xBF then
        -- LoROM mapping: banks 0x80-0xBF mirror 0x00-0x3F
        local rom_offset = ((bank & 0x3F) * 0x8000) + (addr - 0x8000)
        -- IMPORTANT: Add 0x200 (512) if your ROM file has an SMC header
        -- Uncomment the next line if SpritePal shows sprites 512 bytes off:
        -- rom_offset = rom_offset + 0x200
        return rom_offset
    elseif bank <= 0x3F then
        -- Lower ROM banks (0x00-0x3F)
        local rom_offset = (bank * 0x8000) + (addr - 0x8000)
        -- rom_offset = rom_offset + 0x200  -- Uncomment for SMC header
        return rom_offset
    end
    
    -- Invalid bank for ROM access
    if config.debug_logging then
        emu.log(string.format("WARNING: DMA from invalid ROM bank $%02X (addr: $%06X)", bank, cpu_addr))
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
    if value == 0 then 
        if config.debug_logging then
            emu.log("[DEBUG] DMA enable write with value 0, ignoring")
        end
        return 
    end
    
    if not state.capture_active then 
        if config.debug_logging then
            emu.log("[DEBUG] DMA detected but capture not active")
        end
        return 
    end
    
    state.stats.total_dma = state.stats.total_dma + 1
    
    -- DEBUG: Log DMA trigger
    if config.debug_logging then
        emu.log(string.format("[DEBUG] === DMA TRIGGERED === value: 0x%02X, total_dma: %d", 
            value, state.stats.total_dma))
    end
    
    local vram_low = emu.read(VRAM_ADDR_L, emu.memType.snesMemory)
    local vram_high = emu.read(VRAM_ADDR_H, emu.memType.snesMemory)
    local vram_addr = (vram_high << 8) | vram_low
    
    for channel = 0, 7 do
        if (value & (1 << channel)) ~= 0 then
            local dma = read_dma_channel(channel)
            
            -- DEBUG: Log every DMA channel that's active
            if config.debug_logging then
                emu.log(string.format("[DEBUG] Ch%d ACTIVE: src=$%06X (bank $%02X), dest_reg=$%02X, size=$%04X",
                    channel, dma.source_addr, dma.source_bank, dma.dest_reg, dma.transfer_size))
            end
            
            -- First, check if this is a ROM->RAM transfer (decompression)
            -- RAM registers are typically 0x00-0x3F (PPU/CPU registers) or direct writes
            local is_ram_destination = (dma.dest_reg >= 0x00 and dma.dest_reg <= 0x3F)
            local source_bank = dma.source_bank
            
            -- Track ROM->RAM transfers (likely decompression operations)
            if is_ram_destination and source_bank >= 0x80 and source_bank <= 0xBF then
                -- This is ROM->RAM transfer (decompression)
                local rom_source = cpu_to_rom_offset(dma.source_addr)
                if rom_source then
                    -- Calculate RAM destination address
                    local ram_dest = dma.dest_reg  -- This might need adjustment based on the specific register
                    
                    -- Store the mapping
                    state.rom_to_ram_map[ram_dest] = {
                        rom_offset = rom_source,
                        frame = state.frame_count,
                        size = dma.transfer_size
                    }
                    
                    state.stats.ram_transfers_tracked = state.stats.ram_transfers_tracked + 1
                    
                    if config.debug_logging then
                        emu.log(string.format("ROM->RAM: ROM $%06X -> RAM (size: $%04X) [Decompression?]",
                            rom_source, dma.transfer_size))
                    end
                    
                    -- Clean old entries (keep only last 100 frames)
                    for addr, info in pairs(state.rom_to_ram_map) do
                        if state.frame_count - info.frame > 100 then
                            state.rom_to_ram_map[addr] = nil
                        end
                    end
                end
            end
            
            -- Process VRAM transfers (sprite display)
            if dma.dest_reg == 0x18 or dma.dest_reg == 0x19 then
                if config.debug_logging then
                    emu.log(string.format("[DEBUG] VRAM transfer detected on Ch%d to reg $%02X", 
                        channel, dma.dest_reg))
                end
                
                local rom_offset = nil
                
                -- Check if source is RAM (banks 0x7E-0x7F or 0xC0-0xFF)
                if (source_bank >= 0x7E and source_bank <= 0x7F) or 
                   (source_bank >= 0xC0 and source_bank <= 0xFF) then
                    -- RAM->VRAM transfer - try to find original ROM source
                    if config.debug_logging then
                        emu.log(string.format("[DEBUG] RAM->VRAM transfer from bank $%02X (RAM)", source_bank))
                    end
                    local ram_addr = dma.source_addr & 0xFFFF  -- Get just the address part
                    
                    -- Look for recent ROM->RAM transfer to this address
                    for stored_addr, info in pairs(state.rom_to_ram_map) do
                        -- Check if this RAM region matches a recent decompression
                        if math.abs(stored_addr - ram_addr) < 0x8000 then  -- Within reasonable range
                            rom_offset = info.rom_offset
                            state.stats.ram_to_vram_resolved = state.stats.ram_to_vram_resolved + 1
                            
                            if config.debug_logging then
                                emu.log(string.format("RAM->VRAM resolved: RAM $%06X -> VRAM $%04X (Original ROM: $%06X)",
                                    dma.source_addr, vram_addr, rom_offset))
                            end
                            break
                        end
                    end
                    
                    -- NEW: Even if we can't trace to ROM, still capture the RAM address
                    -- This allows us to at least track sprite locations in RAM
                    if not rom_offset then
                        -- Use RAM address as a pseudo-offset for tracking
                        -- Mark it with high bit set to distinguish from real ROM offsets
                        rom_offset = 0x800000 | (dma.source_addr & 0x7FFFFF)  -- Mark as RAM-based
                        
                        if config.debug_logging then
                            emu.log(string.format("[DEBUG] Capturing RAM sprite at $%06X as pseudo-offset $%06X",
                                dma.source_addr, rom_offset))
                        end
                    end
                elseif source_bank >= 0x80 and source_bank <= 0xBF then
                    -- Direct ROM->VRAM transfer (upper banks)
                    if config.debug_logging then
                        emu.log(string.format("[DEBUG] ROM->VRAM transfer from bank $%02X (valid upper ROM bank)", source_bank))
                    end
                    rom_offset = cpu_to_rom_offset(dma.source_addr)
                    if config.debug_logging then
                        if rom_offset then
                            emu.log(string.format("[DEBUG] Calculated ROM offset: $%06X", rom_offset))
                        else
                            emu.log("[DEBUG] Failed to calculate ROM offset (cpu_to_rom_offset returned nil)")
                        end
                    end
                elseif source_bank <= 0x3F then
                    -- Lower ROM banks (0x00-0x3F)
                    if config.debug_logging then
                        emu.log(string.format("[DEBUG] ROM->VRAM transfer from bank $%02X (valid lower ROM bank)", source_bank))
                    end
                    rom_offset = cpu_to_rom_offset(dma.source_addr)
                    if config.debug_logging then
                        if rom_offset then
                            emu.log(string.format("[DEBUG] Calculated ROM offset from lower bank: $%06X", rom_offset))
                        else
                            emu.log("[DEBUG] Failed to calculate ROM offset from lower bank")
                        end
                    end
                else
                    if config.debug_logging then
                        emu.log(string.format("[DEBUG] Bank $%02X not in valid range (not 0x00-3F, 0x7E-7F, 0x80-BF, or 0xC0-FF)", source_bank))
                    end
                end
                
                -- Process the VRAM transfer if we have a valid ROM offset
                if rom_offset then
                    if config.debug_logging then
                        emu.log(string.format("[DEBUG] ✓ CAPTURING: ROM offset $%06X -> VRAM $%04X", 
                            rom_offset, vram_addr))
                    end
                    state.stats.vram_dma = state.stats.vram_dma + 1
                    
                    -- Track capture with detailed info
                    local capture = {
                        frame = state.frame_count,
                        vram_addr = vram_addr * 2,  -- Convert to byte address
                        rom_offset = rom_offset,
                        size = dma.transfer_size,
                        channel = channel
                    }
                    table.insert(state.dma_captures, capture)
                    
                    -- Limit DMA capture buffer to last 200 entries to save memory
                    if #state.dma_captures > 200 then
                        table.remove(state.dma_captures, 1)
                    end
                    
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
                    
                    if config.debug_logging then
                        emu.log(string.format("DMA Ch%d: ROM $%06X -> VRAM $%04X (size: $%04X)",
                            channel, rom_offset, vram_addr, dma.transfer_size))
                    end
                else
                    if config.debug_logging then
                        emu.log("[DEBUG] No valid ROM offset for this VRAM transfer, skipping capture")
                    end
                end
            else
                -- Not a VRAM transfer
                if config.debug_logging then
                    emu.log(string.format("[DEBUG] Non-VRAM transfer: dest_reg=$%02X (not $18/$19)", dma.dest_reg))
                end
            end
        end
    end
    
    if config.debug_logging and state.stats.total_dma % 10 == 0 then
        emu.log(string.format("[DEBUG] Status - Total DMA: %d, VRAM DMA: %d, ROM offsets: %d", 
            state.stats.total_dma, state.stats.vram_dma, state.stats.rom_offsets_found))
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
                size_bit = size_bit,
                palette = (attr >> 1) & 0x07,  -- Extract palette info
                priority = (attr >> 4) & 0x03  -- Extract priority
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
                
                -- Calculate tile count for this sprite
                sprite.tile_count = (sprite.width / 8) * (sprite.height / 8)
            end
            
            table.insert(state.active_sprites, sprite)
        end
    end
    
    state.stats.sprites_found = math.max(state.stats.sprites_found, #state.active_sprites)
end

-- Correlate sprites with DMA (PRECISE OFFSET CALCULATION)
local function correlate_sprites_and_dma()
    if not state.obsel_config or #state.dma_captures == 0 then return end
    
    for _, sprite in ipairs(state.active_sprites) do
        if sprite.vram_addr then
            local sprite_vram_start = sprite.vram_addr
            local sprite_vram_end = sprite_vram_start + (sprite.tile_count * 32)
            
            -- Check recent DMA captures (only last 100 for performance)
            for i = #state.dma_captures, math.max(1, #state.dma_captures - 100), -1 do
                local capture = state.dma_captures[i]
                
                -- Only consider very recent DMA (within last 60 frames)
                if capture.frame >= state.frame_count - 60 then
                    if capture.vram_addr and capture.rom_offset then
                        local dma_start = capture.vram_addr
                        local dma_end = dma_start + capture.size
                        
                        -- Check if sprite's VRAM range overlaps with DMA transfer
                        if sprite_vram_start >= dma_start and sprite_vram_start < dma_end then
                            -- PRECISE CALCULATION: Calculate the exact ROM offset for this sprite
                            -- The sprite's tiles are at a specific offset within the DMA transfer
                            local offset_within_dma = sprite_vram_start - dma_start
                            
                            -- Ensure we don't go beyond the DMA transfer size
                            if offset_within_dma < capture.size then
                                local precise_rom_offset = capture.rom_offset + offset_within_dma
                                
                                -- Map sprite to its precise ROM offset
                                state.sprite_rom_map[sprite.id] = precise_rom_offset
                                -- Also store in persistent map by tile+palette composite key for uniqueness
                                local persistent_key = string.format("%02X_%d", sprite.tile, sprite.palette)
                                state.persistent_rom_map[persistent_key] = precise_rom_offset
                                
                                -- Track unique sprite offsets
                                if not state.stats.unique_sprite_offsets[precise_rom_offset] then
                                    state.stats.unique_sprite_offsets[precise_rom_offset] = true
                                    state.stats.sprites_captured = state.stats.sprites_captured + 1
                                    
                                    if config.debug_logging then
                                        emu.log(string.format("Sprite %d: Tile %02X at VRAM $%04X -> ROM $%06X (DMA base $%06X + $%04X)",
                                            sprite.id, sprite.tile, sprite_vram_start, precise_rom_offset, 
                                            capture.rom_offset, offset_within_dma))
                                    end
                                    
                                    -- Milestone message
                                    if state.stats.sprites_captured % 25 == 0 then
                                        add_message(string.format("%d unique sprite offsets found!", 
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
    end
end

-- Draw HUD
local function draw_hud()
    if not config.hud_enabled then return end
    
    local x = config.hud_x
    local y = config.hud_y
    
    -- Increase height to show RAM tracking stats
    local hud_height = 110
    
    -- Background box
    emu.drawRectangle(x - 2, y - 2, 220, hud_height, config.hud_bg_color, true)
    
    -- Title
    emu.drawString(x, y, "SPRITE CAPTURE (PRECISE)", config.hud_text_color, 0xFF000000)
    y = y + 10
    
    -- Status
    local status_text = state.capture_active and "ACTIVE" or "PAUSED"
    local status_color = state.capture_active and 0xFF00FF00 or 0xFFFFFF00
    emu.drawString(x, y, "Status: " .. status_text, status_color, 0xFF000000)
    y = y + 10
    
    -- Statistics
    local unique_count = 0
    for _ in pairs(state.stats.unique_sprite_offsets) do
        unique_count = unique_count + 1
    end
    
    emu.drawString(x, y, string.format("Unique Offsets: %d", unique_count), 
        config.hud_text_color, 0xFF000000)
    y = y + 10
    
    emu.drawString(x, y, string.format("Active Sprites: %d", #state.active_sprites), 
        config.hud_text_color, 0xFF000000)
    y = y + 10
    
    emu.drawString(x, y, string.format("DMA Captures: %d", state.stats.vram_dma), 
        config.hud_text_color, 0xFF000000)
    y = y + 10
    
    -- RAM tracking stats (NEW)
    emu.drawString(x, y, string.format("RAM Transfers: %d", state.stats.ram_transfers_tracked), 
        config.hud_text_color, 0xFF000000)
    y = y + 10
    
    emu.drawString(x, y, string.format("RAM->VRAM Resolved: %d", state.stats.ram_to_vram_resolved), 
        config.hud_text_color, 0xFF000000)
    y = y + 10
    
    -- Time running
    local seconds = (state.frame_count - state.stats.session_start_frame) / 60
    emu.drawString(x, y, string.format("Time: %.1fs", seconds), 
        config.hud_text_color, 0xFF000000)
    y = y + 10
    
    -- Debug mode indicator
    if config.debug_logging then
        emu.drawString(x, y, "DEBUG MODE ON", 0xFFFF0000, 0xFF000000)
    end
end

-- Draw sprite highlights
local function draw_sprite_highlights()
    if not config.highlight_sprites then return end
    
    for _, sprite in ipairs(state.active_sprites) do
        local color = config.color_missing  -- Default red
        -- Try to get ROM offset from current mapping or persistent map with tile+palette key
        local persistent_key = string.format("%02X_%d", sprite.tile, sprite.palette)
        local rom_offset = state.sprite_rom_map[sprite.id] or state.persistent_rom_map[persistent_key]
        
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
            -- Show offsets for any sprite with a known ROM offset
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
                        config.offset_line_color, 2)  -- 2 frames display
                end
                
                -- Draw enhanced readable box with thick border
                -- Using frameCount=2 for brief display that refreshes each frame
                
                -- Outer border (red, 4 pixels thick)
                emu.drawRectangle(text_x - 4, text_y - 4, label_width + 8, label_height + 8, 
                    0xFFFF0000, true, 2)  -- Red border, 2 frames
                
                -- Inner background (yellow)
                emu.drawRectangle(text_x - 1, text_y - 1, label_width + 2, label_height + 2, 
                    0xFFFFFF00, true, 2)  -- Yellow background, 2 frames
                
                -- Draw the offset text with proper opaque black color
                emu.drawString(text_x + 4, text_y + 4, offset_text, 
                    0xFF000000, 0, 0, 2)  -- Black text, 2 frames
                
                -- Add tile number in corner if debug mode
                if config.debug_logging then
                    local tile_text = string.format("T:%02X", sprite.tile)
                    emu.drawString(sprite.x, sprite.y - 10, tile_text, 
                        0xFFFFFFFF, 0xFF000000)
                end
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

-- Check if two rectangles overlap
local function rectangles_overlap(r1, r2)
    return not (r1.x + r1.w < r2.x or r2.x + r2.w < r1.x or 
                r1.y + r1.h < r2.y or r2.y + r2.h < r1.y)
end

-- Find a non-overlapping position for a box
local function find_free_position(x, y, width, height, occupied_boxes)
    local padding = 4
    local box = {x = x, y = y, w = width, h = height}
    
    -- Check if original position is free
    local collision = false
    for _, occupied in ipairs(occupied_boxes) do
        if rectangles_overlap(box, occupied) then
            collision = true
            break
        end
    end
    if not collision then
        return x, y, false  -- Original position is fine
    end
    
    -- Try different positions in order of preference
    local offsets = {
        {0, -(height + padding * 2)},  -- Up
        {0, height + padding * 2},      -- Down
        {-(width + padding), 0},        -- Left
        {width + padding, 0},           -- Right
        {-(width + padding), -(height + padding * 2)},  -- Up-left
        {width + padding, -(height + padding * 2)},     -- Up-right
        {-(width + padding), height + padding * 2},     -- Down-left
        {width + padding, height + padding * 2},        -- Down-right
    }
    
    for _, offset in ipairs(offsets) do
        local test_x = x + offset[1]
        local test_y = y + offset[2]
        
        -- Keep on screen
        if test_x < 2 then test_x = 2 end
        if test_x + width > 254 then test_x = 254 - width end
        if test_y < 2 then test_y = 2 end
        if test_y + height > 222 then test_y = 222 - height end
        
        local test_box = {x = test_x, y = test_y, w = width, h = height}
        
        -- Check for collisions with existing boxes
        collision = false
        for _, occupied in ipairs(occupied_boxes) do
            if rectangles_overlap(test_box, occupied) then
                collision = true
                break
            end
        end
        
        if not collision then
            return test_x, test_y, true  -- Found free position (was repositioned)
        end
    end
    
    -- If all positions are occupied, use original with slight offset
    return x + 2, y + 2, true
end

-- Dump sprite RAM data for ROM searching
local function dump_sprite_data_for_search()
    -- Find the first captured sprite with a RAM address
    local found_sprite = nil
    local found_offset = nil
    
    for _, sprite in ipairs(state.active_sprites) do
        local persistent_key = string.format("%02X_%d", sprite.tile, sprite.palette)
        local offset = state.sprite_rom_map[sprite.id] or state.persistent_rom_map[persistent_key]
        
        if offset and offset >= 0x800000 then  -- It's a RAM offset
            found_sprite = sprite
            found_offset = offset & 0x7FFFFF  -- Get actual RAM address
            break
        end
    end
    
    if not found_sprite then
        add_message("No RAM sprites found to dump!")
        return
    end
    
    -- Read sprite data from RAM
    local ram_addr = found_offset
    local sprite_size = 0x800  -- 2KB typical sprite size
    local sprite_data = {}
    
    -- Determine memory type based on bank
    local bank = (ram_addr >> 16) & 0xFF
    local mem_type = emu.memType.snesMemory
    
    if bank >= 0x7E and bank <= 0x7F then
        mem_type = emu.memType.snesWorkRam  -- WRAM
    end
    
    -- Read the sprite data
    for i = 0, sprite_size - 1 do
        sprite_data[i + 1] = emu.read(ram_addr + i, mem_type)
    end
    
    -- Save to file
    local output_dir = get_output_path()
    local filename = string.format("sprite_ram_%06X.bin", ram_addr)
    local filepath = output_dir .. "/" .. filename
    
    local file = io.open(filepath, "wb")
    if file then
        for _, byte in ipairs(sprite_data) do
            file:write(string.char(byte))
        end
        file:close()
        
        add_message(string.format("Dumped RAM sprite to %s", filename))
        emu.log(string.format("Sprite RAM dump: %s (address: 0x%06X, size: %d bytes)", 
            filepath, ram_addr, sprite_size))
        emu.log("You can now search for this in ROM using:")
        emu.log(string.format("  python find_sprite_in_rom.py your_rom.sfc %s 0x%06X", 
            filepath, ram_addr))
    else
        add_message("Failed to save RAM dump!")
    end
end

-- Copy sprite offset under cursor to clipboard
local function copy_sprite_offset_at_cursor()
    -- Get mouse position (if available in Mesen2 API)
    -- For now, copy the first visible sprite's offset
    for _, sprite in ipairs(state.active_sprites) do
        local persistent_key = string.format("%02X_%d", sprite.tile, sprite.palette)
        local rom_offset = state.sprite_rom_map[sprite.id] or state.persistent_rom_map[persistent_key]
        if rom_offset then
            -- Format offset for SpritePal (hexadecimal)
            local offset_str = string.format("0x%06X", rom_offset)
            -- Note: Mesen2 doesn't have clipboard API, so we'll export to file
            -- that SpritePal monitors
            local clipboard_file = get_output_path() .. "/sprite_clipboard.txt"
            local file = io.open(clipboard_file, "w")
            if file then
                file:write(offset_str)
                file:close()
                add_message(string.format("Copied offset %s to clipboard file", offset_str), 120)
                emu.log(string.format("Copied sprite offset to clipboard: %s", offset_str))
            end
            return
        end
    end
    add_message("No sprite found to copy", 60)
end

-- Show all sprite offsets on demand (temporary display)
local function show_all_sprite_offsets()
    -- Clear screen first to remove any old drawings
    emu.clearScreen()
    
    -- Track occupied screen areas to prevent overlap
    local occupied_boxes = {}
    
    -- Sort sprites by Y position for consistent layout
    local sorted_sprites = {}
    for _, sprite in ipairs(state.active_sprites) do
        -- Use tile+palette composite key for more unique persistent mapping
        local persistent_key = string.format("%02X_%d", sprite.tile, sprite.palette)
        local rom_offset = state.sprite_rom_map[sprite.id] or state.persistent_rom_map[persistent_key]
        if rom_offset and sprite.x < 256 and sprite.y < 224 then
            table.insert(sorted_sprites, {sprite = sprite, rom_offset = rom_offset})
        end
    end
    table.sort(sorted_sprites, function(a, b) return a.sprite.y < b.sprite.y end)
    
    -- Display offset for each sprite with collision avoidance
    for _, entry in ipairs(sorted_sprites) do
        local sprite = entry.sprite
        local rom_offset = entry.rom_offset
        local offset_text = string.format("$%06X", rom_offset)
        
        -- Calculate initial position (above sprite)
        local label_width = 56
        local label_height = 12
        local initial_x = sprite.x + ((sprite.width or 8) / 2) - (label_width / 2)
        local initial_y = sprite.y - label_height - 8
        
        -- Keep initial position on screen
        if initial_x < 2 then initial_x = 2 end
        if initial_x + label_width > 254 then initial_x = 254 - label_width end
        if initial_y < 2 then initial_y = sprite.y + (sprite.height or 8) + 4 end
        
        -- Find non-overlapping position
        local text_x, text_y, was_repositioned = find_free_position(
            initial_x, initial_y, label_width + 8, label_height + 8, occupied_boxes)
        
        -- Add this box to occupied list
        table.insert(occupied_boxes, {
            x = text_x, y = text_y, 
            w = label_width + 8, h = label_height + 8
        })
        
        -- Draw with temporary display (3 seconds = 180 frames)
        local display_frames = 180
        
        -- Draw connecting line if box was repositioned
        if was_repositioned then
            local sprite_center_x = sprite.x + ((sprite.width or 8) / 2)
            local sprite_center_y = sprite.y + ((sprite.height or 8) / 2)
            local label_center_x = text_x + 4 + (label_width / 2)
            local label_center_y = text_y + 4 + (label_height / 2)
            
            -- Draw thin connecting line
            emu.drawLine(sprite_center_x, sprite_center_y, label_center_x, label_center_y, 
                0xFFFF0000, display_frames)  -- Red line
        end
        
        -- Draw yellow box with red border (temporary)
        -- Outer border (red)
        emu.drawRectangle(text_x, text_y, label_width + 8, label_height + 8, 
            0xFFFF0000, true, display_frames)  -- Red border
        
        -- Inner background (yellow)
        emu.drawRectangle(text_x + 3, text_y + 3, label_width + 2, label_height + 2, 
            0xFFFFFF00, true, display_frames)  -- Yellow background
        
        -- Draw the offset text (black)
        emu.drawString(text_x + 8, text_y + 8, offset_text, 
            0xFF000000, 0, 0, display_frames)  -- Black text
    end
end

-- Export session data for SpritePal import
local function export_session_json()
    local output_dir = get_output_path()
    local filename = generate_filename("sprite_session", "json")
    local filepath = output_dir .. "/" .. filename
    
    -- Build session data
    local session = {
        timestamp = os.date("%Y-%m-%d %H:%M:%S"),
        frame_count = state.frame_count,
        sprites_found = {}
    }
    
    -- Collect all unique sprites with their offsets
    local seen_offsets = {}
    for _, sprite in ipairs(state.active_sprites) do
        local persistent_key = string.format("%02X_%d", sprite.tile, sprite.palette)
        local rom_offset = state.sprite_rom_map[sprite.id] or state.persistent_rom_map[persistent_key]
        
        if rom_offset and not seen_offsets[rom_offset] then
            seen_offsets[rom_offset] = true
            table.insert(session.sprites_found, {
                offset = string.format("0x%06X", rom_offset),
                tile = sprite.tile,
                palette = sprite.palette,
                size = string.format("%dx%d", sprite.width or 8, sprite.height or 8),
                position = {x = sprite.x, y = sprite.y}
            })
        end
    end
    
    -- Sort by offset
    table.sort(session.sprites_found, function(a, b) 
        return a.offset < b.offset 
    end)
    
    -- Write JSON (simple format)
    local file = io.open(filepath, "w")
    if file then
        file:write("{\n")
        file:write(string.format('  "timestamp": "%s",\n', session.timestamp))
        file:write(string.format('  "frame_count": %d,\n', session.frame_count))
        file:write('  "sprites_found": [\n')
        
        for i, sprite in ipairs(session.sprites_found) do
            file:write('    {\n')
            file:write(string.format('      "offset": "%s",\n', sprite.offset))
            file:write(string.format('      "tile": %d,\n', sprite.tile))
            file:write(string.format('      "palette": %d,\n', sprite.palette))
            file:write(string.format('      "size": "%s",\n', sprite.size))
            file:write(string.format('      "position": {"x": %d, "y": %d}\n', 
                sprite.position.x, sprite.position.y))
            file:write('    }')
            if i < #session.sprites_found then
                file:write(',')
            end
            file:write('\n')
        end
        
        file:write('  ]\n')
        file:write('}\n')
        file:close()
        
        add_message("Session exported: " .. filename, 240)
        emu.log("Session exported to: " .. filepath)
    end
end

-- Export data
function export_data()
    local output_dir = get_output_path()
    local filename = generate_filename("sprite_capture_precise", "txt")
    local filepath = output_dir .. "/" .. filename
    
    -- Text output
    local output = "=== Precise Sprite Finder Results ===\n"
    output = output .. string.format("Capture Time: %.1f seconds\n", 
        (state.frame_count - state.stats.session_start_frame) / 60)
    
    local unique_count = 0
    local ram_count = 0
    for offset, _ in pairs(state.stats.unique_sprite_offsets) do
        unique_count = unique_count + 1
        if offset >= 0x800000 then
            ram_count = ram_count + 1
        end
    end
    
    output = output .. string.format("Unique Sprite Offsets: %d (ROM: %d, RAM: %d)\n", 
        unique_count, unique_count - ram_count, ram_count)
    output = output .. string.format("Total Offsets Found: %d\n",
        state.stats.rom_offsets_found)
    output = output .. "\n--- Sprite Offsets (ROM and RAM) ---\n"
    
    local sorted = {}
    for offset, _ in pairs(state.stats.unique_sprite_offsets) do
        table.insert(sorted, offset)
    end
    table.sort(sorted)
    
    for i, offset in ipairs(sorted) do
        if i > 100 then 
            output = output .. string.format("... and %d more\n", #sorted - 100)
            break 
        end
        -- Mark RAM offsets differently
        if offset >= 0x800000 then
            local ram_addr = offset & 0x7FFFFF
            output = output .. string.format("RAM:$%06X (from bank $%02X)\n", ram_addr, (ram_addr >> 16) & 0xFF)
        else
            output = output .. string.format("ROM:$%06X\n", offset)
        end
    end
    
    local file = io.open(filepath, "w")
    if file then
        file:write(output)
        file:close()
        state.last_export_file = filename
        add_message("Exported: " .. filename, 240)
        emu.log("Exported to: " .. filepath)
    end
end

-- Handle hotkeys
local function handle_hotkeys()
    -- 1: Start/Resume (DISABLED - Always active)
    if emu.isKeyPressed(config.key_start) then
        -- state.capture_active = true  -- ALWAYS TRUE
        add_message("Capture is ALWAYS ACTIVE")
    end
    
    -- 2: Pause (DISABLED - Always active)
    if emu.isKeyPressed(config.key_pause) then
        -- state.capture_active = false  -- NEVER PAUSE
        add_message("Capture ALWAYS ACTIVE (pause disabled)")
    end
    
    -- 3: Export (both regular and session)
    if emu.isKeyPressed(config.key_export) then
        export_data()  -- Regular export
        export_session_json()  -- Also export session JSON
    end
    
    -- 4: Reset
    if emu.isKeyPressed(config.key_reset) then
        state.dma_captures = {}
        state.unique_rom_offsets = {}
        state.sprite_rom_map = {}
        state.stats.unique_sprite_offsets = {}
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
    
    -- 7: Toggle Debug Logging (DISABLED - Always on)
    if emu.isKeyPressed(config.key_toggle_debug) then
        -- config.debug_logging = not config.debug_logging  -- ALWAYS TRUE
        add_message("Debug Logging ALWAYS ON (toggle disabled)")
    end
    
    -- 8: Clear Screen (remove persistent drawings)
    if emu.isKeyPressed("8") then
        emu.clearScreen()
        add_message("Screen cleared - offset labels reset")
    end
    
    -- 9: Show All Sprite Offsets (temporary display)
    if emu.isKeyPressed("9") then
        show_all_sprite_offsets()
        add_message("Displaying sprite offsets for 3 seconds...")
    end
    
    -- 0: Copy First Sprite Offset to Clipboard File
    if emu.isKeyPressed("0") then
        copy_sprite_offset_at_cursor()
    end
    
    -- D: Dump RAM sprite data for ROM searching (NEW)
    if emu.isKeyPressed("D") then
        dump_sprite_data_for_search()
    end
end

-- Frame callback
local function on_frame_end()
    state.frame_count = state.frame_count + 1
    
    -- Handle input
    handle_hotkeys()
    
    -- Update OBSEL
    update_obsel()
    
    -- Clear sprite ROM mappings each frame for fresh calculations
    state.sprite_rom_map = {}
    -- Keep persistent_rom_map to maintain offset display
    
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
    
    -- Auto-export every 30 seconds (or 1800 frames at 60fps)
    if state.capture_active and state.frame_count % 1800 == 0 then
        add_message("Auto-exporting data...", 120)
        export_data()
    end
    
    -- Debug status every 300 frames (5 seconds at 60fps) - ALWAYS ACTIVE
    if state.frame_count % 300 == 0 then
        emu.log(string.format("[STATUS @ Frame %d] Total DMA=%d, VRAM DMA=%d, ROM offsets=%d, RAM transfers=%d, RAM->VRAM resolved=%d",
            state.frame_count, state.stats.total_dma, state.stats.vram_dma, 
            state.stats.rom_offsets_found, state.stats.ram_transfers_tracked, 
            state.stats.ram_to_vram_resolved))
        
        -- If we're not getting any DMA, warn the user
        if state.stats.total_dma == 0 then
            emu.log("[WARNING] No DMA transfers detected yet - make sure game is running and sprites are on screen")
        elseif state.stats.vram_dma == 0 and state.stats.total_dma > 0 then
            emu.log("[WARNING] DMA detected but no VRAM transfers - sprites may be using non-standard registers")
        elseif state.stats.rom_offsets_found == 0 and state.stats.vram_dma > 0 then
            emu.log("[WARNING] VRAM transfers detected but no valid ROM offsets - check bank validation in debug log")
        end
    end
end

-- Initialize
function init()
    emu.log("Precise Sprite Finder initialized!")
    emu.log("AUTO-CAPTURE ACTIVE with DEBUG LOGGING! Press 2 to pause, 3 to export")
    
    -- Set session start frame for auto-capture
    state.stats.session_start_frame = state.frame_count
    
    -- DMA callback
    state.callbacks.dma = emu.addMemoryCallback(
        on_dma_enable_write,
        emu.callbackType.write,
        DMA_ENABLE,
        DMA_ENABLE
    )
    
    if config.debug_logging then
        emu.log(string.format("[DEBUG] DMA callback registered for address $%04X", DMA_ENABLE))
    end
    
    -- Frame callback
    state.callbacks.frame = emu.addEventCallback(
        on_frame_end,
        emu.eventType.endFrame
    )
    
    update_obsel()
    
    add_message("ALWAYS ACTIVE MODE", 300)
    add_message("Capture & Debug permanently ON", 300)
    add_message("Check console for debug output", 240)
end

-- Start
init()

-- Debug startup message
if config.debug_logging then
    emu.log("==============================================")
    emu.log("SPRITE FINDER DEBUG MODE ACTIVE")
    emu.log("==============================================")
    emu.log("Script loaded successfully")
    emu.log("Watching for DMA transfers...")
    emu.log("Banks 0x80-0xBF = Valid ROM")
    emu.log("Banks 0x7E-0x7F = RAM")
    emu.log("Banks 0xC0-0xFF = Invalid/RAM")
    emu.log("==============================================")
end