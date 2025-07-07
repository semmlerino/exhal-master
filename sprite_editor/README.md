# Sprite Editor Module

This folder contains all the components of the Kirby Super Star Sprite Editor.

## Main Components

### GUI Application
- `sprite_editor_gui.py` - Main PyQt6 application
- `sprite_viewer_widget.py` - Custom image viewer with zoom/grid
- `multi_palette_viewer.py` - Multi-palette preview widget

### Core Functionality
- `sprite_editor_core.py` - Core sprite processing functions
- `oam_palette_mapper.py` - OAM data parser for palette mapping
- `settings_manager.py` - Persistent settings and recent files management
- `security_utils.py` - Path validation utilities

### Utility Scripts
- `snes_tiles_to_png.py` - Convert SNES tiles to PNG
- `png_to_snes.py` - Convert PNG back to SNES format
- `extract_all_palettes.py` - Apply CGRAM palettes to images

### Workflow Scripts
- `sprite_workflow.py` - Command-line workflow automation
- `sprite_extractor.py` - Standalone extraction tool
- `sprite_injector.py` - Standalone injection tool

### Original Tools
- `sprite_assembler.py` - HAL compression assembler
- `sprite_disassembler.py` - HAL compression disassembler

## Key Features

- **Persistent Settings**: Automatically remembers your last used files and settings
- **Recent Files Menu**: Quick access to recently used VRAM, CGRAM, and OAM files
- **Multi-Palette Support**: View sprites with different palettes simultaneously
- **OAM-based Palette Mapping**: Accurate palette assignment using OAM data
- **Real-time Preview**: Interactive sprite viewer with zoom and grid overlay
- **Batch Operations**: Extract and inject multiple sprites efficiently

## Usage

From the main exhal-master directory, run:

```bash
python run_sprite_editor.py
```

Or use individual scripts:

```bash
python -m sprite_editor.sprite_workflow extract
python -m sprite_editor.snes_tiles_to_png VRAM.dmp 16 32 output.png
```

## Requirements

- Python 3.6+
- PyQt6 (for GUI)
- Pillow (PIL)
- numpy

## Settings

The application saves your preferences and recent files automatically. Settings are stored in:
- Windows: `%APPDATA%\sprite_editor\settings.json`
- Linux/Mac: `~/.sprite_editor/settings.json`

See [SETTINGS_GUIDE.md](../SETTINGS_GUIDE.md) for more details.