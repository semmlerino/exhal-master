-- ===============================================================================
-- Simple Offset Finder for Mesen-S
-- Manual approach that doesn't rely on DMA tracking
-- ===============================================================================
-- Instructions:
-- 1. Play your game to the sprite you want
-- 2. Press F9 to capture current screen state
-- 3. Enter SNES address manually (shown by other debugging tools)
-- 4. Script calculates ROM offset for you
-- ===============================================================================

local state = {
    captures = {},
    message = "Press F9 to capture, then enter SNES address",
    message_timer = 0,
    last_f9 = false,
    last_s = false,
    input_mode = false,
    input_text = "",
    frame = 0,
    -- ROM mapping
    mapping = "lorom",
    has_header = false
}

-- ===============================================================================
-- Simple ROM offset calculation
-- ===============================================================================

function calculate_offset(snes_address_str)
    -- Parse SNES address like "$05:A200" or "05A200" or "0x05A200"
    local bank, addr
    
    -- Try different formats
    if snes_address_str:match("(%x%x):(%x%x%x%x)") then
        -- Format: XX:XXXX
        bank, addr = snes_address_str:match("(%x%x):(%x%x%x%x)")
        bank = tonumber(bank, 16)
        addr = tonumber(addr, 16)
    elseif snes_address_str:match("%$(%x%x):(%x%x%x%x)") then
        -- Format: $XX:XXXX
        bank, addr = snes_address_str:match("%$(%x%x):(%x%x%x%x)")
        bank = tonumber(bank, 16)
        addr = tonumber(addr, 16)
    elseif snes_address_str:match("(%x%x)(%x%x%x%x)") then
        -- Format: XXXXXX
        bank = tonumber(snes_address_str:sub(1, 2), 16)
        addr = tonumber(snes_address_str:sub(3, 6), 16)
    else
        return nil, "Invalid format. Use XX:XXXX or $XX:XXXX"
    end
    
    if not bank or not addr then
        return nil, "Parse error"
    end
    
    -- Calculate both LoROM and HiROM
    local lorom = ((bank & 0x7F) * 0x8000) + (addr & 0x7FFF)
    local hirom = ((bank & 0x3F) * 0x10000) + addr
    
    -- Add header if needed
    if state.has_header then
        lorom = lorom + 512
        hirom = hirom + 512
    end
    
    return {
        snes = string.format("$%02X:%04X", bank, addr),
        lorom = lorom,
        lorom_hex = string.format("0x%06X", lorom),
        hirom = hirom,
        hirom_hex = string.format("0x%06X", hirom)
    }
end

-- ===============================================================================
-- Known sprite locations for common games
-- ===============================================================================

local KNOWN_SPRITES = {
    ["Kirby Super Star"] = {
        {name = "Kirby Walk", snes = "$05:A200", note = "Basic Kirby sprites"},
        {name = "Kirby Abilities", snes = "$06:8000", note = "Power-up sprites"},
        {name = "Enemies", snes = "$07:0000", note = "Common enemies"}
    },
    ["Super Mario World"] = {
        {name = "Mario Small", snes = "$00:E000", note = "Small Mario"},
        {name = "Mario Big", snes = "$00:E800", note = "Super Mario"},
        {name = "Mario Cape", snes = "$01:8000", note = "Cape Mario"}
    }
}

-- ===============================================================================
-- Drawing
-- ===============================================================================

