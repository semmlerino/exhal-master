-- Mesen Sprite Palette Tracker with Fixed Hotkeys
-- Tracks sprite-to-palette mappings during Kirby Super Star gameplay

-- Configuration
local CONFIG = {
    -- Tracking settings
    enabled = true,
    showOverlay = true,
    
    -- Dump settings (frames)
    autoDumpInterval = 0,     -- 0 = disabled, 600 = 10 seconds
    dumpOnSceneChange = true,
    
    -- Hotkeys
    dumpKey = "D",           -- Manual dump
    toggleKey = "O",         -- Toggle overlay
    exportKey = "E",         -- Export mappings
    clearKey = "C",          -- Clear data
    
    -- Scene detection
    sceneChangeThreshold = 20,
    minConfidence = 3,
}

-- State
local state = {
    frameCount = 0,
    lastDumpFrame = 0,
    tilePaletteMap = {},     -- tile -> palette -> count
    tileConfidence = {},     -- tile -> palette (most confident)
    activePalettes = {},     -- current frame's palettes
    totalMappings = 0,
    confidentMappings = 0,
    
    -- Key tracking
    keysPressed = {},
    keysPrevious = {},
}

local dataFolder = emu.getScriptDataFolder()

-- Helper: Check if key was just pressed (not held)
function wasKeyPressed(key)
    return state.keysPressed[key] and not state.keysPrevious[key]
end

-- Read OAM data
function readOAM()
    local sprites = {}
    
    for i = 0, 127 do
        local base = i * 4
        local x_low = emu.read(base, emu.memType.snesSpriteRam)
        local y = emu.read(base + 1, emu.memType.snesSpriteRam)
        local tile_lo = emu.read(base + 2, emu.memType.snesSpriteRam)
        local attr = emu.read(base + 3, emu.memType.snesSpriteRam)
        
        -- High table
        local hi_offset = 0x200 + math.floor(i / 4)
        local hi_byte = emu.read(hi_offset, emu.memType.snesSpriteRam)
        local hi_shift = (i % 4) * 2
        local hi_bits = (hi_byte >> hi_shift) & 0x03
        
        local x_high = hi_bits & 0x01
        local size_bit = (hi_bits >> 1) & 0x01
        
        local sprite = {
            x = x_low + (x_high * 256),
            y = y,
            tile = tile_lo + ((attr & 0x01) * 256),
            palette = (attr >> 1) & 0x07,
            size = size_bit == 1 and "large" or "small"
        }
        
        -- Only visible sprites
        if sprite.y > 0 and sprite.y < 224 then
            table.insert(sprites, sprite)
        end
    end
    
    return sprites
end

-- Update mappings
function updateMappings()
    local oamData = readOAM()
    local newMappings = 0
    state.activePalettes = {}
    
    for _, sprite in ipairs(oamData) do
        state.activePalettes[sprite.palette] = true
        
        -- Track tile-palette mapping
        if not state.tilePaletteMap[sprite.tile] then
            state.tilePaletteMap[sprite.tile] = {}
        end
        
        if not state.tilePaletteMap[sprite.tile][sprite.palette] then
            state.tilePaletteMap[sprite.tile][sprite.palette] = 0
            newMappings = newMappings + 1
        end
        
        state.tilePaletteMap[sprite.tile][sprite.palette] = 
            state.tilePaletteMap[sprite.tile][sprite.palette] + 1
        
        -- Large sprites
        if sprite.size == "large" then
            local tiles = {sprite.tile + 1, sprite.tile + 16, sprite.tile + 17}
            for _, tile in ipairs(tiles) do
                if not state.tilePaletteMap[tile] then
                    state.tilePaletteMap[tile] = {}
                end
                if not state.tilePaletteMap[tile][sprite.palette] then
                    state.tilePaletteMap[tile][sprite.palette] = 0
                    newMappings = newMappings + 1
                end
                state.tilePaletteMap[tile][sprite.palette] = 
                    state.tilePaletteMap[tile][sprite.palette] + 1
            end
        end
    end
    
    state.totalMappings = state.totalMappings + newMappings
    
    -- Update confidence
    updateConfidence()
    
    return newMappings
end

