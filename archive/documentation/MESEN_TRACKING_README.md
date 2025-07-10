# Mesen Sprite Palette Tracking Scripts

These Lua scripts for Mesen allow you to automatically track and capture sprite-to-palette mappings while playing Kirby Super Star. This solves the problem of incomplete palette data by building a comprehensive mapping database during gameplay.

## Scripts Overview

### 1. `mesen_sprite_palette_tracker.lua` (Basic Version)
Simple tracker that captures memory dumps at regular intervals.

**Features:**
- Tracks sprite-to-palette mappings in real-time
- Auto-dumps memory at configurable intervals
- Shows overlay with current tracking stats
- Manual dump on keypress

**Usage:**
```lua
-- In Mesen: Tools -> Script Window -> Open Script
-- Load mesen_sprite_palette_tracker.lua
```

### 2. `mesen_palette_mapper_advanced.lua` (Advanced Version)
Comprehensive tracker with scene detection and confidence tracking.

**Features:**
- Intelligent scene change detection
- Confidence-based palette assignment
- Export complete mapping database
- Debug overlay with detailed information
- JSON export for analysis tools

**Controls:**
- `D` - Manual memory dump
- `E` - Export complete mapping database
- `O` - Toggle overlay display
- `C` - Clear collected data

### 3. `analyze_mesen_dumps.py` (Analysis Tool)
Python script to combine data from multiple gameplay sessions.

**Features:**
- Combines mappings from multiple dumps
- Calculates confidence levels
- Identifies palette usage patterns
- Exports final mapping database

**Usage:**
```bash
# Analyze all dumps in current directory
python3 analyze_mesen_dumps.py

# Analyze dumps in specific directory
python3 analyze_mesen_dumps.py /path/to/dumps/

# Specify output file
python3 analyze_mesen_dumps.py -o complete_mapping.json
```

## Workflow

### Step 1: Collect Data During Gameplay

1. Start Mesen with Kirby Super Star
2. Open Script Window: `Tools -> Script Window`
3. Load the advanced script: `File -> Open Script -> mesen_palette_mapper_advanced.lua`
4. Play through different areas of the game:
   - Visit various levels
   - Encounter different enemies
   - Use different power-ups
   - Access menus and cutscenes

The script will automatically:
- Track all sprite-to-palette mappings
- Dump memory when scene changes are detected
- Build confidence levels for mappings

### Step 2: Manual Dumps

Press `D` at key moments:
- When new enemies appear
- During boss fights
- In special rooms or areas
- When using different abilities

### Step 3: Export and Analyze

1. Press `E` to export the current mapping database
2. After playing multiple sessions, run the analysis script:
   ```bash
   python3 analyze_mesen_dumps.py
   ```

### Step 4: Use the Mapping Data

The generated `final_palette_mapping.json` contains:
- Complete tile-to-palette mappings
- Confidence levels for each mapping
- Palette usage statistics

Use this with the sprite extraction tools:
```python
# Load the mapping
with open('final_palette_mapping.json', 'r') as f:
    mapping_data = json.load(f)

# Get palette for a tile
tile_num = 42
if str(tile_num) in mapping_data['tile_mappings']:
    palette = mapping_data['tile_mappings'][str(tile_num)]['palette']
    confidence = mapping_data['tile_mappings'][str(tile_num)]['confidence']
```

## Configuration

Edit the CONFIG table in `mesen_palette_mapper_advanced.lua`:

```lua
local CONFIG = {
    -- Disable auto-dumps
    autoDumpInterval = 0,
    
    -- More sensitive scene detection
    sceneChangeThreshold = 10,
    
    -- Higher confidence requirement
    minConfidence = 5,
    
    -- Change key bindings
    manualDumpKey = "F1",
    exportMappingKey = "F2",
}
```

## Output Files

The scripts create several types of files:

1. **Memory Dumps** (`*_VRAM.dmp`, `*_CGRAM.dmp`, `*_OAM.dmp`)
   - Raw memory data from specific moments
   - Can be used with sprite extraction tools

2. **Mapping Files** (`*_mappings.json`)
   - Tile-to-palette mappings with counts
   - Metadata about the capture

3. **Export Files** (`complete_palette_mapping_*.txt`)
   - Human-readable mapping data
   - Scene analysis information

4. **Final Mapping** (`final_palette_mapping.json`)
   - Combined data from all sessions
   - Ready for use in sprite extraction

## Tips for Complete Coverage

1. **Play Systematically**: Visit each game area methodically
2. **Use All Abilities**: Each ability may have unique sprites
3. **Check Menus**: UI elements need palette mappings too
4. **Boss Fights**: Often have unique palettes
5. **Multiple Sessions**: Run several gameplay sessions for better coverage

## Troubleshooting

**Script not loading:**
- Ensure you're using Mesen (not Mesen-S)
- Check the script path has no special characters

**No dumps created:**
- Check the script data folder path in the log
- Ensure you have write permissions
- Try manual dump with 'D' key

**Missing sprites:**
- Play more areas of the game
- Check the overlay to see mapping progress
- Lower the confidence threshold in analysis

## Integration with Sprite Editor

Once you have comprehensive mappings:

```python
# In sprite_editor_core.py
def load_palette_mappings(mapping_file):
    """Load Mesen-generated palette mappings"""
    with open(mapping_file, 'r') as f:
        data = json.load(f)
    
    tile_to_palette = {}
    for tile_str, info in data['tile_mappings'].items():
        tile_to_palette[int(tile_str)] = info['palette']
    
    return tile_to_palette

# Use in extraction
mappings = load_palette_mappings('final_palette_mapping.json')
palette_num = mappings.get(tile_index, 0)  # Default to palette 0
```

This approach ensures accurate palette assignments for all sprites in the game!