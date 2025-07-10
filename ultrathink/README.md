# ULTRATHINK Sprite Editing Workflow

## Overview
This folder contains properly extracted sprite sheets in grayscale indexed format with companion palette files.

## Contents

### sprites/
- `kirby_sprites.png` - Grayscale indexed sprite sheet (pixel values 0-15)
- `kirby_sprites.pal.json` - Default companion palette (auto-detected by editor)
- `kirby_sprites_metadata.json` - Tile and palette mapping information
- `kirby_sprites_editing_guide.png` - Visual reference showing index-to-gray mapping
- `kirby_palette_14.pal.json` - Pink Kirby palette (standard colors)
- `kirby_palette_8.pal.json` - Purple Kirby palette (special state)

## Usage

### Quick Start
```bash
# Load with auto-detected palette (grayscale by default, press C for color)
cd ultrathink
python3 ../indexed_pixel_editor.py sprites/kirby_sprites.png
```

### Different Palette Options
```bash
# Pink Kirby (standard)
python3 ../indexed_pixel_editor.py sprites/kirby_sprites.png -p sprites/kirby_palette_14.pal.json

# Purple Kirby (power-up)
python3 ../indexed_pixel_editor.py sprites/kirby_sprites.png -p sprites/kirby_palette_8.pal.json
```

## Editor Controls
- **C** - Toggle between grayscale (index view) and color preview
- **P** - Switch between available palettes (when metadata is loaded)
- **Mouse Wheel** - Zoom in/out
- **Left Click** - Draw with selected color
- **Right Click** - Pick color from canvas
- **Number Keys 0-9, A-F** - Select palette color

## Enhanced Editor
Use the enhanced editor for palette switching support:
```bash
python3 ../indexed_pixel_editor_enhanced.py sprites/kirby_sprites.png
```

This will:
- Auto-load the metadata file with all 16 palettes
- Allow switching between palettes with 'P' key
- Show Kirby with correct pink/purple colors (palette 8)

## Technical Details
- Sprites use 4bpp indexed color (16 colors)
- Index 0 is transparent (shows as black in grayscale)
- Indices 1-15 map to game colors
- Grayscale display uses evenly spaced gray values for clarity

## Workflow Benefits
1. See exact palette indices while editing
2. Preview game colors in real-time
3. Maintain proper indexed format for game compatibility
4. Easy palette swapping for different variants