-- Update confidence levels
function updateConfidence()
    state.confidentMappings = 0
    
    for tile, palettes in pairs(state.tilePaletteMap) do
        local bestPal = -1
        local bestCount = 0
        
        for pal, count in pairs(palettes) do
            if count > bestCount then
                bestCount = count
                bestPal = pal
            end
        end
        
        if bestCount >= CONFIG.minConfidence then
            state.tileConfidence[tile] = bestPal
            state.confidentMappings = state.confidentMappings + 1
        end
    end
end

-- Dump memory
function dumpMemory(reason)
    local timestamp = os.date("%Y%m%d_%H%M%S")
    local prefix = reason .. "_" .. timestamp
    
    -- VRAM dump (sprite area)
    local vramFile = dataFolder .. "/" .. prefix .. "_VRAM.dmp"
    local vram = io.open(vramFile, "wb")
    if vram then
        for i = 0xC000, 0xFFFF do
            vram:write(string.char(emu.read(i, emu.memType.snesVideoRam)))
        end
        vram:close()
    end
    
    -- CGRAM dump
    local cgramFile = dataFolder .. "/" .. prefix .. "_CGRAM.dmp"
    local cgram = io.open(cgramFile, "wb")
    if cgram then
        for i = 0, 511 do
            cgram:write(string.char(emu.read(i, emu.memType.snesCgRam)))
        end
        cgram:close()
    end
    
    -- OAM dump
    local oamFile = dataFolder .. "/" .. prefix .. "_OAM.dmp"
    local oam = io.open(oamFile, "wb")
    if oam then
        for i = 0, 543 do
            oam:write(string.char(emu.read(i, emu.memType.snesSpriteRam)))
        end
        oam:close()
    end
    
    -- Export mappings
    exportMappingData(dataFolder .. "/" .. prefix .. "_mappings.json")
    
    emu.displayMessage("Dump", "Saved: " .. prefix)
    emu.log("Dumped: " .. prefix)
    state.lastDumpFrame = state.frameCount
end

-- Export mapping data
function exportMappingData(filename)
    local file = io.open(filename, "w")
    if not file then return end
    
    file:write("{\n")
    file:write('  "frameCount": ' .. state.frameCount .. ',\n')
    file:write('  "totalMappings": ' .. state.totalMappings .. ',\n')
    file:write('  "confidentMappings": ' .. state.confidentMappings .. ',\n')
    
    -- Confident mappings
    file:write('  "tileMappings": {\n')
    local first = true
    for tile, pal in pairs(state.tileConfidence) do
        if not first then file:write(',\n') end
        file:write('    "' .. tile .. '": ' .. pal)
        first = false
    end
    file:write('\n  },\n')
    
    -- Detailed counts
    file:write('  "detailedCounts": {\n')
    first = true
    for tile, palettes in pairs(state.tilePaletteMap) do
        if not first then file:write(',\n') end
        file:write('    "' .. tile .. '": {')
        local firstPal = true
        for pal, count in pairs(palettes) do
            if not firstPal then file:write(', ') end
            file:write('"' .. pal .. '": ' .. count)
            firstPal = false
        end
        file:write('}')
        first = false
    end
    file:write('\n  }\n')
    
    file:write('}\n')
    file:close()
end

-- Export full report
function exportFullReport()
    local filename = dataFolder .. "/palette_report_" .. os.date("%Y%m%d_%H%M%S") .. ".txt"
    local file = io.open(filename, "w")
    if not file then return end
    
    file:write("Kirby Super Star - Sprite Palette Mapping Report\n")
    file:write("=" .. string.rep("=", 50) .. "\n\n")
    file:write("Frames analyzed: " .. state.frameCount .. "\n")
    file:write("Total mappings: " .. state.totalMappings .. "\n")
    file:write("Confident mappings: " .. state.confidentMappings .. "\n\n")
    
    file:write("Confident Tile->Palette Mappings:\n")
    file:write("-" .. string.rep("-", 30) .. "\n")
    
    -- Sort tiles
    local tiles = {}
    for tile in pairs(state.tileConfidence) do
        table.insert(tiles, tile)
    end
    table.sort(tiles)
    
    for _, tile in ipairs(tiles) do
        local pal = state.tileConfidence[tile]
        local count = state.tilePaletteMap[tile][pal]
        file:write(string.format("Tile %03d -> Palette %d [seen %d times]\n", 
                                tile, pal, count))
    end
    
    file:close()
    emu.displayMessage("Export", "Report saved")
    emu.log("Exported report to: " .. filename)
