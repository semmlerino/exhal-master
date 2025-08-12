-- ===============================================================================
-- SpritePal Sprite Finder for Mesen-S - WORKING VERSION
-- Based on official Mesen-S API documentation
-- ===============================================================================
-- This version uses the CORRECT Mesen-S memory types and API!
-- Works specifically for Kirby SNES games with HAL compression
-- ===============================================================================

local state = {
    frame = 0,
    sprites = {},
    vram_writes = {},
    dma_transfers = {},
    captured_offsets = {},
    message = "Sprite Finder Active",
    message_timer = 0,
    enabled = true
}

-- ===============================================================================
-- Read OAM (Sprite Data) - CORRECT API
-- ===============================================================================

function read_oam_sprites()
    -- Read OBSEL register to get sprite VRAM base
    local OBSEL = emu.read(0x2101, emu.memType.snesDebug)  -- No side effects
    local base_index = OBSEL & 0x07  -- ccc bits: OBJ tile VRAM base index
    local name_select = (OBSEL >> 3) & 0x03  -- Name select bits
    local obj_vram_base = base_index * 0x4000  -- Base VRAM address for sprite tiles
    
    local active_sprites = {}
    
    -- Read all 128 sprite entries
    for i = 0, 127 do
        local addr = i * 4
        
        -- Read sprite data from OAM
        local y = emu.read(addr, emu.memType.snesSpriteRam)
        local tile = emu.read(addr + 1, emu.memType.snesSpriteRam)
        local attr = emu.read(addr + 2, emu.memType.snesSpriteRam)
        local x_lo = emu.read(addr + 3, emu.memType.snesSpriteRam)
        
        -- Get high X bit (9th bit of X coordinate)
        local high_x_byte = emu.read(0x200 + math.floor(i/8), emu.memType.snesSpriteRam)
        local x_hi = (high_x_byte >> (i % 8)) & 0x1
        local x = x_lo + (x_hi << 8)
        
        -- Check if sprite is active (Y < 0xF0 means on-screen)
        if y < 0xF0 then
            local pal = attr & 0x7  -- 3-bit palette index
            local h_flip = (attr >> 6) & 1
            local v_flip = (attr >> 7) & 1
            local priority = (attr >> 4) & 0x3
            
            -- Calculate VRAM tile address
            local tile_addr
            if tile < 0x100 then
                -- First 256-tile block
                tile_addr = obj_vram_base + tile * 32  -- Each 4bpp tile is 32 bytes
            else
                -- Second 256-tile block
                tile_addr = obj_vram_base + ((name_select + 1) * 0x2000) + (tile - 0x100) * 32
            end
            
            table.insert(active_sprites, {
                index = i,
                x = x,
                y = y,
                tile = tile,
                tile_addr = tile_addr,
                palette = pal,
                h_flip = h_flip,
                v_flip = v_flip,
                priority = priority
            })
        end
    end
    
    return active_sprites
end

-- ===============================================================================
-- VRAM Write Callback - Track Graphics Loading
-- ===============================================================================

function setup_vram_callback()
    -- Set callback for VRAM writes to track when sprite graphics are loaded
    emu.addMemoryCallback(function(address, value)
        -- VRAM is being written - check DMA source
        check_dma_source(address)
        
        -- Log VRAM write
        table.insert(state.vram_writes, {
            vram_addr = address,
            value = value,
            frame = state.frame
        })
        
        -- Keep only last 100 writes
        if #state.vram_writes > 100 then
            table.remove(state.vram_writes, 1)
        end
        
        return value  -- Don't modify the write
    end, emu.memCallbackType.snesVramWrite, 0x0000, 0x7FFF)  -- Monitor all VRAM
end

-- ===============================================================================
-- DMA Tracking - Find ROM Source
-- ===============================================================================

