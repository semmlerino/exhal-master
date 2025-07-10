# Delta-Based Undo System Design

## Executive Summary

This document outlines the design for replacing the current memory-intensive undo/redo system in `pixel_editor_widgets.py` with a delta-based Command pattern implementation. The current system stores full image copies (using `deque` with `maxlen=50`), which is extremely memory-hungry for large sprite sheets.

## Current System Analysis

### Memory Usage Problem

The current implementation in `PixelCanvas`:
```python
# Lines 388-389: Undo/redo system
self.undo_stack = deque(maxlen=50)
self.redo_stack = deque(maxlen=50)

# Line 528: Save full image copy
self.undo_stack.append(self.image_data.copy())
```

**Memory calculation for current system:**
- Typical sprite sheet: 256x256 pixels
- Each pixel: 1 byte (uint8 for 4bpp indexed color)
- Full image copy: 256 × 256 × 1 = 65,536 bytes (64 KB)
- Maximum undo stack: 50 × 64 KB = 3.2 MB
- Maximum redo stack: 50 × 64 KB = 3.2 MB
- **Total: ~6.4 MB for undo/redo alone**

For larger sheets (512x512): ~25.6 MB total!

## Delta-Based Design

### Core Architecture

```
┌─────────────────────┐
│   UndoManager       │
├─────────────────────┤
│ - command_stack     │
│ - current_index     │
│ - max_commands      │
│ - compression_age   │
├─────────────────────┤
│ + execute_command() │
│ + undo()           │
│ + redo()           │
│ + compress_old()    │
└─────────────────────┘
          │
          │ manages
          ▼
┌─────────────────────┐
│   UndoCommand       │ (Abstract Base)
├─────────────────────┤
│ - timestamp        │
│ - compressed       │
├─────────────────────┤
│ + execute()        │
│ + undo()           │
│ + get_memory_size()│
│ + compress()       │
│ + decompress()     │
└─────────────────────┘
          △
          │ inherits
          │
    ┌─────┴─────┬──────────┬──────────┐
    │           │          │          │
┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐
│DrawPixel│ │DrawLine│ │FloodFill│ │BatchCmd│
└─────────┘ └─────────┘ └─────────┘ └─────────┘
```

### Base Command Class

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Any
import zlib
import pickle
from datetime import datetime

class UndoCommand(ABC):
    """Abstract base class for all undo commands"""
    
    def __init__(self):
        self.timestamp = datetime.now()
        self.compressed = False
        self._compressed_data: Optional[bytes] = None
    
    @abstractmethod
    def execute(self, canvas: 'PixelCanvas') -> None:
        """Apply this command to the canvas"""
        pass
    
    @abstractmethod
    def undo(self, canvas: 'PixelCanvas') -> None:
        """Revert this command on the canvas"""
        pass
    
    @abstractmethod
    def get_memory_size(self) -> int:
        """Return approximate memory usage in bytes"""
        pass
    
    def compress(self) -> None:
        """Compress command data for long-term storage"""
        if not self.compressed:
            data = self._get_compress_data()
            self._compressed_data = zlib.compress(pickle.dumps(data))
            self._clear_uncompressed_data()
            self.compressed = True
    
    def decompress(self) -> None:
        """Decompress command data for execution"""
        if self.compressed and self._compressed_data:
            data = pickle.loads(zlib.decompress(self._compressed_data))
            self._restore_from_compressed(data)
            self._compressed_data = None
            self.compressed = False
    
    @abstractmethod
    def _get_compress_data(self) -> Any:
        """Get data to be compressed"""
        pass
    
    @abstractmethod
    def _clear_uncompressed_data(self) -> None:
        """Clear uncompressed data after compression"""
        pass
    
    @abstractmethod
    def _restore_from_compressed(self, data: Any) -> None:
        """Restore state from compressed data"""
        pass
