-- Mesen 2 Sprite Finder - CORRECTED VERSION
-- Uses the CORRECT callback type (1, not 2!)

emu.log("=== Mesen 2 Sprite Finder (CORRECTED - Using Callback Type 1) ===")
emu.log("Fixed: Using emu.callbackType.write (value 1) instead of 2")

-- Global state
local state = {
    frame_count = 0,
    dma_captures = {},
    active_sprites = {},
    unique_rom_offsets = {},
    obsel_config = nil,
    callbacks = {},
    stats = {
        total_dma = 0,
        vram_dma = 0,
        oam_dma = 0,
        cgram_dma = 0,
        sprites_found = 0,
        mappings = 0
    }
}

-- Constants
local DMA_ENABLE = 0x420B
local HDMA_ENABLE = 0x420C
local DMA_BASE = 0x4300
local OBSEL = 0x2101
local VRAM_ADDR_L = 0x2116
local VRAM_ADDR_H = 0x2117

-- Helper: Convert CPU address to ROM offset
local function cpu_to_rom_offset(cpu_addr)
    -- Banks $C0-$FF and $80-$BF map to ROM in LoROM
    local bank = (cpu_addr >> 16) & 0xFF
    local addr = cpu_addr & 0xFFFF
    
    -- Skip if not in ROM range
    if addr < 0x8000 then
        return nil
    end
    
    -- Skip work RAM banks ($7E-$7F)
    if bank == 0x7E or bank == 0x7F then
        return nil
    end
    
    -- Banks $00-$7D and $80-$FF can contain ROM
    -- For Kirby games (LoROM), banks $C0-$FF and $80-$BF typically have ROM
    if bank >= 0xC0 or (bank >= 0x80 and bank < 0xC0) then
        -- LoROM calculation
        local rom_offset = ((bank & 0x7F) * 0x8000) + (addr - 0x8000)
        return rom_offset
    end
    
    return nil
end

-- Helper: Read DMA channel registers
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
        transfer_size = transfer_size,
        transfer_mode = control & 0x07,
        fixed = (control & 0x08) ~= 0,
        direction = (control & 0x80) ~= 0 and "B->A" or "A->B"
    }
end

-- Update OBSEL from register
local function update_obsel()
    local obsel = emu.read(OBSEL, emu.memType.snesMemory)
    state.obsel_config = {
        name_base = obsel & 0x07,
        name_select = (obsel >> 3) & 0x03,
        size_select = (obsel >> 5) & 0x07,
        raw = obsel
    }
end

