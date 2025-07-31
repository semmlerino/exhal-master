# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Widget Initialization Pattern

**IMPORTANT**: Always follow this initialization order in `__init__` methods to avoid bugs:

1. **Declare ALL instance variables with type hints FIRST**
2. **Call super().__init__() second**  
3. **Call setup methods (_setup_ui, etc) AFTER variable declaration**
4. **NEVER assign instance variables to None after setup methods**

### ❌ Bad Pattern (causes AttributeError)
```python
def __init__(self):
    super().__init__()
    self._setup_ui()  # Creates self.widget = QWidget()
    
    # BUG: This overwrites the widget with None!
    self.widget: QWidget | None = None
```

### ✅ Good Pattern
```python
def __init__(self):
    # Step 1: Declare instance variables
    self.widget: QWidget | None = None
    self.data: list[str] = []
    
    # Step 2: Initialize parent
    super().__init__()
    
    # Step 3: Setup methods that create widgets
    self._setup_ui()  # Now safely creates self.widget = QWidget()
```

This prevents the common bug where widgets are created in setup methods but then overwritten with None due to late instance variable declarations.

## Commands

### Development Environment

#### Virtual Environment Setup
```bash
# Set up virtual environment (from exhal-master directory)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install PyQt6 Pillow pytest pytest-qt ruff pyright

# Verify virtual environment is active
which python              # Should show venv/bin/python (Linux/macOS)
# OR
where python              # Should show venv\Scripts\python.exe (Windows)
```

#### Running Commands
**IMPORTANT**: Always activate the virtual environment before running any commands:
```bash
# Activate venv first
source venv/bin/activate  # Linux/macOS
# OR  
venv\Scripts\activate     # Windows

# Then run SpritePal
python launch_spritepal.py

# Run tests (from spritepal directory)
pytest tests/ -m "not gui"              # Run non-GUI tests only (headless)
pytest tests/ -x                         # Run all tests, stop on first failure
pytest tests/test_extractor.py -v       # Run specific test file
pytest -k "test_palette"                 # Run tests matching keyword

# Linting and Type Checking
source venv/bin/activate                 # Activate virtual environment first (REQUIRED)
ruff check .                             # Check for linting issues
ruff check . --fix --unsafe-fixes        # Auto-fix linting issues
.venv/bin/basedpyright                   # Type check with basedpyright (installed in venv)

# Type Checking Analysis Tools
python scripts/show_critical_errors.py   # Quick view of critical type errors
python scripts/typecheck_analysis.py     # Comprehensive type error analysis
python scripts/typecheck_analysis.py --critical   # Show only critical errors
python scripts/typecheck_analysis.py --save       # Save analysis report to JSON

# IMPORTANT: Always run linting tools from virtual environment
# - ruff and basedpyright are installed in venv/, not globally
# - Commands will fail with "command not found" without venv activation
# - Install linting tools: pip install ruff basedpyright
# - basedpyright must be run with full path: .venv/bin/basedpyright

# Test Coverage
pytest tests/ --cov=core --cov=ui --cov=utils    # Run tests with coverage
coverage report                                   # View coverage report
coverage html                                     # Generate HTML coverage report
```

#### Deactivating Virtual Environment
```bash
deactivate                               # Return to system Python
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

### Development Tools

#### Type Checking Analysis Scripts
SpritePal includes development scripts for analyzing type checking results:

**Quick Critical Errors View:**
```bash
python scripts/show_critical_errors.py
```
Shows only the most critical basedpyright errors that should be fixed first:
- General type issues
- Missing type arguments  
- Import cycles
- Argument/assignment type errors

**Comprehensive Type Analysis:**
```bash
python scripts/typecheck_analysis.py [options]

