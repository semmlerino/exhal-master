-- Mesen 2 DMA Test - All Detection Methods
-- Tests different ways to detect DMA to find what works

emu.log("=== DMA DETECTION TEST - ALL METHODS ===")

local detections = {
    enum_write = 0,
    string_write = 0,
    int_1 = 0,
    int_2 = 0,
    manual_poll = 0
}

-- Method 1: Using discovered enum
local cb1 = emu.addMemoryCallback(
    function(addr, val)
        if val ~= 0 then
            detections.enum_write = detections.enum_write + 1
            emu.log(string.format("ENUM_WRITE: $420B = $%02X", val))
        end
    end,
    emu.callbackType.write,
    0x420B,
    0x420B
)

-- Method 2: Using string "write"
local cb2 = emu.addMemoryCallback(
    function(addr, val)
        if val ~= 0 then
            detections.string_write = detections.string_write + 1
            emu.log(string.format("STRING_WRITE: $420B = $%02X", val))
        end
    end,
    "write",
    0x420B,
    0x420B
)

-- Method 3: Using integer 1
local cb3 = emu.addMemoryCallback(
    function(addr, val)
        if val ~= 0 then
            detections.int_1 = detections.int_1 + 1
            emu.log(string.format("INT_1: $420B = $%02X", val))
        end
    end,
    1,
    0x420B,
    0x420B
)

-- Method 4: Using integer 2
local cb4 = emu.addMemoryCallback(
    function(addr, val)
        if val ~= 0 then
            detections.int_2 = detections.int_2 + 1
            emu.log(string.format("INT_2: $420B = $%02X", val))
        end
    end,
    2,
    0x420B,
    0x420B
)

-- Method 5: Manual polling each frame
local frame_count = 0
local last_dma_val = 0

local cb5 = emu.addEventCallback(
    function()
        frame_count = frame_count + 1
        
        -- Read DMA enable register
        local dma_val = emu.read(0x420B, emu.memType.snesMemory)
        
        -- Detect rising edge (0 -> non-zero transition)
        if dma_val ~= 0 and last_dma_val == 0 then
            detections.manual_poll = detections.manual_poll + 1
            emu.log(string.format("MANUAL_POLL: DMA triggered = $%02X at frame %d", 
                dma_val, frame_count))
        end
        
        last_dma_val = dma_val
        
        -- Status report every 300 frames
        if frame_count % 300 == 0 then
            emu.log("=== DETECTION COUNTS ===")
            emu.log(string.format("enum_write:   %d", detections.enum_write))
            emu.log(string.format("string_write: %d", detections.string_write))
            emu.log(string.format("int_1:        %d", detections.int_1))
            emu.log(string.format("int_2:        %d", detections.int_2))
            emu.log(string.format("manual_poll:  %d", detections.manual_poll))
            emu.log("========================")
            
            if detections.manual_poll > 0 and detections.enum_write == 0 then
                emu.log("!!! CALLBACKS NOT WORKING - USE POLLING !!!")
            end
        end
    end,
    emu.eventType.endFrame
)

emu.log("All detection methods active!")
emu.log("Play the game and watch which methods detect DMA...")
emu.log("Enter doors, change screens, collect items...")