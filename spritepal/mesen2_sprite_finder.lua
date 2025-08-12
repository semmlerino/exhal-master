-- Mesen 2 Sprite Finder for Kirby SNES Games
-- Uses Mesen 2's enhanced callback API for accurate DMA capture
-- Tracks sprites and correlates them with ROM offsets via DMA transfers

-- Global state
local state = {
    frame_count = 0,
    dma_captures = {},
    active_sprites = {},
    unique_rom_offsets = {},
    obsel_config = {
        name_base = 0,
        name_select = 0,
        size_select = 0
    },
    last_vram_addr = 0,
    callbacks = {}  -- Store callback IDs for cleanup
}

-- Constants
local DMA_ENABLE = 0x420B
local DMA_BASE = 0x4300
local OBSEL = 0x2101
local VRAM_ADDR_L = 0x2116
local VRAM_ADDR_H = 0x2117
local VRAM_DATA_L = 0x2118
local VRAM_DATA_H = 0x2119
local OAM_ADDR = 0x2102
local OAM_DATA = 0x2104

-- Helper: Convert CPU address to ROM offset (LoROM)
local function cpu_to_rom_offset(cpu_addr)
    -- LoROM mapping: banks $00-$7F and $80-$FF
    local bank = (cpu_addr >> 16) & 0xFF
    local addr = cpu_addr & 0xFFFF
    
    -- Check if address is in ROM range
    if addr < 0x8000 then
        return nil  -- Not ROM
    end
    
    -- Calculate LoROM offset
    local rom_offset = ((bank & 0x7F) * 0x8000) + (addr - 0x8000)
    return rom_offset
end

-- Helper: Read DMA channel registers
local function read_dma_channel(channel)
    local base = DMA_BASE + (channel * 0x10)
    
    local control = emu.read(base + 0x00, emu.cpu)
    local dest_reg = emu.read(base + 0x01, emu.cpu)
    local src_low = emu.read(base + 0x02, emu.cpu)
    local src_mid = emu.read(base + 0x03, emu.cpu)
    local src_bank = emu.read(base + 0x04, emu.cpu)
    local size_low = emu.read(base + 0x05, emu.cpu)
    local size_high = emu.read(base + 0x06, emu.cpu)
    
    local source_addr = (src_bank << 16) | (src_mid << 8) | src_low
    local transfer_size = (size_high << 8) | size_low
    if transfer_size == 0 then
        transfer_size = 0x10000  -- 0 means 64KB
    end
    
    return {
        control = control,
        dest_reg = dest_reg,
        source_addr = source_addr,
        transfer_size = transfer_size,
        direction = (control & 0x80) ~= 0 and "B->A" or "A->B"
    }
end

-- Callback: DMA Enable register write
local function on_dma_enable_write(address, value)
    if value == 0 then return end  -- No channels enabled
    
    -- Read current VRAM address
    local vram_low = emu.read(VRAM_ADDR_L, emu.MemoryType.CpuMemory)
    local vram_high = emu.read(VRAM_ADDR_H, emu.MemoryType.CpuMemory)
    local vram_addr = (vram_high << 8) | vram_low
    
    -- Check each DMA channel
    for channel = 0, 7 do
        if (value & (1 << channel)) ~= 0 then
            local dma = read_dma_channel(channel)
            
            -- Check if this is a VRAM transfer
            if dma.dest_reg == 0x18 or dma.dest_reg == 0x19 then
                -- Calculate ROM offset
                local rom_offset = cpu_to_rom_offset(dma.source_addr)
                
                if rom_offset then
                    -- Capture the DMA transfer
                    local capture = {
                        frame = state.frame_count,
                        channel = channel,
                        vram_addr = vram_addr * 2,  -- VRAM is word-addressed
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
                            hit_count = 0
                        }
                    end
                    
                    local rom_data = state.unique_rom_offsets[rom_offset]
                    rom_data.last_frame = state.frame_count
                    rom_data.hit_count = rom_data.hit_count + 1
                    rom_data.vram_addrs[vram_addr] = true
                    
                    -- Log the capture
                    emu.log(string.format(
                        "DMA_CAPTURE: Frame=%d Channel=%d VRAM=$%04X ROM=$%06X Size=%d",
                        state.frame_count, channel, vram_addr, rom_offset, dma.transfer_size
                    ))
                end
            end
        end
    end
end

-- Callback: OBSEL register write
local function on_obsel_write(address, value)
    state.obsel_config.name_base = value & 0x07
    state.obsel_config.name_select = (value >> 3) & 0x03
    state.obsel_config.size_select = (value >> 5) & 0x07
    
    emu.log(string.format(
        "OBSEL_UPDATE: base=%d select=%d size=%d",
        state.obsel_config.name_base,
        state.obsel_config.name_select,
        state.obsel_config.size_select
    ))
end

