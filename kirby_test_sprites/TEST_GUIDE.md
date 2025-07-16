# Kirby Test Sprites

A collection of grayscale Kirby sprites with color palettes for pixel editor testing.

## Quick Start

```bash
# Test basic functionality
python launch_pixel_editor.py kirby_test_sprites/kirby_main.png

# Test color picker on small sprite  
python launch_pixel_editor.py kirby_test_sprites/kirby_small.png

# Test palette switching
python launch_pixel_editor.py kirby_test_sprites/kirby_multipalette.png
# Then press 'P' to switch between palettes
```

## Available Sprites

| Sprite | Size | Description | Default Palette |
|--------|------|-------------|-----------------|
| kirby_main.png | 64x64 (8x8 tiles) | Main Kirby sprites | Pink (pal 8) |
| kirby_small.png | 32x32 (4x4 tiles) | Small Kirby subset | Pink (pal 8) |
| kirby_effects.png | 32x64 (4x8 tiles) | Kirby with effects | Pink (pal 8) |
| enemy_sprites.png | 32x64 (4x8 tiles) | Enemy sprites | Blue (pal 11) |
| ui_elements.png | 32x32 (4x4 tiles) | UI elements | UI (pal 14) |
| kirby_multipalette.png | 64x64 | Multi-palette test | 8 palettes |

## Testing Scenarios

### 1. Color Picker Test
- Open any sprite
- Press 'I' to activate color picker
- Click on different colored pixels
- Verify tool returns to pencil mode
- Check selected color in palette panel

### 2. Grid Toggle Test
- Press 'G' to toggle grid
- Should be OFF by default
- Verify grid appears/disappears

### 3. Color Mode Toggle
- Press 'C' to toggle color preview
- Verify sprite switches between grayscale and color

### 4. Palette Switching (multipalette sprite)
- Open kirby_multipalette.png
- Press 'P' to open palette switcher
- Try different palettes (Pink, Yellow, Blue, etc.)
- Verify colors update correctly

### 5. Edit and Save Test
- Make some edits
- Save the file
- Verify it remains grayscale
- Reload and check edits preserved

## Keyboard Shortcuts
- **I** - Color picker tool
- **G** - Toggle grid visibility  
- **C** - Toggle color/grayscale mode
- **P** - Palette switcher (if available)
- **Ctrl+Z/Y** - Undo/Redo
- **Ctrl+S** - Save
