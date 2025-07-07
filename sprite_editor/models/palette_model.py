#!/usr/bin/env python3
"""
Palette model for managing color palette data
Handles palette operations and conversions
"""

from PIL import Image
from PyQt6.QtCore import pyqtSignal

from ..sprite_editor_core import SpriteEditorCore
from .base_model import BaseModel, ObservableProperty


class PaletteModel(BaseModel):
    """Model for palette data and operations"""

    # Observable properties
    current_palette_index = ObservableProperty(0)
    palettes_loaded = ObservableProperty(False)
    # List of palette indices used by OAM
    active_palettes = ObservableProperty([])

    # Signals
    current_palette_index_changed = pyqtSignal(int)
    palettes_loaded_changed = pyqtSignal(bool)
    active_palettes_changed = pyqtSignal(list)
    palette_applied = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.core = SpriteEditorCore()
        self._palettes = []  # List of 16 palettes
        self._palette_names = {}
        self._oam_statistics = None

    def load_palettes_from_cgram(self, cgram_file):
        """Load all 16 palettes from CGRAM file"""
        self._palettes = []
        success_count = 0

        for i in range(16):
            palette = self.core.read_cgram_palette(cgram_file, i)
            if palette:
                self._palettes.append(palette)
                success_count += 1
            else:
                # Use grayscale palette as fallback
                self._palettes.append(self.core.get_grayscale_palette())

        self.palettes_loaded = success_count > 0
        return success_count

    def get_palette(self, index):
        """Get a specific palette by index"""
        if 0 <= index < len(self._palettes):
            return self._palettes[index]
        return None

    def get_all_palettes(self):
        """Get all loaded palettes"""
        return self._palettes.copy()

    def apply_palette_to_image(self, image, palette_index):
        """Apply a palette to an indexed image"""
        if not isinstance(image, Image.Image) or image.mode != 'P':
            return False

        palette = self.get_palette(palette_index)
        if palette:
            image.putpalette(palette)
            self.current_palette_index = palette_index
            self.palette_applied.emit(palette_index)
            return True

        return False

    def set_palette_name(self, index, name):
        """Set a custom name for a palette"""
        self._palette_names[index] = name

    def get_palette_name(self, index):
        """Get the name of a palette"""
        return self._palette_names.get(index, f"Palette {index}")

    def set_oam_statistics(self, stats):
        """Set OAM usage statistics for palettes"""
        self._oam_statistics = stats
        if stats:
            # Update active palettes based on OAM data
            active = []
            for pal_num, count in stats.items():
                if count > 0:
                    active.append(pal_num)
            self.active_palettes = sorted(active)

    def get_oam_statistics(self):
        """Get OAM usage statistics"""
        return self._oam_statistics

    def is_palette_active(self, index):
        """Check if a palette is actively used by OAM"""
        return index in self.active_palettes

    def get_palette_usage_count(self, index):
        """Get the number of sprites using a palette"""
        if self._oam_statistics:
            return self._oam_statistics.get(index, 0)
        return 0

    def create_palette_preview_images(self, base_image):
        """Create preview images with all palettes applied"""
        if not isinstance(base_image, Image.Image) or base_image.mode != 'P':
            return []

        preview_images = []
        for i, palette in enumerate(self._palettes):
            img_copy = base_image.copy()
            img_copy.putpalette(palette)
            preview_images.append({
                'index': i,
                'name': self.get_palette_name(i),
                'image': img_copy,
                'is_active': self.is_palette_active(i),
                'usage_count': self.get_palette_usage_count(i)
            })

        return preview_images

    def export_palette(self, index, format='act'):
        """Export a palette to various formats"""
        palette = self.get_palette(index)
        if not palette:
            return None

        if format == 'act':
            # Adobe Color Table format
            return bytes(palette[:768])
        elif format == 'pal':
            # JASC-PAL format
            lines = ['JASC-PAL', '0100', '256']
            for i in range(256):
                if i * 3 < len(palette):
                    r = palette[i * 3]
                    g = palette[i * 3 + 1]
                    b = palette[i * 3 + 2]
                    lines.append(f'{r} {g} {b}')
                else:
                    lines.append('0 0 0')
            return '\n'.join(lines)
        elif format == 'gpl':
            # GIMP Palette format
            lines = [
                'GIMP Palette', f'Name: {
                    self.get_palette_name(index)}', '#']
            for i in range(16):  # Only export 16 colors for SNES
                if i * 3 < len(palette):
                    r = palette[i * 3]
                    g = palette[i * 3 + 1]
                    b = palette[i * 3 + 2]
                    lines.append(f'{r:3d} {g:3d} {b:3d}  Color {i}')
            return '\n'.join(lines)

        return None