```

### Specific Command Implementations

#### DrawPixelCommand

```python
@dataclass
class DrawPixelCommand(UndoCommand):
    """Command for single pixel changes"""
    x: int
    y: int
    old_color: int
    new_color: int
    
    def execute(self, canvas: 'PixelCanvas') -> None:
        if 0 <= self.x < canvas.image_data.shape[1] and \
           0 <= self.y < canvas.image_data.shape[0]:
            canvas.image_data[self.y, self.x] = self.new_color
    
    def undo(self, canvas: 'PixelCanvas') -> None:
        if 0 <= self.x < canvas.image_data.shape[1] and \
           0 <= self.y < canvas.image_data.shape[0]:
            canvas.image_data[self.y, self.x] = self.old_color
    
    def get_memory_size(self) -> int:
        # 4 ints (x, y, old_color, new_color) + overhead
        return 4 * 4 + 64  # ~80 bytes
    
    def _get_compress_data(self) -> tuple:
        return (self.x, self.y, self.old_color, self.new_color)
    
    def _clear_uncompressed_data(self) -> None:
        # No need to clear primitive types
        pass
    
    def _restore_from_compressed(self, data: tuple) -> None:
        self.x, self.y, self.old_color, self.new_color = data
```

#### DrawLineCommand

```python
@dataclass
class DrawLineCommand(UndoCommand):
    """Command for line drawing (stores affected pixels)"""
    pixels: list[tuple[int, int, int]]  # [(x, y, old_color), ...]
    new_color: int
    
    def execute(self, canvas: 'PixelCanvas') -> None:
        for x, y, _ in self.pixels:
            if 0 <= x < canvas.image_data.shape[1] and \
               0 <= y < canvas.image_data.shape[0]:
                canvas.image_data[y, x] = self.new_color
    
    def undo(self, canvas: 'PixelCanvas') -> None:
        for x, y, old_color in self.pixels:
            if 0 <= x < canvas.image_data.shape[1] and \
               0 <= y < canvas.image_data.shape[0]:
                canvas.image_data[y, x] = old_color
    
    def get_memory_size(self) -> int:
        # Each pixel: 3 ints (12 bytes) + list overhead
        return len(self.pixels) * 12 + 64
    
    def _get_compress_data(self) -> tuple:
        return (self.pixels, self.new_color)
    
    def _clear_uncompressed_data(self) -> None:
        self.pixels = []
    
    def _restore_from_compressed(self, data: tuple) -> None:
        self.pixels, self.new_color = data
```

#### FloodFillCommand

```python
@dataclass
class FloodFillCommand(UndoCommand):
    """Command for flood fill operations"""
    # For efficiency, we store a sparse representation
    affected_region: tuple[int, int, int, int]  # x, y, width, height
    old_data: np.ndarray  # Only the affected region
    new_color: int
    
    def execute(self, canvas: 'PixelCanvas') -> None:
        x, y, w, h = self.affected_region
        # Fill the region with new color where old data matches
        for dy in range(h):
            for dx in range(w):
                if 0 <= x+dx < canvas.image_data.shape[1] and \
                   0 <= y+dy < canvas.image_data.shape[0]:
                    if self.old_data[dy, dx] != 255:  # 255 = not affected
                        canvas.image_data[y+dy, x+dx] = self.new_color
    
    def undo(self, canvas: 'PixelCanvas') -> None:
        x, y, w, h = self.affected_region
        # Restore old data
        for dy in range(h):
            for dx in range(w):
                if 0 <= x+dx < canvas.image_data.shape[1] and \
                   0 <= y+dy < canvas.image_data.shape[0]:
                    if self.old_data[dy, dx] != 255:
                        canvas.image_data[y+dy, x+dx] = self.old_data[dy, dx]
    
    def get_memory_size(self) -> int:
        if self.compressed:
            return len(self._compressed_data) if self._compressed_data else 0
        return self.old_data.nbytes + 64
    
    def _get_compress_data(self) -> tuple:
        return (self.affected_region, self.old_data, self.new_color)
    
    def _clear_uncompressed_data(self) -> None:
        self.old_data = None
    
    def _restore_from_compressed(self, data: tuple) -> None:
        self.affected_region, self.old_data, self.new_color = data
