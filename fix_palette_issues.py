#!/usr/bin/env python3
"""
Script to demonstrate fixes for palette-related issues in the sprite editor
"""

import os
import sys

from PIL import Image

# Add sprite_editor directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sprite_editor"))

from palette_utils import read_cgram_palette
from sprite_editor_core import SpriteEditorCore


def demonstrate_palette_fix():
    """Demonstrate how to properly handle palettes"""

    print("Demonstrating proper palette handling...")

    # Find test files
    vram_file = None
    cgram_file = None

    for f in ["vram_from_savestate.dmp", "SnesVideoRam.VRAM.dmp", "mss2_VRAM.dmp"]:
        if os.path.exists(f):
            vram_file = f
            break

    for f in ["SnesCgRam.dmp", "cgram_from_savestate.dmp", "mss2_CGRAM.dmp"]:
        if os.path.exists(f):
            cgram_file = f
            break

    if not vram_file:
        print("No VRAM file found for testing")
        return

    print(f"\nUsing VRAM file: {vram_file}")
    print(f"Using CGRAM file: {cgram_file or 'None'}")

    # Extract sprites
    core = SpriteEditorCore()
    image, tile_count = core.extract_sprites(
        vram_file=vram_file,
        offset=0x6000,
        size=0x800,
        tiles_per_row=8
    )

    print(f"\nExtracted {tile_count} tiles")
    print(f"Image mode: {image.mode}")
    print(f"Image size: {image.size}")

    # Test 1: Save with grayscale palette (default)
    image.save("test_fix_grayscale.png")
    print("\nSaved with grayscale palette: test_fix_grayscale.png")

    # Test 2: Apply and save with CGRAM palette
    if cgram_file:
        palette = read_cgram_palette(cgram_file, 0)
        if palette:
            # Important: Create a copy before modifying palette
            img_pal = image.copy()
            img_pal.putpalette(palette)
            img_pal.save("test_fix_cgram_pal0.png")
            print("Saved with CGRAM palette 0: test_fix_cgram_pal0.png")

            # Test with different palette
            palette2 = read_cgram_palette(cgram_file, 8)
            if palette2:
                img_pal2 = image.copy()
                img_pal2.putpalette(palette2)
                img_pal2.save("test_fix_cgram_pal8.png")
                print("Saved with CGRAM palette 8: test_fix_cgram_pal8.png")

    # Test 3: Demonstrate proper palette preservation
    print("\n\nDemonstrating palette preservation:")

    # Load the saved image and check palette
    loaded = Image.open("test_fix_grayscale.png")
    print(f"\nLoaded image mode: {loaded.mode}")
    if hasattr(loaded, "getpalette"):
        pal = loaded.getpalette()
        if pal:
            print(f"Has palette data: {len(pal)} bytes")
            # Check if it's grayscale
            is_grayscale = True
            for i in range(16):
                r, g, b = pal[i*3], pal[i*3+1], pal[i*3+2]
                if r != g or g != b:
                    is_grayscale = False
                    break
            print(f"Is grayscale: {is_grayscale}")


def create_palette_fix_patch():
    """Create a patch file showing the recommended fixes"""

    patch_content = '''
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
'''

    with open("palette_fixes.md", "w") as f:
        f.write(patch_content)

    print("\n\nCreated palette_fixes.md with recommended fixes")


def main():
    """Run palette fix demonstrations"""
    print("=" * 60)
    print("PALETTE FIX DEMONSTRATION")
    print("=" * 60)

    demonstrate_palette_fix()
    create_palette_fix_patch()

    print("\n" + "=" * 60)
    print("Testing complete. Check the generated files:")
    print("- test_fix_*.png files show palette application")
    print("- palette_fixes.md contains recommended code fixes")
    print("=" * 60)


if __name__ == "__main__":
    main()
