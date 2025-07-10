# Kirby Super Star Unified Sprite Editor

A comprehensive tool for extracting, editing, and reinserting sprites for Kirby Super Star (SNES) with full palette support.

## Features

- **Unified Interface**: Choose between GUI (PyQt6) or interactive CLI
- **Palette-Aware Extraction**: Uses collected palette mappings (43% coverage)
- **SNES Constraint Validation**: Ensures edits follow hardware limitations
- **Safe Reinsertion**: Automatic backups and preview generation
- **Visual Tools**: Palette references, coverage maps, and more
- **Batch Operations**: Process multiple sprites efficiently

## Quick Start

### Option 1: Launch with GUI (Recommended)
```bash
python3 launch_sprite_editor.py
```

### Option 2: Interactive CLI (No GUI dependencies)
```bash
python3 sprite_editor_cli.py
```

### Option 3: Direct command-line tools
```bash
# Extract sprites
python3 sprite_edit_workflow.py extract VRAM.dmp CGRAM.dmp -m final_palette_mapping.json

# Validate edits
python3 sprite_edit_workflow.py validate extracted_sprites/

# Reinsert sprites
python3 sprite_edit_workflow.py reinsert extracted_sprites/
```

## Requirements

### Minimum Requirements
- Python 3.8+
- Pillow (PIL)

### For GUI Version
- PyQt6

Install dependencies:
```bash
pip install PyQt6 Pillow
```

## Workflow Overview

### 1. Extract Sprites
Choose between:
- **Individual Tiles**: Best for precise editing of specific sprites
- **Sprite Sheet**: Best for viewing sprites in context

### 2. Edit Sprites
Use any image editor that supports indexed PNG:
- Aseprite (recommended for pixel art)
- GIMP
- GraphicsGale
- Photoshop (with indexed color mode)

### 3. Validate Edits
Check that your edits follow SNES constraints:
- Maximum 15 colors + transparent per tile
- No new colors added
- Proper palette assignments maintained

### 4. Reinsert Sprites
Convert edited sprites back to VRAM format:
- Automatic backup creation
- Preview generation
- Ready for emulator testing

## GUI Interface

### Main Features

#### Extract Tab
- Select VRAM and CGRAM dumps
- Choose extraction mode (tiles or sheet)
- Set memory offset and size
- Optional palette mapping support

#### Edit Workflow Tab
- Load and manage workspaces
- View editing tips
- Quick access to file explorer

#### Validate Tab
- Check individual tiles or full sheets
- Detailed error reporting
- Constraint violation details

#### Reinsert Tab
- Convert sprites back to VRAM
- Optional backup creation
- Preview generation

#### Visual Tools Tab
- Create palette references
- Generate coverage maps
- Compare before/after

### Quick Actions Panel
- Extract Kirby sprites
- Extract enemy sprites
- Validate workspace
- Recent files access

## CLI Interface

### Interactive Menu System
```
Main Menu:
1. Extract Sprites
2. Validate Edited Sprites
3. Reinsert Sprites
4. Quick Actions
5. Visual Tools
6. Help
0. Exit
```

### Quick Actions
- Extract and validate Kirby sprites
- Extract full sprite sheet with guide
- Batch validate all workspaces

## File Formats

### Input Files
- **VRAM dump**: Binary file containing sprite graphics (usually 64KB)
- **CGRAM dump**: Binary file containing color palettes (512 bytes)
- **Palette mappings**: JSON file with tile-to-palette assignments

### Output Files
- **Individual tiles**: PNG files named `tile_XXXX_palY.png`
- **Sprite sheets**: Single PNG with all sprites
- **Metadata**: JSON files with extraction information
- **Validation reports**: JSON files with constraint check results

## Common Use Cases

### Quick Extract Kirby Sprites
1. Launch the editor
2. Click "Extract Kirby Sprites" in quick actions
3. Sprites extracted to `kirby_sprites/` folder

### Edit and Reinsert Workflow
1. Extract sprites (tiles or sheet)
2. Edit in your image editor
3. Validate changes
4. Reinsert to create modified VRAM

### Batch Processing
1. Use "Tools → Batch Extract" in GUI
2. Or use CLI quick actions for automation

## SNES Sprite Constraints

### Must Follow
- **Tile Size**: 8×8 pixels (cannot change)
- **Colors**: Maximum 15 + transparent per tile
- **Transparency**: Color index 0 is always transparent
- **Palettes**: Cannot add new colors, only use existing

### Memory Layout
- Sprites typically at VRAM offset 0xC000
- 4 bits per pixel (4bpp) format
- 32 bytes per tile
- OAM palettes 0-7 map to CGRAM palettes 8-15

## Troubleshooting

### "No palette mapping found"
The sprite hasn't been mapped yet (57% are unmapped). The tool will use a default palette.

### "Validation failed: too many colors"
Reduce the color count in your edited tile. Each 8×8 tile can only use 15 colors + transparent.

### "Colors look wrong after reinsertion"
Ensure you:
1. Saved as indexed PNG (not RGB)
2. Used only existing palette colors
3. Didn't change color indices

### GUI won't start
Try the CLI version: `python3 sprite_editor_cli.py`

## Tips for Best Results

1. **Always validate** before reinsertion
2. **Keep backups** of original dumps
3. **Work in indexed mode** in your image editor
4. **Test frequently** in emulator
5. **Use the editing guide** for palette reference

## Project Structure

```
sprite_editor_unified.py    # Main GUI application
sprite_editor_cli.py        # Interactive CLI version
launch_sprite_editor.py     # Smart launcher with dependency check
sprite_edit_workflow.py     # Core workflow implementation
sprite_sheet_editor.py      # Sheet-based operations
sprite_edit_helpers.py      # Shared utilities
```

## Advanced Features

### Custom Palette Mappings
Edit `final_palette_mapping.json` to add your own tile-to-palette assignments.

### Batch Validation
Validate multiple workspaces at once using CLI quick actions.

### Visual Analysis
Generate coverage maps and palette references for documentation.

## Contributing

To extend the palette mapping coverage:
1. Use the Mesen tracking scripts
2. Play through more game areas
3. Share your `final_palette_mapping.json`

## Credits

Built with:
- PyQt6 for GUI
- PIL/Pillow for image processing
- Based on reverse engineering of Kirby Super Star

---

Happy sprite editing! 🎨✨