function check_dma_source(vram_addr)
    -- Check all 8 DMA channels
    for channel = 0, 7 do
        local base = 0x4300 + (channel * 0x10)
        
        -- Read DMA registers
        local control = emu.read(base, emu.memType.snesDebug)
        local dest = emu.read(base + 0x01, emu.memType.snesDebug)
        
        -- Check if this is a VRAM transfer
        if dest == 0x18 or dest == 0x19 then
            -- Get source address
            local src_low = emu.read(base + 0x02, emu.memType.snesDebug)
            local src_high = emu.read(base + 0x03, emu.memType.snesDebug)
            local src_bank = emu.read(base + 0x04, emu.memType.snesDebug)
            local src_addr = (src_high * 256) + src_low
            
            -- Get size
            local size_low = emu.read(base + 0x05, emu.memType.snesDebug)
            local size_high = emu.read(base + 0x06, emu.memType.snesDebug)
            local size = (size_high * 256) + size_low
            
            if size > 0 then
                -- Calculate ROM offset
                local rom_offset = calculate_rom_offset(src_bank, src_addr)
                
                -- Record DMA transfer
                local transfer = {
                    channel = channel,
                    source = string.format("$%02X:%04X", src_bank, src_addr),
                    vram = string.format("$%04X", vram_addr),
                    size = size,
                    rom_offset = rom_offset,
                    rom_offset_hex = string.format("0x%06X", rom_offset),
                    frame = state.frame
                }
                
                table.insert(state.dma_transfers, transfer)
                
                -- Check if this is a new offset
                local is_new = true
                for _, captured in ipairs(state.captured_offsets) do
                    if captured.rom_offset == rom_offset then
                        is_new = false
                        break
                    end
                end
                
                if is_new then
                    table.insert(state.captured_offsets, transfer)
                    emu.log(string.format("DMA Transfer Found: %s -> VRAM %s, ROM: %s (%d bytes)",
                        transfer.source, transfer.vram, transfer.rom_offset_hex, size))
                    
                    state.message = "Found: " .. transfer.rom_offset_hex
                    state.message_timer = 120
                end
            end
        end
    end
end

-- ===============================================================================
-- ROM Offset Calculation
-- ===============================================================================

function calculate_rom_offset(bank, address)
    -- Detect ROM mapping (simplified - assumes LoROM for Kirby)
    -- Check for SMC header (512 bytes)
    local has_header = false
    local header_test = emu.read(0x7FC0 + 512 + 0x15, emu.memType.snesPrgRom)
    if header_test and header_test ~= 0xFF then
        has_header = true
    end
    
    -- LoROM calculation
    local offset = ((bank & 0x7F) * 0x8000) + (address & 0x7FFF)
    
    -- Add header if present
    if has_header then
        offset = offset + 512
    end
    
    return offset
end

-- ===============================================================================
-- Read Palette Data (CGRAM)
-- ===============================================================================

function read_sprite_palette(pal_index)
    -- Sprite palettes are in second half of CGRAM (indices 128-255)
    local cgram_start = 128 + pal_index * 16
    local colors = {}
    
    for j = 0, 15 do
        local color_addr = (cgram_start + j) * 2
        local color_word = emu.read16(color_addr, emu.memType.snesCgRam)
        
        local r = (color_word & 0x1F) * 8
        local g = ((color_word >> 5) & 0x1F) * 8
        local b = ((color_word >> 10) & 0x1F) * 8
        
        colors[j] = {r = r, g = g, b = b}
    end
    
    return colors
end

-- ===============================================================================
-- Frame Callback - Main Loop
-- ===============================================================================

function frame_callback()
    state.frame = state.frame + 1
    
    -- Read sprite data every frame
    state.sprites = read_oam_sprites()
    
    -- Log interesting sprites (e.g., Kirby is often sprite 0)
    if state.frame % 60 == 0 and #state.sprites > 0 then
        local kirby = state.sprites[1]  -- Assuming Kirby is sprite 0
        if kirby then
            emu.log(string.format("Sprite 0: X=%d,Y=%d Tile=$%03X VRAM=$%04X Pal=%d",
                kirby.x, kirby.y, kirby.tile, kirby.tile_addr, kirby.palette))
        end
    end
end

-- ===============================================================================
-- Drawing UI
-- ===============================================================================

