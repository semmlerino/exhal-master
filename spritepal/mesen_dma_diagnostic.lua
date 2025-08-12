-- ===============================================================================
-- DMA Diagnostic Script for Mesen-S
-- Logs ALL DMA activity to understand what's happening
-- ===============================================================================

local state = {
    frame = 0,
    last_dma = 0,
    last_vram_addr = 0,
    dma_count = 0,
    vram_writes = 0,
    logged_channels = {}
}

-- Safe read function
function safe_read(address, memType)
    local success, value = pcall(emu.read, address, memType)
    if success and value then
        return value
    end
    return nil
end

function safe_read16(address, memType)
    local success, value = pcall(emu.read16, address, memType)
    if success and value then
        return value
    end
    return nil
end

-- Log DMA channel details
function log_dma_channel(channel, dma_enable)
    local base = 0x4300 + (channel * 0x10)
    
    -- Read all DMA registers for this channel
    local mode = safe_read(base, emu.memType.snesDebug)
    local dest = safe_read(base + 0x01, emu.memType.snesDebug)
    local src_low = safe_read(base + 0x02, emu.memType.snesDebug)
    local src_high = safe_read(base + 0x03, emu.memType.snesDebug)
    local src_bank = safe_read(base + 0x04, emu.memType.snesDebug)
    local size_low = safe_read(base + 0x05, emu.memType.snesDebug)
    local size_high = safe_read(base + 0x06, emu.memType.snesDebug)
    
    if mode == nil then
        emu.log(string.format("  Ch%d: FAILED TO READ REGISTERS!", channel))
        return
    end
    
    local size = (size_high or 0) * 256 + (size_low or 0)
    if size == 0 then size = 0x10000 end
    
    -- Get destination name
    local dest_name = "UNKNOWN"
    if dest == 0x18 then dest_name = "VRAM_LOW ($2118)"
    elseif dest == 0x19 then dest_name = "VRAM_HIGH ($2119)"
    elseif dest == 0x22 then dest_name = "CGRAM ($2122)"
    elseif dest == 0x04 then dest_name = "OAM ($2104)"
    elseif dest == 0x80 then dest_name = "WRAM ($2180)"
    else dest_name = string.format("$21%02X", dest)
    end
    
    emu.log(string.format("  Ch%d: Mode=$%02X Dest=%s Src=$%02X:%04X Size=%d bytes",
        channel, mode or 0, dest_name, src_bank or 0, 
        ((src_high or 0) * 256 + (src_low or 0)), size))
    
    -- If VRAM transfer, show VRAM address
    if dest == 0x18 or dest == 0x19 then
        local vram_low = safe_read(0x2116, emu.memType.snesDebug)
        local vram_high = safe_read(0x2117, emu.memType.snesDebug)
        local vram_addr = ((vram_high or 0) * 256) + (vram_low or 0)
        emu.log(string.format("       -> VRAM Address: $%04X", vram_addr))
        
        -- Check if this looks like sprite data
        if vram_addr >= 0x0000 and vram_addr <= 0x8000 then
            emu.log("       -> POSSIBLE SPRITE DATA TRANSFER!")
            state.dma_count = state.dma_count + 1
        end
    end
end

-- Main diagnostic function
function diagnose_dma()
    state.frame = state.frame + 1
    
    -- Read DMA enable register
    local dma_enable = safe_read(0x420B, emu.memType.snesDebug)
    
    if dma_enable == nil then
        if state.frame % 60 == 0 then
            emu.log("WARNING: Cannot read DMA enable register $420B!")
        end
        return
    end
    
    -- Check if DMA state changed
    if dma_enable ~= state.last_dma then
        if dma_enable ~= 0 then
            emu.log(string.format("\n[Frame %d] DMA TRIGGERED! Enable=$%02X (binary: %s)",
                state.frame, dma_enable, 
                string.format("%08b", dma_enable):reverse()))
            
            -- Check each channel
            for channel = 0, 7 do
                if (dma_enable & (1 << channel)) ~= 0 then
                    log_dma_channel(channel, dma_enable)
                end
            end
        else
            -- DMA was cleared
            if state.last_dma ~= 0 then
                emu.log(string.format("[Frame %d] DMA cleared (was $%02X)", 
                    state.frame, state.last_dma))
            end
        end
        
        state.last_dma = dma_enable
    end
    
    -- Also check VRAM address register changes
    local vram_low = safe_read(0x2116, emu.memType.snesDebug) or 0
    local vram_high = safe_read(0x2117, emu.memType.snesDebug) or 0
    local vram_addr = (vram_high * 256) + vram_low
    
    if vram_addr ~= state.last_vram_addr and vram_addr ~= 0 then
        -- Only log significant changes
        if math.abs(vram_addr - state.last_vram_addr) > 0x100 then
            state.vram_writes = state.vram_writes + 1
        end
        state.last_vram_addr = vram_addr
    end
    
    -- Periodic status
    if state.frame % 300 == 0 then
        emu.log(string.format("\n=== STATUS at Frame %d ===", state.frame))
        emu.log(string.format("DMA Transfers Found: %d", state.dma_count))
        emu.log(string.format("VRAM Write Activity: %d significant changes", state.vram_writes))
        
        -- Check OBSEL for sprite configuration
        local obsel = safe_read(0x2101, emu.memType.snesDebug)
        if obsel then
            local base = (obsel & 0x07) * 0x4000
            local name = ((obsel >> 3) & 0x03)
            emu.log(string.format("OBSEL=$%02X -> Sprite Base VRAM: $%04X, Name Select: %d",
                obsel, base, name))
        end
        
        -- Check if sprites are active
        local active_sprites = 0
        for i = 0, 127 do
            local y = safe_read(i * 4, emu.memType.snesSpriteRam)
            if y and y < 0xF0 then
                active_sprites = active_sprites + 1
            end
        end
        emu.log(string.format("Active Sprites in OAM: %d", active_sprites))
        emu.log("========================\n")
    end
end

-- UI overlay
function draw_diagnostic()
    emu.drawRectangle(5, 5, 250, 60, 0xCC000000, true)
    emu.drawRectangle(5, 5, 250, 60, 0xFFFF00FF, false)
    
    emu.drawString(10, 10, "DMA DIAGNOSTIC", 0xFFFF00FF)
    emu.drawString(10, 25, "Frame: " .. state.frame, 0xFFFFFFFF)
    emu.drawString(10, 40, "DMA Captures: " .. state.dma_count, 0xFF00FF00)
    emu.drawString(10, 55, "Check console for details", 0xFFAAAAAA)
end

-- Register callbacks
emu.addEventCallback(diagnose_dma, emu.eventType.startFrame)
emu.addEventCallback(draw_diagnostic, emu.eventType.endFrame)

-- Initial message
emu.log("================================================================================")
emu.log("DMA DIAGNOSTIC SCRIPT - Logging ALL DMA Activity")
emu.log("================================================================================")
emu.log("This script logs every DMA transfer to help diagnose issues.")
emu.log("Play the game normally and watch the console output.")
emu.log("")
emu.log("What we're looking for:")
emu.log("- DMA transfers to VRAM ($2118/2119)")
emu.log("- VRAM addresses where sprites might be loaded")
emu.log("- Any errors reading registers")
emu.log("")
emu.log("Status updates every 5 seconds (300 frames)")
emu.log("================================================================================")