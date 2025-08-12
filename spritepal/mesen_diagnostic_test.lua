-- ===============================================================================
-- Mesen-S API Diagnostic Script
-- Tests different API approaches to find what actually works
-- ===============================================================================

local frame_count = 0
local test_results = {}
local dma_history = {}
local callback_fired = false
local callback_count = 0

-- ===============================================================================
-- Test 1: Memory Read Syntax Variations
-- ===============================================================================

function test_memory_reads()
    local results = {}
    
    -- Test different ways to read $420B (DMA enable register)
    local address = 0x420B
    
    -- Method 1: String memory type
    local success1, value1 = pcall(function()
        return emu.read(address, "cpu")
    end)
    results["read(addr, 'cpu')"] = success1 and string.format("0x%02X", value1) or "FAILED"
    
    -- Method 2: No memory type
    local success2, value2 = pcall(function()
        return emu.read(address)
    end)
    results["read(addr)"] = success2 and string.format("0x%02X", value2) or "FAILED"
    
    -- Method 3: Try emu.memType if it exists
    local success3, value3 = pcall(function()
        return emu.read(address, emu.memType.cpu)
    end)
    results["read(addr, emu.memType.cpu)"] = success3 and string.format("0x%02X", value3) or "FAILED"
    
    -- Method 4: Try numeric type
    local success4, value4 = pcall(function()
        return emu.read(address, 0)  -- 0 might be cpu
    end)
    results["read(addr, 0)"] = success4 and string.format("0x%02X", value4) or "FAILED"
    
    -- Test controller reading (should change when buttons pressed)
    local success5, value5 = pcall(function()
        return emu.read(0x4218, "cpu")  -- Controller 1 low byte
    end)
    results["Controller at $4218"] = success5 and string.format("0x%02X", value5) or "FAILED"
    
    return results
end

-- ===============================================================================
-- Test 2: Monitor DMA-related registers
-- ===============================================================================

function check_dma_registers()
    local dma_info = {}
    
    -- Try to read DMA enable register
    local success, dma_enable = pcall(function()
        return emu.read(0x420B, "cpu")
    end)
    
    if success and dma_enable and dma_enable ~= 0 then
        dma_info.enable = string.format("0x%02X", dma_enable)
        dma_info.channels_active = {}
        
        -- Check which channels are active
        for ch = 0, 7 do
            if (dma_enable & (1 << ch)) ~= 0 then
                table.insert(dma_info.channels_active, ch)
                
                -- Read DMA channel parameters
                local base = 0x4300 + (ch * 0x10)
                local mode = emu.read(base, "cpu") or 0
                local dest = emu.read(base + 1, "cpu") or 0
                
                -- If it's a VRAM transfer
                if dest == 0x18 or dest == 0x19 then
                    local src_low = emu.read(base + 2, "cpu") or 0
                    local src_high = emu.read(base + 3, "cpu") or 0  
                    local src_bank = emu.read(base + 4, "cpu") or 0
                    
                    dma_info["ch" .. ch] = string.format("$%02X:%02X%02X -> VRAM", 
                        src_bank, src_high, src_low)
                    
                    -- Log this DMA
                    table.insert(dma_history, {
                        frame = frame_count,
                        channel = ch,
                        info = dma_info["ch" .. ch]
                    })
                end
            end
        end
    else
        dma_info.enable = success and "0x00" or "READ FAILED"
    end
    
    -- Also check HDMA enable
    local hdma_success, hdma_enable = pcall(function()
        return emu.read(0x420C, "cpu")
    end)
    dma_info.hdma = hdma_success and string.format("0x%02X", hdma_enable) or "FAILED"
    
    return dma_info
end

-- ===============================================================================
-- Test 3: Callback Registration
-- ===============================================================================

function test_callbacks()
    local results = {}
    
    -- Test 1: Memory callback with string type
    local success1 = pcall(function()
        emu.addMemoryCallback(function(addr, value)
            callback_fired = true
            callback_count = callback_count + 1
        end, "cpuWrite", 0x420B)
    end)
    results["addMemoryCallback with 'cpuWrite'"] = success1 and "Registered" or "FAILED"
    
    -- Test 2: Memory callback with enum if exists
    local success2 = pcall(function()
        if emu.memCallbackType then
            emu.addMemoryCallback(function(addr, value)
                callback_fired = true
                callback_count = callback_count + 1
            end, emu.memCallbackType.cpuWrite, 0x420B)
        end
    end)
    results["addMemoryCallback with enum"] = success2 and "Registered" or "FAILED"
    
    -- Test 3: Simple callback without type
    local success3 = pcall(function()
        emu.addMemoryCallback(function(addr, value)
            callback_fired = true
            callback_count = callback_count + 1
        end, 0x420B)  -- Just address
    end)
    results["addMemoryCallback minimal"] = success3 and "Registered" or "FAILED"
    
    return results
end

-- ===============================================================================
-- Test 4: Manual ROM Offset Calculation
-- ===============================================================================

