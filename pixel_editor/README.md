# Pixel Editor

A specialized sprite editing tool for indexed color images, particularly designed for SNES sprite editing.

## Directory Structure

```
pixel_editor/
├── launch_pixel_editor.py      # Main launcher script
├── core/                       # Core pixel editor modules
│   ├── indexed_pixel_editor_v3.py    # Main GUI application
│   ├── pixel_editor_canvas_v3.py     # Canvas widget
│   ├── pixel_editor_controller_v3.py # MVC Controller
│   ├── pixel_editor_models.py        # Data models
│   ├── pixel_editor_managers.py      # Business logic managers
│   ├── pixel_editor_workers.py       # Async workers
│   ├── pixel_editor_widgets.py       # UI widgets
│   ├── pixel_editor_commands.py      # Command pattern implementation
│   ├── pixel_editor_utils.py         # Utility functions
│   ├── pixel_editor_constants.py     # Constants and configuration
│   └── views/                        # View components
│       ├── dialogs/                  # Dialog windows
│       └── panels/                   # UI panels
└── README.md                   # This file
```

## Usage

### From the pixel_editor directory:
```bash
python launch_pixel_editor.py
```

### From the project root:
```bash
python launch_pixel_editor.py
# or
python pixel_editor/launch_pixel_editor.py
```

### Command Line Options:
- `--gui` - Launch GUI version (default)
- `--test` - Run headless tests only
- `--check` - Check dependencies and environment
- `--help` - Show help message

## Features

- **4bpp Indexed Color Editing**: Optimized for SNES sprite formats
- **16-Color Palette Support**: Full SNES palette management
- **Drawing Tools**: Pencil, fill, and color picker tools
- **Enhanced Zoom and Pan**: 
  - Cursor-focused zoom (zooms towards mouse position)
  - Keyboard shortcuts for zoom reset and fit
  - Pan with middle mouse or arrow keys
  - Zoom level display in status bar
- **Undo/Redo**: Full undo/redo support with command pattern
- **Import/Export**: PNG file support with palette preservation
- **Keyboard Shortcuts**: Efficient workflow with keyboard shortcuts

## Keyboard Shortcuts

- **C** - Toggle color mode (grayscale/color preview)
- **G** - Toggle grid visibility
- **I** - Switch to color picker tool (auto-returns to pencil after picking)
- **P** - Open palette switcher (when multiple palettes available)
- **Ctrl+N** - New file
- **Ctrl+O** - Open file
- **Ctrl+S** - Save file
- **Ctrl+Z** - Undo
- **Ctrl+Y** - Redo
- **Ctrl++** - Zoom in
- **Ctrl+-** - Zoom out
- **Ctrl+0** - Reset zoom to default (4x)
- **Ctrl+Shift+0** or **F** - Zoom to fit window
- **Arrow Keys** - Pan the canvas
- **Shift+Arrow Keys** - Pan the canvas faster
- **Mouse Wheel** - Zoom in/out (focused on cursor position)
- **Middle Mouse Button + Drag** - Pan the canvas

## Architecture

The pixel editor follows an MVC (Model-View-Controller) architecture:

- **Models** (`pixel_editor_models.py`): Data structures for images, palettes, and projects
- **Views** (`views/` directory): UI components and dialogs
- **Controller** (`pixel_editor_controller_v3.py`): Business logic coordination
- **Managers** (`pixel_editor_managers.py`): Tool, file, and palette management
- **Workers** (`pixel_editor_workers.py`): Async operations for file I/O

## Dependencies

- Python 3.8+
- PyQt6
- NumPy
- Pillow (PIL)

## Development

To import pixel editor modules in your code:

```python
from pixel_editor.core import IndexedPixelEditor, PixelEditorController
from pixel_editor.core.pixel_editor_models import ImageModel, PaletteModel
from pixel_editor.core.pixel_editor_managers import ToolManager
```

## Testing

Run tests from the project root:

```bash
python -m pytest pixel_editor/tests/
```

Or use the test mode:

```bash
python pixel_editor/launch_pixel_editor.py --test
```