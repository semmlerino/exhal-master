-- Mesen 2 Enhanced Sprite Finder with JSON Export
-- Optimized for Kirby SNES games with HAL compression awareness
-- Exports data in SpritePal-compatible format

-- Enhanced state tracking
local state = {
    frame_count = 0,
    dma_captures = {},
    active_sprites = {},
    sprite_rom_mappings = {},  -- sprite_id -> {rom_offsets}
    unique_rom_offsets = {},
    obsel_config = {
        name_base = 0,
        name_select = 0,
        size_select = 0
    },
    vram_writes = {},  -- Track VRAM write patterns
    callbacks = {},
    stats = {
        total_dma = 0,
        vram_dma = 0,
        oam_dma = 0,
        cgram_dma = 0,
        sprites_tracked = 0,
        mappings_found = 0
    }
}

-- Constants
local DMA_ENABLE = 0x420B
local HDMA_ENABLE = 0x420C
local DMA_BASE = 0x4300
local OBSEL = 0x2101
local VRAM_ADDR_L = 0x2116
local VRAM_ADDR_H = 0x2117
local VRAM_DATA_L = 0x2118
local VRAM_DATA_H = 0x2119
local CGRAM_ADDR = 0x2121
local CGRAM_DATA = 0x2122
local OAM_ADDR_L = 0x2102
local OAM_ADDR_H = 0x2103
local OAM_DATA = 0x2104

-- Helper: Format hex with proper width
local function hex(value, width)
    width = width or 2
    return string.format("$%0" .. width .. "X", value)
end

-- Helper: Convert CPU address to ROM offset (LoROM/HiROM detection)
local function cpu_to_rom_offset(cpu_addr)
    local bank = (cpu_addr >> 16) & 0xFF
    local addr = cpu_addr & 0xFFFF
    
    -- Skip non-ROM addresses
    if addr < 0x8000 then
        return nil
    end
    
    -- Try LoROM mapping first (most Kirby games)
    local lorom_offset = ((bank & 0x7F) * 0x8000) + (addr - 0x8000)
    
    -- Could add HiROM detection if needed
    return lorom_offset
end

-- Helper: Calculate sprite VRAM address from tile number
local function sprite_tile_to_vram(tile_num)
    -- Based on OBSEL configuration
    local name_base = state.obsel_config.name_base * 0x2000
    local name_select = state.obsel_config.name_select
    
    -- Handle name table selection for 16x16 sprites
    if name_select > 0 then
        -- Upper 4KB blocks for large sprites
        name_base = name_base + (name_select * 0x1000)
    end
    
    local vram_addr = name_base + (tile_num * 32)  -- 32 bytes per 8x8 tile
    return vram_addr
end

-- Enhanced DMA channel reading with full parameter extraction
local function read_dma_channel_detailed(channel)
    local base = DMA_BASE + (channel * 0x10)
    
    -- Read all DMA registers
    local params = {}
    params.control = emu.read(base + 0x00, emu.MemoryType.CpuMemory)
    params.dest_reg = emu.read(base + 0x01, emu.MemoryType.CpuMemory)
    params.src_low = emu.read(base + 0x02, emu.MemoryType.CpuMemory)
    params.src_mid = emu.read(base + 0x03, emu.MemoryType.CpuMemory)
    params.src_bank = emu.read(base + 0x04, emu.MemoryType.CpuMemory)
    params.size_low = emu.read(base + 0x05, emu.MemoryType.CpuMemory)
    params.size_high = emu.read(base + 0x06, emu.MemoryType.CpuMemory)
    
    -- HDMA specific (if applicable)
    params.hdma_addr_low = emu.read(base + 0x08, emu.MemoryType.CpuMemory)
    params.hdma_addr_high = emu.read(base + 0x09, emu.MemoryType.CpuMemory)
    params.hdma_line_counter = emu.read(base + 0x0A, emu.MemoryType.CpuMemory)
    
    -- Calculate derived values
    params.source_addr = (params.src_bank << 16) | (params.src_mid << 8) | params.src_low
    params.transfer_size = (params.size_high << 8) | params.size_low
    if params.transfer_size == 0 then
        params.transfer_size = 0x10000  -- 0 means 64KB
    end
    
    -- Decode control register
    params.transfer_mode = params.control & 0x07
    params.fixed_transfer = (params.control & 0x08) ~= 0
    params.address_step = (params.control & 0x10) ~= 0 and -1 or 1
    params.indirect_hdma = (params.control & 0x40) ~= 0
    params.direction = (params.control & 0x80) ~= 0 and "B->A" or "A->B"
    
    -- Identify destination type
    local dest_names = {
        [0x04] = "OAM_DATA",
        [0x18] = "VRAM_LOW",
        [0x19] = "VRAM_HIGH",
        [0x22] = "CGRAM_DATA",
        [0x80] = "WRAM"
    }
    params.dest_name = dest_names[params.dest_reg] or string.format("PPU_%02X", params.dest_reg)
    
    return params