end

-- Draw overlay
function drawOverlay()
    if not CONFIG.showOverlay then return end
    
    local y = 5
    
    -- Title
    emu.drawString(5, y, "Palette Tracker", 0xFFFFFF, 0x7F000000)
    y = y + 10
    
    -- Stats
    emu.drawString(5, y, "Tiles: " .. state.confidentMappings .. "/" .. state.totalMappings, 
                  0xFFFFFF, 0x7F000000)
    y = y + 10
    
    -- Active palettes
    local palStr = "Palettes: "
    for pal in pairs(state.activePalettes) do
        palStr = palStr .. pal .. " "
    end
    emu.drawString(5, y, palStr, 0xFFFFFF, 0x7F000000)
    y = y + 10
    
    -- Controls
    emu.drawString(5, y, "Keys: D=Dump E=Export O=Hide C=Clear", 0xFFFF00, 0x7F000000)
    y = y + 10
    
    -- Show palette colors
    local x = 5
    y = y + 5
    for pal in pairs(state.activePalettes) do
        -- Read color from palette
        local addr = (128 + pal * 16) * 2 + 2  -- Skip transparent
        local color = emu.read16(addr, emu.memType.snesCgRam)
        
        local r = (color & 0x1F) * 8
        local g = ((color >> 5) & 0x1F) * 8
        local b = ((color >> 10) & 0x1F) * 8
        local rgb = (r << 16) | (g << 8) | b
        
        emu.drawRectangle(x, y, 20, 15, rgb, true)
        emu.drawString(x + 6, y + 3, tostring(pal), 0xFFFFFF, 0x7F000000)
        x = x + 25
    end
end

-- Frame callback
function onFrame()
    if not CONFIG.enabled then return end
    
    state.frameCount = state.frameCount + 1
    
    -- Update key states
    state.keysPrevious = {}
    for k, v in pairs(state.keysPressed) do
        state.keysPrevious[k] = v
    end
    
    state.keysPressed[CONFIG.dumpKey] = emu.isKeyPressed(CONFIG.dumpKey)
    state.keysPressed[CONFIG.toggleKey] = emu.isKeyPressed(CONFIG.toggleKey)
    state.keysPressed[CONFIG.exportKey] = emu.isKeyPressed(CONFIG.exportKey)
    state.keysPressed[CONFIG.clearKey] = emu.isKeyPressed(CONFIG.clearKey)
    
    -- Handle key presses
    if wasKeyPressed(CONFIG.dumpKey) then
        dumpMemory("manual")
    elseif wasKeyPressed(CONFIG.toggleKey) then
        CONFIG.showOverlay = not CONFIG.showOverlay
        emu.displayMessage("Overlay", CONFIG.showOverlay and "ON" or "OFF")
    elseif wasKeyPressed(CONFIG.exportKey) then
        exportFullReport()
    elseif wasKeyPressed(CONFIG.clearKey) then
        state.tilePaletteMap = {}
        state.tileConfidence = {}
        state.totalMappings = 0
        state.confidentMappings = 0
        emu.displayMessage("Clear", "Data cleared")
    end
    
    -- Update mappings
    local newMappings = updateMappings()
    
    -- Scene change detection
    if CONFIG.dumpOnSceneChange and newMappings > CONFIG.sceneChangeThreshold then
        dumpMemory("scene")
    end
    
    -- Auto dump
    if CONFIG.autoDumpInterval > 0 and 
       state.frameCount - state.lastDumpFrame >= CONFIG.autoDumpInterval then
        dumpMemory("auto")
    end
    
    -- Draw overlay
    drawOverlay()
end

-- Initialize
emu.log("=== Sprite Palette Tracker Started ===")
emu.log("Data folder: " .. dataFolder)
emu.log("Hotkeys:")
emu.log("  " .. CONFIG.dumpKey .. " = Dump memory")
emu.log("  " .. CONFIG.exportKey .. " = Export report")
emu.log("  " .. CONFIG.toggleKey .. " = Toggle overlay")
emu.log("  " .. CONFIG.clearKey .. " = Clear data")

-- Register callback
emu.addEventCallback(onFrame, emu.eventType.endFrame)

-- Initial dump
dumpMemory("startup")