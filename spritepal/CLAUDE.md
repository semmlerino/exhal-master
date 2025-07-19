# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Environment
```bash
# Set up virtual environment (from exhal-master directory)
python3 -m venv venv
source venv/bin/activate
pip install PyQt6 Pillow pytest pytest-qt

# Run SpritePal
python launch_spritepal.py

# Run tests (from spritepal directory)
pytest tests/ -m "not gui"              # Run non-GUI tests only (headless)
pytest tests/ -x                         # Run all tests, stop on first failure
pytest tests/test_extractor.py -v       # Run specific test file
pytest -k "test_palette"                 # Run tests matching keyword

# Linting
ruff check .                             # Check for linting issues
ruff check . --fix --unsafe-fixes        # Auto-fix linting issues
```

### Type Checking
```bash
mypy spritepal/                          # Type check all code
mypy spritepal/core/palette_manager.py  # Type check specific file
```

### Testing with Virtual Display
```bash
# Install system dependencies (Linux)
sudo ./install_test_deps.sh

# Run with automatic Xvfb (recommended)
python run_tests_xvfb.py

# Run without virtual display (unit tests only)
pytest tests/ --no-xvfb -m "not gui"

# Run mock-based tests (works anywhere)
pytest tests/test_integration_mock.py
```

## Architecture

### SpritePal Overview
SpritePal is a PyQt6 application for extracting SNES sprites from memory dumps with automatic palette association. It's part of the Kirby Super Star sprite editing toolkit.

### Core Components

**MVC Architecture:**
- **Model**: Core extraction logic in `core/` (extractor.py, palette_manager.py)
- **View**: PyQt6 UI components in `ui/` (main_window.py, preview widgets)
- **Controller**: Workflow coordination in `core/controller.py`

**Key Classes:**
- `SpriteExtractor`: Handles VRAM sprite extraction to grayscale PNG
- `PaletteManager`: Manages CGRAM palette extraction and JSON generation
- `ExtractionWorker`: QThread for non-blocking extraction process
- `MainWindow`: Primary UI with drag-drop zones and preview panels

### Data Flow
1. User drops VRAM/CGRAM/OAM dump files onto UI
2. `ExtractionController` validates inputs and creates worker thread
3. `ExtractionWorker` runs extraction process:
   - Extract sprites from VRAM → grayscale PNG
   - Extract palettes from CGRAM → palette JSON files
   - Analyze OAM for active palette highlighting
4. Worker emits signals for UI updates (progress, preview, completion)
5. Generated files ready for pixel editor integration

### File Formats
- **Input**: SNES memory dumps (.dmp files)
  - VRAM: 64KB sprite graphics at offset 0xC000
  - CGRAM: 512 bytes palette data (256 colors in BGR555)
  - OAM: 544 bytes sprite attribute data
- **Output**: 
  - Indexed PNG (grayscale preserving pixel indices)
  - .pal.json files (RGB888 palette data for pixel editor)
  - .metadata.json (palette switching configuration)

### Testing Strategy
- **Unit tests**: Core logic (extractor, palette manager) - no GUI required
- **Integration tests**: Workflow scenarios with real Qt components using pytest-xvfb
- **Mock tests**: GUI component testing using mocks for any environment 
- **GUI tests**: Full application testing with virtual display (Xvfb) or offscreen backend
- **CI/CD**: Automatic virtual display setup with comprehensive platform coverage

### Key Constants (utils/constants.py)
- `VRAM_SPRITE_OFFSET`: 0xC000 (sprite data location in VRAM)
- `SPRITE_PALETTE_START/END`: 8-15 (sprite palette indices)
- `COLORS_PER_PALETTE`: 16
- `BYTES_PER_TILE`: 32 (4bpp format)

### HAL Compression Tools
- **Location**: Pre-built HAL tools (exhal/inhal) are available in `../archive/obsolete_test_images/ultrathink/`
- **Status**: Tools are automatically discovered and working for ROM injection functionality
- **Usage**: Integrated into SpritePal's ROM injection workflow for compressed sprite data

### Session Persistence
Settings saved to `.spritepal_settings.json` include:
- Last loaded file paths
- Window geometry
- Output preferences

### Integration Points
- Pixel editor launcher in `controller.py`
- Auto-loading palette files by matching names
- Metadata for advanced palette features