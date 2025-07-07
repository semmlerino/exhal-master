# Legacy Archive

This directory contains the original pre-refactoring implementation of the sprite editor.

## Contents

- `sprite_editor_gui.py` - Original monolithic GUI implementation (1211 lines)
- `sprite_editor_gui.py` (launcher) - Simple launcher that imported the GUI
- `manual_tests/` - Manual test scripts that were mixed with production code
  - `test_multi_palette.py` - Manual palette testing script
  - `test_multi_palette_gui.py` - GUI testing script
  - `sprite_workflow_demo.py` - Workflow demonstration script

## Migration Notes

The new refactored implementation uses MVC architecture with:
- Proper separation of concerns
- Observable properties for data binding
- Dependency injection pattern
- Modular component structure

To use the new implementation, run:
```bash
python run_sprite_editor.py
```

The refactored code maintains 100% feature parity with the legacy implementation.