end

-- Enhanced DMA capture with correlation
local function capture_dma_transfer(channel, enable_value)
    local dma = read_dma_channel_detailed(channel)
    state.stats.total_dma = state.stats.total_dma + 1
    
    -- Get current PPU state
    local vram_addr = (emu.read(VRAM_ADDR_H, emu.MemoryType.CpuMemory) << 8) |
                      emu.read(VRAM_ADDR_L, emu.MemoryType.CpuMemory)
    
    -- Calculate ROM offset
    local rom_offset = cpu_to_rom_offset(dma.source_addr)
    
    -- Create capture record
    local capture = {
        frame = state.frame_count,
        channel = channel,
        source_addr = dma.source_addr,
        rom_offset = rom_offset,
        dest_reg = dma.dest_reg,
        dest_name = dma.dest_name,
        size = dma.transfer_size,
        transfer_mode = dma.transfer_mode,
        vram_addr = nil,
        cgram_addr = nil,
        oam_addr = nil
    }
    
    -- Handle destination-specific tracking
    if dma.dest_reg == 0x18 or dma.dest_reg == 0x19 then
        -- VRAM transfer
        capture.vram_addr = vram_addr * 2  -- Word to byte address
        state.stats.vram_dma = state.stats.vram_dma + 1
        
        -- Track VRAM write pattern
        if not state.vram_writes[vram_addr] then
            state.vram_writes[vram_addr] = {}
        end
        table.insert(state.vram_writes[vram_addr], {
            frame = state.frame_count,
            rom_offset = rom_offset,
            size = dma.transfer_size
        })
        
        -- Check if this might be sprite data
        local sprite_base = state.obsel_config.name_base * 0x2000
        if capture.vram_addr >= sprite_base and capture.vram_addr < sprite_base + 0x4000 then
            capture.is_sprite_region = true
        end
        
    elseif dma.dest_reg == 0x04 then
        -- OAM transfer
        local oam_addr = (emu.read(OAM_ADDR_H, emu.MemoryType.CpuMemory) << 8) |
                         emu.read(OAM_ADDR_L, emu.MemoryType.CpuMemory)
        capture.oam_addr = oam_addr
        state.stats.oam_dma = state.stats.oam_dma + 1
        
    elseif dma.dest_reg == 0x22 then
        -- CGRAM (palette) transfer
        capture.cgram_addr = emu.read(CGRAM_ADDR, emu.MemoryType.CpuMemory)
        state.stats.cgram_dma = state.stats.cgram_dma + 1
    end
    
    -- Store capture
    table.insert(state.dma_captures, capture)
    
    -- Track unique ROM offsets with metadata
    if rom_offset then
        if not state.unique_rom_offsets[rom_offset] then
            state.unique_rom_offsets[rom_offset] = {
                first_frame = state.frame_count,
                last_frame = state.frame_count,
                destinations = {},
                hit_count = 0,
                total_size = 0,
                is_sprite_data = false
            }
        end
        
        local rom_data = state.unique_rom_offsets[rom_offset]
        rom_data.last_frame = state.frame_count
        rom_data.hit_count = rom_data.hit_count + 1
        rom_data.total_size = rom_data.total_size + dma.transfer_size
        
        -- Track destination
        if capture.vram_addr then
            rom_data.destinations["VRAM_" .. hex(capture.vram_addr, 4)] = true
            if capture.is_sprite_region then
                rom_data.is_sprite_data = true
            end
        elseif capture.cgram_addr then
            rom_data.destinations["CGRAM_" .. hex(capture.cgram_addr, 2)] = true
        elseif capture.oam_addr then
            rom_data.destinations["OAM_" .. hex(capture.oam_addr, 3)] = true
        end
    end
    
    -- Log significant captures
    if rom_offset and (capture.is_sprite_region or dma.dest_reg == 0x04) then
        emu.log(string.format(
            "DMA_CAPTURE: F=%d Ch=%d %s -> %s ROM=%s Size=%d %s",
            state.frame_count,
            channel,
            hex(dma.source_addr, 6),
            capture.dest_name,
            hex(rom_offset, 6),
            dma.transfer_size,
            capture.is_sprite_region and "[SPRITE]" or ""
        ))
    end
    
    return capture