-- Callback: DMA Enable register write
local function on_dma_enable_write(address, value)
    if value == 0 then return end
    
    state.stats.total_dma = state.stats.total_dma + 1
    
    -- Read current VRAM address
    local vram_low = emu.read(VRAM_ADDR_L, emu.memType.snesMemory)
    local vram_high = emu.read(VRAM_ADDR_H, emu.memType.snesMemory)
    local vram_addr = (vram_high << 8) | vram_low
    
    -- Process each enabled channel
    for channel = 0, 7 do
        if (value & (1 << channel)) ~= 0 then
            local dma = read_dma_channel(channel)
            
            -- Identify destination
            local dest_name = "UNKNOWN"
            if dma.dest_reg == 0x18 then
                dest_name = "VRAM_LOW"
                state.stats.vram_dma = state.stats.vram_dma + 1
            elseif dma.dest_reg == 0x19 then
                dest_name = "VRAM_HIGH"
                state.stats.vram_dma = state.stats.vram_dma + 1
            elseif dma.dest_reg == 0x04 then
                dest_name = "OAM_DATA"
                state.stats.oam_dma = state.stats.oam_dma + 1
            elseif dma.dest_reg == 0x22 then
                dest_name = "CGRAM"
                state.stats.cgram_dma = state.stats.cgram_dma + 1
            end
            
            -- Process VRAM transfers
            if dma.dest_reg == 0x18 or dma.dest_reg == 0x19 then
                -- Check if source is ROM (banks $80-$FF typically)
                if dma.source_bank >= 0x80 then
                    local rom_offset = cpu_to_rom_offset(dma.source_addr)
                    
                    if rom_offset then
                        -- This is a ROM -> VRAM transfer!
                        local capture = {
                            frame = state.frame_count,
                            channel = channel,
                            vram_addr = vram_addr * 2,  -- Word to byte
                            source_addr = dma.source_addr,
                            rom_offset = rom_offset,
                            size = dma.transfer_size,
                            dest_reg = dma.dest_reg
                        }
                        
                        table.insert(state.dma_captures, capture)
                        
                        -- Track unique ROM offsets
                        if not state.unique_rom_offsets[rom_offset] then
                            state.unique_rom_offsets[rom_offset] = {
                                first_frame = state.frame_count,
                                last_frame = state.frame_count,
                                vram_addrs = {},
                                hit_count = 0,
                                total_size = 0
                            }
                        end
                        
                        local rom_data = state.unique_rom_offsets[rom_offset]
                        rom_data.last_frame = state.frame_count
                        rom_data.hit_count = rom_data.hit_count + 1
                        rom_data.total_size = rom_data.total_size + dma.transfer_size
                        rom_data.vram_addrs[vram_addr] = true
                        
                        -- Check if in sprite region
                        if state.obsel_config then
                            local sprite_base = state.obsel_config.name_base * 0x2000
                            if vram_addr >= sprite_base and vram_addr < sprite_base + 0x4000 then
                                emu.log(string.format(
                                    "*** SPRITE_DMA: VRAM=$%04X <- ROM=$%06X size=%d ***",
                                    vram_addr, rom_offset, dma.transfer_size
                                ))
                            end
                        end
                        
                        emu.log(string.format(
                            "ROM_TRANSFER: ROM=$%06X -> VRAM=$%04X size=%d",
                            rom_offset, vram_addr, dma.transfer_size
                        ))
                    end
                else
                    -- Log work RAM transfers for debugging
                    emu.log(string.format(
                        "WRAM_DMA: Bank=$%02X:%04X -> %s size=%d",
                        dma.source_bank, dma.source_addr & 0xFFFF,
                        dest_name, dma.transfer_size
                    ))
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
        
        -- Get X MSB and size from high table
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
                sprite.tile_count = (sprite.width / 8) * (sprite.height / 8)
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
            local sprite_vram_end = sprite_vram_start + (sprite.tile_count * 32)
            
            -- Check recent DMA captures
            for i = #state.dma_captures, math.max(1, #state.dma_captures - 100), -1 do
                local capture = state.dma_captures[i]
                
                if capture.vram_addr and capture.rom_offset then
                    local dma_vram_start = capture.vram_addr
                    local dma_vram_end = dma_vram_start + capture.size
                    
                    -- Check for overlap
                    if dma_vram_start < sprite_vram_end and dma_vram_end > sprite_vram_start then
                        state.stats.mappings = state.stats.mappings + 1
                        emu.log(string.format(
                            "SPRITE_MAPPED: id=%d pos=(%d,%d) tile=$%02X -> ROM=$%06X",
                            sprite.id, sprite.x, sprite.y, sprite.tile, capture.rom_offset
                        ))
                        break
                    end
                end
            end
        end
    end
end

-- Frame end callback
local function on_frame_end()
    state.frame_count = state.frame_count + 1
    
    -- Update OBSEL
    update_obsel()
    
    -- Analyze OAM
    analyze_oam()
    
    -- Correlate
    correlate_sprites_and_dma()
    
    -- Status every 300 frames
    if state.frame_count % 300 == 0 then
        local unique_count = 0
        for _ in pairs(state.unique_rom_offsets) do
            unique_count = unique_count + 1
        end
        
        emu.log(string.format(
            "STATUS: F=%d Sprites=%d DMA=%d (VRAM=%d OAM=%d PAL=%d) ROM_Offsets=%d Maps=%d",
            state.frame_count,
            #state.active_sprites,
            state.stats.total_dma,
            state.stats.vram_dma,
            state.stats.oam_dma,
            state.stats.cgram_dma,
            unique_count,
            state.stats.mappings
        ))
        
        if unique_count > 0 then
            export_findings()
        end
    end
