# Kirby Super Star Sprite Editor

A comprehensive PyQt6 GUI application for extracting, viewing, and editing sprites from Kirby Super Star SNES ROM dumps.

## Quick Start

```bash
# Run the GUI application (any of these work)
python sprite_editor_gui.py
python run_sprite_editor.py

# Or use command-line tools
python -m sprite_editor.sprite_workflow extract
python -m sprite_editor.sprite_workflow inject edited.png
```

## Features

- **Extract sprites** from VRAM dumps with customizable settings
- **Multi-palette preview** showing sprites with all 16 palettes
- **OAM integration** for correct palette assignments
- **Advanced viewer** with zoom, grid overlay, and palette info
- **Inject edited sprites** back into VRAM with validation
- **Dark theme UI** for comfortable editing

## File Organization

All sprite editor components are now in the `sprite_editor/` folder:

```
sprite_editor/
├── sprite_editor_gui.py      # Main GUI application
├── sprite_editor_core.py     # Core processing functions
├── multi_palette_viewer.py   # Multi-palette preview widget
├── oam_palette_mapper.py     # OAM data parser
├── sprite_viewer_widget.py   # Image viewer widget
├── snes_tiles_to_png.py     # SNES → PNG converter
├── png_to_snes.py           # PNG → SNES converter
├── sprite_workflow.py        # Command-line workflow
└── README.md                # Detailed documentation
```

## Required Files

- **VRAM.dmp** - Video RAM dump (64KB)
- **CGRAM.dmp** - Color palette data (512 bytes)
- **OAM.dmp** - Sprite attributes (544 bytes)

## Documentation

- `sprite_editor/README.md` - Module documentation
- `sprite_editor/README_GUI.md` - GUI user guide
- `sprite_editor/MULTI_PALETTE_GUIDE.md` - Multi-palette feature guide

## Requirements

```bash
pip install PyQt6 Pillow numpy
```

## Common Sprite Locations

- Kirby sprites: VRAM offset 0xC000 (file offset)
- Enemies: Various offsets, check with sprite viewer
- Use palette 8 for Kirby's normal colors