end

-- Callback: DMA Enable register write
local function on_dma_enable_write(address, value)
    if value == 0 then return end
    
    -- Process each enabled channel
    for channel = 0, 7 do
        if (value & (1 << channel)) ~= 0 then
            capture_dma_transfer(channel, value)
        end
    end
end

-- Callback: HDMA Enable register write
local function on_hdma_enable_write(address, value)
    if value == 0 then return end
    
    -- Log HDMA usage (might affect sprite rendering)
    emu.log(string.format("HDMA_ENABLE: %02X at frame %d", value, state.frame_count))
end

-- Callback: OBSEL register write
local function on_obsel_write(address, value)
    local old_base = state.obsel_config.name_base
    
    state.obsel_config.name_base = value & 0x07
    state.obsel_config.name_select = (value >> 3) & 0x03
    state.obsel_config.size_select = (value >> 5) & 0x07
    
    if old_base ~= state.obsel_config.name_base then
        emu.log(string.format(
            "OBSEL_CHANGE: base=%d->%d select=%d size=%d (VRAM base=$%04X)",
            old_base,
            state.obsel_config.name_base,
            state.obsel_config.name_select,
            state.obsel_config.size_select,
            state.obsel_config.name_base * 0x2000
        ))
    end
end

-- Enhanced OAM analysis with sprite tracking
local function analyze_oam_enhanced()
    -- Get current emulator state for accurate OAM reading
    local ppuState = emu.getState()
    
    -- Read OAM data
    local oam_data = {}
    for i = 0, 511 do
        oam_data[i] = emu.read(0x2000 + i, emu.MemoryType.PpuMemory)
    end
    
    -- Read high table for X-position MSB and size
    local oam_high = {}
    for i = 512, 543 do
        oam_high[i - 512] = emu.read(0x2000 + i, emu.MemoryType.PpuMemory)
    end
    
    -- Parse sprite entries
    state.active_sprites = {}
    for i = 0, 127 do
        local base = i * 4
        local x = oam_data[base]
        local y = oam_data[base + 1]
        local tile = oam_data[base + 2]
        local attr = oam_data[base + 3]
        
        -- Get X MSB and size from high table
        local high_byte_index = math.floor(i / 4)
        local high_bit_index = (i % 4) * 2
        local high_byte = oam_high[high_byte_index]
        local x_msb = (high_byte >> high_bit_index) & 0x01
        local size_bit = (high_byte >> (high_bit_index + 1)) & 0x01
        
        -- Calculate actual X position
        x = x | (x_msb * 256)
        
        -- Check if sprite is potentially visible
        if y < 224 or (y >= 240) then  -- Handle wrapped sprites
            local sprite = {
                id = i,
                x = x,
                y = y,
                tile = tile,
                attr = attr,
                palette = (attr >> 1) & 0x07,
                priority = (attr >> 4) & 0x03,
                flip_h = (attr & 0x40) ~= 0,
                flip_v = (attr & 0x80) ~= 0,
                size_bit = size_bit,
                name_table = (attr & 0x01)  -- Name table select
            }
            
            -- Calculate sprite size based on OBSEL and size bit
            local size_select = state.obsel_config.size_select
            local sizes = {
                [0] = {8, 16}, [1] = {8, 32}, [2] = {8, 64},
                [3] = {16, 32}, [4] = {16, 64}, [5] = {32, 64},
                [6] = {16, 32}, [7] = {16, 32}  -- Undocumented
            }
            
            local size_pair = sizes[size_select] or {8, 16}
            sprite.width = size_pair[size_bit + 1]
            sprite.height = sprite.width  -- Square sprites
            
            -- Calculate VRAM address for this sprite's tiles
            sprite.vram_addr = sprite_tile_to_vram(tile)
            sprite.tile_count = (sprite.width / 8) * (sprite.height / 8)
            
            table.insert(state.active_sprites, sprite)
            
            -- Initialize sprite->ROM mapping if new
            if not state.sprite_rom_mappings[i] then
                state.sprite_rom_mappings[i] = {
                    rom_offsets = {},
                    last_tile = tile,
                    last_pos = {x = x, y = y}
                }
            end
        end
    end
    
    state.stats.sprites_tracked = #state.active_sprites
