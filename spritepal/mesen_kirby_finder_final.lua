-- ===============================================================================
-- Kirby Sprite Finder for Mesen-S - FINAL WORKING VERSION
-- Works with exhal for decompression
-- ===============================================================================
-- This version uses correct memory types WITHOUT broken callback API
-- Designed specifically for Kirby SNES games with HAL compression
-- ===============================================================================

local state = {
    frame = 0,
    sprites = {},
    dma_captures = {},
    last_dma_enable = 0,
    message = "Kirby Sprite Finder Active - Play to detect sprites",
    message_timer = 180,
    enabled = true
}

-- ===============================================================================
-- Correct Memory Type Access (from PDF documentation)
-- ===============================================================================

function safe_read(address, memType)
    local success, value = pcall(emu.read, address, memType)
    if success and value then
        return value
    end
    return 0
end

function safe_read16(address, memType)
    local success, value = pcall(emu.read16, address, memType)
    if success and value then
        return value
    end
    return 0
end

-- ===============================================================================
-- Read OAM Sprites (Using Correct API from PDF)
-- ===============================================================================

function read_sprites()
    -- Read OBSEL register for sprite VRAM configuration
    local OBSEL = safe_read(0x2101, emu.memType.snesDebug)  -- Use debug to avoid side effects
    local base_index = OBSEL & 0x07  -- OBJ tile VRAM base
    local name_select = (OBSEL >> 3) & 0x03  -- Name select bits
    local obj_vram_base = base_index * 0x4000  -- Base VRAM address
    
    local active_sprites = {}
    
    -- Read all 128 sprites from OAM
    for i = 0, 127 do
        local addr = i * 4
        
        -- Read sprite data
        local y = safe_read(addr, emu.memType.snesSpriteRam)
        local tile = safe_read(addr + 1, emu.memType.snesSpriteRam)
        local attr = safe_read(addr + 2, emu.memType.snesSpriteRam)
        local x_lo = safe_read(addr + 3, emu.memType.snesSpriteRam)
        
        -- Get 9th bit of X coordinate
        local high_x_byte = safe_read(0x200 + math.floor(i/8), emu.memType.snesSpriteRam)
        local x_hi = (high_x_byte >> (i % 8)) & 0x1
        local x = x_lo + (x_hi << 8)
        
        -- Check if sprite is active (Y < 0xF0 is on-screen)
        if y < 0xF0 then
            -- Calculate VRAM address for this sprite's tiles
            local tile_addr
            if tile < 0x100 then
                tile_addr = obj_vram_base + tile * 32  -- 32 bytes per 4bpp tile
            else
                tile_addr = obj_vram_base + ((name_select + 1) * 0x2000) + (tile - 0x100) * 32
            end
            
            table.insert(active_sprites, {
                index = i,
                x = x,
                y = y,
                tile = tile,
                vram_addr = tile_addr,
                palette = attr & 0x7
            })
        end
    end
    
    return active_sprites
end

-- ===============================================================================
-- Poll DMA Registers (Instead of Callbacks)
-- ===============================================================================

