# SpritePal - Modern Sprite Extraction Tool

SpritePal is a sleek, intuitive PyQt6 application that simplifies sprite extraction from SNES memory dumps with automatic palette association. Designed specifically for Kirby Super Star sprite editing workflows.

## Features

### 🎯 Core Functionality
- **Drag & Drop Interface** - Simply drop your dump files onto the application
- **Automatic Palette Association** - Generates properly named .pal.json files for pixel editor integration
- **Smart File Detection** - Automatically finds related VRAM, CGRAM, and OAM files
- **Real-time Preview** - See sprites and palettes before extraction
- **One-Click Workflow** - Extract sprites with palettes ready for editing
- **Session Persistence** - Automatically remembers loaded files and settings between sessions

### 🎨 Modern UI Design
- **Dark Theme** - Easy on the eyes during long editing sessions
- **Clean Layout** - Intuitive organization with clear visual hierarchy
- **Visual Feedback** - Green checkmarks show loaded files
- **Status Updates** - Real-time progress information

### 🔧 Technical Features
- **Grayscale Extraction** - Preserves pixel indices for accurate editing
- **Multi-Palette Support** - Generates all sprite palettes (8-15)
- **Metadata Generation** - Creates .metadata.json for palette switching
- **Pixel Editor Integration** - Opens extracted sprites directly in editor

## Installation

```bash
# Required dependencies
pip install PyQt6 Pillow

# Clone or download the project
cd /path/to/exhal-master

# Run SpritePal
python3 launch_spritepal.py
```

## Usage

### Quick Start
1. Launch SpritePal
2. Drop your dump files onto the input zones:
   - VRAM dump (required) - Contains sprite graphics
   - CGRAM dump (required) - Contains color palettes
   - OAM dump (optional) - Enables smart palette mapping
3. Click "Extract for Editing"
4. Click "Open in Editor" to launch pixel editor

### File Naming
SpritePal automatically generates organized output files:
- `[name]_sprites_editor.png` - Grayscale sprite sheet
- `[name]_sprites_editor.pal.json` - Main palette file (auto-loads)
- `[name]_sprites_editor_pal8-15.pal.json` - Individual palette files
- `[name]_sprites_editor.metadata.json` - Palette switching metadata

### Workflow Example
```bash
# Input files:
Cave.SnesVideoRam.dmp
Cave.SnesCgRam.dmp
Cave.SnesSpriteRam.dmp

# Output files:
cave_sprites_editor.png
cave_sprites_editor.pal.json
cave_sprites_editor_pal8.pal.json  # Kirby (Pink)
cave_sprites_editor_pal9.pal.json  # Kirby Alt
cave_sprites_editor_pal10.pal.json # Helper
cave_sprites_editor_pal11.pal.json # Enemy 1
cave_sprites_editor_pal12.pal.json # UI/HUD
cave_sprites_editor_pal13.pal.json # Enemy 2
cave_sprites_editor_pal14.pal.json # Boss/Enemy
cave_sprites_editor_pal15.pal.json # Effects
cave_sprites_editor.metadata.json
```

## UI Overview

### Main Window Layout

```
┌─────────────────────────────────────────────┐
│ SpritePal - Sprite Extraction Tool          │
├─────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────────┐ │
│ │ Input Files     │ │ Extraction Preview  │ │
│ │                 │ │                     │ │
│ │ [VRAM Drop]  ✓  │ │ [Sprite Preview]    │ │
│ │ [CGRAM Drop] ✓  │ │ Tiles: 512          │ │
│ │ [OAM Drop]   ✓  │ │                     │ │
│ │                 │ └─────────────────────┘ │
│ │ Auto-detect     │ ┌─────────────────────┐ │
│ └─────────────────┘ │ Palette Preview     │ │
│                     │ [8][9][10][11]      │ │
│ Output Settings:    │ [12][13][14][15]    │ │
│ Name: [cave_sprites_editor]                 │ │
│ ☑ Create grayscale with palettes            │ │
│ ☑ Generate metadata for palette switching   │ │
│                                             │
│ [Extract for Editing] [Open in Editor]      │
└─────────────────────────────────────────────┘
```

### Key Components

1. **Input Files Panel**
   - Three drop zones with visual status indicators
   - Browse buttons for manual file selection
   - Auto-detect button finds files automatically

2. **Preview Panels**
   - Sprite preview shows extracted tiles with zoom/pan controls:
     - **Mouse wheel**: Zoom in/out (0.1x to 20x)
     - **Click and drag**: Pan around the image
     - **Right-click**: Reset view to 1:1
     - **Fit button**: Fit entire sprite sheet in view
     - **1:1 button**: Reset to actual pixel size
     - **Pixel grid**: Auto-appears when zoomed > 4x
   - Palette preview displays all 8 sprite palettes
   - Real-time updates during extraction

3. **Output Settings**
   - Smart naming based on input files
   - Options for grayscale and metadata generation
   - Browse button for custom output location

4. **Action Buttons**
   - "Extract for Editing" - Main extraction button
   - "Open in Editor" - Launches pixel editor with results

## Integration with Pixel Editor

SpritePal creates files specifically formatted for the pixel editor:

1. **Auto-loading Palettes** - The `.pal.json` file with matching name loads automatically
2. **Palette Switching** - Use number keys 0-7 to switch between palettes
3. **Metadata Support** - Enables advanced palette features in the editor

## Tips

- **File Organization** - Keep dump files in the same directory for auto-detection
- **Naming Convention** - SpritePal recognizes common patterns like `*VRAM.dmp`, `*CGRAM.dmp`
- **OAM Benefits** - Including OAM enables smart palette highlighting
- **Quick Workflow** - Use auto-detect, then extract with defaults for fastest results
- **Session Persistence** - SpritePal automatically saves your work:
  - Previously loaded files are restored when you restart the app
  - Window size and position are remembered
  - Output settings are preserved
  - Use "File > New Extraction" to start fresh

## Technical Details

### Architecture
- **MVC Pattern** - Clean separation of UI and logic
- **Threaded Extraction** - UI remains responsive during processing
- **Modular Design** - Easy to extend with new features

### File Structure
```
spritepal/
├── ui/              # User interface components
├── core/            # Extraction and palette logic
└── utils/           # Constants and utilities
```

### Supported Formats
- **Input**: SNES memory dumps (.dmp files)
- **Output**: Indexed PNG + JSON palette files
- **Palettes**: BGR555 to RGB888 conversion

### Session Management
- **Settings File**: `.spritepal_settings.json` in the current directory
- **Auto-save**: Session data is saved whenever files are loaded or settings change
- **Auto-restore**: Previous session is restored on startup if files still exist
- **Manual Clear**: Use "File > New Extraction" to clear session data

## Future Enhancements

- Batch extraction of multiple sprite sets
- Direct ROM file extraction
- Built-in palette editor
- Export to additional formats
- Project save/load functionality

## Credits

SpritePal is part of the Kirby Super Star sprite editing toolkit, designed to work seamlessly with the indexed pixel editor for a complete sprite editing workflow.