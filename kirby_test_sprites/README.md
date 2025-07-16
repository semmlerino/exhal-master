# Kirby Test Sprites

Grayscale Kirby sprites with color palettes for pixel editor testing.

## Usage

### Open with default palette:
```bash
python launch_pixel_editor.py kirby_test_sprites/kirby_idle.png
```

### Open with specific palette:
```bash
python launch_pixel_editor.py kirby_test_sprites/kirby_idle.png -p kirby_test_sprites/kirby_idle.pal.json
```

### Test different palettes:
1. Open any sprite
2. Load different .pal.json files via File > Load Palette File
3. Or press 'P' if multiple palettes are available

## Testing Color Picker
1. Press 'I' to activate color picker
2. Click any pixel to pick its color
3. Tool returns to pencil mode automatically

## Available Sprites
- kirby_idle.png - Kirby standing pose
- kirby_walk.png - Kirby walking animation
- kirby_small.png - Small 4x4 tile Kirby
- kirby_test_multicolor.png - Uses palette 11 instead of 8

## Test Palettes
- test_rainbow.pal.json - Full rainbow spectrum
- test_gameboy.pal.json - Game Boy green palette
