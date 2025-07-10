# Canvas Optimization Design for PixelCanvas.paintEvent

## Current Implementation Analysis

### Performance Bottlenecks Identified

1. **Full Canvas Redraw on Every Update**
   - Lines 630-640: Every pixel in the image is drawn regardless of visibility
   - No viewport culling - pixels outside the visible area are still processed
   - Inefficient for large images or high zoom levels

2. **QColor Object Creation Per Pixel**
   - Line 634: `color = QColor(*colors[pixel_index])` creates a new QColor for every pixel
   - For a 256x256 image, this creates 65,536 QColor objects per paint event
   - QColor construction is relatively expensive

3. **No Caching of Rendered Tiles**
   - Each paint event recalculates and redraws everything from scratch
   - Common zoom levels (1x, 2x, 4x, 8x) could benefit from pre-rendered tiles

4. **Inefficient Grid Drawing**
   - Lines 647-652: Grid lines are drawn individually
   - Could be optimized with QPainter path or cached grid pattern

5. **No Dirty Rectangle Tracking**
   - Entire canvas updates even when only one pixel changes
   - Mouse hover causes full redraw (line 704)

## Optimization Strategies

### 1. Viewport Culling Algorithm

Calculate visible pixel range based on scroll position and widget size:

```python
def get_visible_pixel_range(self):
    """Calculate which pixels are visible in the current viewport"""
    if self.image_data is None:
        return None
    
    # Get the parent scroll area's viewport
    scroll_area = self.parent()
    if not scroll_area:
        return None
        
    viewport = scroll_area.viewport()
    viewport_rect = viewport.rect()
    
    # Convert viewport coordinates to canvas coordinates
    # Account for pan offset
    canvas_rect = self.mapFromParent(viewport_rect.topLeft())
    
    # Calculate pixel boundaries
    left = max(0, int((canvas_rect.x() - self.pan_offset.x()) // self.zoom))
    top = max(0, int((canvas_rect.y() - self.pan_offset.y()) // self.zoom))
    
    # Add 1 pixel border for safety
    right = min(self.image_data.shape[1], 
                int((canvas_rect.x() + viewport_rect.width() - self.pan_offset.x()) // self.zoom) + 2)
    bottom = min(self.image_data.shape[0], 
                 int((canvas_rect.y() + viewport_rect.height() - self.pan_offset.y()) // self.zoom) + 2)
    
    return (left, top, right, bottom)
```

### 2. QColor Caching System

Pre-create QColor objects for all 16 palette colors:

```python
class PixelCanvas(QWidget):
    def __init__(self, palette_widget=None):
        # ... existing init code ...
        
        # Color caching
        self._qcolor_cache = {}
        self._palette_version = 0
        
    def _update_qcolor_cache(self):
        """Update cached QColor objects when palette changes"""
        self._qcolor_cache.clear()
        
        # Get current color palette
        if self.greyscale_mode:
            colors = [(i * 17, i * 17, i * 17) for i in range(16)]
        elif (self.editor_parent and 
              hasattr(self.editor_parent, 'external_palette_colors') and 
              self.editor_parent.external_palette_colors):
            colors = self.editor_parent.external_palette_colors
        elif self.palette_widget:
            colors = self.palette_widget.colors
        else:
            colors = [(i * 17, i * 17, i * 17) for i in range(16)]
        
        # Pre-create QColor objects
        for i, color in enumerate(colors[:16]):
            self._qcolor_cache[i] = QColor(*color)
        
        # Add magenta for invalid indices
        self._qcolor_cache[-1] = QColor(255, 0, 255)
        
        self._palette_version += 1
```

### 3. Dirty Rectangle Tracking

Track modified regions to enable partial updates:

