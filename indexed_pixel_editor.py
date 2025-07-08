#!/usr/bin/env python3
"""
Indexed Pixel Editor for SNES Sprites
A dedicated editor for pixel-level editing of indexed color sprites
Maintains 4bpp indexed format throughout the editing process
"""

import sys
import os
from typing import Optional, List, Tuple
from collections import deque

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QMessageBox, QGroupBox,
    QGridLayout, QSlider, QSpinBox, QCheckBox, QButtonGroup,
    QRadioButton, QToolBar, QStatusBar, QScrollArea
)
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QPainter, QPixmap, QImage, QPen, QColor, QBrush,
    QAction, QIcon, QKeySequence, QMouseEvent, QPalette
)

from PIL import Image
import numpy as np


class ColorPaletteWidget(QWidget):
    """Widget for displaying and selecting colors from the palette"""
    colorSelected = pyqtSignal(int)  # Emits the color index
    
    def __init__(self):
        super().__init__()
        # Default SNES-like palette with actual colors
        self.colors = [
            (0, 0, 0),        # 0 - Black (transparent)
            (255, 183, 197),  # 1 - Kirby pink
            (255, 255, 255),  # 2 - White
            (64, 64, 64),     # 3 - Dark gray (outline)
            (255, 0, 0),      # 4 - Red
            (0, 0, 255),      # 5 - Blue
            (255, 220, 220),  # 6 - Light pink
            (200, 120, 150),  # 7 - Dark pink
            (255, 255, 0),    # 8 - Yellow
            (0, 255, 0),      # 9 - Green
            (255, 128, 0),    # 10 - Orange
            (128, 0, 255),    # 11 - Purple
            (0, 128, 128),    # 12 - Teal
            (128, 128, 0),    # 13 - Olive
            (192, 192, 192),  # 14 - Light gray
            (128, 128, 128),  # 15 - Medium gray
        ]
        self.selected_index = 1  # Start with color 1 (Kirby pink)
        self.cell_size = 24
        self.setFixedSize(self.cell_size * 4 + 10, self.cell_size * 4 + 10)
        
        # Debug: Show palette initialization
        print(f"[PALETTE] Initialized with {len(self.colors)} colors")
        print(f"[PALETTE] Key colors: 0={self.colors[0]}, 1={self.colors[1]}, 4={self.colors[4]}, 8={self.colors[8]}")
        print(f"[PALETTE] Selected index: {self.selected_index} (color: {self.colors[self.selected_index]})")
        
    def set_palette(self, colors: List[Tuple[int, int, int]]):
        """Set the palette colors (RGB tuples)"""
        old_colors = self.colors.copy()
        self.colors = colors[:16]  # Ensure we only have 16 colors
        while len(self.colors) < 16:
            self.colors.append((0, 0, 0))
        
        # Debug: Show palette changes
        print(f"[PALETTE] Palette updated with {len(colors)} new colors")
        print(f"[PALETTE] New key colors: 0={self.colors[0]}, 1={self.colors[1]}, 4={self.colors[4]}, 8={self.colors[8]}")
        
        # Check if colors actually changed
        if old_colors != self.colors:
            print(f"[PALETTE] Colors changed from old to new")
        else:
            print(f"[PALETTE] Colors unchanged")
        
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(60, 60, 60))
        
        # Draw color cells
        for i in range(16):
            row = i // 4
            col = i % 4
            x = col * self.cell_size + 5
            y = row * self.cell_size + 5
            
            # Draw color
            color = QColor(*self.colors[i])
            painter.fillRect(x, y, self.cell_size - 2, self.cell_size - 2, color)
            
            # Draw selection border
            if i == self.selected_index:
                painter.setPen(QPen(Qt.GlobalColor.white, 2))
                painter.drawRect(x - 1, y - 1, self.cell_size, self.cell_size)
            
            # Draw index number
            painter.setPen(Qt.GlobalColor.white if sum(self.colors[i]) < 384 else Qt.GlobalColor.black)
            painter.drawText(QRect(x, y, self.cell_size - 2, self.cell_size - 2),
                           Qt.AlignmentFlag.AlignCenter, str(i))
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            x = int((event.position().x() - 5) // self.cell_size)
            y = int((event.position().y() - 5) // self.cell_size)
            if 0 <= x < 4 and 0 <= y < 4:
                index = y * 4 + x
                if 0 <= index < 16:
                    old_index = self.selected_index
                    self.selected_index = index
                    
                    # Debug: Show color selection
                    print(f"[PALETTE] Color selected: {old_index} -> {index}")
                    print(f"[PALETTE] Selected color RGB: {self.colors[index]}")
                    
                    self.colorSelected.emit(index)
                    self.update()


class PixelCanvas(QWidget):
    """Main canvas for pixel editing with zoom support"""
    pixelChanged = pyqtSignal()
    
    def __init__(self, palette_widget=None):
        super().__init__()
        self.image_data = None  # numpy array of pixel indices
        self.zoom = 16  # Default zoom level
        self.grid_visible = True
        self.greyscale_mode = False  # Show indices as greyscale
        self.show_color_preview = True  # Show color preview
        self.current_color = 1
        self.tool = "pencil"
        self.drawing = False
        self.last_point = None
        self.palette_widget = palette_widget  # Direct reference to palette widget
        
        # Debug: Show canvas initialization
        print(f"[CANVAS] Canvas initialized with zoom={self.zoom}, current_color={self.current_color}")
        if self.palette_widget:
            print(f"[CANVAS] Received palette widget with {len(self.palette_widget.colors)} colors")
            print(f"[CANVAS] Palette key colors: 0={self.palette_widget.colors[0]}, 1={self.palette_widget.colors[1]}, 4={self.palette_widget.colors[4]}")
        else:
            print(f"[CANVAS] No palette widget provided - will use grayscale fallback")
        
        # Undo/redo system
        self.undo_stack = deque(maxlen=50)
        self.redo_stack = deque(maxlen=50)
        
        # Canvas setup
        self.setMouseTracking(True)
        self.setMinimumSize(200, 200)
        
    def new_image(self, width: int, height: int):
        """Create a new blank image"""
        self.image_data = np.zeros((height, width), dtype=np.uint8)
        self.undo_stack.clear()
        self.redo_stack.clear()
        
        # Debug: Show new image creation
        print(f"[CANVAS] Created new image: {width}x{height}")
        print(f"[CANVAS] Current drawing color: {self.current_color}")
        if self.palette_widget and self.current_color < len(self.palette_widget.colors):
            rgb_color = self.palette_widget.colors[self.current_color]
            print(f"[CANVAS] Drawing color RGB: {rgb_color}")
        
        self.update_size()
        self.update()
    
    def load_image(self, pil_image: Image.Image):
        """Load an indexed image"""
        if pil_image.mode != 'P':
            raise ValueError("Image must be in indexed color mode (P)")
        
        # Convert to numpy array
        self.image_data = np.array(pil_image)
        
        # Store palette if available
        if pil_image.palette:
            palette_data = pil_image.palette.palette
            colors = []
            for i in range(16):
                if i * 3 + 2 < len(palette_data):
                    r = palette_data[i * 3]
                    g = palette_data[i * 3 + 1] 
                    b = palette_data[i * 3 + 2]
                    colors.append((r, g, b))
                else:
                    colors.append((0, 0, 0))
            if self.palette_widget:
                self.palette_widget.set_palette(colors)
        
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.update_size()
        self.update()
    
    def get_pil_image(self) -> Optional[Image.Image]:
        """Convert current image to PIL Image"""
        if self.image_data is None:
            return None
        
        # Create indexed image
        img = Image.fromarray(self.image_data, mode='P')
        
        # Set palette based on mode
        palette = []
        if self.greyscale_mode:
            # Greyscale mode: use grayscale palette
            for i in range(16):
                gray = (i * 255) // 15
                palette.extend([gray, gray, gray])
        else:
            # Color mode: use actual palette
            if self.palette_widget:
                for color in self.palette_widget.colors:
                    palette.extend(color)
            else:
                # Default grayscale palette
                for i in range(16):
                    gray = (i * 255) // 15
                    palette.extend([gray, gray, gray])
        
        # Pad to 256 colors
        while len(palette) < 768:
            palette.extend([0, 0, 0])
        
        img.putpalette(palette)
        return img
    
    def update_size(self):
        """Update widget size based on image and zoom"""
        if self.image_data is not None:
            height, width = self.image_data.shape
            self.setFixedSize(width * self.zoom, height * self.zoom)
    
    def set_zoom(self, zoom: int):
        """Set zoom level"""
        self.zoom = max(1, min(64, zoom))
        self.update_size()
        self.update()
    
    def paintEvent(self, event):
        if self.image_data is None:
            return
        
        painter = QPainter(self)
        height, width = self.image_data.shape
        
        # Get colors based on mode
        if self.greyscale_mode:
            # Greyscale mode: show indices as shades of grey
            colors = [(i * 17, i * 17, i * 17) for i in range(16)]
            print(f"[CANVAS] paintEvent using greyscale mode colors")
        else:
            # Color mode: use palette colors
            if self.palette_widget:
                colors = self.palette_widget.colors
                # Debug: print first few colors to verify they're not all black
                if not hasattr(self, '_debug_colors_printed'):
                    print(f"[CANVAS] paintEvent using palette colors: {colors[:4]}")
                    print(f"[CANVAS] Palette has {len(colors)} colors")
                    
                    # Check if palette looks correct
                    unique_colors = set(colors)
                    if len(unique_colors) == 1:
                        print(f"[CANVAS] WARNING: All palette colors are the same: {colors[0]}")
                    elif len(unique_colors) < 4:
                        print(f"[CANVAS] WARNING: Only {len(unique_colors)} unique colors in palette")
                    else:
                        print(f"[CANVAS] Palette looks good with {len(unique_colors)} unique colors")
                    
                    self._debug_colors_printed = True
            else:
                # Default grayscale palette
                colors = [(i * 17, i * 17, i * 17) for i in range(16)]
                print("[CANVAS] paintEvent using grayscale fallback colors!")
        
        # Draw pixels
        for y in range(height):
            for x in range(width):
                pixel_index = self.image_data[y, x]
                if pixel_index < len(colors):
                    color = QColor(*colors[pixel_index])
                else:
                    color = QColor(255, 0, 255)  # Magenta for invalid indices
                
                painter.fillRect(x * self.zoom, y * self.zoom, 
                               self.zoom, self.zoom, color)
        
        # Draw grid
        if self.grid_visible and self.zoom > 4:
            painter.setPen(QPen(QColor(128, 128, 128, 128), 1))
            
            # Vertical lines
            for x in range(width + 1):
                painter.drawLine(x * self.zoom, 0, x * self.zoom, height * self.zoom)
            
            # Horizontal lines
            for y in range(height + 1):
                painter.drawLine(0, y * self.zoom, width * self.zoom, y * self.zoom)
        
        # Draw current mouse position highlight
        if hasattr(self, 'hover_pos'):
            painter.setPen(QPen(Qt.GlobalColor.white, 2))
            painter.drawRect(self.hover_pos.x() * self.zoom, 
                           self.hover_pos.y() * self.zoom,
                           self.zoom, self.zoom)
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.save_undo()
            pos = self.get_pixel_pos(event.position())
            if pos:
                if self.tool == "pencil":
                    self.draw_pixel(pos.x(), pos.y())
                elif self.tool == "fill":
                    self.flood_fill(pos.x(), pos.y())
                elif self.tool == "picker":
                    self.pick_color(pos.x(), pos.y())
                self.last_point = pos
    
    def mouseMoveEvent(self, event: QMouseEvent):
        pos = self.get_pixel_pos(event.position())
        if pos:
            self.hover_pos = pos
            self.update()
            
            if self.drawing and self.tool == "pencil":
                if self.last_point and self.last_point != pos:
                    self.draw_line(self.last_point.x(), self.last_point.y(),
                                 pos.x(), pos.y())
                    self.last_point = pos
                else:
                    self.draw_pixel(pos.x(), pos.y())
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False
            self.last_point = None
    
    def get_pixel_pos(self, pos) -> Optional[QPoint]:
        """Convert mouse position to pixel coordinates"""
        if self.image_data is None:
            return None
        
        x = int(pos.x() // self.zoom)
        y = int(pos.y() // self.zoom)
        
        height, width = self.image_data.shape
        if 0 <= x < width and 0 <= y < height:
            return QPoint(x, y)
        return None
    
    def draw_pixel(self, x: int, y: int):
        """Draw a single pixel"""
        if self.image_data is None:
            print(f"[CANVAS] Cannot draw pixel - no image data")
            return
        
        height, width = self.image_data.shape
        if 0 <= x < width and 0 <= y < height:
            # Validate and clamp color to 4bpp range (0-15)
            color = max(0, min(15, int(self.current_color)))
            old_value = self.image_data[y, x]
            self.image_data[y, x] = np.uint8(color)
            
            # Debug: Show pixel drawing
            if self.palette_widget and color < len(self.palette_widget.colors):
                rgb_color = self.palette_widget.colors[color]
                print(f"[CANVAS] Drew pixel at ({x},{y}): index {old_value} -> {color} (RGB: {rgb_color})")
            else:
                print(f"[CANVAS] Drew pixel at ({x},{y}): index {old_value} -> {color} (no palette)")
            
            self.update()
            self.pixelChanged.emit()
        else:
            print(f"[CANVAS] Cannot draw pixel at ({x},{y}) - out of bounds ({width}x{height})")
    
    def draw_line(self, x0: int, y0: int, x1: int, y1: int):
        """Draw a line between two points using Bresenham's algorithm"""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        while True:
            self.draw_pixel(x0, y0)
            
            if x0 == x1 and y0 == y1:
                break
                
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
    
    def flood_fill(self, x: int, y: int):
        """Flood fill from the given point"""
        if self.image_data is None:
            return
        
        height, width = self.image_data.shape
        if not (0 <= x < width and 0 <= y < height):
            return
        
        target_color = self.image_data[y, x]
        # Validate and clamp color to 4bpp range (0-15)
        fill_color = max(0, min(15, int(self.current_color)))
        if target_color == fill_color:
            return
        
        # Use a stack for iterative flood fill
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if not (0 <= cx < width and 0 <= cy < height):
                continue
            
            if self.image_data[cy, cx] != target_color:
                continue
            
            self.image_data[cy, cx] = np.uint8(fill_color)
            
            # Add neighbors
            stack.extend([(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)])
        
        self.update()
        self.pixelChanged.emit()
    
    def pick_color(self, x: int, y: int):
        """Pick color from the canvas"""
        if self.image_data is None:
            return
        
        height, width = self.image_data.shape
        if 0 <= x < width and 0 <= y < height:
            color_index = self.image_data[y, x]
            if self.palette_widget:
                self.palette_widget.selected_index = color_index
                self.palette_widget.colorSelected.emit(color_index)
                self.palette_widget.update()
    
    def save_undo(self):
        """Save current state for undo"""
        if self.image_data is not None:
            self.undo_stack.append(self.image_data.copy())
            self.redo_stack.clear()
    
    def undo(self):
        """Undo last action"""
        if self.undo_stack:
            self.redo_stack.append(self.image_data.copy())
            self.image_data = self.undo_stack.pop()
            self.update()
            self.pixelChanged.emit()
    
    def redo(self):
        """Redo last undone action"""
        if self.redo_stack:
            self.undo_stack.append(self.image_data.copy())
            self.image_data = self.redo_stack.pop()
            self.update()
            self.pixelChanged.emit()


class IndexedPixelEditor(QMainWindow):
    """Main window for the indexed pixel editor"""
    
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.modified = False
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Indexed Pixel Editor")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        # Left panel - Tools and palette
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(200)
        
        # Tool selection
        tool_group = QGroupBox("Tools")
        tool_layout = QVBoxLayout()
        
        self.tool_group = QButtonGroup()
        pencil_btn = QRadioButton("Pencil")
        pencil_btn.setChecked(True)
        fill_btn = QRadioButton("Fill")
        picker_btn = QRadioButton("Color Picker")
        
        self.tool_group.addButton(pencil_btn, 0)
        self.tool_group.addButton(fill_btn, 1)
        self.tool_group.addButton(picker_btn, 2)
        
        tool_layout.addWidget(pencil_btn)
        tool_layout.addWidget(fill_btn)
        tool_layout.addWidget(picker_btn)
        tool_group.setLayout(tool_layout)
        
        # Palette widget
        palette_group = QGroupBox("Palette")
        palette_layout = QVBoxLayout()
        self.palette_widget = ColorPaletteWidget()
        self.palette_widget.colorSelected.connect(self.on_color_selected)
        palette_layout.addWidget(self.palette_widget)
        palette_group.setLayout(palette_layout)
        
        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        self.grid_checkbox = QCheckBox("Show Grid")
        self.grid_checkbox.setChecked(True)
        self.grid_checkbox.toggled.connect(self.toggle_grid)
        
        self.greyscale_checkbox = QCheckBox("Greyscale Mode")
        self.greyscale_checkbox.setChecked(False)
        self.greyscale_checkbox.toggled.connect(self.toggle_greyscale_mode)
        
        self.preview_checkbox = QCheckBox("Show Color Preview")
        self.preview_checkbox.setChecked(True)
        self.preview_checkbox.toggled.connect(self.toggle_color_preview)
        
        zoom_layout = QHBoxLayout()
        zoom_layout.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(1, 64)
        self.zoom_slider.setValue(16)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        self.zoom_label = QLabel("16x")
        zoom_layout.addWidget(self.zoom_slider)
        zoom_layout.addWidget(self.zoom_label)
        
        options_layout.addWidget(self.grid_checkbox)
        options_layout.addWidget(self.greyscale_checkbox)
        options_layout.addWidget(self.preview_checkbox)
        options_layout.addLayout(zoom_layout)
        options_group.setLayout(options_layout)
        
        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        
        # Main preview (changes based on mode)
        main_preview_label = QLabel("Current View:")
        main_preview_label.setStyleSheet("QLabel { font-weight: bold; }")
        preview_layout.addWidget(main_preview_label)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("QLabel { background-color: #202020; }")
        self.preview_label.setMinimumHeight(100)
        preview_layout.addWidget(self.preview_label)
        
        # Color preview (always shows colored version)
        color_preview_label = QLabel("With Colors:")
        color_preview_label.setStyleSheet("QLabel { font-weight: bold; }")
        preview_layout.addWidget(color_preview_label)
        
        self.color_preview_label = QLabel()
        self.color_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.color_preview_label.setStyleSheet("QLabel { background-color: #202020; border: 2px solid #666; }")
        self.color_preview_label.setMinimumHeight(100)
        preview_layout.addWidget(self.color_preview_label)
        
        preview_group.setLayout(preview_layout)
        
        left_layout.addWidget(tool_group)
        left_layout.addWidget(palette_group)
        left_layout.addWidget(options_group)
        left_layout.addWidget(preview_group)
        left_layout.addStretch()
        
        # Right panel - Canvas
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Scroll area for canvas
        scroll_area = QScrollArea()
        
        # Create canvas with palette widget
        self.canvas = PixelCanvas(self.palette_widget)
        self.canvas.pixelChanged.connect(self.on_canvas_changed)
        
        # Set initial drawing color
        self.canvas.current_color = self.palette_widget.selected_index
        print(f"[EDITOR] Canvas created with initial color: {self.canvas.current_color}")
        scroll_area.setWidget(self.canvas)
        scroll_area.setWidgetResizable(False)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        right_layout.addWidget(scroll_area)
        
        # Add panels to main layout
        layout.addWidget(left_panel)
        layout.addWidget(right_panel, 1)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Connect tool selection
        self.tool_group.buttonClicked.connect(self.on_tool_changed)
        
        # Start with a new 8x8 image
        self.new_file()
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_file)
        
        open_action = QAction("Open", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        
        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_file_as)
        
        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.canvas.undo)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.canvas.redo)
        
        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)
    
    def create_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Add common actions
        toolbar.addAction("New", self.new_file)
        toolbar.addAction("Open", self.open_file)
        toolbar.addAction("Save", self.save_file)
        toolbar.addSeparator()
        toolbar.addAction("Undo", self.canvas.undo)
        toolbar.addAction("Redo", self.canvas.redo)
    
    def new_file(self):
        """Create a new 8x8 image"""
        if self.check_save():
            print(f"[EDITOR] Creating new file...")
            self.canvas.new_image(8, 8)
            # Set initial color to palette selection
            self.canvas.current_color = self.palette_widget.selected_index
            self.current_file = None
            self.modified = False
            self.setWindowTitle("Indexed Pixel Editor - New File")
            self.update_preview()
            print(f"[EDITOR] New file created with current color: {self.canvas.current_color}")
    
    def open_file(self):
        """Open an indexed PNG file"""
        if not self.check_save():
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Indexed PNG", "", "PNG Files (*.png);;All Files (*)"
        )
        
        if file_path:
            try:
                img = Image.open(file_path)
                if img.mode != 'P':
                    QMessageBox.warning(self, "Invalid Format", 
                                      "File must be an indexed color PNG (mode P)")
                    return
                
                self.canvas.load_image(img)
                self.current_file = file_path
                self.modified = False
                self.setWindowTitle(f"Indexed Pixel Editor - {os.path.basename(file_path)}")
                self.update_preview()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")
    
    def save_file(self):
        """Save the current file"""
        if self.current_file:
            self.save_to_file(self.current_file)
        else:
            self.save_file_as()
    
    def save_file_as(self):
        """Save with a new filename"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Indexed PNG", "", "PNG Files (*.png)"
        )
        
        if file_path:
            if not file_path.endswith('.png'):
                file_path += '.png'
            self.save_to_file(file_path)
    
    def save_to_file(self, file_path: str):
        """Save image to file"""
        try:
            img = self.canvas.get_pil_image()
            if img:
                img.save(file_path)
                self.current_file = file_path
                self.modified = False
                self.setWindowTitle(f"Indexed Pixel Editor - {os.path.basename(file_path)}")
                self.status_bar.showMessage(f"Saved to {file_path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")
    
    def check_save(self) -> bool:
        """Check if we need to save before continuing"""
        if self.modified:
            result = QMessageBox.question(
                self, "Save Changes",
                "Do you want to save your changes?",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel
            )
            
            if result == QMessageBox.StandardButton.Save:
                self.save_file()
                return True
            elif result == QMessageBox.StandardButton.Cancel:
                return False
        
        return True
    
    def on_tool_changed(self, button):
        """Handle tool selection change"""
        tools = ["pencil", "fill", "picker"]
        self.canvas.tool = tools[self.tool_group.id(button)]
    
    def on_color_selected(self, index: int):
        """Handle color selection"""
        # Validate and clamp index to 4bpp range (0-15)
        valid_index = max(0, min(15, int(index)))
        old_color = self.canvas.current_color
        self.canvas.current_color = valid_index
        
        # Debug: Show color selection change
        if self.palette_widget and valid_index < len(self.palette_widget.colors):
            rgb_color = self.palette_widget.colors[valid_index]
            print(f"[EDITOR] Color selected: {old_color} -> {valid_index} (RGB: {rgb_color})")
        else:
            print(f"[EDITOR] Color selected: {old_color} -> {valid_index} (no RGB info)")
        
        self.status_bar.showMessage(f"Selected color {valid_index}")
    
    def toggle_grid(self, checked: bool):
        """Toggle grid visibility"""
        self.canvas.grid_visible = checked
        self.canvas.update()
    
    def toggle_greyscale_mode(self, checked: bool):
        """Toggle greyscale drawing mode"""
        self.canvas.greyscale_mode = checked
        self.canvas.update()
        print(f"[EDITOR] Greyscale mode: {'ON' if checked else 'OFF'}")
    
    def toggle_color_preview(self, checked: bool):
        """Toggle color preview visibility"""
        self.canvas.show_color_preview = checked
        self.update_preview()
        print(f"[EDITOR] Color preview: {'ON' if checked else 'OFF'}")
    
    def on_zoom_changed(self, value: int):
        """Handle zoom slider change"""
        self.canvas.set_zoom(value)
        self.zoom_label.setText(f"{value}x")
    
    def on_canvas_changed(self):
        """Handle canvas modification"""
        self.modified = True
        if self.current_file:
            self.setWindowTitle(f"Indexed Pixel Editor - {os.path.basename(self.current_file)}*")
        else:
            self.setWindowTitle("Indexed Pixel Editor - New File*")
        self.update_preview()
    
    def update_preview(self):
        """Update the preview labels"""
        if self.canvas.image_data is None:
            self.preview_label.clear()
            self.color_preview_label.clear()
            return
        
        # Get main preview image (respects greyscale mode)
        main_img = self.canvas.get_pil_image()
        if main_img:
            # Convert to QPixmap for display
            img_rgb = main_img.convert('RGBA')
            data = img_rgb.tobytes('raw', 'RGBA')
            qimage = QImage(data, main_img.width, main_img.height, QImage.Format.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qimage)
            
            # Scale up for better visibility but maintain pixel art look
            scale = min(100 // main_img.width, 100 // main_img.height, 8)
            scaled_pixmap = pixmap.scaled(
                main_img.width * scale, main_img.height * scale,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            
            self.preview_label.setPixmap(scaled_pixmap)
        else:
            self.preview_label.clear()
        
        # Get color preview image (always shows colored version)
        if self.preview_checkbox.isChecked():
            color_img = self.get_color_preview_image()
            if color_img:
                # Convert to QPixmap for display
                img_rgb = color_img.convert('RGBA')
                data = img_rgb.tobytes('raw', 'RGBA')
                qimage = QImage(data, color_img.width, color_img.height, QImage.Format.Format_RGBA8888)
                pixmap = QPixmap.fromImage(qimage)
                
                # Scale up for better visibility but maintain pixel art look
                scale = min(100 // color_img.width, 100 // color_img.height, 8)
                scaled_pixmap = pixmap.scaled(
                    color_img.width * scale, color_img.height * scale,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.FastTransformation
                )
                
                self.color_preview_label.setPixmap(scaled_pixmap)
                self.color_preview_label.show()
            else:
                self.color_preview_label.clear()
        else:
            self.color_preview_label.hide()
    
    def get_color_preview_image(self):
        """Get the colored version of the image for preview"""
        if self.canvas.image_data is None or not self.palette_widget:
            return None
        
        # Create indexed image
        img = Image.fromarray(self.canvas.image_data, mode='P')
        
        # Set palette using the actual palette colors
        palette = []
        for color in self.palette_widget.colors:
            palette.extend(color)
        
        # Pad to 256 colors
        while len(palette) < 768:
            palette.extend([0, 0, 0])
        
        img.putpalette(palette)
        return img


def main():
    app = QApplication(sys.argv)
    editor = IndexedPixelEditor()
    editor.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()