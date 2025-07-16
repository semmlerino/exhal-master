# Legacy to V3 Pixel Editor Migration Guide

## Overview

The pixel editor has been refactored from a monolithic architecture to a clean MVC (Model-View-Controller) pattern. This guide explains the migration from the legacy `indexed_pixel_editor.py` to the new `indexed_pixel_editor_v3.py`.

## Architecture Changes

### Legacy (indexed_pixel_editor.py)
- **Single file**: 1,896 lines containing everything
- **Mixed concerns**: UI, business logic, and data management intertwined
- **God class**: IndexedPixelEditor handled everything
- **Direct state management**: Canvas had its own image data copy
- **Duplicate code**: Multiple implementations of same functionality

### V3 (indexed_pixel_editor_v3.py)
- **Modular design**: Main file reduced to 594 lines
- **MVC pattern**: Clear separation of Model, View, Controller
- **Single responsibility**: Each component has one clear purpose
- **Centralized state**: All data managed by models in controller
- **DRY principle**: Shared functionality properly abstracted

## File Structure

### Legacy Files (Archived)
```
archive/legacy_pixel_editor/
├── indexed_pixel_editor.py      # Original monolithic editor
├── pixel_editor_controller.py   # Old controller (replaced by v3)
└── pixel_editor_tools.py        # Tool implementations (moved to managers)
```

### V3 Files (Active)
```
# Main application
indexed_pixel_editor_v3.py       # Refactored main window

# MVC Components
pixel_editor_controller_v3.py    # Business logic controller
pixel_editor_canvas_v3.py        # Refactored canvas (view only)
pixel_editor_models.py          # Data models
pixel_editor_managers.py        # Business logic managers

# UI Components
pixel_editor_views/
├── panels/
│   ├── tool_panel.py          # Tool selection UI
│   ├── palette_panel.py       # Color palette UI
│   ├── options_panel.py       # Settings UI
│   └── preview_panel.py       # Preview displays
└── dialogs/                   # Dialog windows

# Supporting Modules (Shared)
pixel_editor_utils.py           # Utility functions
pixel_editor_widgets.py         # Custom widgets
pixel_editor_constants.py       # Constants
pixel_editor_commands.py        # Command definitions
pixel_editor_workers.py         # Async workers
pixel_editor_settings_adapter.py # Settings compatibility
```

## API Compatibility

The V3 version includes a compatibility layer to support legacy code:

### Facade Methods
```python
# Legacy method → V3 implementation
editor.load_file_by_path(path)    # → controller.open_file(path)
editor.new_image(width, height)    # → controller.new_file(width, height)
editor.save_to_file(path)          # → controller.save_file(path)
editor.apply_palette(idx, colors)  # → Updates palette model
editor.toggle_color_mode_shortcut() # → Toggles UI checkbox
editor.set_zoom_preset(zoom)       # → Sets zoom level
```

### Property Accessors
```python
# Legacy property → V3 implementation
editor.metadata                    # → Returns palette metadata dict
editor.current_palette_index       # → controller.palette_manager.current_palette_index
editor.palette_widget              # → palette_panel.palette_widget
editor.apply_palette_checkbox      # → options_panel.apply_palette_checkbox
```

## Migration Steps

### For Application Code

1. **Update imports**:
   ```python
   # Old
   from indexed_pixel_editor import IndexedPixelEditor
   
   # New
   from indexed_pixel_editor_v3 import IndexedPixelEditor
   ```

2. **No other changes needed** - The compatibility layer handles the rest!

### For Test Code

Tests should work without modification due to the compatibility layer. However, for new tests, prefer using the controller directly:

```python
# Legacy style (still works)
editor.load_file_by_path("test.png")

# Preferred V3 style
editor.controller.open_file("test.png")
```

## Key Improvements

### 1. Performance
- Eliminated duplicate image data storage
- Optimized color caching in canvas
- Reduced memory footprint

### 2. Maintainability
- Clear separation of concerns
- Each file has a single responsibility
- Easy to locate and modify functionality

### 3. Testability
- Components can be tested in isolation
- Mock-friendly architecture
- No UI dependencies in business logic

### 4. Extensibility
- Easy to add new tools (Strategy pattern)
- Simple to add new UI panels
- Clean plugin architecture possible

## Breaking Changes

None! The V3 version is designed to be a drop-in replacement. All existing code should continue to work thanks to the compatibility layer.

## Future Considerations

### Undo/Redo System
Currently placeholder implementation. The V3 architecture makes it easy to implement:
- Command pattern in controller
- Delta-based state tracking
- Proper memory management

### New Features
The clean architecture enables:
- Advanced drawing tools
- Layer support
- Animation frames
- Plugin system

## Troubleshooting

### Import Errors
If you get import errors, ensure you're using the V3 version:
```python
# This should import from indexed_pixel_editor_v3.py
from indexed_pixel_editor_v3 import IndexedPixelEditor
```

### Missing Methods
All legacy methods are supported via the compatibility layer. If something is missing, check:
1. The method exists in the legacy version
2. It's been added to the compatibility section in V3

### Test Failures
Tests written for the legacy version should pass. If not:
1. Check the test isn't accessing internal implementation details
2. Verify the compatibility layer covers the required API

## Summary

The V3 refactoring transforms the pixel editor from a legacy monolith to a modern, maintainable application while preserving full backward compatibility. Existing code continues to work, while new development benefits from the clean architecture.