```python
class PixelCanvas(QWidget):
    def __init__(self, palette_widget=None):
        # ... existing init code ...
        
        # Dirty rectangle tracking
        self._dirty_rect = None
        self._accumulate_dirty = False
        
    def mark_dirty(self, x, y, w=1, h=1):
        """Mark a region as needing redraw"""
        # Convert pixel coordinates to canvas coordinates
        canvas_x = int(x * self.zoom)
        canvas_y = int(y * self.zoom)
        canvas_w = int(w * self.zoom)
        canvas_h = int(h * self.zoom)
        
        dirty = QRect(canvas_x, canvas_y, canvas_w, canvas_h)
        
        if self._dirty_rect is None:
            self._dirty_rect = dirty
        else:
            self._dirty_rect = self._dirty_rect.united(dirty)
        
        # Schedule update for dirty region only
        self.update(self._dirty_rect)
    
    def draw_pixel(self, x: int, y: int):
        """Draw a single pixel with dirty tracking"""
        if self.image_data is None:
            return
            
        height, width = self.image_data.shape
        if 0 <= x < width and 0 <= y < height:
            color = max(0, min(15, int(self.current_color)))
            old_value = self.image_data[y, x]
            self.image_data[y, x] = np.uint8(color)
            
            # Mark only this pixel as dirty
            self.mark_dirty(x, y)
            self.pixelChanged.emit()
```

### 4. Tile Caching Strategy

Cache rendered tiles for common zoom levels:

```python
class TileCache:
    """Cache for pre-rendered image tiles"""
    
    def __init__(self, tile_size=32):
        self.tile_size = tile_size
        self.cache = {}  # (zoom, tile_x, tile_y, palette_version) -> QPixmap
        self.max_cache_size = 100  # Maximum tiles to cache
        
    def get_tile_key(self, zoom, tile_x, tile_y, palette_version):
        return (zoom, tile_x, tile_y, palette_version)
    
    def get_tile(self, zoom, tile_x, tile_y, palette_version):
        """Get cached tile or None if not cached"""
        key = self.get_tile_key(zoom, tile_x, tile_y, palette_version)
        return self.cache.get(key)
    
    def set_tile(self, zoom, tile_x, tile_y, palette_version, pixmap):
        """Cache a rendered tile"""
        key = self.get_tile_key(zoom, tile_x, tile_y, palette_version)
        
        # LRU eviction if cache is full
        if len(self.cache) >= self.max_cache_size:
            # Remove oldest entry (simple FIFO for now)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[key] = pixmap
    
    def invalidate_tile(self, tile_x, tile_y):
        """Remove all cached versions of a tile"""
        keys_to_remove = []
        for key in self.cache:
            if key[1] == tile_x and key[2] == tile_y:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.cache[key]
    
    def clear(self):
        """Clear entire cache"""
        self.cache.clear()
```

### 5. Optimized paintEvent Implementation