# Examples:
python scripts/typecheck_analysis.py               # Full analysis
python scripts/typecheck_analysis.py --critical    # Critical errors only
python scripts/typecheck_analysis.py --save        # Save JSON report
python scripts/typecheck_analysis.py --limit 10    # Limit errors shown
python scripts/typecheck_analysis.py core/*.py     # Check specific files
```

Features:
- Groups errors by type with counts
- Shows files with most errors
- Prioritizes critical issues
- Can save JSON reports for tracking progress
- Provides actionable summaries

These tools help maintain code quality by making it easier to identify and fix the most important type issues.

## Architecture

### SpritePal Overview
SpritePal is a PyQt6 application for extracting SNES sprites from memory dumps with automatic palette association. It's part of the Kirby Super Star sprite editing toolkit.

### Core Components

**Manager-Based Architecture:**
- **Business Logic**: Centralized in `core/managers/` (ExtractionManager, InjectionManager, SessionManager)
- **View**: PyQt6 UI components in `ui/` (main_window.py, preview widgets) - presentation only
- **Controller**: Thin coordination layer in `core/controller.py` - delegates to managers
- **Core**: Low-level extraction/injection classes in `core/` (used by managers)

**Manager Classes:**
- `ExtractionManager`: Handles all extraction workflows (VRAM/ROM), validation, and preview generation
- `InjectionManager`: Manages all injection operations (VRAM/ROM) with unified interface
- `SessionManager`: Handles application state, settings persistence, and session management
- `ManagerRegistry`: Singleton registry providing global access to manager instances

**UI Components:**
- `MainWindow`: Primary UI - delegates to controller, no business logic
- `ROMExtractionPanel`: ROM selection UI - uses ExtractionManager via registry
- `InjectionDialog`: Injection configuration - uses managers for validation
- Workers: QThread wrappers that delegate to managers for actual operations

### Data Flow
1. User interacts with UI (drag-drop files, configure extraction/injection)
2. UI delegates to `Controller` for workflow coordination
3. `Controller` uses `ExtractionManager` or `InjectionManager` for business logic:
   - Manager validates parameters and handles errors
   - Manager creates worker threads with proper configuration
   - Manager coordinates low-level core classes (SpriteExtractor, ROMExtractor, etc.)
4. Workers emit signals to managers, managers emit signals to controller/UI
5. UI updates presentation based on manager signals (progress, preview, completion)
6. `SessionManager` handles state persistence and settings throughout the process

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

### Architecture Patterns

#### Manager Pattern (2025 Refactoring)
- **Business Logic Separation**: All business logic moved from UI components to dedicated manager classes
- **Centralized Validation**: Parameter validation and error handling consolidated in managers
- **Unified Interfaces**: Managers provide consistent APIs for UI components
- **Registry Access**: Global singleton registry provides access to manager instances

#### Clean Architecture Benefits
- **Testability**: Business logic can be unit tested independently of UI
- **Maintainability**: Changes to business rules don't require UI modifications  
- **Reusability**: Manager logic can be reused across different UI components
- **Type Safety**: Strong typing and validation at the manager layer

#### Legacy Pattern Support
- **ROM Extraction UI**: Modular widget architecture in `ui/rom_extraction/`
- **Error Handling**: Centralized exception hierarchy in `core/managers/exceptions.py`
- **Thread Safety**: Manager operations are thread-safe with proper locking

### ROM Cache System

#### Overview
SpritePal includes a high-performance ROM caching system that dramatically speeds up repeated sprite scans. The cache stores scan results in a SQLite database, eliminating the need to re-scan ROMs for the same parameters.

#### Key Features
- **Automatic Cache Detection**: When loading a ROM, SpritePal automatically checks for cached scan results
- **Resume Partial Scans**: If a scan was interrupted, SpritePal offers to resume from where it left off
- **Visual Indicators**: Cache status is shown throughout the UI:
  - ROM file widget shows cache status badges
  - Scan dialog displays cache hit/miss status
  - Sprite selector indicates cached vs fresh results
  - Manual offset dialog shows when using cached data

#### Cache Operations
- **Automatic Saving**: Scan results are automatically cached after completion
- **Smart Invalidation**: Cache entries are invalidated when ROM modification time changes
- **Clear Cache**: Available through the Settings dialog to free up disk space
- **Performance**: Typical cache hits reduce load time from minutes to milliseconds

#### Technical Details
- **Storage**: SQLite database at `~/.cache/spritepal/rom_cache.db`
- **Key Components**:
  - `utils/rom_cache.py`: Core cache implementation with thread-safe singleton
  - `ui/dialogs/resume_scan_dialog.py`: UI for resuming partial scans
  - Cache integration in `ExtractionManager` and UI components
- **Cache Keys**: Based on ROM path, scan parameters, and file modification time