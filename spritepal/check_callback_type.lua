-- Quick check for emu.callbackType enum values
emu.log("=== Checking emu.callbackType ===")
if emu.callbackType then
    for k, v in pairs(emu.callbackType) do
        emu.log("emu.callbackType." .. k .. " = " .. v)
    end
else
    emu.log("emu.callbackType not found")
end