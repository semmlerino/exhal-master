#!/usr/bin/env python3
"""
Viewer tab for the sprite editor
Handles sprite viewing and editing functionality
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QPushButton, QLabel, QCheckBox,
    QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...sprite_viewer_widget import SpriteViewerWidget, PaletteViewerWidget


class ViewerTab(QWidget):
    """Tab widget for sprite viewing and editing"""
    
    # Signals
    zoom_in_requested = pyqtSignal()
    zoom_out_requested = pyqtSignal()
    zoom_fit_requested = pyqtSignal()
    grid_toggled = pyqtSignal(bool)
    save_requested = pyqtSignal()
    open_editor_requested = pyqtSignal()
    tile_hovered = pyqtSignal(int, int)
    pixel_hovered = pyqtSignal(int, int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the viewer tab UI"""
        layout = QVBoxLayout(self)
        
        # Create splitter for viewer and info panel
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side - Image viewer
        viewer_container = QWidget()
        viewer_layout = QVBoxLayout(viewer_container)
        
        # Viewer controls
        controls_layout = QHBoxLayout()
        
        zoom_in_btn = QPushButton("Zoom In (+)")
        zoom_in_btn.clicked.connect(self.zoom_in_requested.emit)
        zoom_out_btn = QPushButton("Zoom Out (-)")
        zoom_out_btn.clicked.connect(self.zoom_out_requested.emit)
        zoom_fit_btn = QPushButton("Fit")
        zoom_fit_btn.clicked.connect(self.zoom_fit_requested.emit)
        
        self.zoom_label = QLabel("Zoom: 1x")
        self.grid_check = QCheckBox("Show Grid")
        self.grid_check.setChecked(True)
        self.grid_check.toggled.connect(self.grid_toggled.emit)
        
        controls_layout.addWidget(zoom_in_btn)
        controls_layout.addWidget(zoom_out_btn)
        controls_layout.addWidget(zoom_fit_btn)
        controls_layout.addWidget(self.zoom_label)
        controls_layout.addStretch()
        controls_layout.addWidget(self.grid_check)
        
        viewer_layout.addLayout(controls_layout)
        
        # Image viewer
        self.sprite_viewer = SpriteViewerWidget()
        self.sprite_viewer.tile_hovered.connect(self._on_tile_hover)
        self.sprite_viewer.pixel_hovered.connect(self._on_pixel_hover)
        viewer_layout.addWidget(self.sprite_viewer)
        
        # Palette viewer
        self.palette_viewer = PaletteViewerWidget()
        viewer_layout.addWidget(self.palette_viewer)
        
        splitter.addWidget(viewer_container)
        
        # Right side - Info panel
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_widget.setMaximumWidth(300)
        
        # Image info
        info_group = QGroupBox("Image Info")
        info_group_layout = QGridLayout()
        
        self.info_labels = {}
        info_items = [
            ("Dimensions:", "dimensions"),
            ("Tiles:", "tiles"),
            ("Mode:", "mode"),
            ("Colors:", "colors")
        ]
        
        for i, (label, key) in enumerate(info_items):
            info_group_layout.addWidget(QLabel(label), i, 0)
            self.info_labels[key] = QLabel("-")
            info_group_layout.addWidget(self.info_labels[key], i, 1)
        
        info_group.setLayout(info_group_layout)
        info_layout.addWidget(info_group)
        
        # Hover info
        hover_group = QGroupBox("Hover Info")
        hover_layout = QGridLayout()
        
        self.tile_pos_label = QLabel("-")
        self.pixel_pos_label = QLabel("-")
        self.color_index_label = QLabel("-")
        
        hover_layout.addWidget(QLabel("Tile:"), 0, 0)
        hover_layout.addWidget(self.tile_pos_label, 0, 1)
        hover_layout.addWidget(QLabel("Pixel:"), 1, 0)
        hover_layout.addWidget(self.pixel_pos_label, 1, 1)
        hover_layout.addWidget(QLabel("Color:"), 2, 0)
        hover_layout.addWidget(self.color_index_label, 2, 1)
        
        hover_group.setLayout(hover_layout)
        info_layout.addWidget(hover_group)
        
        # Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        
        save_btn = QPushButton("Save Current View")
        save_btn.clicked.connect(self.save_requested.emit)
        open_editor_btn = QPushButton("Open in External Editor")
        open_editor_btn.clicked.connect(self.open_editor_requested.emit)
        
        actions_layout.addWidget(save_btn)
        actions_layout.addWidget(open_editor_btn)
        
        actions_group.setLayout(actions_layout)
        info_layout.addWidget(actions_group)
        
        info_layout.addStretch()
        
        splitter.addWidget(info_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
    
    def _on_tile_hover(self, tile_x, tile_y):
        """Handle tile hover event"""
        self.tile_pos_label.setText(f"{tile_x}, {tile_y}")
        self.tile_hovered.emit(tile_x, tile_y)
    
    def _on_pixel_hover(self, x, y, color_index):
        """Handle pixel hover event"""
        self.pixel_pos_label.setText(f"{x}, {y}")
        self.color_index_label.setText(f"Index {color_index}")
        self.pixel_hovered.emit(x, y, color_index)
    
    def set_image(self, image):
        """Set the image to display"""
        self.sprite_viewer.set_image(image)
    
    def set_palette(self, palette):
        """Set the palette to display"""
        self.palette_viewer.set_palette(palette)
    
    def update_zoom_label(self, zoom_level):
        """Update the zoom label"""
        self.zoom_label.setText(f"Zoom: {zoom_level}x")
    
    def update_image_info(self, info):
        """Update image information display"""
        if info:
            self.info_labels["dimensions"].setText(f"{info['width']}x{info['height']}")
            self.info_labels["tiles"].setText(f"{info['tiles_x']}x{info['tiles_y']} ({info['total_tiles']})")
            self.info_labels["mode"].setText(info.get("mode", "-"))
            self.info_labels["colors"].setText(str(info.get("colors", "-")))
    
    def get_sprite_viewer(self):
        """Get the sprite viewer widget"""
        return self.sprite_viewer
    
    def get_palette_viewer(self):
        """Get the palette viewer widget"""
        return self.palette_viewer