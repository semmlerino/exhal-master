-- Advanced Sprite Palette Mapper for Mesen
-- Tracks all sprite-to-palette mappings across gameplay
-- Exports comprehensive mapping data for sprite extraction tools

-- Configuration
local CONFIG = {
    -- Tracking settings
    enabled = true,
    showOverlay = true,
    overlayDetail = "full",  -- "minimal", "full", "debug"
    
    -- Dump settings
    autoDumpInterval = 0,    -- Set to 0 to disable auto dumps
    dumpOnSceneChange = true,
    dumpOnPaletteChange = true,
    
    -- Controls
    manualDumpKey = "D",
    toggleOverlayKey = "O",
    exportMappingKey = "E",
    clearDataKey = "C",
    
    -- Detection thresholds
    sceneChangeThreshold = 20,  -- Number of new sprites to consider scene change
    minConfidence = 3,         -- Minimum times a mapping must be seen
}

-- Global state
local state = {
    frameCount = 0,
    lastDumpFrame = 0,
    tilePaletteMap = {},       -- tile -> palette -> count
    tileConfidence = {},       -- tile -> palette (most confident)
    scenePalettes = {},        -- Track palettes per "scene"
    currentScene = 1,
    lastOAMHash = 0,
    totalMappings = 0,
    confidentMappings = 0,
}

-- Get script data folder
local dataFolder = emu.getScriptDataFolder()

-- Helper: Calculate simple hash of OAM data for change detection
function hashOAM(oamData)
    local hash = 0
    for i, sprite in ipairs(oamData) do
        if i <= 32 then  -- Only hash first 32 sprites for performance
            hash = hash + sprite.tile * 1000 + sprite.palette * 100 + sprite.x + sprite.y
        end
    end
    return hash
end

-- Read and parse OAM data
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
            index = i,
            x = x_low + (x_high * 256),
            y = y,
            tile = tile_lo + ((attr & 0x01) * 256),
            palette = (attr >> 1) & 0x07,
            priority = (attr >> 4) & 0x03,
            xflip = (attr & 0x40) ~= 0,
            yflip = (attr & 0x80) ~= 0,
            size = size_bit == 1 and "large" or "small"
        }
        
        -- Only include visible sprites
        if sprite.y > 0 and sprite.y < 224 then
            table.insert(sprites, sprite)
        end
    end
    
    return sprites
end

-- Update tile-to-palette mappings
function updateMappings(oamData)
    local newMappings = 0
    local activePalettes = {}
    
    for _, sprite in ipairs(oamData) do
        activePalettes[sprite.palette] = true
        
        -- Initialize tile entry if needed
        if not state.tilePaletteMap[sprite.tile] then
            state.tilePaletteMap[sprite.tile] = {}
        end
        
        -- Update count for this tile-palette combination
        if not state.tilePaletteMap[sprite.tile][sprite.palette] then
            state.tilePaletteMap[sprite.tile][sprite.palette] = 0
            newMappings = newMappings + 1
        end
        state.tilePaletteMap[sprite.tile][sprite.palette] = 
            state.tilePaletteMap[sprite.tile][sprite.palette] + 1
        
        -- Handle large sprites (16x16)
        if sprite.size == "large" then
            local extraTiles = {sprite.tile + 1, sprite.tile + 16, sprite.tile + 17}
            for _, tile in ipairs(extraTiles) do
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
    
    -- Update confidence levels
    updateConfidence()
    
    -- Track scene palettes
    if not state.scenePalettes[state.currentScene] then
        state.scenePalettes[state.currentScene] = {}
    end
    for pal, _ in pairs(activePalettes) do
        state.scenePalettes[state.currentScene][pal] = true
    end
    
    state.totalMappings = state.totalMappings + newMappings
    
    return newMappings, activePalettes
end

-- Update confidence levels for tile-palette mappings
function updateConfidence()
    state.confidentMappings = 0
    
    for tile, palettes in pairs(state.tilePaletteMap) do
        local bestPalette = -1
        local bestCount = 0
        
        for palette, count in pairs(palettes) do
            if count > bestCount then
                bestCount = count
                bestPalette = palette
            end
        end
        
        if bestCount >= CONFIG.minConfidence then
            state.tileConfidence[tile] = bestPalette
            state.confidentMappings = state.confidentMappings + 1
        end
    end
