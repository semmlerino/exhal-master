
# Recommended fixes for palette issues in sprite_editor

## Fix 1: sprite_viewer_widget.py - Preserve palette when converting
In set_image method, around line 66:

```python
if isinstance(image, Image.Image):
    # Convert PIL to QPixmap
    if image.mode == 'P':
        # Handle indexed images - ensure palette is preserved
        if not image.getpalette():
            # Apply default palette if none exists
            image.putpalette(get_grayscale_palette())
        
        # Convert to RGBA while preserving colors
        image_rgb = image.convert('RGBA')
        data = image_rgb.tobytes('raw', 'RGBA')
        qimage = QImage(
            data,
            image.width,
            image.height,
            QImage.Format.Format_RGBA8888)
```

## Fix 2: sprite_editor_core.py - Make palette optional
In extract_sprites method, add parameter:

```python
def extract_sprites(self, vram_file: str, offset: int, size: int,
                    tiles_per_row: int = DEFAULT_TILES_PER_ROW,
                    apply_default_palette: bool = True) -> Tuple[Image.Image, int]:
    """Extract sprites from VRAM dump."""
    # ... existing code ...
    
    # Create indexed color image
    img = Image.new('P', (width, height))
    
    # Only apply default palette if requested
    if apply_default_palette:
        img.putpalette(get_grayscale_palette())
```

## Fix 3: Add palette validation utility
New function in palette_utils.py:

```python
def validate_palette(palette: List[int]) -> bool:
    """Validate palette data format"""
    if not palette or not isinstance(palette, (list, bytes)):
        return False
    
    # Check length (should be 768 for 256 colors * 3 components)
    if len(palette) != 768:
        return False
    
    # Check value range
    for val in palette[:48]:  # Check first 16 colors
        if not isinstance(val, int) or val < 0 or val > 255:
            return False
    
    return True
```

## Fix 4: Improve palette application in models
In sprite_model.py apply_palette method:

```python
def apply_palette(self, palette_num):
    """Apply a specific palette to the current image"""
    if self.current_image and self.current_image.mode == 'P':
        if self.cgram_file:
            palette = self.core.read_cgram_palette(
                self.cgram_file, palette_num)
            if palette and validate_palette(palette):
                # Create a copy to preserve original
                new_image = self.current_image.copy()
                new_image.putpalette(palette)
                self.current_image = new_image
                self.current_palette = palette_num
                self.current_image_changed.emit(self.current_image)
                return True
    return False
```