```

#### BatchCommand

```python
class BatchCommand(UndoCommand):
    """Groups multiple commands executed together (e.g., continuous drawing)"""
    
    def __init__(self, commands: list[UndoCommand]):
        super().__init__()
        self.commands = commands
    
    def execute(self, canvas: 'PixelCanvas') -> None:
        for cmd in self.commands:
            cmd.execute(canvas)
    
    def undo(self, canvas: 'PixelCanvas') -> None:
        # Undo in reverse order
        for cmd in reversed(self.commands):
            cmd.undo(canvas)
    
    def get_memory_size(self) -> int:
        return sum(cmd.get_memory_size() for cmd in self.commands) + 64
    
    def compress(self) -> None:
        # Compress individual commands
        for cmd in self.commands:
            cmd.compress()
        super().compress()
    
    def _get_compress_data(self) -> list:
        return self.commands
    
    def _clear_uncompressed_data(self) -> None:
        # Commands are already compressed individually
        pass
    
    def _restore_from_compressed(self, data: list) -> None:
        self.commands = data
```

### UndoManager Implementation

```python
class UndoManager:
    """Manages undo/redo operations with automatic compression"""
    
    def __init__(self, max_commands: int = 100, compression_age: int = 20):
        self.command_stack: list[UndoCommand] = []
        self.current_index: int = -1
        self.max_commands = max_commands
        self.compression_age = compression_age  # Compress commands older than this
    
    def execute_command(self, command: UndoCommand, canvas: 'PixelCanvas') -> None:
        """Execute a new command and add to history"""
        # Remove any commands after current index (redo stack)
        if self.current_index < len(self.command_stack) - 1:
            self.command_stack = self.command_stack[:self.current_index + 1]
        
        # Execute the command
        command.execute(canvas)
        
        # Add to stack
        self.command_stack.append(command)
        self.current_index += 1
        
        # Enforce maximum size
        if len(self.command_stack) > self.max_commands:
            self.command_stack.pop(0)
            self.current_index -= 1
        
        # Compress old commands
        self._compress_old_commands()
    
    def undo(self, canvas: 'PixelCanvas') -> bool:
        """Undo the last command"""
        if self.current_index >= 0:
            command = self.command_stack[self.current_index]
            
            # Decompress if needed
            if command.compressed:
                command.decompress()
            
            command.undo(canvas)
            self.current_index -= 1
            return True
        return False
    
    def redo(self, canvas: 'PixelCanvas') -> bool:
        """Redo the next command"""
        if self.current_index < len(self.command_stack) - 1:
            self.current_index += 1
            command = self.command_stack[self.current_index]
            
            # Decompress if needed
            if command.compressed:
                command.decompress()
            
            command.execute(canvas)
            return True
        return False
    
    def _compress_old_commands(self) -> None:
        """Compress commands older than compression_age"""
        compress_before = max(0, self.current_index - self.compression_age)
        
        for i in range(compress_before):
            if not self.command_stack[i].compressed:
                self.command_stack[i].compress()
    
    def get_memory_usage(self) -> dict:
        """Get current memory usage statistics"""
        total = sum(cmd.get_memory_size() for cmd in self.command_stack)
        compressed = sum(1 for cmd in self.command_stack if cmd.compressed)
        
        return {
            'total_bytes': total,
            'total_mb': total / (1024 * 1024),
            'command_count': len(self.command_stack),
            'compressed_count': compressed,
            'current_index': self.current_index
        }
```

## Integration Plan

### Phase 1: Add New System Alongside Existing

1. Create new file `delta_undo_system.py` with all command classes
2. Add `UndoManager` instance to `PixelCanvas`
3. Keep existing undo system temporarily for fallback

### Phase 2: Modify Canvas Methods

Update drawing methods to create and execute commands:

```python
# In PixelCanvas class

def __init__(self, palette_widget=None):
    # ... existing code ...
    
    # New delta-based undo system
    self.undo_manager = UndoManager(max_commands=100)
    
    # Keep old system temporarily
    self.undo_stack_legacy = deque(maxlen=50)
    self.redo_stack_legacy = deque(maxlen=50)

def draw_pixel(self, x: int, y: int):
    """Draw a single pixel using command pattern"""
    if self.image_data is None:
        return
    
    height, width = self.image_data.shape
    if 0 <= x < width and 0 <= y < height:
        old_color = int(self.image_data[y, x])
        new_color = max(0, min(15, int(self.current_color)))
        
        if old_color != new_color:
            cmd = DrawPixelCommand(x, y, old_color, new_color)
            self.undo_manager.execute_command(cmd, self)
            
            self.update()
            self.pixelChanged.emit()