end

-- Dump memory data
function dumpMemory(reason)
    local timestamp = os.date("%Y%m%d_%H%M%S")
    local prefix = reason .. "_" .. timestamp
    local basePath = dataFolder .. "/" .. prefix
    
    -- Create dumps
    local files = {
        {name = "_VRAM.dmp", memType = emu.memType.snesVideoRam, start = 0xC000, size = 0x4000},
        {name = "_CGRAM.dmp", memType = emu.memType.snesCgRam, start = 0, size = 512},
        {name = "_OAM.dmp", memType = emu.memType.snesSpriteRam, start = 0, size = 544}
    }
    
    for _, fileInfo in ipairs(files) do
        local file = io.open(basePath .. fileInfo.name, "wb")
        if file then
            for i = 0, fileInfo.size - 1 do
                file:write(string.char(emu.read(fileInfo.start + i, fileInfo.memType)))
            end
            file:close()
        end
    end
    
    -- Save current mappings
    saveMappingData(basePath .. "_mappings.json")
    
    emu.log("Dumped: " .. prefix)
    state.lastDumpFrame = state.frameCount
end

-- Save mapping data in JSON format
function saveMappingData(filename)
    local file = io.open(filename, "w")
    if not file then return end
    
    file:write("{\n")
    file:write('  "metadata": {\n')
    file:write('    "frame": ' .. state.frameCount .. ',\n')
    file:write('    "totalMappings": ' .. state.totalMappings .. ',\n')
    file:write('    "confidentMappings": ' .. state.confidentMappings .. ',\n')
    file:write('    "currentScene": ' .. state.currentScene .. '\n')
    file:write('  },\n')
    
    -- Write confident mappings
    file:write('  "tilePaletteMappings": {\n')
    local first = true
    for tile, palette in pairs(state.tileConfidence) do
        if not first then file:write(',\n') end
        file:write('    "' .. tile .. '": ' .. palette)
        first = false
    end
    file:write('\n  },\n')
    
    -- Write detailed counts
    file:write('  "detailedCounts": {\n')
    first = true
    for tile, palettes in pairs(state.tilePaletteMap) do
        if not first then file:write(',\n') end
        file:write('    "' .. tile .. '": {')
        local firstPal = true
        for palette, count in pairs(palettes) do
            if not firstPal then file:write(', ') end
            file:write('"' .. palette .. '": ' .. count)
            firstPal = false
        end
        file:write('}')
        first = false
    end
    file:write('\n  }\n')
    
    file:write('}\n')
    file:close()
end

-- Export complete mapping database
function exportCompleteMapping()
    local filename = dataFolder .. "/complete_palette_mapping_" .. os.date("%Y%m%d_%H%M%S") .. ".txt"
    local file = io.open(filename, "w")
    if not file then return end
    
    file:write("Kirby Super Star - Complete Sprite Palette Mapping\n")
    file:write("=" .. string.rep("=", 50) .. "\n\n")
    file:write("Generated after " .. state.frameCount .. " frames\n")
    file:write("Total unique mappings: " .. state.totalMappings .. "\n")
    file:write("Confident mappings: " .. state.confidentMappings .. "\n\n")
    
    -- Scene analysis
    file:write("Scene Palette Usage:\n")
    for scene, palettes in pairs(state.scenePalettes) do
        file:write("  Scene " .. scene .. ": ")
        for pal, _ in pairs(palettes) do
            file:write(pal .. " ")
        end
        file:write("\n")
    end
    
    file:write("\nConfident Tile-to-Palette Mappings:\n")
    file:write("(Tile -> Palette [confidence])\n")
    file:write("-" .. string.rep("-", 30) .. "\n")
    
    -- Sort tiles for readability
    local sortedTiles = {}
    for tile, _ in pairs(state.tileConfidence) do
        table.insert(sortedTiles, tile)
    end
    table.sort(sortedTiles)
    
    for _, tile in ipairs(sortedTiles) do
        local palette = state.tileConfidence[tile]
        local count = state.tilePaletteMap[tile][palette]
        file:write(string.format("Tile %03d -> Palette %d [%d times]\n", tile, palette, count))
    end
    
    file:close()
    emu.log("Exported complete mapping to: " .. filename)
