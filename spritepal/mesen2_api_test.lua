-- Mesen 2 API Test Script
-- Minimal script to verify the correct API calls

emu.log("=== Mesen 2 API Test ===")

-- Test 1: Memory read
local function test_memory_read()
    local value = emu.read(0x420B, emu.memType.cpu)
    emu.log(string.format("Read $420B (DMA Enable): $%02X", value))
end

-- Test 2: Memory callback
local function on_dma_write(address, value)
    emu.log(string.format("DMA Write: $%04X = $%02X", address, value))
end

-- Test 3: Frame callback
local frame_count = 0
local function on_frame()
    frame_count = frame_count + 1
    if frame_count % 60 == 0 then
        emu.log(string.format("Frame %d", frame_count))
        test_memory_read()
    end
end

-- Register callbacks
local dma_callback = emu.addMemoryCallback(on_dma_write, emu.memCallbackType.cpuWrite, 0x420B, 0x420B)
local frame_callback = emu.addEventCallback(on_frame, emu.eventType.endFrame)

emu.log("Callbacks registered - monitoring $420B writes and frames")
emu.log("If you see frame counts and DMA writes, the API is working!")