function show_offset_for_bank_addr(bank, addr)
    -- LoROM calculation
    local lorom_offset = ((bank & 0x7F) * 0x8000) + (addr & 0x7FFF)
    
    -- HiROM calculation  
    local hirom_offset = ((bank & 0x3F) * 0x10000) + addr
    
    return {
        lorom = string.format("0x%06X", lorom_offset),
        hirom = string.format("0x%06X", hirom_offset)
    }
end

-- ===============================================================================
-- Drawing
-- ===============================================================================

function draw_diagnostics()
    local y = 10
    
    -- Title
    emu.drawRectangle(5, y, 400, 20, 0xCC000000, true)
    emu.drawString(10, y + 5, "MESEN-S DIAGNOSTIC - Frame: " .. frame_count, 0xFFFFFFFF)
    y = y + 25
    
    -- Memory Read Test Results
    emu.drawRectangle(5, y, 400, 100, 0xCC000000, true)
    emu.drawString(10, y + 5, "MEMORY READ TESTS:", 0xFFFFFF00)
    local read_results = test_memory_reads()
    local i = 0
    for method, result in pairs(read_results) do
        local color = result == "FAILED" and 0xFFFF0000 or 0xFF00FF00
        emu.drawString(10, y + 20 + (i * 12), method .. ": " .. result, color)
        i = i + 1
    end
    y = y + 105
    
    -- DMA Register Status
    emu.drawRectangle(5, y, 400, 80, 0xCC000000, true)
    emu.drawString(10, y + 5, "DMA REGISTERS THIS FRAME:", 0xFFFFFF00)
    local dma_info = check_dma_registers()
    emu.drawString(10, y + 20, "DMA Enable ($420B): " .. dma_info.enable, 0xFFFFFFFF)
    emu.drawString(10, y + 35, "HDMA Enable ($420C): " .. dma_info.hdma, 0xFFFFFFFF)
    if dma_info.channels_active and #dma_info.channels_active > 0 then
        emu.drawString(10, y + 50, "Active channels: " .. table.concat(dma_info.channels_active, ", "), 0xFF00FF00)
        for ch = 0, 7 do
            if dma_info["ch" .. ch] then
                emu.drawString(10, y + 65, "Ch" .. ch .. ": " .. dma_info["ch" .. ch], 0xFF00FF00)
            end
        end
    end
    y = y + 85
    
    -- Callback Status
    emu.drawRectangle(5, y, 400, 50, 0xCC000000, true)
    emu.drawString(10, y + 5, "CALLBACK STATUS:", 0xFFFFFF00)
    emu.drawString(10, y + 20, "Callback fired: " .. tostring(callback_fired), 0xFFFFFFFF)
    emu.drawString(10, y + 35, "Callback count: " .. callback_count, 0xFFFFFFFF)
    y = y + 55
    
    -- DMA History
    if #dma_history > 0 then
        emu.drawRectangle(5, y, 400, math.min(#dma_history * 15 + 20, 100), 0xCC000000, true)
        emu.drawString(10, y + 5, "DMA HISTORY (Last 5):", 0xFFFFFF00)
        for i = 1, math.min(#dma_history, 5) do
            local dma = dma_history[#dma_history - i + 1]
            emu.drawString(10, y + 5 + (i * 15), 
                "Frame " .. dma.frame .. ", Ch" .. dma.channel .. ": " .. dma.info, 
                0xFF00FF00)
        end
        y = y + math.min(#dma_history * 15 + 25, 105)
    end
    
    -- Manual offset calculator
    emu.drawRectangle(5, y, 400, 65, 0xCC000000, true)
    emu.drawString(10, y + 5, "EXAMPLE OFFSET CALCULATION:", 0xFFFFFF00)
    local example = show_offset_for_bank_addr(0x05, 0xA200)
    emu.drawString(10, y + 20, "SNES $05:A200 converts to:", 0xFFFFFFFF)
    emu.drawString(10, y + 35, "  LoROM: " .. example.lorom, 0xFF00FF00)
    emu.drawString(10, y + 50, "  HiROM: " .. example.hirom, 0xFF00FF00)
end

-- ===============================================================================
-- Main Callbacks
-- ===============================================================================

-- Test different callback registrations
test_callbacks()

-- Frame callback
emu.addEventCallback(function()
    frame_count = frame_count + 1
end, emu.eventType and emu.eventType.startFrame or "startFrame")

-- Draw callback
emu.addEventCallback(function()
    draw_diagnostics()
end, emu.eventType and emu.eventType.endFrame or "endFrame")

-- Log initial message
emu.log("================================================================================")
emu.log("MESEN-S DIAGNOSTIC SCRIPT")
emu.log("================================================================================")
emu.log("This script tests different API approaches to find what works.")
emu.log("Watch the overlay for test results.")
emu.log("")
emu.log("What to look for:")
emu.log("- Which memory read methods succeed")
emu.log("- Whether DMA registers show non-zero values")
emu.log("- Whether callbacks fire when DMA occurs")
emu.log("- Controller values should change when you press buttons")
emu.log("================================================================================")