-- Mesen 2 API Diagnostic Script
-- Discovers the actual API format through testing

emu.log("=== Mesen 2 API Diagnostic ===")
emu.log("Discovering actual API format...")

-- Function to safely test API calls
local function safe_test(name, func)
    local success, result = pcall(func)
    if success then
        emu.log("[SUCCESS] " .. name .. ": " .. tostring(result))
        return result
    else
        emu.log("[FAILED] " .. name .. ": " .. tostring(result))
        return nil
    end
end

-- 1. Enumerate emu table contents
emu.log("\n--- Enumerating emu namespace ---")
for k, v in pairs(emu) do
    emu.log("emu." .. k .. " = " .. type(v))
end

-- 2. Check for global constants
emu.log("\n--- Checking global constants ---")
local globals_to_check = {
    "CPU_WRITE", "CPU_READ", "PPU_WRITE", "PPU_READ",
    "MEMORY_CPU", "MEMORY_PPU", "MEMORY_OAM",
    "EVENT_FRAME", "EVENT_END_FRAME", "EVENT_START_FRAME"
}
for _, name in ipairs(globals_to_check) do
    if _G[name] then
        emu.log("Found global: " .. name .. " = " .. tostring(_G[name]))
    end
end

-- 3. Test memory callback registration with different formats
emu.log("\n--- Testing addMemoryCallback formats ---")

local test_callback = function(addr, val)
    emu.log("Callback triggered!")
end

-- Try with strings
safe_test("String 'write'", function()
    return emu.addMemoryCallback(test_callback, "write", 0x420B, 0x420B)
end)

safe_test("String 'cpuWrite'", function()
    return emu.addMemoryCallback(test_callback, "cpuWrite", 0x420B, 0x420B)
end)

safe_test("String 'cpu-write'", function()
    return emu.addMemoryCallback(test_callback, "cpu-write", 0x420B, 0x420B)
end)

-- Try with numbers
safe_test("Number 0", function()
    return emu.addMemoryCallback(test_callback, 0, 0x420B, 0x420B)
end)

safe_test("Number 1", function()
    return emu.addMemoryCallback(test_callback, 1, 0x420B, 0x420B)
end)

safe_test("Number 2", function()
    return emu.addMemoryCallback(test_callback, 2, 0x420B, 0x420B)
end)

-- Try without type parameter (maybe it's optional?)
safe_test("No type param", function()
    return emu.addMemoryCallback(test_callback, 0x420B, 0x420B)
end)

-- Try different parameter orders
safe_test("Reversed params", function()
    return emu.addMemoryCallback(0x420B, 0x420B, test_callback)
end)

-- 4. Test memory read formats
emu.log("\n--- Testing emu.read formats ---")

safe_test("Read with string 'cpu'", function()
    return emu.read(0x420B, "cpu")
end)

safe_test("Read with string 'CPU'", function()
    return emu.read(0x420B, "CPU")
end)

safe_test("Read with number 0", function()
    return emu.read(0x420B, 0)
end)

safe_test("Read with number 1", function()
    return emu.read(0x420B, 1)
end)

safe_test("Read without type", function()
    return emu.read(0x420B)
end)

-- 5. Test event callback formats
emu.log("\n--- Testing addEventCallback formats ---")

local frame_callback = function()
    -- Frame callback
end

safe_test("Event string 'frame'", function()
    return emu.addEventCallback(frame_callback, "frame")
end)

safe_test("Event string 'endFrame'", function()
    return emu.addEventCallback(frame_callback, "endFrame")
end)

safe_test("Event string 'end-frame'", function()
    return emu.addEventCallback(frame_callback, "end-frame")
end)

safe_test("Event number 0", function()
    return emu.addEventCallback(frame_callback, 0)
end)

safe_test("Event number 1", function()
    return emu.addEventCallback(frame_callback, 1)
end)

-- 6. Check if enums exist in sub-tables
emu.log("\n--- Checking for enum sub-tables ---")
local enum_tables = {"memType", "memCallbackType", "eventType", "CallbackType", "EventType", "MemoryType"}
for _, name in ipairs(enum_tables) do
    if emu[name] then
        emu.log("Found emu." .. name .. ":")
        for k, v in pairs(emu[name]) do
            emu.log("  ." .. k .. " = " .. tostring(v))
        end
    end
end

-- 7. Try to find working format by looking at function signatures
emu.log("\n--- Function signatures ---")
if emu.addMemoryCallback then
    emu.log("emu.addMemoryCallback exists")
    -- Try to get info about the function
    local info = debug.getinfo(emu.addMemoryCallback)
    if info then
        emu.log("  nparams: " .. tostring(info.nparams))
    end
end

emu.log("\n=== Diagnostic Complete ===")
emu.log("Check the log above to see which formats worked!")