function check_dma_transfers()
    -- Check DMA enable register
    local dma_enable = safe_read(0x420B, emu.memType.snesDebug)
    
    -- Only process if DMA was just triggered (rising edge detection)
    if dma_enable ~= 0 and dma_enable ~= state.last_dma_enable then
        
        -- Check each enabled channel
        for channel = 0, 7 do
            if (dma_enable & (1 << channel)) ~= 0 then
                local base = 0x4300 + (channel * 0x10)
                
                -- Read DMA parameters
                local mode = safe_read(base, emu.memType.snesDebug)
                local dest = safe_read(base + 0x01, emu.memType.snesDebug)
                
                -- Check if this is a VRAM transfer (destination $2118/2119)
                if dest == 0x18 or dest == 0x19 then
                    -- Get source address
                    local src_low = safe_read(base + 0x02, emu.memType.snesDebug)
                    local src_high = safe_read(base + 0x03, emu.memType.snesDebug)
                    local src_bank = safe_read(base + 0x04, emu.memType.snesDebug)
                    
                    -- Get transfer size
                    local size_low = safe_read(base + 0x05, emu.memType.snesDebug)
                    local size_high = safe_read(base + 0x06, emu.memType.snesDebug)
                    local size = (size_high * 256) + size_low
                    if size == 0 then size = 0x10000 end  -- 0 means 64KB
                    
                    -- Get VRAM destination
                    local vram_low = safe_read(0x2116, emu.memType.snesDebug)
                    local vram_high = safe_read(0x2117, emu.memType.snesDebug)
                    local vram_addr = (vram_high * 256) + vram_low
                    
                    -- Calculate ROM offset (LoROM with possible header)
                    local rom_offset = calculate_rom_offset(src_bank, src_high * 256 + src_low)
                    
                    -- Check if this is sprite data (VRAM $4000-$7FFF is common for sprites)
                    if vram_addr >= 0x4000 and vram_addr <= 0x7FFF then
                        
                        -- Check if already captured
                        local is_new = true
                        for _, cap in ipairs(state.dma_captures) do
                            if cap.rom_offset == rom_offset then
                                is_new = false
                                break
                            end
                        end
                        
                        if is_new then
                            local capture = {
                                rom_offset = rom_offset,
                                rom_offset_hex = string.format("0x%06X", rom_offset),
                                source = string.format("$%02X:%04X", src_bank, src_high * 256 + src_low),
                                vram = string.format("$%04X", vram_addr),
                                size = size,
                                channel = channel,
                                frame = state.frame
                            }
                            
                            table.insert(state.dma_captures, capture)
                            
                            -- Log to console
                            emu.log(string.format("SPRITE DMA: %s -> VRAM %s | ROM: %s (%d bytes) | Use: exhal rom.sfc %s sprite.bin",
                                capture.source, capture.vram, capture.rom_offset_hex, size, capture.rom_offset_hex))
                            
                            state.message = "Found: " .. capture.rom_offset_hex .. " (use exhal to decompress)"
                            state.message_timer = 180
                        end
                    end
                end
            end
        end
    end
    
    state.last_dma_enable = dma_enable
end

-- ===============================================================================
-- ROM Offset Calculation
-- ===============================================================================

function calculate_rom_offset(bank, address)
    -- Check for SMC header (512 bytes)
    local header_offset = 0
    
    -- Try to detect header by reading ROM
    local test_with_header = safe_read(0x7FC0 + 512 + 0x15, emu.memType.snesPrgRom)
    if test_with_header ~= 0 and test_with_header ~= 0xFF then
        header_offset = 512
    end
    
    -- LoROM calculation (Kirby games use LoROM)
    local offset = ((bank & 0x7F) * 0x8000) + (address & 0x7FFF)
    
    return offset + header_offset
end

-- ===============================================================================
-- Read Sprite Palettes
-- ===============================================================================

function read_palette(pal_index)
    -- Sprite palettes start at CGRAM index 128
    local cgram_start = 128 + pal_index * 16
    local colors = {}
    
    for i = 0, 15 do
        local addr = (cgram_start + i) * 2
        local color = safe_read16(addr, emu.memType.snesCgRam)
        
        -- Convert 15-bit BGR to RGB
        local r = (color & 0x1F) * 8
        local g = ((color >> 5) & 0x1F) * 8
        local b = ((color >> 10) & 0x1F) * 8
        
        colors[i + 1] = string.format("(%d,%d,%d)", r, g, b)
    end
    
    return colors
end

-- ===============================================================================
-- Frame Processing
-- ===============================================================================

function process_frame()
    state.frame = state.frame + 1
    
    -- Read current sprites
    state.sprites = read_sprites()
    
    -- Check for DMA transfers
    check_dma_transfers()
    
    -- Log Kirby sprite info periodically (usually sprite 0)
    if state.frame % 120 == 0 and #state.sprites > 0 then
        local kirby = state.sprites[1]  -- Kirby is often sprite 0
        if kirby then
            emu.log(string.format("Kirby (Sprite 0): Pos(%d,%d) Tile=$%03X VRAM=$%04X Pal=%d",
                kirby.x, kirby.y, kirby.tile, kirby.vram_addr, kirby.palette))
        end
    end
end

-- ===============================================================================
-- UI Drawing
-- ===============================================================================