end

-- Advanced correlation: Match sprites to DMA transfers
local function correlate_sprites_advanced()
    local new_mappings = 0
    
    for _, sprite in ipairs(state.active_sprites) do
        local sprite_vram_start = sprite.vram_addr
        local sprite_vram_end = sprite_vram_start + (sprite.tile_count * 32)
        
        -- Check recent DMA captures (last 10 frames)
        local recent_frame = state.frame_count - 10
        
        for i = #state.dma_captures, 1, -1 do
            local capture = state.dma_captures[i]
            
            -- Stop if capture is too old
            if capture.frame < recent_frame then
                break
            end
            
            -- Check if this is a VRAM transfer in sprite region
            if capture.vram_addr and capture.rom_offset then
                local dma_start = capture.vram_addr
                local dma_end = dma_start + capture.size
                
                -- Check for overlap
                if dma_start < sprite_vram_end and dma_end > sprite_vram_start then
                    -- Found a match!
                    local mapping = state.sprite_rom_mappings[sprite.id]
                    
                    if not mapping.rom_offsets[capture.rom_offset] then
                        mapping.rom_offsets[capture.rom_offset] = {
                            first_frame = capture.frame,
                            last_frame = capture.frame,
                            hit_count = 0
                        }
                        new_mappings = new_mappings + 1
                        
                        emu.log(string.format(
                            "SPRITE_MAPPED: id=%d pos=(%d,%d) tile=$%02X size=%dx%d -> ROM=%s",
                            sprite.id, sprite.x, sprite.y, sprite.tile,
                            sprite.width, sprite.height,
                            hex(capture.rom_offset, 6)
                        ))
                    end
                    
                    local rom_info = mapping.rom_offsets[capture.rom_offset]
                    rom_info.last_frame = state.frame_count
                    rom_info.hit_count = rom_info.hit_count + 1
                end
            end
        end
    end
    
    if new_mappings > 0 then
        state.stats.mappings_found = state.stats.mappings_found + new_mappings
    end
end

-- Frame end callback with comprehensive processing
local function on_frame_end()
    state.frame_count = state.frame_count + 1
    
    -- Analyze OAM every frame
    analyze_oam_enhanced()
    
    -- Correlate sprites with DMA captures
    if #state.active_sprites > 0 then
        correlate_sprites_advanced()
    end
    
    -- Periodic status update
    if state.frame_count % 300 == 0 then
        local unique_count = 0
        for _ in pairs(state.unique_rom_offsets) do
            unique_count = unique_count + 1
        end
        
        emu.log(string.format(
            "STATUS: Frame=%d Active=%d Tracked=%d Mapped=%d DMA=%d (VRAM=%d) Unique=%d",
            state.frame_count,
            #state.active_sprites,
            state.stats.sprites_tracked,
            state.stats.mappings_found,
            state.stats.total_dma,
            state.stats.vram_dma,
            unique_count
        ))
    end
    
    -- Export at regular intervals
    if state.frame_count % 1800 == 0 then  -- Every 30 seconds at 60fps
        export_json()
    end