function draw_ui()
    if not state.enabled then return end
    
    -- Main info panel
    emu.drawRectangle(5, 10, 400, 100, 0xCC000000, true)
    emu.drawRectangle(5, 10, 400, 100, 0xFFFFFFFF, false)
    
    emu.drawString(10, 15, "Mesen-S Sprite Finder (Correct API)", 0xFFFFFFFF)
    emu.drawString(10, 30, state.message, 0xFFFFFF00)
    emu.drawString(10, 45, "Active Sprites: " .. #state.sprites, 0xFFAAAAAA)
    emu.drawString(10, 60, "Captured Offsets: " .. #state.captured_offsets, 0xFF00FF00)
    emu.drawString(10, 75, "DMA Transfers: " .. #state.dma_transfers, 0xFFAAAAAA)
    emu.drawString(10, 90, "Frame: " .. state.frame, 0xFFAAAAAA)
    
    -- Show recent captures
    if #state.captured_offsets > 0 then
        local y = 115
        emu.drawRectangle(5, y, 400, math.min(#state.captured_offsets * 15 + 20, 90), 0xCC000000, true)
        emu.drawString(10, y + 5, "Captured ROM Offsets:", 0xFF00FF00)
        
        for i = math.max(1, #state.captured_offsets - 4), #state.captured_offsets do
            local cap = state.captured_offsets[i]
            if cap then
                emu.drawString(10, y + 5 + ((i - math.max(1, #state.captured_offsets - 4) + 1) * 15),
                    cap.source .. " -> " .. cap.vram .. " [" .. cap.rom_offset_hex .. "]", 0xFFFFFFFF)
            end
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

function handle_input()
    -- S key: Save results
    if emu.isKeyPressed("S") then
        save_results()
    end
    
    -- F10: Toggle overlay
    if emu.isKeyPressed("F10") then
        state.enabled = not state.enabled
    end
end

-- ===============================================================================
-- Save Results
-- ===============================================================================

function save_results()
    if #state.captured_offsets == 0 then
        emu.log("No offsets captured yet")
        return
    end
    
    emu.log("================================================================================")
    emu.log("SPRITE FINDER RESULTS - ROM OFFSETS")
    emu.log("================================================================================")
    
    for i, cap in ipairs(state.captured_offsets) do
        emu.log(string.format("%d. %s (%d bytes)", i, cap.rom_offset_hex, cap.size))
        emu.log("   Source: " .. cap.source .. " -> VRAM " .. cap.vram)
    end
    
    emu.log("")
    emu.log("QUICK COPY LIST FOR SPRITEPAL:")
    for _, cap in ipairs(state.captured_offsets) do
        emu.log(cap.rom_offset_hex)
    end
    emu.log("================================================================================")
    
    -- Also check for HAL compression
    emu.log("")
    emu.log("Note: Kirby games use HAL compression.")
    emu.log("Use exhal tool to decompress: exhal rom.sfc " .. (state.captured_offsets[1] and state.captured_offsets[1].rom_offset_hex or "0x??????") .. " output.bin")
end

-- ===============================================================================
-- Initialize
-- ===============================================================================

-- Setup VRAM write callback
setup_vram_callback()

-- Register frame callbacks
emu.addEventCallback(frame_callback, emu.eventType.endFrame)
emu.addEventCallback(draw_ui, emu.eventType.endFrame)
emu.addEventCallback(handle_input, emu.eventType.startFrame)

-- Initial log
emu.log("================================================================================")
emu.log("MESEN-S SPRITE FINDER - WORKING VERSION")
emu.log("================================================================================")
emu.log("This script uses the CORRECT Mesen-S API:")
emu.log("- emu.memType.snesSpriteRam for OAM")
emu.log("- emu.memType.snesVideoRam for VRAM")
emu.log("- emu.memType.snesPrgRom for ROM")
emu.log("- emu.memType.snesCgRam for palettes")
emu.log("")
emu.log("The script tracks DMA transfers to find ROM offsets.")
emu.log("Press S to save results, F10 to toggle overlay.")
emu.log("")
emu.log("For Kirby games, offsets point to HAL-compressed data.")
emu.log("Use exhal to decompress: exhal rom.sfc 0xOFFSET output.bin")
emu.log("================================================================================")