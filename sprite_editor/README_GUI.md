# Kirby Super Star Sprite Editor GUI

A complete PyQt6 graphical interface for extracting and editing sprites from Kirby Super Star SNES ROM dumps.

## Features

- **Extract Tab**: Extract sprites from VRAM dumps with customizable settings
- **Inject Tab**: Inject edited PNG sprites back into VRAM with validation
- **View/Edit Tab**: Advanced sprite viewer with zoom, grid overlay, and color info
- **Dark Theme**: Professional dark UI for comfortable editing
- **Multi-threaded**: Smooth UI with background processing
- **Settings Persistence**: Remembers your last used files and settings

## Requirements

```bash
pip install PyQt6 Pillow numpy
```

## Usage

### Quick Start

```bash
python sprite_editor_gui.py
```

### Workflow

1. **Extract Sprites**:
   - Open a VRAM dump file (e.g., VRAM.dmp)
   - Set offset to 0xC000 (for Kirby sprites at VRAM $6000)
   - Optionally load CGRAM.dmp and select palette 8 for colors
   - Click "Extract Sprites"

2. **Edit Sprites**:
   - Save the extracted image from the View/Edit tab
   - Edit in your favorite image editor
   - **IMPORTANT**: Keep the image in indexed color mode!
   - Use only the existing 16 colors

3. **Inject Sprites**:
   - Load your edited PNG in the Inject tab
   - Select target VRAM file
   - Click "Inject Sprites"
   - Load the output file in your emulator

### Keyboard Shortcuts

- `Ctrl+O`: Open VRAM file
- `Ctrl+E`: Quick extract with current settings
- `Ctrl+I`: Quick inject (opens file dialog)

### GUI Components

#### Extract Tab
- **VRAM File**: Source dump file to extract from
- **Offset**: Hexadecimal offset in VRAM (default: 0xC000)
- **Size**: Amount of data to extract (default: 0x4000 = 16KB)
- **Tiles/Row**: How many 8x8 tiles per row (affects image width)
- **Palette**: Optional CGRAM palette application

#### Inject Tab
- **PNG File**: Your edited sprite image
- **Validation**: Real-time checking for SNES compatibility
- **Target VRAM**: Destination file for injection
- **Output**: Name for the modified VRAM file

#### View/Edit Tab
- **Zoom Controls**: Zoom in/out or fit to window
- **Grid Toggle**: Show/hide 8x8 tile boundaries
- **Hover Info**: See tile coordinates and color indices
- **Save/Export**: Save current view or open in external editor

## Technical Details

### Color Mode Requirements
- PNG files MUST be in indexed color mode (8-bit palette)
- Maximum 16 colors (4bpp SNES limitation)
- Image dimensions must be multiples of 8 pixels

### Common Sprite Locations
- Kirby sprites: VRAM $6000 (file offset 0xC000)
- Size: 16KB (0x4000 bytes)
- Palette: Usually palette 8 for Kirby

### File Structure
- `sprite_editor_gui.py`: Main GUI application
- `sprite_editor_core.py`: Core sprite processing functions
- `sprite_viewer_widget.py`: Custom image viewer widget

## Troubleshooting

### "PNG validation failed"
- Ensure your image is in indexed color mode
- Check that width/height are multiples of 8
- Verify you're using 16 colors or less

### Sprites appear corrupted
- Original image may have been saved as RGB/RGBA
- Re-extract and edit in indexed mode only
- Some editors auto-convert to RGB - use GIMP or similar

### Can't find sprites
- Try different offsets (common: 0x0000, 0x8000, 0xC000)
- Sprites may be spread across multiple VRAM regions
- Use memory dumps from actual gameplay moments