end

-- Draw overlay
function drawOverlay()
    if not CONFIG.showOverlay then return end
    
    local y = 5
    
    if CONFIG.overlayDetail ~= "minimal" then
        emu.drawString(5, y, "Palette Tracker", 0xFFFFFF, 0x7F000000)
        y = y + 10
    end
    
    -- Basic stats
    emu.drawString(5, y, "Mapped: " .. state.confidentMappings .. "/" .. state.totalMappings, 0xFFFFFF, 0x7F000000)
    y = y + 10
    
    if CONFIG.overlayDetail == "full" or CONFIG.overlayDetail == "debug" then
        emu.drawString(5, y, "Scene: " .. state.currentScene, 0xFFFFFF, 0x7F000000)
        y = y + 10
    end
    
    -- Controls reminder
    if CONFIG.overlayDetail ~= "minimal" then
        emu.drawString(5, y, CONFIG.manualDumpKey .. ":Dump " .. CONFIG.exportMappingKey .. ":Export", 0xFFFF00, 0x7F000000)
        y = y + 10
    end
    
    -- Debug info
    if CONFIG.overlayDetail == "debug" then
        emu.drawString(5, y, "Frame: " .. state.frameCount, 0xFFFFFF, 0x7F000000)
        y = y + 10
        
        -- Show recent mappings
        local recentY = y
        local count = 0
        for tile, palettes in pairs(state.tilePaletteMap) do
            if count >= 5 then break end
            for pal, cnt in pairs(palettes) do
                if cnt == 1 then  -- New mapping
                    emu.drawString(5, recentY, "NEW: T" .. tile .. "->P" .. pal, 0x00FF00, 0x7F000000)
                    recentY = recentY + 10
                    count = count + 1
                    break
                end
            end
        end
    end
end

-- Frame callback
function onFrame()
    if not CONFIG.enabled then return end
    
    state.frameCount = state.frameCount + 1
    
    -- Read current OAM state
    local oamData = readOAM()
    local oamHash = hashOAM(oamData)
    
    -- Update mappings
    local newMappings, activePalettes = updateMappings(oamData)
    
    -- Detect scene changes
    if CONFIG.dumpOnSceneChange and newMappings > CONFIG.sceneChangeThreshold then
        state.currentScene = state.currentScene + 1
        dumpMemory("scene" .. state.currentScene)
    end
    
    -- Detect palette changes
    if CONFIG.dumpOnPaletteChange and math.abs(oamHash - state.lastOAMHash) > 1000 then
        local paletteCount = 0
        for _ in pairs(activePalettes) do paletteCount = paletteCount + 1 end
        if paletteCount > 2 then  -- Significant palette usage
            dumpMemory("palette_change")
        end
    end
    
    state.lastOAMHash = oamHash
    
    -- Auto dump
    if CONFIG.autoDumpInterval > 0 and 
       state.frameCount - state.lastDumpFrame >= CONFIG.autoDumpInterval then
        dumpMemory("auto")
    end
    
    -- Draw overlay
    drawOverlay()
end

-- Input handler
function onInput()
    local keys = emu.getMouseState()
    
    if keys[CONFIG.manualDumpKey] then
        dumpMemory("manual")
    elseif keys[CONFIG.toggleOverlayKey] then
        CONFIG.showOverlay = not CONFIG.showOverlay
    elseif keys[CONFIG.exportMappingKey] then
        exportCompleteMapping()
    elseif keys[CONFIG.clearDataKey] then
        state.tilePaletteMap = {}
        state.tileConfidence = {}
        state.totalMappings = 0
        state.confidentMappings = 0
        emu.log("Cleared mapping data")
    end
end

-- Initialize
emu.log("Advanced Palette Mapper initialized")
emu.log("Controls: " .. CONFIG.manualDumpKey .. "=Dump, " .. 
        CONFIG.exportMappingKey .. "=Export, " ..
        CONFIG.toggleOverlayKey .. "=Toggle overlay, " ..
        CONFIG.clearDataKey .. "=Clear data")

-- Register callbacks
emu.addEventCallback(onFrame, emu.eventType.endFrame)
emu.addEventCallback(onInput, emu.eventType.inputPolled)

-- Initial state
dumpMemory("startup")