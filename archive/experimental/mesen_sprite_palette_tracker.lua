-- Mesen Lua Script: Sprite Palette Tracker for Kirby Super Star
-- This script tracks sprite-to-palette mappings during gameplay
-- and can dump synchronized VRAM, CGRAM, and OAM data

-- Configuration
local TRACKING_ENABLED = true
local AUTO_DUMP_INTERVAL = 600  -- Dump every 10 seconds (60 fps * 10)
local MANUAL_DUMP_KEY = "D"     -- Press D to manually dump
local SHOW_OVERLAY = true       -- Show tracking info on screen

-- State tracking
local frameCounter = 0
local lastDumpFrame = 0
local tilePaletteMap = {}      -- Maps tile numbers to palette numbers
local activePalettes = {}      -- Tracks which palettes are in use
local uniqueMappings = 0       -- Count of unique tile-palette mappings
local scriptDataPath = emu.getScriptDataFolder()

-- Helper functions
function readOAM()
    -- OAM is 544 bytes (512 + 32 for high table)
    local oam = {}
    
    -- Read low table (4 bytes per sprite, 128 sprites)
    for i = 0, 127 do
        local base = i * 4
        local x_low = emu.read(base, emu.memType.snesSpriteRam)
        local y = emu.read(base + 1, emu.memType.snesSpriteRam)
        local tile_lo = emu.read(base + 2, emu.memType.snesSpriteRam)
        local attr = emu.read(base + 3, emu.memType.snesSpriteRam)
        
        -- Read high table bits (2 bits per sprite)
        local hi_offset = 0x200 + math.floor(i / 4)
        local hi_byte = emu.read(hi_offset, emu.memType.snesSpriteRam)
        local hi_shift = (i % 4) * 2
        local hi_bits = (hi_byte >> hi_shift) & 0x03
        
        local x_high = hi_bits & 0x01
        local size_bit = (hi_bits >> 1) & 0x01
        
        -- Parse sprite data
        local sprite = {
            x = x_low + (x_high * 256),
            y = y,
            tile = tile_lo + ((attr & 0x01) * 256),
            palette = (attr >> 1) & 0x07,
            priority = (attr >> 4) & 0x03,
            xflip = (attr & 0x40) ~= 0,
            yflip = (attr & 0x80) ~= 0,
            size = size_bit == 1 and "large" or "small"
        }
        
        -- Only track visible sprites
        if sprite.y < 224 then
            table.insert(oam, sprite)
        end
    end
    
    return oam
end

function updateTilePaletteMap()
    local oam = readOAM()
    local newMappings = 0
    
    -- Clear active palette tracking for this frame
    activePalettes = {}
    
    for _, sprite in ipairs(oam) do
        -- Track active palettes
        activePalettes[sprite.palette] = true
        
        -- Update tile-to-palette mapping
        if not tilePaletteMap[sprite.tile] then
            tilePaletteMap[sprite.tile] = {}
        end
        
        if not tilePaletteMap[sprite.tile][sprite.palette] then
            tilePaletteMap[sprite.tile][sprite.palette] = 0
            newMappings = newMappings + 1
        end
        
        tilePaletteMap[sprite.tile][sprite.palette] = tilePaletteMap[sprite.tile][sprite.palette] + 1
        
        -- For large sprites, map additional tiles
        if sprite.size == "large" then
            local extraTiles = {sprite.tile + 1, sprite.tile + 16, sprite.tile + 17}
            for _, extraTile in ipairs(extraTiles) do
                if not tilePaletteMap[extraTile] then
                    tilePaletteMap[extraTile] = {}
                end
                if not tilePaletteMap[extraTile][sprite.palette] then
                    tilePaletteMap[extraTile][sprite.palette] = 0
                    newMappings = newMappings + 1
                end
                tilePaletteMap[extraTile][sprite.palette] = tilePaletteMap[extraTile][sprite.palette] + 1
            end
        end
    end
    
    uniqueMappings = uniqueMappings + newMappings
    return newMappings
end

