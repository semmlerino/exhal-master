-- Mesen 2 Aggressive DMA Monitor
-- Monitors ALL DMA activity with multiple detection methods

emu.log("=== AGGRESSIVE DMA MONITOR STARTING ===")
emu.log("This will detect ANY DMA/HDMA activity")
emu.log("INSTRUCTIONS: Enter gameplay and move between areas!")

local frame_count = 0
local total_writes = 0
local dma_triggers = 0
local hdma_triggers = 0

-- Monitor MORE registers
local DMA_REGISTERS = {
    {addr = 0x420B, name = "DMA_ENABLE"},
    {addr = 0x420C, name = "HDMA_ENABLE"},
    {addr = 0x4300, name = "DMA0_CTRL"},
    {addr = 0x4310, name = "DMA1_CTRL"},
    {addr = 0x4320, name = "DMA2_CTRL"},
    {addr = 0x4330, name = "DMA3_CTRL"},
    {addr = 0x4340, name = "DMA4_CTRL"},
    {addr = 0x4350, name = "DMA5_CTRL"},
    {addr = 0x4360, name = "DMA6_CTRL"},
    {addr = 0x4370, name = "DMA7_CTRL"}
}

-- Callback for ANY write to DMA registers
local function on_dma_write(address, value)
    total_writes = total_writes + 1
    
    -- Find which register was written
    local reg_name = string.format("$%04X", address)
    for _, reg in ipairs(DMA_REGISTERS) do
        if reg.addr == address then
            reg_name = reg.name
            break
        end
    end
    
    -- Always log non-zero writes
    if value ~= 0 then
        emu.log(string.format("DMA_WRITE: %s = $%02X at frame %d", 
            reg_name, value, frame_count))
        
        -- Special handling for enable registers
        if address == 0x420B then
            dma_triggers = dma_triggers + 1
            emu.log("*** DMA TRIGGERED! ***")
            
            -- Read all channel parameters
            for ch = 0, 7 do
                if (value & (1 << ch)) ~= 0 then
                    local base = 0x4300 + (ch * 0x10)
                    local ctrl = emu.read(base, emu.memType.snesMemory)
                    local dest = emu.read(base + 1, emu.memType.snesMemory)
                    local src_bank = emu.read(base + 4, emu.memType.snesMemory)
                    
                    emu.log(string.format("  Channel %d: dest=$21%02X bank=$%02X mode=%d",
                        ch, dest, src_bank, ctrl & 7))
                end
            end
        elseif address == 0x420C then
            hdma_triggers = hdma_triggers + 1
            emu.log("*** HDMA TRIGGERED! ***")
        end
    end
end

-- Register callbacks for ALL DMA-related addresses
local callbacks = {}

-- Method 1: Monitor enable registers
callbacks[#callbacks+1] = emu.addMemoryCallback(
    on_dma_write,
    emu.callbackType.write,  -- Use the enum we discovered
    0x420B,
    0x420C
)

-- Method 2: Monitor all DMA control registers
callbacks[#callbacks+1] = emu.addMemoryCallback(
    on_dma_write,
    emu.callbackType.write,
    0x4300,
    0x437F
)

-- Also try using integer directly
callbacks[#callbacks+1] = emu.addMemoryCallback(
    function(addr, val)
        if addr == 0x420B and val ~= 0 then
            emu.log(string.format("ALT_DETECT: DMA $420B = $%02X", val))
        end
    end,
    1,  -- Try integer 1 (write)
    0x420B,
    0x420B
)

-- Frame callback for status
local frame_callback = emu.addEventCallback(
    function()
        frame_count = frame_count + 1
        
        -- Status every 60 frames (1 second)
        if frame_count % 60 == 0 then
            -- Also manually check DMA enable registers
            local dma_val = emu.read(0x420B, emu.memType.snesMemory)
            local hdma_val = emu.read(0x420C, emu.memType.snesMemory)
            
            emu.log(string.format(
                "STATUS: Frame=%d Writes=%d DMA=%d HDMA=%d [Regs: DMA=$%02X HDMA=$%02X]",
                frame_count, total_writes, dma_triggers, hdma_triggers,
                dma_val, hdma_val
            ))
            
            -- Check if DMA might be happening without our callbacks
            if dma_val ~= 0 then
                emu.log("!!! DMA REGISTER IS SET BUT NOT CAUGHT BY CALLBACK !!!")
            end
        end
        
        -- Big status every 300 frames
        if frame_count % 300 == 0 then
            emu.log("=====================================")
            if dma_triggers == 0 and hdma_triggers == 0 then
                emu.log("NO DMA DETECTED YET!")
                emu.log("TIPS:")
                emu.log("  1. Make sure you're in GAMEPLAY, not menus")
                emu.log("  2. Enter a door or pipe to load new area")
                emu.log("  3. Move to different screens")
                emu.log("  4. Collect a power-up")
                emu.log("  5. Die and respawn")
            else
                emu.log(string.format("SUCCESS: %d DMA and %d HDMA triggers detected!",
                    dma_triggers, hdma_triggers))
            end
            emu.log("=====================================")
        end
    end,
    emu.eventType.endFrame
)

-- Also poll DMA registers directly every frame
local poll_callback = emu.addEventCallback(
    function()
        local dma = emu.read(0x420B, emu.memType.snesMemory)
        local hdma = emu.read(0x420C, emu.memType.snesMemory)
        
        -- Only log if non-zero
        if dma ~= 0 then
            emu.log(string.format("POLL: DMA active = $%02X at frame %d", dma, frame_count))
        end
        if hdma ~= 0 then
            emu.log(string.format("POLL: HDMA active = $%02X at frame %d", hdma, frame_count))
        end
    end,
    emu.eventType.startFrame  -- Check at start of frame too
)

emu.log("=== MONITOR ACTIVE ===")
emu.log(string.format("Registered %d callbacks", #callbacks + 2))
emu.log("Now PLAY THE GAME and watch for DMA activity!")
emu.log("Enter doors, collect items, change screens...")