```python
def paintEvent(self, event):
    if self.image_data is None:
        return
    
    painter = QPainter(self)
    
    # Apply pan offset transform
    painter.translate(self.pan_offset)
    
    # Update color cache if needed
    if not self._qcolor_cache or self._needs_palette_update():
        self._update_qcolor_cache()
    
    height, width = self.image_data.shape
    
    # Get visible pixel range
    visible_range = self.get_visible_pixel_range()
    if not visible_range:
        # Fallback to full image if we can't determine visibility
        visible_range = (0, 0, width, height)
    
    left, top, right, bottom = visible_range
    
    # Use tile caching for common zoom levels
    if self.zoom in [1, 2, 4, 8, 16] and self.tile_cache_enabled:
        self._paint_with_tiles(painter, left, top, right, bottom)
    else:
        self._paint_pixels_direct(painter, left, top, right, bottom)
    
    # Draw grid only for visible area
    if self.grid_visible and self.zoom > 4:
        self._draw_grid_optimized(painter, left, top, right, bottom)
    
    # Draw hover highlight
    if self.hover_pos and not self.panning:
        painter.setPen(QPen(Qt.GlobalColor.white, 2))
        painter.drawRect(
            self.hover_pos.x() * self.zoom,
            self.hover_pos.y() * self.zoom,
            self.zoom,
            self.zoom,
        )
    
    # Clear dirty rect after painting
    self._dirty_rect = None

def _paint_pixels_direct(self, painter, left, top, right, bottom):
    """Direct pixel painting with viewport culling"""
    for y in range(top, bottom):
        for x in range(left, right):
            pixel_index = self.image_data[y, x]
            
            # Use cached QColor
            color = self._qcolor_cache.get(pixel_index, self._qcolor_cache[-1])
            
            painter.fillRect(
                x * self.zoom, y * self.zoom, self.zoom, self.zoom, color
            )

def _paint_with_tiles(self, painter, left, top, right, bottom):
    """Paint using cached tiles"""
    tile_size = self.tile_cache.tile_size
    
    # Calculate tile boundaries
    tile_left = left // tile_size
    tile_top = top // tile_size
    tile_right = (right + tile_size - 1) // tile_size
    tile_bottom = (bottom + tile_size - 1) // tile_size
    
    for tile_y in range(tile_top, tile_bottom):
        for tile_x in range(tile_left, tile_right):
            # Check cache first
            cached_tile = self.tile_cache.get_tile(
                self.zoom, tile_x, tile_y, self._palette_version
            )
            
            if cached_tile:
                # Draw cached tile
                painter.drawPixmap(
                    tile_x * tile_size * self.zoom,
                    tile_y * tile_size * self.zoom,
                    cached_tile
                )
            else:
                # Render and cache tile
                tile_pixmap = self._render_tile(tile_x, tile_y)
                self.tile_cache.set_tile(
                    self.zoom, tile_x, tile_y, self._palette_version, tile_pixmap
                )
                painter.drawPixmap(
                    tile_x * tile_size * self.zoom,
                    tile_y * tile_size * self.zoom,
                    tile_pixmap
                )

def _render_tile(self, tile_x, tile_y):
    """Render a single tile to QPixmap"""
    tile_size = self.tile_cache.tile_size
    pixmap = QPixmap(tile_size * self.zoom, tile_size * self.zoom)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    tile_painter = QPainter(pixmap)
    
    # Calculate pixel range for this tile
    start_x = tile_x * tile_size
    start_y = tile_y * tile_size
    end_x = min(start_x + tile_size, self.image_data.shape[1])
    end_y = min(start_y + tile_size, self.image_data.shape[0])
    
    # Draw pixels in tile
    for y in range(start_y, end_y):
        for x in range(start_x, end_x):
            pixel_index = self.image_data[y, x]
            color = self._qcolor_cache.get(pixel_index, self._qcolor_cache[-1])
            
            tile_painter.fillRect(
                (x - start_x) * self.zoom,
                (y - start_y) * self.zoom,
                self.zoom,
                self.zoom,
                color
            )
    
    tile_painter.end()
    return pixmap

def _draw_grid_optimized(self, painter, left, top, right, bottom):
    """Draw grid lines only for visible area"""
    painter.setPen(QPen(QColor(128, 128, 128, 128), 1))
    
    # Create a path for all grid lines
    grid_path = QPainterPath()
    
    # Vertical lines
    for x in range(left, right + 1):
        grid_path.moveTo(x * self.zoom, top * self.zoom)
        grid_path.lineTo(x * self.zoom, bottom * self.zoom)
    
    # Horizontal lines
    for y in range(top, bottom + 1):
        grid_path.moveTo(left * self.zoom, y * self.zoom)
        grid_path.lineTo(right * self.zoom, y * self.zoom)
    
    # Draw all grid lines in one operation
    painter.drawPath(grid_path)
```

## Implementation Priority

1. **High Priority**: QColor caching - Easy win with significant performance boost
2. **High Priority**: Viewport culling - Essential for large images
3. **Medium Priority**: Dirty rectangle tracking - Good for interactive performance
4. **Medium Priority**: Optimized grid drawing - Noticeable improvement at high zoom
5. **Low Priority**: Tile caching - Complex but beneficial for very large canvases

## Expected Performance Improvements

- **QColor Caching**: 10-20x faster color lookup per pixel
- **Viewport Culling**: Proportional to visible area (e.g., 10% visible = 10x faster)
- **Dirty Rectangles**: Single pixel edits become O(1) instead of O(n)
- **Grid Optimization**: 2-3x faster grid rendering
- **Tile Caching**: Amortized O(1) for cached areas vs O(n) for pixel rendering

## Testing Strategy

1. Profile before/after with large images (512x512, 1024x1024)
2. Measure FPS during continuous drawing operations
3. Test zoom performance at various levels
4. Verify memory usage stays reasonable with caching
5. Ensure visual quality is maintained