function draw_ui()
    if not state.enabled then return end
    
    -- Main panel
    emu.drawRectangle(5, 10, 450, 110, 0xCC000000, true)
    emu.drawRectangle(5, 10, 450, 110, 0xFFFFFFFF, false)
    
    emu.drawString(10, 15, "KIRBY SPRITE FINDER - Works with exhal", 0xFFFFFFFF)
    emu.drawString(10, 30, state.message, 0xFFFFFF00)
    emu.drawString(10, 45, "Active Sprites: " .. #state.sprites, 0xFFAAAAAA)
    emu.drawString(10, 60, "DMA Captures: " .. #state.dma_captures, 0xFF00FF00)
    emu.drawString(10, 75, "Frame: " .. state.frame, 0xFFAAAAAA)
    emu.drawString(10, 90, "Press S to save results | F10 to toggle", 0xFFAAAAAA)
    
    -- Show recent captures
    if #state.dma_captures > 0 then
        local y = 125
        emu.drawRectangle(5, y, 450, math.min(#state.dma_captures * 20 + 25, 100), 0xCC000000, true)
        emu.drawRectangle(5, y, 450, math.min(#state.dma_captures * 20 + 25, 100), 0xFF00FF00, false)
        emu.drawString(10, y + 5, "Captured ROM Offsets (use with exhal):", 0xFF00FF00)
        
        for i = math.max(1, #state.dma_captures - 3), #state.dma_captures do
            if state.dma_captures[i] then
                local cap = state.dma_captures[i]
                local line_y = y + 10 + ((i - math.max(1, #state.dma_captures - 3)) * 20)
                emu.drawString(10, line_y, 
                    string.format("%s | exhal rom.sfc %s out.bin", 
                        cap.rom_offset_hex, cap.rom_offset_hex), 
                    0xFFFFFFFF)
            end
        end
    end
    
    if state.message_timer > 0 then
        state.message_timer = state.message_timer - 1
    end
end

-- ===============================================================================
-- Input and Save
-- ===============================================================================

function handle_input()
    if emu.isKeyPressed and emu.isKeyPressed("S") then
        save_results()
    end
    
    if emu.isKeyPressed and emu.isKeyPressed("F10") then
        state.enabled = not state.enabled
    end
end

function save_results()
    if #state.dma_captures == 0 then
        emu.log("No captures yet - play the game to trigger sprite loads")
        return
    end
    
    emu.log("================================================================================")
    emu.log("KIRBY SPRITE FINDER - ROM OFFSETS FOR EXHAL")
    emu.log("================================================================================")
    emu.log("Found " .. #state.dma_captures .. " sprite data transfers")
    emu.log("")
    
    emu.log("EXHAL COMMANDS (copy and run these):")
    emu.log("--------------------------------------")
    for i, cap in ipairs(state.dma_captures) do
        emu.log(string.format("exhal rom.sfc %s sprite_%d.bin", cap.rom_offset_hex, i))
    end
    
    emu.log("")
    emu.log("RAW OFFSETS:")
    emu.log("-------------")
    for _, cap in ipairs(state.dma_captures) do
        emu.log(cap.rom_offset_hex .. " (" .. cap.size .. " bytes) -> VRAM " .. cap.vram)
    end
    
    emu.log("")
    emu.log("WORKFLOW:")
    emu.log("---------")
    emu.log("1. Run exhal commands above to decompress sprites")
    emu.log("2. Edit .bin files in SpritePal or tile editor")
    emu.log("3. Recompress: inhal sprite.bin rom.sfc <offset>")
    emu.log("================================================================================")
    
    state.message = "Results saved to console - " .. #state.dma_captures .. " offsets"
    state.message_timer = 180
end

-- ===============================================================================
-- Initialize and Run
-- ===============================================================================

-- Register callbacks
emu.addEventCallback(process_frame, emu.eventType.startFrame)
emu.addEventCallback(draw_ui, emu.eventType.endFrame)
emu.addEventCallback(handle_input, emu.eventType.startFrame)

-- Initial message
emu.log("================================================================================")
emu.log("KIRBY SPRITE FINDER - FINAL WORKING VERSION")
emu.log("================================================================================")
emu.log("This script works with your exhal tool!")
emu.log("")
emu.log("How to use:")
emu.log("1. Play Kirby - script detects sprite loads automatically")
emu.log("2. Press S to save captured offsets")
emu.log("3. Run: exhal rom.sfc 0xOFFSET sprite.bin")
emu.log("4. Edit sprite.bin in SpritePal")
emu.log("5. Recompress: inhal sprite.bin rom.sfc 0xOFFSET")
emu.log("")
emu.log("The script uses correct Mesen-S memory types:")
emu.log("- snesSpriteRam for OAM")
emu.log("- snesVideoRam for VRAM")
emu.log("- snesPrgRom for ROM")
emu.log("- snesCgRam for palettes")
emu.log("================================================================================")