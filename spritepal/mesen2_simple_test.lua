-- Mesen 2 Simple API Test
-- Tests the most likely API formats

emu.log("=== Mesen 2 Simple API Test ===")

-- Test callback
local function test_callback(address, value)
    emu.log(string.format("Callback: $%04X = $%02X", address, value))
end

-- Test frame callback
local frame_count = 0
local function frame_callback()
    frame_count = frame_count + 1
    if frame_count % 60 == 0 then
        emu.log("Frame: " .. frame_count)
    end
end

-- Try most common formats
emu.log("\nTrying common API formats...")

-- Format 1: Integer constants (many emulators use this)
local success, callback1 = pcall(function()
    -- 2 might be write, 1 might be read, 0 might be exec
    return emu.addMemoryCallback(test_callback, 2, 0x420B, 0x420B)
end)
if success then
    emu.log("Format 1 worked: Integer constant (2)")
else
    emu.log("Format 1 failed: " .. tostring(callback1))
end

-- Format 2: String literals (FCEUX style)
success, callback2 = pcall(function()
    return emu.addMemoryCallback(test_callback, "write", 0x420B, 0x420B)
end)
if success then
    emu.log("Format 2 worked: String 'write'")
else
    emu.log("Format 2 failed: " .. tostring(callback2))
end

-- Format 3: No type parameter (address range only)
success, callback3 = pcall(function()
    -- Maybe type is determined by callback or is optional
    return emu.addMemoryCallback(test_callback, 0x420B, 0x420B)
end)
if success then
    emu.log("Format 3 worked: No type parameter")
else
    emu.log("Format 3 failed: " .. tostring(callback3))
end

-- Format 4: Different parameter order (callback last)
success, callback4 = pcall(function()
    return emu.addMemoryCallback(0x420B, 0x420B, 2, test_callback)
end)
if success then
    emu.log("Format 4 worked: Callback last")
else
    emu.log("Format 4 failed")
end

-- Test memory read
emu.log("\nTesting memory read...")

-- Try reading with no type (defaults to CPU)
success, value1 = pcall(function()
    return emu.read(0x420B)
end)
if success then
    emu.log(string.format("Read with no type: $%02X", value1 or 0))
end

-- Try reading with integer type
success, value2 = pcall(function()
    return emu.read(0x420B, 0)  -- 0 might be CPU
end)
if success then
    emu.log(string.format("Read with type 0: $%02X", value2 or 0))
end

-- Try reading with string type
success, value3 = pcall(function()
    return emu.read(0x420B, "cpu")
end)
if success then
    emu.log(string.format("Read with type 'cpu': $%02X", value3 or 0))
end

-- Test event callback
emu.log("\nTesting event callback...")

-- Try common event formats
local event_formats = {
    {1, "Integer 1"},
    {0, "Integer 0"},
    {"frame", "String 'frame'"},
    {"endFrame", "String 'endFrame'"},
    {"frameEnd", "String 'frameEnd'"}
}

for _, format in ipairs(event_formats) do
    success, event_cb = pcall(function()
        return emu.addEventCallback(frame_callback, format[1])
    end)
    if success then
        emu.log("Event format worked: " .. format[2])
        break
    end
end

emu.log("\n=== Test Complete ===")
emu.log("If you see callbacks triggering above, that format works!")