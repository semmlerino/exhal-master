#!/usr/bin/env python3
"""
Sprite data model
Manages sprite data and provides business logic for sprite operations
"""

from PyQt6.QtCore import pyqtSignal
from PIL import Image

from .base_model import BaseModel, ObservableProperty
from ..sprite_editor_core import SpriteEditorCore


class SpriteModel(BaseModel):
    """Model for sprite data and operations"""
    
    # Observable properties
    current_image = ObservableProperty(None)
    vram_file = ObservableProperty("")
    cgram_file = ObservableProperty("")
    oam_file = ObservableProperty("")
    extraction_offset = ObservableProperty(0xC000)
    extraction_size = ObservableProperty(0x4000)
    tiles_per_row = ObservableProperty(16)
    current_palette = ObservableProperty(0)
    
    # Signals
    current_image_changed = pyqtSignal(object)
    vram_file_changed = pyqtSignal(str)
    cgram_file_changed = pyqtSignal(str)
    oam_file_changed = pyqtSignal(str)
    extraction_offset_changed = pyqtSignal(int)
    extraction_size_changed = pyqtSignal(int)
    tiles_per_row_changed = pyqtSignal(int)
    current_palette_changed = pyqtSignal(int)
    
    # Operation signals
    extraction_started = pyqtSignal()
    extraction_completed = pyqtSignal(object, int)  # image, tile_count
    extraction_error = pyqtSignal(str)
    injection_started = pyqtSignal()
    injection_completed = pyqtSignal(str)  # output_file
    injection_error = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.core = SpriteEditorCore()
        self._palettes = []
        self._tile_count = 0
    
    def extract_sprites(self, apply_palette=False):
        """Extract sprites from VRAM"""
        try:
            self.extraction_started.emit()
            
            image, tile_count = self.core.extract_sprites(
                self.vram_file,
                self.extraction_offset,
                self.extraction_size,
                self.tiles_per_row
            )
            
            # Apply palette if requested
            if apply_palette and self.cgram_file:
                palette = self.core.read_cgram_palette(self.cgram_file, self.current_palette)
                if palette:
                    image.putpalette(palette)
            
            self.current_image = image
            self._tile_count = tile_count
            
            self.extraction_completed.emit(image, tile_count)
            
        except Exception as e:
            self.extraction_error.emit(str(e))
    
    def inject_sprites(self, png_file, output_file):
        """Inject sprites into VRAM"""
        try:
            self.injection_started.emit()
            
            # Validate PNG
            valid, issues = self.core.validate_png_for_snes(png_file)
            if not valid:
                self.injection_error.emit("PNG validation failed:\n" + "\n".join(issues))
                return
            
            # Convert to SNES format
            tile_data, tile_count = self.core.png_to_snes(png_file)
            
            # Inject into VRAM
            output = self.core.inject_into_vram(
                tile_data,
                self.vram_file,
                self.extraction_offset,
                output_file
            )
            
            self.injection_completed.emit(output)
            
        except Exception as e:
            self.injection_error.emit(str(e))
    
    def load_oam_mapping(self):
        """Load OAM mapping data"""
        if self.oam_file:
            return self.core.load_oam_mapping(self.oam_file)
        return False
    
    def load_all_palettes(self):
        """Load all palettes from CGRAM"""
        if not self.cgram_file:
            return []
        
        self._palettes = []
        for i in range(16):
            palette = self.core.read_cgram_palette(self.cgram_file, i)
            if palette:
                self._palettes.append(palette)
        
        return self._palettes
    
    def apply_palette(self, palette_num):
        """Apply a specific palette to the current image"""
        if self.current_image and self.current_image.mode == 'P':
            if self.cgram_file:
                palette = self.core.read_cgram_palette(self.cgram_file, palette_num)
                if palette:
                    self.current_image.putpalette(palette)
                    self.current_palette = palette_num
                    return True
        return False
    
    def get_vram_info(self):
        """Get information about current VRAM file"""
        if self.vram_file:
            return self.core.get_vram_info(self.vram_file)
        return None
    
    def get_tile_count(self):
        """Get the number of tiles in current extraction"""
        return self._tile_count
    
    def validate_png(self, png_file):
        """Validate a PNG file for SNES compatibility"""
        return self.core.validate_png_for_snes(png_file)