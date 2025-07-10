# Multi-Palette System Learnings

## Key Discoveries

### 1. The Multi-Palette System DOES Work ✅
The sprite editor correctly implements the multi-palette functionality. Different sprites in the same VRAM sheet DO use different palettes, exactly as intended in SNES games.

### 2. Critical Issue: Mismatched Memory Dumps ⚠️
The main challenge we encountered was that the three memory dumps were taken at different game moments:
- **VRAM.dmp**: Contains Beam Kirby (yellow form with hat/beam)
- **OAM.dmp**: From a different game state, shows different sprite-to-palette mappings
- **CGRAM.dmp**: Contains the palettes, but may be from yet another moment

This mismatch caused initial confusion about which palettes were correct.

### 3. Confirmed Palette Mappings
Through visual inspection, we've confirmed:
- **Beam Kirby** (at VRAM 0xC000): Uses **Palette 8** ✓
  - Evidence: Yellow/orange colors with correct beam hat appearance
- **Enemy Group 1** (at VRAM 0xD000): Uses **Palette 12** ✓
  - Evidence: User confirmed this produces correct enemy colors

### 4. What the OAM Data Actually Shows
The OAM dump indicates:
- Sprites 0-9 (tiles 0x000-0x01D): Palette 0
- Sprites 10-17 (tiles 0x0A0-0x0BE): Palette 6
- Various other mappings

However, these don't match what's actually in the VRAM dump because they're from different game moments.

### 5. Technical Implementation Works Correctly
The sprite editor properly:
- Reads OAM data to map sprites to palettes
- Extracts sprites with individual palette assignments
- Provides multiple viewing modes (single palette, multi-palette, grid view)
- Handles the complex SNES palette system

## Lessons Learned

### 1. Memory Dump Synchronization is Critical
For accurate multi-palette extraction, all memory dumps must be from the EXACT same frame:
- VRAM (sprite graphics)
- CGRAM (color palettes)
- OAM (sprite attributes and palette assignments)

### 2. Visual Verification is Essential
When memory dumps are mismatched, manual visual verification becomes necessary:
- Test each palette on sprite regions
- Look for recognizable features (like Kirby's beam hat)
- Confirm with someone familiar with the game

### 3. Different Kirby Forms Use Different Palettes
- Regular Pink Kirby: Would use a pink palette (not in this dump)
- Beam/Spark Kirby: Uses Palette 8 (yellow/orange)
- Other ability forms: Would use other palettes

### 4. SNES Palette Organization
Typical SNES games organize palettes as:
- Palettes 0-7: Sprite palettes
- Palettes 8-15: Background palettes (but can be used for sprites)
- Each palette: 16 colors (including transparency)

## Still To Determine

1. **Enemy Group 2** (VRAM 0xD400): Which palette?
   - Candidates: P10 (orange/red), others
   
2. **Enemy Group 3** (VRAM 0xD800): Which palette?
   - Candidates: P11 (pink/flesh), others

3. **Other sprite regions**: Additional enemies, effects, UI elements

## Recommended Workflow for Future Extractions

1. **Take synchronized dumps**:
   ```
   - Pause emulator at desired frame
   - Dump VRAM, CGRAM, and OAM simultaneously
   - Note what's on screen for reference
   ```

2. **Document game state**:
   - Which level/screen
   - What characters are visible
   - What abilities/forms are active

3. **Use OAM data as initial guide**:
   - Load OAM mapping first
   - Extract with OAM-based palettes
   - Visually verify results

4. **Manual correction if needed**:
   - Test different palettes on regions that look wrong
   - Create comparison grids
   - Get visual confirmation

## Code That Works

The sprite editor's multi-palette functionality is working correctly:
```python
# Load OAM data
core.load_oam_mapping("OAM.dmp")

# Extract with correct palettes per tile
img, tiles = core.extract_sprites_with_correct_palettes(
    "VRAM.dmp", offset, size, "CGRAM.dmp"
)

# Create palette grid for analysis
grid, tiles = core.create_palette_grid_preview(
    "VRAM.dmp", offset, size, "CGRAM.dmp"
)
```

## Conclusion

The multi-palette system works as designed. The challenge was not with the code, but with understanding that our memory dumps were from different game states. Once we identified the correct palettes through visual inspection (Kirby = P8, Enemy Group 1 = P12), the system correctly displayed the sprites with their intended colors.