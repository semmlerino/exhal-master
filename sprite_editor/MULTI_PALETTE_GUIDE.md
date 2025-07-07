# Multi-Palette Preview Guide

The Kirby Super Star Sprite Editor now includes a powerful **Multi-Palette Preview** mode that shows sprites with their correctly associated palettes based on OAM (Object Attribute Memory) data.

## What's New

### 1. **OAM Palette Mapping**
- Automatically reads sprite-to-palette assignments from OAM dumps
- Shows which palettes are actually used by sprites in the game
- Maps VRAM tiles to their correct palettes

### 2. **Multi-Palette Viewer Tab**
- New "Multi-Palette" tab in the GUI
- Shows sprites with all 16 possible palettes in a 4x4 grid
- Highlights which palettes are actively used (green border)
- Click any palette to apply it to the main viewer

### 3. **Enhanced Sprite Viewer**
- Palette switching support
- Optional overlay showing palette assignments per tile
- Real-time palette preview

## How to Use

### Basic Workflow

1. **Load Required Files**:
   - VRAM.dmp - Contains sprite graphics
   - CGRAM.dmp - Contains color palettes
   - OAM.dmp - Contains sprite attributes and palette assignments

2. **Generate Multi-Palette Preview**:
   - Go to the "Multi-Palette" tab
   - Click "Load OAM" to load OAM.dmp
   - Click "Generate Multi-Palette Preview"
   - View all 16 palette variations of your sprites

3. **Identify Correct Palettes**:
   - Green borders indicate palettes used by actual sprites
   - Usage statistics show how many sprites use each palette
   - Click any palette to see it applied to the full sprite sheet

### Advanced Features

#### OAM-Correct Extraction
The system can extract sprites with each tile using its OAM-assigned palette:

```python
# Programmatic usage
core = SpriteEditorCore()
core.load_oam_mapping("OAM.dmp")
img, tiles = core.extract_sprites_with_correct_palettes(
    "VRAM.dmp", 0xC000, 0x4000, "CGRAM.dmp"
)
```

#### Palette Grid Preview
Create a grid showing the same sprites with all 16 palettes:

```python
grid_img, tiles = core.create_palette_grid_preview(
    "VRAM.dmp", 0xC000, 0x4000, "CGRAM.dmp"
)
```

## Understanding the Display

### Palette Numbers
- **Palette 0-7**: Standard sprite palettes
- **Palette 8-15**: Additional palettes (often used for backgrounds)

### OAM Information
The OAM dump tells us:
- Which tiles are active sprites
- What palette each sprite uses
- Sprite positions and attributes

### Common Palette Assignments (Kirby)
Based on the OAM analysis:
- **Palette 0**: Often used for main character sprites
- **Palette 2-4**: Enemy sprites and effects
- **Palette 6-7**: Special effects and UI elements

## Benefits

1. **Accurate Preview**: See sprites as they appear in-game
2. **Easy Palette Identification**: Quickly find which palette a sprite uses
3. **Better Editing**: Edit sprites with the correct colors in mind
4. **Multi-Palette Testing**: See how edits look with different palettes

## Technical Details

### File Requirements
- **VRAM.dmp**: 64KB dump of Video RAM
- **CGRAM.dmp**: 512 bytes (16 palettes × 16 colors × 2 bytes)
- **OAM.dmp**: 544 bytes (128 sprites × 4 bytes + 32 bytes high table)

### Memory Mapping
- Sprites at VRAM $6000 = file offset 0xC000
- Each tile is 32 bytes in 4bpp format
- Palette assignment in OAM attribute bits 0-2

## Improved Visibility Features

### Preview Size Control
The Multi-Palette tab now includes a **Preview Size** control:
- Default: 64 tiles (shows just Kirby and nearby sprites)
- Range: 16-512 tiles
- Smaller values = better visibility of individual sprites

### Recommended Settings for Clear Previews
- **Preview Size**: 64 tiles (focuses on main character area)
- **Tiles per Row**: 8 (creates a more vertical layout)
- **Result**: 64x64 pixel images that are easy to see

### Size Comparison
- **Full extraction**: 512 tiles → 128x256 pixels (hard to see details)
- **Focused extraction**: 64 tiles → 64x64 pixels (clear and visible)
- **Minimal extraction**: 32 tiles → 64x32 pixels (just Kirby)

## Troubleshooting

### "Sprites are too small to see"
- Reduce Preview Size to 64 or 32 tiles
- Focus on the sprite area you're interested in
- The preview tiles are now larger (256x256) and scrollable

### "No active palettes shown"
- Ensure OAM.dmp is from the same game state as VRAM.dmp
- Check that sprites are actually on-screen when dumps were taken

### "Wrong colors"
- Verify CGRAM.dmp matches the game state
- Some sprites may use palette cycling or special effects

### "Can't see all sprites"
- Sprites may be distributed across multiple VRAM regions
- Try different offsets: 0x0000, 0x8000, 0xC000
- Adjust the main Extract tab settings for full dumps