end

-- Export findings
function export_findings()
    local output = "=== Mesen 2 Sprite Finder Results ===\n"
    output = output .. string.format("Frame: %d (%.1f seconds)\n", 
        state.frame_count, state.frame_count / 60.0)
    output = output .. string.format("Total DMA: %d (VRAM: %d, OAM: %d, CGRAM: %d)\n", 
        state.stats.total_dma, state.stats.vram_dma, 
        state.stats.oam_dma, state.stats.cgram_dma)
    output = output .. string.format("Sprite-ROM Mappings: %d\n", state.stats.mappings)
    
    if state.obsel_config then
        output = output .. string.format("\nOBSEL: $%02X (base=%d, VRAM=$%04X)\n",
            state.obsel_config.raw, state.obsel_config.name_base,
            state.obsel_config.name_base * 0x2000)
    end
    
    output = output .. "\n--- ROM Offsets Found ---\n"
    
    local sorted = {}
    for offset, data in pairs(state.unique_rom_offsets) do
        table.insert(sorted, {offset = offset, data = data})
    end
    table.sort(sorted, function(a, b) 
        return a.data.hit_count > b.data.hit_count 
    end)
    
    for i, entry in ipairs(sorted) do
        if i > 30 then break end
        
        local vram_list = {}
        for vram in pairs(entry.data.vram_addrs) do
            table.insert(vram_list, string.format("$%04X", vram))
            if #vram_list >= 3 then break end
        end
        
        output = output .. string.format(
            "ROM $%06X: %d hits, %d bytes, VRAM: %s\n",
            entry.offset, entry.data.hit_count, 
            entry.data.total_size, table.concat(vram_list, ",")
        )
    end
    
    local file = io.open("mesen2_sprite_findings.txt", "w")
    if file then
        file:write(output)
        file:close()
        emu.log("*** Exported to mesen2_sprite_findings.txt ***")
    end
    
    -- JSON export
    export_json()
end

-- JSON export
function export_json()
    local json_data = {
        metadata = {
            frame_count = state.frame_count,
            duration_sec = state.frame_count / 60.0,
            stats = state.stats,
            obsel = state.obsel_config
        },
        rom_offsets = {}
    }
    
    for offset, data in pairs(state.unique_rom_offsets) do
        table.insert(json_data.rom_offsets, {
            offset = offset,
            hits = data.hit_count,
            size = data.total_size,
            first_frame = data.first_frame,
            last_frame = data.last_frame
        })
    end
    
    table.sort(json_data.rom_offsets, function(a, b) 
        return a.hits > b.hits 
    end)
    
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
    
    local json_str = to_json(json_data)
    
    local file = io.open("mesen2_sprite_data.json", "w")
    if file then
        file:write(json_str)
        file:close()
    end
end

-- Initialize
function init()
    emu.log("Initializing with CORRECT callback type...")
    emu.log("FIX: Using emu.callbackType.write = 1 (not 2!)")
    
    -- Use emu.callbackType.write which equals 1
    state.callbacks.dma = emu.addMemoryCallback(
        on_dma_enable_write,
        emu.callbackType.write,  -- Value is 1
        DMA_ENABLE,
        DMA_ENABLE
    )
    
    -- Also monitor HDMA
    state.callbacks.hdma = emu.addMemoryCallback(
        function(addr, val)
            if val ~= 0 then
                emu.log(string.format("HDMA: $%02X", val))
            end
        end,
        emu.callbackType.write,
        HDMA_ENABLE,
        HDMA_ENABLE
    )
    
    -- Frame callback
    state.callbacks.frame = emu.addEventCallback(
        on_frame_end,
        emu.eventType.endFrame
    )
    
    -- Get initial OBSEL
    update_obsel()
    
    emu.log("*** DMA DETECTION FIXED AND ACTIVE ***")
    emu.log("Play the game and watch for ROM transfers!")
end

-- Start
init()