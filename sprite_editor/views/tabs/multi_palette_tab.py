#!/usr/bin/env python3
"""
Multi-palette tab for the sprite editor
Handles multi-palette preview functionality
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QPushButton, QLabel, QLineEdit, QSpinBox
)
from PyQt6.QtCore import pyqtSignal

from ...multi_palette_viewer import MultiPaletteViewer


class MultiPaletteTab(QWidget):
    """Tab widget for multi-palette preview functionality"""
    
    # Signals
    browse_oam_requested = pyqtSignal()
    generate_preview_requested = pyqtSignal()
    palette_selected = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the multi-palette tab UI"""
        layout = QVBoxLayout(self)
        
        # Controls
        controls_group = QGroupBox("Multi-Palette Controls")
        controls_layout = QHBoxLayout()
        
        # OAM file selection
        self.oam_file_edit = QLineEdit()
        self.oam_file_edit.setReadOnly(True)
        self.oam_browse_btn = QPushButton("Load OAM")
        self.oam_browse_btn.clicked.connect(self.browse_oam_requested.emit)
        
        controls_layout.addWidget(QLabel("OAM:"))
        controls_layout.addWidget(self.oam_file_edit)
        controls_layout.addWidget(self.oam_browse_btn)
        
        # Preview size control
        controls_layout.addWidget(QLabel("Preview Size:"))
        self.preview_size_spin = QSpinBox()
        self.preview_size_spin.setRange(16, 512)
        self.preview_size_spin.setValue(64)  # Default to 64 tiles (2KB)
        self.preview_size_spin.setSuffix(" tiles")
        controls_layout.addWidget(self.preview_size_spin)
        
        # Generate preview button
        self.generate_multi_btn = QPushButton("Generate Multi-Palette Preview")
        self.generate_multi_btn.clicked.connect(self.generate_preview_requested.emit)
        controls_layout.addWidget(self.generate_multi_btn)
        
        controls_layout.addStretch()
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Create multi-palette viewer
        self.multi_palette_viewer = MultiPaletteViewer()
        self.multi_palette_viewer.palette_selected.connect(self._on_palette_selected)
        layout.addWidget(self.multi_palette_viewer)
    
    def _on_palette_selected(self, palette_num):
        """Handle palette selection"""
        self.palette_selected.emit(palette_num)
    
    def set_oam_file(self, file_path):
        """Set the OAM file path"""
        self.oam_file_edit.setText(file_path)
    
    def get_preview_size(self):
        """Get the preview size in tiles"""
        return self.preview_size_spin.value()
    
    def set_single_image_all_palettes(self, base_img, palettes):
        """Set single image with all palettes"""
        self.multi_palette_viewer.set_single_image_all_palettes(base_img, palettes)
    
    def set_oam_statistics(self, stats):
        """Set OAM statistics"""
        self.multi_palette_viewer.set_oam_statistics(stats)
    
    def get_multi_palette_viewer(self):
        """Get the multi-palette viewer widget"""
        return self.multi_palette_viewer