end

-- Export to JSON for SpritePal
function export_json()
    local export_data = {
        metadata = {
            frame_count = state.frame_count,
            timestamp = os.time(),
            obsel_config = state.obsel_config,
            stats = state.stats
        },
        sprites = {},
        rom_offsets = {},
        dma_patterns = {}
    }
    
    -- Export sprite->ROM mappings
    for sprite_id, mapping in pairs(state.sprite_rom_mappings) do
        if next(mapping.rom_offsets) then  -- Has mappings
            local sprite_data = {
                id = sprite_id,
                last_pos = mapping.last_pos,
                last_tile = mapping.last_tile,
                rom_offsets = {}
            }
            
            for rom_offset, info in pairs(mapping.rom_offsets) do
                table.insert(sprite_data.rom_offsets, {
                    offset = rom_offset,
                    hits = info.hit_count,
                    frames = {info.first_frame, info.last_frame}
                })
            end
            
            table.insert(export_data.sprites, sprite_data)
        end
    end
    
    -- Export unique ROM offsets with metadata
    for rom_offset, data in pairs(state.unique_rom_offsets) do
        local dest_list = {}
        for dest, _ in pairs(data.destinations) do
            table.insert(dest_list, dest)
        end
        
        table.insert(export_data.rom_offsets, {
            offset = rom_offset,
            size = data.total_size,
            hits = data.hit_count,
            frames = {data.first_frame, data.last_frame},
            destinations = dest_list,
            is_sprite = data.is_sprite_data
        })
    end
    
    -- Sort for consistency
    table.sort(export_data.sprites, function(a, b) return a.id < b.id end)
    table.sort(export_data.rom_offsets, function(a, b) return a.offset < b.offset end)
    
    -- Write JSON file
    local json_str = "{\n"
    json_str = json_str .. '  "metadata": ' .. table_to_json(export_data.metadata) .. ",\n"
    json_str = json_str .. '  "sprites": ' .. table_to_json(export_data.sprites) .. ",\n"
    json_str = json_str .. '  "rom_offsets": ' .. table_to_json(export_data.rom_offsets) .. "\n"
    json_str = json_str .. "}"
    
    local file = io.open("mesen2_sprite_data.json", "w")
    if file then
        file:write(json_str)
        file:close()
        emu.log("JSON export complete: mesen2_sprite_data.json")
    end
    
    -- Also create human-readable summary
    export_summary()
end

-- Simple JSON serialization (since Mesen 2 might not have json library)
function table_to_json(t)
    if type(t) == "number" then
        return tostring(t)
    elseif type(t) == "string" then
        return '"' .. t:gsub('"', '\\"') .. '"'
    elseif type(t) == "boolean" then
        return t and "true" or "false"
    elseif type(t) == "table" then
        local is_array = #t > 0
        local result = is_array and "[" or "{"
        local first = true
        
        if is_array then
            for i, v in ipairs(t) do
                if not first then result = result .. "," end
                result = result .. table_to_json(v)
                first = false
            end
        else
            for k, v in pairs(t) do
                if not first then result = result .. "," end
                result = result .. '"' .. k .. '":' .. table_to_json(v)
                first = false
            end
        end
        
        result = result .. (is_array and "]" or "}")
        return result
    else
        return "null"
    end
end

