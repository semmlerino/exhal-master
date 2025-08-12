-- Mesen 2 Minimal Working Example
-- Absolute minimum to test the API

emu.log("=== Mesen 2 Minimal Test ===")

-- List all functions in emu
emu.log("Available emu functions:")
for k, v in pairs(emu) do
    if type(v) == "function" then
        emu.log("  emu." .. k .. "()")
    end
end

-- Try the simplest possible callback
local function callback(...)
    local args = {...}
    emu.log("Callback fired with " .. #args .. " args")
    for i, v in ipairs(args) do
        emu.log("  Arg " .. i .. ": " .. tostring(v))
    end
end

-- Try different ways to register a callback
emu.log("\nTrying to register callbacks...")

-- Method 1: Just callback and addresses
local ok, result = pcall(emu.addMemoryCallback, callback, 0x420B, 0x420B)
emu.log("Method 1 (callback, start, end): " .. (ok and "SUCCESS" or "FAILED"))

-- Method 2: With integer type
ok, result = pcall(emu.addMemoryCallback, callback, 1, 0x420B, 0x420B)
emu.log("Method 2 (callback, 1, start, end): " .. (ok and "SUCCESS" or "FAILED"))

-- Method 3: With string type
ok, result = pcall(emu.addMemoryCallback, callback, "write", 0x420B, 0x420B)
emu.log("Method 3 (callback, 'write', start, end): " .. (ok and "SUCCESS" or "FAILED"))

-- Try reading memory
emu.log("\nTrying to read memory...")
ok, value = pcall(emu.read, 0x420B)
if ok then
    emu.log(string.format("emu.read(0x420B) = $%02X", value or 0))
else
    emu.log("emu.read(0x420B) failed")
end

emu.log("\n=== End of minimal test ===")