def draw_line(self, x0: int, y0: int, x1: int, y1: int):
    """Draw a line using command pattern"""
    # Collect all affected pixels first
    pixels = []
    
    # Bresenham's algorithm to collect pixels
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    
    x, y = x0, y0
    while True:
        if 0 <= x < self.image_data.shape[1] and \
           0 <= y < self.image_data.shape[0]:
            old_color = int(self.image_data[y, x])
            pixels.append((x, y, old_color))
        
        if x == x1 and y == y1:
            break
        
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    
    if pixels:
        new_color = max(0, min(15, int(self.current_color)))
        cmd = DrawLineCommand(pixels, new_color)
        self.undo_manager.execute_command(cmd, self)
        
        self.update()
        self.pixelChanged.emit()

def undo(self):
    """Undo last operation using new system"""
    if self.undo_manager.undo(self):
        self.update()
        self.pixelChanged.emit()

def redo(self):
    """Redo last undone operation using new system"""
    if self.undo_manager.redo(self):
        self.update()
        self.pixelChanged.emit()
```

### Phase 3: Optimize Mouse Movement

For continuous drawing, batch pixels into single command:

```python
def mousePressEvent(self, event: QMouseEvent):
    if event.button() == Qt.MouseButton.LeftButton:
        self.drawing = True
        # Start collecting pixels for batch command
        self.current_stroke_pixels = []
        
        pos = self.get_pixel_pos(event.position())
        if pos:
            if self.tool == "pencil":
                # Collect pixel instead of drawing directly
                self._collect_pixel(pos.x(), pos.y())
            # ... other tools ...

def mouseReleaseEvent(self, event: QMouseEvent):
    if event.button() == Qt.MouseButton.LeftButton:
        self.drawing = False
        # Create batch command for all collected pixels
        if self.current_stroke_pixels:
            new_color = max(0, min(15, int(self.current_color)))
            cmd = DrawLineCommand(self.current_stroke_pixels, new_color)
            self.undo_manager.execute_command(cmd, self)
            self.current_stroke_pixels = []
        self.last_point = None
```

## Memory Usage Comparison

### Example: 256x256 sprite sheet, typical editing session

**Current System:**
- 50 undo states × 64 KB = 3.2 MB
- 50 redo states × 64 KB = 3.2 MB
- **Total: 6.4 MB**

**Delta-Based System:**
- Single pixel edit: ~80 bytes
- 10-pixel line: ~200 bytes
- 100-pixel flood fill (compressed): ~500 bytes
- Average command: ~150 bytes
- 100 commands × 150 bytes = 15 KB
- With compression overhead: ~20 KB
- **Total: 0.02 MB (320x reduction!)**

### Worst Case: Large flood fills

Even with large flood fills affecting 10,000 pixels:
- Uncompressed: 10,000 × 1 byte = 10 KB
- Compressed (zlib): ~2-3 KB
- Still much better than 64 KB full image copy

## Additional Optimizations

### 1. Smart Batching
- Combine rapid pixel edits within same area
- Merge adjacent single-pixel commands
- Coalesce flood fills that overlap

### 2. Adaptive Compression
- Compress based on command age AND size
- Keep frequently accessed commands uncompressed
- Use RLE for flood fill regions

### 3. Memory Limits
- Set total memory budget (e.g., 1 MB)
- Remove oldest commands when exceeded
- Show warning when approaching limit

### 4. Persistence
- Serialize command history to disk
- Enable "unlimited" undo with disk backing
- Save/restore undo history with project

## Testing Strategy

1. **Unit Tests**: Each command type
2. **Integration Tests**: UndoManager with canvas
3. **Performance Tests**: Memory usage under various scenarios
4. **Stress Tests**: Rapid operations, large images
5. **Compatibility Tests**: Ensure existing functionality preserved

## Migration Timeline

1. **Week 1**: Implement command classes and UndoManager
2. **Week 2**: Integrate with canvas, maintain dual systems
3. **Week 3**: Testing and optimization
4. **Week 4**: Remove legacy system, final testing

## Conclusion

The delta-based undo system will provide:
- **320x+ memory reduction** for typical usage
- **Better scalability** for large images
- **Unlimited undo** potential with disk backing
- **Faster operations** due to smaller data movement
- **Foundation for advanced features** (undo history visualization, selective undo)

This design maintains full compatibility while dramatically improving resource efficiency.