function dumpMemoryData(prefix)
    local timestamp = os.date("%Y%m%d_%H%M%S")
    if prefix then
        prefix = prefix .. "_" .. timestamp
    else
        prefix = "dump_" .. timestamp
    end
    
    -- Dump VRAM (64KB starting at sprite area 0xC000)
    local vramFile = scriptDataPath .. "/" .. prefix .. "_VRAM.dmp"
    local vram = io.open(vramFile, "wb")
    if vram then
        -- VRAM is 64KB total, sprite area starts at 0xC000
        for i = 0xC000, 0xFFFF do
            vram:write(string.char(emu.read(i, emu.memType.snesVideoRam)))
        end
        vram:close()
    end
    
    -- Dump CGRAM (512 bytes)
    local cgramFile = scriptDataPath .. "/" .. prefix .. "_CGRAM.dmp"
    local cgram = io.open(cgramFile, "wb")
    if cgram then
        for i = 0, 511 do
            cgram:write(string.char(emu.read(i, emu.memType.snesCgRam)))
        end
        cgram:close()
    end
    
    -- Dump OAM (544 bytes)
    local oamFile = scriptDataPath .. "/" .. prefix .. "_OAM.dmp"
    local oam = io.open(oamFile, "wb")
    if oam then
        for i = 0, 543 do
            oam:write(string.char(emu.read(i, emu.memType.snesSpriteRam)))
        end
        oam:close()
    end
    
    -- Save palette mapping data
    local mappingFile = scriptDataPath .. "/" .. prefix .. "_mapping.txt"
    local mapping = io.open(mappingFile, "w")
    if mapping then
        mapping:write("Sprite Palette Mapping Data\n")
        mapping:write("Generated: " .. timestamp .. "\n")
        mapping:write("Unique mappings found: " .. uniqueMappings .. "\n\n")
        
        -- Write active palettes
        mapping:write("Active palettes this frame: ")
        for pal, _ in pairs(activePalettes) do
            mapping:write(pal .. " ")
        end
        mapping:write("\n\n")
        
        -- Write tile mappings
        mapping:write("Tile-to-Palette Mappings:\n")
        for tile, palettes in pairs(tilePaletteMap) do
            local mostUsedPal = -1
            local maxCount = 0
            for pal, count in pairs(palettes) do
                if count > maxCount then
                    maxCount = count
                    mostUsedPal = pal
                end
            end
            mapping:write(string.format("Tile %03d: Palette %d (seen %d times)\n", 
                         tile, mostUsedPal, maxCount))
        end
        
        mapping:close()
    end
    
    emu.log("Dumped memory to: " .. prefix)
    return prefix
end

function drawOverlay()
    if not SHOW_OVERLAY then return end
    
    -- Count active palettes
    local activePalCount = 0
    for _ in pairs(activePalettes) do
        activePalCount = activePalCount + 1
    end
    
    -- Count mapped tiles
    local mappedTiles = 0
    for _ in pairs(tilePaletteMap) do
        mappedTiles = mappedTiles + 1
    end
    
    -- Draw info
    emu.drawString(5, 5, "Sprite Tracker Active", 0xFFFFFF, 0x7F000000)
    emu.drawString(5, 15, "Mapped tiles: " .. mappedTiles, 0xFFFFFF, 0x7F000000)
    emu.drawString(5, 25, "Active pals: " .. activePalCount, 0xFFFFFF, 0x7F000000)
    emu.drawString(5, 35, "Press " .. MANUAL_DUMP_KEY .. " to dump", 0xFFFFFF, 0x7F000000)
    
    -- Show active palettes with color preview
    local x = 5
    for pal, _ in pairs(activePalettes) do
        -- Read first few colors from the palette
        local baseAddr = 128 + (pal * 16)  -- OBJ palettes start at CGRAM 128
        local color1 = emu.read16(baseAddr * 2 + 2, emu.memType.snesCgRam)  -- Skip transparent
        
        -- Convert BGR555 to RGB
        local r = (color1 & 0x1F) * 8
        local g = ((color1 >> 5) & 0x1F) * 8
        local b = ((color1 >> 10) & 0x1F) * 8
        local displayColor = (r << 16) | (g << 8) | b
        
        emu.drawRectangle(x, 45, 15, 15, displayColor, true)
        emu.drawString(x + 2, 47, tostring(pal), 0xFFFFFF, 0x7F000000)
        x = x + 20
    end
end

-- Frame callback
function onFrame()
    if not TRACKING_ENABLED then return end
    
    frameCounter = frameCounter + 1
    
    -- Update mappings
    local newMappings = updateTilePaletteMap()
    
    -- Auto dump at intervals
    if AUTO_DUMP_INTERVAL > 0 and frameCounter - lastDumpFrame >= AUTO_DUMP_INTERVAL then
        dumpMemoryData("auto")
        lastDumpFrame = frameCounter
    end
    
    -- Draw overlay
    drawOverlay()
end

-- Input callback for manual dumps
function onInput()
    local input = emu.getInput(0)
    
    -- Check for manual dump key
    if emu.getMouseState()[MANUAL_DUMP_KEY] then
        dumpMemoryData("manual")
        emu.log("Manual dump completed")
    end
end

-- Initialize
emu.log("Sprite Palette Tracker initialized")
emu.log("Script data folder: " .. scriptDataPath)
emu.log("Press " .. MANUAL_DUMP_KEY .. " to manually dump memory")
emu.log("Auto-dump every " .. (AUTO_DUMP_INTERVAL / 60) .. " seconds")

-- Register callbacks
emu.addEventCallback(onFrame, emu.eventType.endFrame)
emu.addEventCallback(onInput, emu.eventType.inputPolled)

-- Initial dump
dumpMemoryData("initial")