-- Human-readable summary export
function export_summary()
    local output = "=== Mesen 2 Enhanced Sprite Finder Results ===\n"
    output = output .. string.format("Analysis Duration: %d frames (%.1f seconds)\n",
                                      state.frame_count, state.frame_count / 60.0)
    output = output .. "\n--- Statistics ---\n"
    output = output .. string.format("Total DMA Transfers: %d\n", state.stats.total_dma)
    output = output .. string.format("  VRAM: %d\n", state.stats.vram_dma)
    output = output .. string.format("  OAM: %d\n", state.stats.oam_dma)
    output = output .. string.format("  CGRAM: %d\n", state.stats.cgram_dma)
    output = output .. string.format("Sprites Tracked: %d\n", state.stats.sprites_tracked)
    output = output .. string.format("ROM Mappings Found: %d\n", state.stats.mappings_found)
    
    output = output .. "\n--- Sprite Pattern Base ---\n"
    output = output .. string.format("OBSEL: base=%d select=%d size=%d\n",
                                      state.obsel_config.name_base,
                                      state.obsel_config.name_select,
                                      state.obsel_config.size_select)
    output = output .. string.format("VRAM Base Address: $%04X\n",
                                      state.obsel_config.name_base * 0x2000)
    
    output = output .. "\n--- Top ROM Offsets (Sprite Data) ---\n"
    
    -- Find top sprite ROM offsets
    local sprite_roms = {}
    for offset, data in pairs(state.unique_rom_offsets) do
        if data.is_sprite_data then
            table.insert(sprite_roms, {
                offset = offset,
                hits = data.hit_count,
                size = data.total_size
            })
        end
    end
    table.sort(sprite_roms, function(a, b) return a.hits > b.hits end)
    
    for i = 1, math.min(20, #sprite_roms) do
        local rom = sprite_roms[i]
        output = output .. string.format("  %s: %d hits, %d bytes total\n",
                                          hex(rom.offset, 6),
                                          rom.hits,
                                          rom.size)
    end
    
    output = output .. "\n--- Active Sprite Mappings ---\n"
    local mapped_count = 0
    for sprite_id, mapping in pairs(state.sprite_rom_mappings) do
        if next(mapping.rom_offsets) then
            mapped_count = mapped_count + 1
            if mapped_count <= 10 then  -- Show first 10
                output = output .. string.format("Sprite %d: ", sprite_id)
                local rom_list = {}
                for offset, _ in pairs(mapping.rom_offsets) do
                    table.insert(rom_list, hex(offset, 6))
                end
                output = output .. table.concat(rom_list, ", ") .. "\n"
            end
        end
    end
    
    if mapped_count > 10 then
        output = output .. string.format("... and %d more sprites with mappings\n",
                                          mapped_count - 10)
    end
    
    -- Write summary file
    local file = io.open("mesen2_sprite_summary.txt", "w")
    if file then
        file:write(output)
        file:close()
        emu.log("Summary exported: mesen2_sprite_summary.txt")
    end
end

-- Initialize enhanced callbacks
function init()
    emu.log("=== Mesen 2 Enhanced Sprite Finder Starting ===")
    emu.log("Advanced DMA tracking with sprite correlation enabled")
    emu.log("JSON export for SpritePal integration")
    
    -- Memory write callbacks
    state.callbacks.dma = emu.addMemoryCallback(
        on_dma_enable_write,
        emu.CallbackType.CpuWrite,
        DMA_ENABLE,
        DMA_ENABLE
    )
    
    state.callbacks.hdma = emu.addMemoryCallback(
        on_hdma_enable_write,
        emu.CallbackType.CpuWrite,
        HDMA_ENABLE,
        HDMA_ENABLE
    )
    
    state.callbacks.obsel = emu.addMemoryCallback(
        on_obsel_write,
        emu.CallbackType.CpuWrite,
        OBSEL,
        OBSEL
    )
    
    -- Frame callback
    state.callbacks.frame = emu.addEventCallback(
        on_frame_end,
        emu.EventType.EndFrame
    )
    
    emu.log("Enhanced callbacks registered. Monitoring active...")
    emu.log("Outputs: mesen2_sprite_data.json, mesen2_sprite_summary.txt")
end

-- Cleanup
function cleanup()
    emu.log("Finalizing analysis...")
    
    -- Final export
    export_json()
    
    -- Remove callbacks
    if state.callbacks.dma then
        emu.removeMemoryCallback(state.callbacks.dma)
    end
    if state.callbacks.hdma then
        emu.removeMemoryCallback(state.callbacks.hdma)
    end
    if state.callbacks.obsel then
        emu.removeMemoryCallback(state.callbacks.obsel)
    end
    if state.callbacks.frame then
        emu.removeEventCallback(state.callbacks.frame)
    end
    
    emu.log(string.format(
        "=== Analysis Complete: %d frames, %d mappings found ===",
        state.frame_count,
        state.stats.mappings_found
    ))
end

-- Start
init()