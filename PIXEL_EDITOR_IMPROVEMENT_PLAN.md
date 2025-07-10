# Pixel Editor Improvement Plan

## Phase 1: Critical Performance & UI Responsiveness (Week 1)

### 1.1 Fix UI Blocking (Highest Priority)
**Problem**: File operations freeze the UI
**Solution**: Implement worker threads for all file I/O

- Create `PixelEditorWorkers` module with:
  - `FileLoadWorker` - async image loading with progress signals
  - `FileSaveWorker` - async saving with progress
  - `PaletteLoadWorker` - async palette file loading
- Add progress dialogs for operations > 100ms
- Keep UI responsive during all operations

### 1.2 Optimize Canvas Rendering
**Problem**: Entire canvas redraws on every pixel change
**Solution**: Implement smart rendering with caching

- Add viewport culling - only draw visible pixels when zoomed
- Pre-cache QColor objects for all 16 palette colors
- Implement dirty rectangle tracking for partial updates
- Cache rendered tiles at common zoom levels (1x, 2x, 4x, 8x)
- Use QPainter.drawImage() instead of individual fillRect calls

### 1.3 Fix Memory-Hungry Undo System
**Problem**: Stores 50 full image copies
**Solution**: Delta-based undo system

- Store only changed regions, not full images
- Implement `UndoCommand` classes:
  - `DrawPixelCommand` - stores single pixel change
  - `FloodFillCommand` - stores affected region
  - `DrawLineCommand` - stores line pixels
- Compress older undo states
- Limit memory usage, not just count

## Phase 2: Architecture Refactoring (Week 2)

### 2.1 Extract Model Layer
**Problem**: 1660-line main class doing everything
**Solution**: Proper separation of concerns

Create new modules:
- `pixel_image_model.py` - Image data and operations
- `pixel_editor_tools.py` - Tool system with Strategy pattern
- `pixel_editor_utils.py` - Common utilities (debug, colors)
- `pixel_editor_constants.py` - All magic numbers as constants

Refactor `IndexedPixelEditor` to delegate to:
- `ImageModel` - handles image data
- `ToolManager` - manages drawing tools
- `PaletteManager` - handles palette operations
- `FileManager` - file I/O operations

### 2.2 Implement Proper Tool System
**Problem**: Tools handled with string comparisons
**Solution**: Strategy pattern for tools

```python
class Tool(ABC):
    @abstractmethod
    def on_mouse_press(self, x: int, y: int): ...
    @abstractmethod
    def on_mouse_move(self, x: int, y: int): ...

class PencilTool(Tool): ...
class FillTool(Tool): ...
class ColorPickerTool(Tool): ...
```

### 2.3 Fix Widget Coupling
**Problem**: Direct widget references and tight coupling
**Solution**: Use signals/slots properly

- Remove `editor_parent` references
- Use proper Qt parent-child relationships
- Communicate via signals only
- Create `PixelEditorSignals` class for centralized signals

## Phase 3: Code Quality & Maintainability (Week 3)

### 3.1 Add Comprehensive Type Hints
- Create `pixel_editor_types.py` with type aliases
- Add all missing `-> None` annotations
- Use `TypedDict` for settings and metadata
- Fix mypy errors to enable strict checking

### 3.2 Improve Error Handling
- Replace generic `Exception` with specific types
- Add validation for image dimensions (max 1024x1024)
- Protect all event handlers with try/except
- Add graceful degradation for corrupted files

### 3.3 Define Constants & Remove Magic Numbers
```python
# pixel_editor_constants.py
MAX_COLORS = 16
BITS_PER_PIXEL = 4
DEFAULT_ZOOM = 4
MAX_ZOOM = 64
PALETTE_CELL_SIZE = 32
UNDO_STACK_SIZE = 50
MAX_IMAGE_DIMENSION = 1024
GRAYSCALE_STEP = 17  # 255 / 15
```

### 3.4 Refactor Complex Methods
Break down methods > 50 lines:
- `_check_and_offer_palette_loading()` → 3-4 focused methods
- `paintEvent()` → separate grid, pixels, and overlay drawing
- `load_file_by_path()` → separate validation, loading, and setup

## Phase 4: Testing & Documentation

### 4.1 Add Missing Tests
- Edge cases (0x0 images, corrupted files)
- Performance benchmarks for large images
- Error recovery scenarios
- Integration tests for complete workflows

### 4.2 Create Documentation
- User guide with screenshots
- Architecture overview diagram
- API documentation for modules
- Common workflows and tips

## Implementation Order

### Week 1: Performance Critical
1. Implement worker threads (2 days)
2. Optimize canvas rendering (2 days)  
3. Create delta undo system (1 day)

### Week 2: Architecture
1. Extract model layer (2 days)
2. Implement tool system (1 day)
3. Refactor main class (2 days)

### Week 3: Quality
1. Add type hints (1 day)
2. Improve error handling (1 day)
3. Constants & refactoring (1 day)
4. Testing & documentation (2 days)

## Expected Benefits

- **50-70% performance improvement** for large images
- **Zero UI freezing** during file operations
- **90% memory reduction** for undo system
- **Maintainable codebase** with clear separation
- **Better developer experience** with types and docs

## Files to Archive

Keep archiving pattern as requested:
- Move old implementations to `archive/pixel_editor/`
- Keep commit history for reference
- Archive after each major refactoring phase