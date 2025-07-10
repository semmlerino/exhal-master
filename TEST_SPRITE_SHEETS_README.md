# Test Sprite Sheets for Enhanced Palette Workflow

## Created Sprite Sheets

### 1. Focused Kirby sprites (8x8 grid)
- **Image**: `kirby_focused_test.png`
- **Palette**: `kirby_focused_test.pal.json`
- **Size**: 64x64 pixels
- **Tiles**: 64 tiles

### 2. 4x4 Kirby sprites
- **Image**: `tiny_test.png`
- **Palette**: `tiny_test.pal.json`
- **Size**: 0x0 pixels
- **Tiles**: 16 tiles

### 3. 8x4 sprite section
- **Image**: `medium_test.png`
- **Palette**: `medium_test.pal.json`
- **Size**: 0x0 pixels
- **Tiles**: 32 tiles

### 4. Level/environment sprites
- **Image**: `level_sprites_test.png`
- **Palette**: `level_sprites_test.pal.json`
- **Size**: 0x0 pixels
- **Tiles**: 48 tiles

## How to Test

1. **Launch Editor**: `python3 indexed_pixel_editor.py`
2. **Open Image**: Load any `.png` file above
3. **Auto-Palette**: Editor detects `.pal.json` and offers to load it
4. **Accept**: Click "Yes" to load the companion palette
5. **Toggle Views**:
   - ☑️ **Greyscale Mode**: See index values (0-15) as grayscale
   - ☐ **Greyscale Mode**: See game-accurate colors using external palette

## Visual Indicators

- **Green border** around palette = external palette loaded
- **Green triangle** on first color = external palette indicator
- **Tooltip** shows palette source information
- **Window title** shows current palette name

## Available Palettes

You can also manually load any of these palette files:

- `kirby_reference.pal.json` - Reference Kirby colors from documentation
- `Cave.SnesCgRam_palette_8.pal.json` - Kirby's palette (most common)
- `Cave.SnesCgRam_palette_9.pal.json` - Additional sprite palette
- `Cave.SnesCgRam_palette_10.pal.json` - Additional sprite palette
- `Cave.SnesCgRam_palette_11.pal.json` - Additional sprite palette
- `Cave.SnesCgRam_palette_12.pal.json` - Additional sprite palette
- `Cave.SnesCgRam_palette_13.pal.json` - Additional sprite palette
- `Cave.SnesCgRam_palette_14.pal.json` - Additional sprite palette
- `Cave.SnesCgRam_palette_15.pal.json` - Additional sprite palette

## Testing Different Palettes

Try loading the same sprite sheet with different palettes to see how it affects the color preview:

1. Load a sprite sheet (e.g., `kirby_focused_test.png`)
2. Load its default palette (`kirby_focused_test.pal.json`)
3. Try "File → Load Palette File..." with a different palette (e.g., `Cave.SnesCgRam_palette_9.pal.json`)
4. See how the same sprite indices look with different color palettes!

## Workflow Verification

This tests the complete enhanced workflow:
- ✅ Sprite extraction with companion palettes
- ✅ Auto-detection of paired files  
- ✅ External palette loading
- ✅ Greyscale/color mode switching
- ✅ Settings persistence
- ✅ Recent files tracking