function draw_ui()
    local y = 10
    
    -- Main panel
    emu.drawRectangle(5, y, 350, 120, 0xCC000000, true)
    emu.drawRectangle(5, y, 350, 120, 0xFFFFFFFF, false)
    
    emu.drawString(10, y + 5, "Simple ROM Offset Calculator", 0xFFFFFFFF)
    emu.drawString(10, y + 20, state.message, 0xFFFFFF00)
    
    -- Controls
    emu.drawString(10, y + 40, "Controls:", 0xFFAAAAAA)
    emu.drawString(10, y + 55, "F9: Enter SNES address | S: Save list | F10: Toggle", 0xFFAAAAAA)
    
    -- ROM type
    emu.drawString(10, y + 75, "Mapping: " .. state.mapping .. (state.has_header and " (+header)" or ""), 0xFFAAAAAA)
    
    -- Capture count
    if #state.captures > 0 then
        emu.drawString(10, y + 95, "Captured: " .. #state.captures .. " offsets", 0xFF00FF00)
    end
    
    y = y + 125
    
    -- Input mode
    if state.input_mode then
        emu.drawRectangle(5, y, 350, 60, 0xCC000000, true)
        emu.drawRectangle(5, y, 350, 60, 0xFF00FF00, false)
        emu.drawString(10, y + 5, "Enter SNES Address (format: XX:XXXX or $XX:XXXX):", 0xFF00FF00)
        emu.drawString(10, y + 25, "> " .. state.input_text .. "_", 0xFFFFFFFF)
        emu.drawString(10, y + 45, "Press Enter to calculate, ESC to cancel", 0xFFAAAAAA)
        y = y + 65
    end
    
    -- Recent captures
    if #state.captures > 0 then
        local height = math.min(#state.captures * 30 + 25, 150)
        emu.drawRectangle(5, y, 350, height, 0xCC000000, true)
        emu.drawRectangle(5, y, 350, height, 0xFFFFFF00, false)
        
        emu.drawString(10, y + 5, "Recent Captures:", 0xFFFFFF00)
        
        for i = 1, math.min(#state.captures, 4) do
            local cap = state.captures[#state.captures - i + 1]
            local cy = y + 10 + (i * 30)
            emu.drawString(10, cy, cap.snes .. " -> " .. cap.lorom_hex .. " (LoROM)", 0xFFFFFFFF)
            emu.drawString(10, cy + 12, "           -> " .. cap.hirom_hex .. " (HiROM)", 0xFFAAAAAA)
        end
        
        y = y + height + 5
    end
    
    -- Quick reference
    emu.drawRectangle(5, y, 350, 85, 0xCC000000, true)
    emu.drawRectangle(5, y, 350, 85, 0xFFAAAAAA, false)
    emu.drawString(10, y + 5, "Quick Reference (common Kirby locations):", 0xFFAAAAAA)
    emu.drawString(10, y + 20, "$05:A200 - Kirby walking sprites", 0xFFFFFFFF)
    emu.drawString(10, y + 35, "$06:8000 - Ability sprites", 0xFFFFFFFF)
    emu.drawString(10, y + 50, "$07:0000 - Enemy sprites", 0xFFFFFFFF)
    emu.drawString(10, y + 65, "$08:0000 - Boss sprites", 0xFFFFFFFF)
    
    -- Update message timer
    if state.message_timer > 0 then
        state.message_timer = state.message_timer - 1
    end
end

-- ===============================================================================
-- Input handling  
-- ===============================================================================

function handle_input()
    -- Check for text input mode
    if state.input_mode then
        -- Simple text input (numbers and colon)
        for i = 0, 9 do
            if emu.isKeyPressed(tostring(i)) then
                state.input_text = state.input_text .. tostring(i)
            end
        end
        
        -- Hex letters A-F
        local hex_keys = {"A", "B", "C", "D", "E", "F"}
        for _, key in ipairs(hex_keys) do
            if emu.isKeyPressed(key) then
                state.input_text = state.input_text .. key
            end
        end
        
        -- Colon
        if emu.isKeyPressed("OemPeriod") then  -- Might be colon
            state.input_text = state.input_text .. ":"
        end
        
        -- Backspace
        if emu.isKeyPressed("Backspace") then
            if #state.input_text > 0 then
                state.input_text = state.input_text:sub(1, -2)
            end
        end
        
        -- Enter - calculate offset
        if emu.isKeyPressed("Return") or emu.isKeyPressed("Enter") then
            local result, err = calculate_offset(state.input_text)
            if result then
                table.insert(state.captures, result)
                state.message = "Captured: " .. result.snes .. " -> " .. result.lorom_hex
                state.message_timer = 120
                
                -- Log to console
                emu.log("=====================================")
                emu.log("SNES Address: " .. result.snes)
                emu.log("LoROM Offset: " .. result.lorom_hex .. " (" .. result.lorom .. ")")
                emu.log("HiROM Offset: " .. result.hirom_hex .. " (" .. result.hirom .. ")")
                emu.log("=====================================")
            else
                state.message = "Error: " .. (err or "Invalid address")
                state.message_timer = 120
            end
            
            state.input_mode = false
            state.input_text = ""
        end
        
        -- ESC - cancel
        if emu.isKeyPressed("Escape") then
            state.input_mode = false
            state.input_text = ""
            state.message = "Input cancelled"
            state.message_timer = 60
        end
        
        return  -- Don't process other keys in input mode
    end
    
    -- F9 - Start input mode
    local f9 = emu.isKeyPressed("F9")
    if f9 and not state.last_f9 then
        state.input_mode = true
        state.input_text = ""
        state.message = "Enter SNES address..."
        state.message_timer = 0
    end
    state.last_f9 = f9
    
    -- S - Save captures
    local s = emu.isKeyPressed("S")
    if s and not state.last_s then
        if #state.captures > 0 then
            emu.log("=====================================")
            emu.log("CAPTURED ROM OFFSETS")
            emu.log("=====================================")
            for i, cap in ipairs(state.captures) do
                emu.log(i .. ". " .. cap.snes)
                emu.log("   LoROM: " .. cap.lorom_hex)
                emu.log("   HiROM: " .. cap.hirom_hex)
                emu.log("")
            end
            emu.log("QUICK COPY (LoROM):")
            for _, cap in ipairs(state.captures) do
                emu.log(cap.lorom_hex)
            end
            emu.log("=====================================")
            
            state.message = "Saved " .. #state.captures .. " offsets to console"
            state.message_timer = 120
        else
            state.message = "No captures to save"
            state.message_timer = 60
        end
    end
    state.last_s = s
end

-- ===============================================================================
-- Initialization
-- ===============================================================================

-- Frame callback
emu.addEventCallback(function()
    state.frame = state.frame + 1
    handle_input()
end, "startFrame")

-- Draw callback
emu.addEventCallback(function()
    draw_ui()
end, "endFrame")

-- Initial log
emu.log("=====================================")
emu.log("Simple ROM Offset Calculator")
emu.log("=====================================")
emu.log("This tool converts SNES addresses to ROM offsets.")
emu.log("")
emu.log("How to use:")
emu.log("1. Find sprite address using emulator debugger")
emu.log("2. Press F9 and enter the SNES address")
emu.log("3. Get both LoROM and HiROM offsets")
emu.log("4. Use the offset in SpritePal")
emu.log("")
emu.log("Common Kirby sprite locations:")
emu.log("$05:A200 - Walking Kirby")
emu.log("$06:8000 - Ability sprites")
emu.log("$07:0000 - Enemy sprites")
emu.log("=====================================")