-- Analyze OAM for active sprites
local function analyze_oam()
    -- Read OAM data
    local oam_data = {}
    for i = 0, 511 do
        oam_data[i] = emu.read(0x2000 + i, emu.MemoryType.PpuMemory)
    end
    
    -- Parse sprite entries
    state.active_sprites = {}
    for i = 0, 127 do
        local base = i * 4
        local x = oam_data[base]
        local y = oam_data[base + 1]
        local tile = oam_data[base + 2]
        local attr = oam_data[base + 3]
        
        -- Check if sprite is visible
        if y < 224 then  -- On-screen
            local sprite = {
                id = i,
                x = x,
                y = y,
                tile = tile,
                attr = attr,
                palette = (attr >> 1) & 0x07,
                priority = (attr >> 4) & 0x03,
                flip_h = (attr & 0x40) ~= 0,
                flip_v = (attr & 0x80) ~= 0
            }
            
            -- Calculate VRAM address for this sprite's tiles
            local name_base = state.obsel_config.name_base * 0x2000
            local tile_addr = name_base + (tile * 32)  -- 32 bytes per tile
            sprite.vram_addr = tile_addr
            
            table.insert(state.active_sprites, sprite)
        end
    end
end

-- Correlate sprites with DMA captures
local function correlate_sprites_and_dma()
    for _, sprite in ipairs(state.active_sprites) do
        -- Look for DMA captures that match this sprite's VRAM region
        for _, capture in ipairs(state.dma_captures) do
            -- Check if DMA destination overlaps with sprite tiles
            local sprite_vram_start = sprite.vram_addr
            local sprite_vram_end = sprite_vram_start + 128  -- 4 tiles max
            local dma_vram_start = capture.vram_addr
            local dma_vram_end = dma_vram_start + capture.size
            
            if dma_vram_start < sprite_vram_end and dma_vram_end > sprite_vram_start then
                -- Found a match!
                emu.log(string.format(
                    "SPRITE_MATCH: id=%d pos=(%d,%d) tile=$%02X -> ROM=$%06X",
                    sprite.id, sprite.x, sprite.y, sprite.tile, capture.rom_offset
                ))
            end
        end
    end
end

-- Frame end callback
local function on_frame_end()
    state.frame_count = state.frame_count + 1
    
    -- Analyze OAM every frame
    analyze_oam()
    
    -- Correlate sprites with DMA captures
    if #state.active_sprites > 0 and #state.dma_captures > 0 then
        correlate_sprites_and_dma()
    end
    
    -- Status update every 300 frames
    if state.frame_count % 300 == 0 then
        local unique_count = 0
        for _ in pairs(state.unique_rom_offsets) do
            unique_count = unique_count + 1
        end
        
        emu.log(string.format(
            "STATUS: Frame=%d Sprites=%d DMA_Captures=%d Unique_ROM=%d",
            state.frame_count,
            #state.active_sprites,
            #state.dma_captures,
            unique_count
        ))
        
        -- Export findings
        if unique_count > 0 then
            export_findings()
        end
    end
end

-- Export findings to file
function export_findings()
    local output = "=== Mesen 2 Sprite Finder Results ===\n"
    output = output .. string.format("Frame: %d\n", state.frame_count)
    output = output .. string.format("Total DMA Captures: %d\n", #state.dma_captures)
    output = output .. "\nUnique ROM Offsets:\n"
    
    -- Sort ROM offsets
    local sorted_offsets = {}
    for offset, data in pairs(state.unique_rom_offsets) do
        table.insert(sorted_offsets, {offset = offset, data = data})
    end
    table.sort(sorted_offsets, function(a, b) return a.offset < b.offset end)
    
    -- Output each unique ROM offset
    for _, entry in ipairs(sorted_offsets) do
        output = output .. string.format(
            "  ROM $%06X: hits=%d frames=%d-%d vram_count=%d\n",
            entry.offset,
            entry.data.hit_count,
            entry.data.first_frame,
            entry.data.last_frame,
            table.getn(entry.data.vram_addrs)
        )
    end
    
    -- Write to file
    local file = io.open("mesen2_sprite_findings.txt", "w")
    if file then
        file:write(output)
        file:close()
        emu.log("Findings exported to mesen2_sprite_findings.txt")
    end
end

-- Initialize callbacks
function init()
    emu.log("=== Mesen 2 Sprite Finder Starting ===")
    emu.log("Monitoring DMA transfers to VRAM for sprite tracking...")
    
    -- Set up memory callbacks
    state.callbacks.dma = emu.addMemoryCallback(
        on_dma_enable_write,
        emu.cpuWrite,
        DMA_ENABLE,
        DMA_ENABLE
    )
    
    state.callbacks.obsel = emu.addMemoryCallback(
        on_obsel_write,
        emu.cpuWrite,
        OBSEL,
        OBSEL
    )
    
    -- Set up frame callback
    state.callbacks.frame = emu.addEventCallback(
        on_frame_end,
        emu.endFrame
    )
    
    emu.log("Callbacks registered. Monitoring active...")
end

-- Cleanup on script end
function cleanup()
    emu.log("Cleaning up callbacks...")
    
    -- Remove all callbacks
    if state.callbacks.dma then
        emu.removeMemoryCallback(state.callbacks.dma)
    end
    if state.callbacks.obsel then
        emu.removeMemoryCallback(state.callbacks.obsel)
    end
    if state.callbacks.frame then
        emu.removeEventCallback(state.callbacks.frame)
    end
    
    -- Final export
    export_findings()
    
    emu.log("=== Mesen 2 Sprite Finder Stopped ===")
end

-- Main execution
init()

-- Note: Mesen 2 handles script lifecycle automatically
-- The script will run until stopped by the user