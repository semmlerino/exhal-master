# Cave Area Palette Mapping Solution

## Summary

Using synchronized memory dumps from the Cave area (same paused moment), we've successfully determined the correct palette mappings for all sprites.

## Key Findings

### Active Palettes in Cave Area
- **OAM Palette 0**: Pink Kirby sprites
- **OAM Palette 4**: UI elements and numbers  
- **OAM Palette 6**: Cave enemy sprites

### Memory Layout
- **Kirby sprites**: Tiles 0-31 use Palette 0
- **UI/Numbers**: Tiles 32-63 use Palette 4
- **Cave Enemies**: Tiles 160-191 use Palette 6

### Color Characteristics
1. **Palette 0 (Kirby)**:
   - Main colors: Pink [224,56,248], Light pink [248,160,232]
   - Used for Pink Kirby's body and features

2. **Palette 4 (UI)**:
   - Main colors: White [248,248,248], Orange [248,152,0]
   - Used for HUD numbers and interface elements

3. **Palette 6 (Cave Enemies)**:
   - Main colors: White [248,248,248], Teal [128,224,232], Brown/Yellow tones
   - Used for cave-specific enemy sprites

## Important Technical Details

### OAM to CGRAM Mapping
- OAM palettes 0-7 map to CGRAM palettes 8-15
- OAM Palette N = CGRAM Palette (N + 8)

### Synchronization Importance
- Memory dumps must be from the exact same frame
- Different game areas use different palette combinations
- Not all 8 OBJ palettes are active in every scene

## Files Generated
- `cave_final_sheet_4x.png` - Complete sprite sheet with correct palettes
- `cave_detailed_showcase.png` - Individual character examples with palette info
- `cave_sprites_synchronized_*.png` - Various resolution outputs

## Lessons Learned
1. Always use synchronized dumps from the same exact moment
2. OAM data is crucial for determining which tiles use which palettes
3. Different game areas have different active palette sets
4. The palette offset (OAM +8 = CGRAM) is consistent across all SNES games

This solution can be applied to other game areas by:
1. Capturing synchronized VRAM, CGRAM, and OAM dumps
2. Analyzing OAM to determine active palettes and tile mappings
3. Applying the correct palettes based on actual sprite usage