"""
Row Arrangement Dialog for SpritePal
Intuitive drag-and-drop interface for arranging sprite rows
"""

from PyQt6.QtCore import Qt, QMimeData, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QDrag, QImage, QPainter, QPixmap, QColor, QFont, QPen
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QStatusBar,
    QApplication,
)
from PIL import Image
import tempfile
import os
import io


class RowPreviewWidget(QWidget):
    """Enhanced widget displaying a thumbnail preview of a sprite row"""
    
    def __init__(self, row_index, row_image, tiles_per_row, is_selected=False, parent=None):
        super().__init__(parent)
        self.row_index = row_index
        self.row_image = row_image
        self.tiles_per_row = tiles_per_row
        self.is_selected = is_selected
        self.is_hovered = False
        self.setFixedHeight(56)  # Larger height for better visibility
        self.setMinimumWidth(300)
        self.setMouseTracking(True)
        
    def paintEvent(self, event):
        """Paint the row thumbnail with enhanced visuals"""
        painter = QPainter(self)
        
        # Draw main background
        if self.is_selected:
            painter.fillRect(self.rect(), QColor(45, 45, 45))
        elif self.is_hovered:
            painter.fillRect(self.rect(), QColor(42, 42, 42))
        else:
            painter.fillRect(self.rect(), QColor(40, 40, 40))
        
        # Draw prominent selection border
        if self.is_selected:
            painter.setPen(QPen(QColor(70, 140, 200), 3))  # Blue selection border
            painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        elif self.is_hovered:
            painter.setPen(QPen(QColor(90, 90, 90), 1))  # Subtle hover border
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        else:
            painter.setPen(QPen(QColor(70, 70, 70), 1))  # Normal border
            painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        
        # Create light image background well
        image_well_rect = self.rect().adjusted(4, 4, -4, -4)
        image_well_rect.setHeight(48)
        painter.fillRect(image_well_rect, QColor(30, 30, 30))  # Dark background for enhanced sprites
        
        # Draw subtle inset border for image well
        painter.setPen(QPen(QColor(20, 20, 20), 1))
        painter.drawRect(image_well_rect.adjusted(0, 0, -1, -1))
        
        # Convert PIL image to QPixmap with brightness enhancement
        image_end_x = 10  # Default position if no image
        
        if self.row_image:
            # Apply brightness/gamma correction for better visibility
            enhanced_image = self._enhance_image_visibility(self.row_image)
            
            # Scale to fit within both width and height constraints
            target_height = 48  # Maximum height for the image
            max_width = 280  # Maximum width to leave room for labels
            
            # Calculate scale factors for both dimensions
            height_scale = target_height / enhanced_image.height
            width_scale = max_width / enhanced_image.width
            
            # Use the smaller scale factor to maintain aspect ratio
            scale_factor = min(height_scale, width_scale)
            
            # Ensure at least 1x scaling and use integer scaling for pixel art
            scale_factor = max(1, int(scale_factor))
            
            scaled_width = enhanced_image.width * scale_factor
            scaled_height = enhanced_image.height * scale_factor
            
            scaled_image = enhanced_image.resize(
                (scaled_width, scaled_height),
                Image.Resampling.NEAREST
            )
            
            # Ensure grayscale mode
            if scaled_image.mode != 'L':
                scaled_image = scaled_image.convert('L')
            
            # Convert to QPixmap using BytesIO to avoid stride issues
            buffer = io.BytesIO()
            scaled_image.save(buffer, format='PNG')
            buffer.seek(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.read())
            
            # Draw scaled thumbnail centered in the well
            draw_x = image_well_rect.x() + 1
            draw_y = image_well_rect.y() + 1
            painter.drawPixmap(draw_x, draw_y, pixmap)
            
            # Update image end position for label placement
            image_end_x = draw_x + pixmap.width() + 10
            
        # Draw row label with better formatting
        painter.setPen(QColor(220, 220, 220))
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        
        # Position label after the image with some padding
        painter.drawText(image_end_x, 20, f"Row {self.row_index}")
        
        # Draw tile count
        painter.setPen(QColor(180, 180, 180))
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(image_end_x, 35, f"{self.tiles_per_row} tiles")
        
        # Draw selection indicator with better styling
        if self.is_selected:
            painter.setPen(QColor(70, 140, 200))  # Match border color
            painter.drawText(image_end_x, 50, "● Selected")
    
    def _enhance_image_visibility(self, image):
        """Apply aggressive brightness enhancement with auto-normalization for very dark sprites"""
        # Convert to grayscale if not already
        if image.mode != 'L':
            image = image.convert('L')
            
        # Get pixel data
        pixels = list(image.getdata())
        
        # Find min and max values (excluding pure black)
        non_zero_pixels = [p for p in pixels if p > 0]
        
        if not non_zero_pixels:
            # All black image, return as-is
            return image
            
        min_val = min(non_zero_pixels)
        max_val = max(non_zero_pixels)
        
        # If the image is very dark (max < 64), use auto-normalization
        if max_val < 64:
            # Normalize to use more of the grayscale range
            range_val = max_val - min_val if max_val > min_val else 1
            
            enhanced_pixels = []
            for pixel in pixels:
                if pixel == 0:
                    # Keep pure black as black
                    enhanced_pixels.append(0)
                else:
                    # Normalize to 80-220 range for good visibility
                    normalized = ((pixel - min_val) / range_val) * 140 + 80
                    enhanced_pixels.append(int(normalized))
        else:
            # For brighter images, use the standard enhancement
            enhanced_pixels = []
            for pixel in pixels:
                if pixel == 0:
                    enhanced_pixels.append(0)
                else:
                    # Apply 2x multiplier with minimum floor of 80
                    new_pixel = max(80, int(pixel * 2.0))
                    new_pixel = min(255, new_pixel)
                    enhanced_pixels.append(new_pixel)
        
        # Create new image with enhanced pixels
        enhanced = Image.new('L', image.size)
        enhanced.putdata(enhanced_pixels)
        return enhanced
    
    def enterEvent(self, event):
        """Handle mouse enter"""
        self.is_hovered = True
        self.update()
        
    def leaveEvent(self, event):
        """Handle mouse leave"""
        self.is_hovered = False
        self.update()
        
    def set_selected(self, selected):
        """Set selection state"""
        self.is_selected = selected
        self.update()


class DragDropListWidget(QListWidget):
    """List widget with enhanced drag-and-drop support"""
    
    item_dropped = pyqtSignal(int, int)  # from_index, to_index
    external_drop = pyqtSignal(object)  # dropped item data
    
    def __init__(self, accept_external_drops=False):
        super().__init__()
        self.accept_external_drops = accept_external_drops
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        
    def dragEnterEvent(self, event):
        """Handle drag enter"""
        if event.mimeData().hasText() and self.accept_external_drops:
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)
            
    def dragMoveEvent(self, event):
        """Handle drag move"""
        if event.mimeData().hasText() and self.accept_external_drops:
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)
            
    def dropEvent(self, event):
        """Handle drop events"""
        if event.mimeData().hasText() and self.accept_external_drops:
            # Handle external drop
            try:
                row_index = int(event.mimeData().text())
                self.external_drop.emit(row_index)
                event.acceptProposedAction()
            except ValueError:
                pass
        else:
            # Handle internal reordering
            super().dropEvent(event)
            self.item_dropped.emit(0, 0)  # Signal for refresh
            
    def startDrag(self, supportedActions):
        """Start drag operation"""
        item = self.currentItem()
        if item:
            drag = QDrag(self)
            mimeData = QMimeData()
            
            # Store the row index for external drops
            row_data = item.data(Qt.ItemDataRole.UserRole)
            if row_data is not None:
                mimeData.setText(str(row_data))
            
            drag.setMimeData(mimeData)
            drag.exec(Qt.DropAction.MoveAction)


class RowArrangementDialog(QDialog):
    """Dialog for arranging sprite rows with intuitive drag-and-drop interface"""
    
    def __init__(self, sprite_path, tiles_per_row=16, parent=None):
        super().__init__(parent)
        self.sprite_path = sprite_path
        self.tiles_per_row = tiles_per_row
        self.original_image = None
        self.tile_rows = []
        self.arranged_rows = []  # List of row indices in arrangement order
        self.output_path = None
        self.tile_width = None  # Will be calculated based on image width
        self.tile_height = None  # Will be calculated based on tile width
        
        self.setWindowTitle("Arrange Sprite Rows")
        self.setModal(True)
        self.resize(1200, 700)
        
        self._load_sprite_data()
        self._setup_ui()
        self._update_status("Drag rows from left to right to arrange them")
        
    def _load_sprite_data(self):
        """Load sprite image and extract rows"""
        try:
            # Load the sprite sheet
            self.original_image = Image.open(self.sprite_path)
            
            # Convert palette mode images to grayscale for proper display
            if self.original_image.mode == 'P':
                # Convert palette indices to actual grayscale values
                self.original_image = self.original_image.convert('L')
            elif self.original_image.mode not in ['L', '1']:
                # Convert any other mode (RGB, RGBA, etc.) to grayscale
                self.original_image = self.original_image.convert('L')
            
            # Calculate tile dimensions dynamically
            image_width = self.original_image.width
            image_height = self.original_image.height
            
            # Calculate tile width based on tiles_per_row
            self.tile_width = image_width // self.tiles_per_row
            # Assume square tiles (most common case)
            self.tile_height = self.tile_width
            
            # Extract each row as a separate image
            num_rows = image_height // self.tile_height
            
            for row_idx in range(num_rows):
                y_start = row_idx * self.tile_height
                y_end = y_start + self.tile_height
                
                # Crop row
                row_image = self.original_image.crop((0, y_start, image_width, y_end))
                
                self.tile_rows.append({
                    'index': row_idx,
                    'image': row_image,
                    'tiles': image_width // self.tile_width
                })
                
        except Exception as e:
            print(f"Error loading sprite data: {e}")
            
    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Create main vertical splitter for resizable layout
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setHandleWidth(8)
        main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #555;
                border: 1px solid #666;
            }
            QSplitter::handle:hover {
                background-color: #666;
            }
        """)
        
        # Create horizontal splitter for main content (Available/Arranged panels)
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setHandleWidth(8)
        content_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #555;
                border: 1px solid #666;
            }
            QSplitter::handle:hover {
                background-color: #666;
            }
        """)
        
        # Left panel - Available rows
        left_panel = QGroupBox("Available Rows")
        left_panel.setMinimumWidth(200)
        left_layout = QVBoxLayout(left_panel)
        
        # Available rows list
        self.available_list = DragDropListWidget(accept_external_drops=False)
        self.available_list.itemDoubleClicked.connect(self._add_row_to_arrangement)
        self.available_list.itemSelectionChanged.connect(self._on_available_selection_changed)
        left_layout.addWidget(self.available_list)
        
        # Populate available rows
        self._populate_available_rows()
        
        # Quick action buttons
        buttons_layout = QHBoxLayout()
        
        self.add_all_btn = QPushButton("Add All →")
        self.add_all_btn.clicked.connect(self._add_all_rows)
        buttons_layout.addWidget(self.add_all_btn)
        
        self.add_selected_btn = QPushButton("Add Selected →")
        self.add_selected_btn.clicked.connect(self._add_selected_rows)
        buttons_layout.addWidget(self.add_selected_btn)
        
        left_layout.addLayout(buttons_layout)
        
        # Right panel - Arranged rows
        right_panel = QGroupBox("Arranged Rows")
        right_panel.setMinimumWidth(200)
        right_layout = QVBoxLayout(right_panel)
        
        # Arranged rows list
        self.arranged_list = DragDropListWidget(accept_external_drops=True)
        self.arranged_list.external_drop.connect(self._add_row_to_arrangement)
        self.arranged_list.item_dropped.connect(self._refresh_arrangement)
        self.arranged_list.itemDoubleClicked.connect(self._remove_row_from_arrangement)
        self.arranged_list.itemSelectionChanged.connect(self._on_arranged_selection_changed)
        right_layout.addWidget(self.arranged_list)
        
        # Arrangement controls
        controls_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self._clear_arrangement)
        controls_layout.addWidget(self.clear_btn)
        
        self.remove_selected_btn = QPushButton("← Remove Selected")
        self.remove_selected_btn.clicked.connect(self._remove_selected_rows)
        controls_layout.addWidget(self.remove_selected_btn)
        
        right_layout.addLayout(controls_layout)
        
        # Add panels to horizontal splitter
        content_splitter.addWidget(left_panel)
        content_splitter.addWidget(right_panel)
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 1)
        
        # Preview area
        preview_group = QGroupBox("Preview")
        preview_group.setMinimumHeight(150)
        preview_layout = QVBoxLayout(preview_group)
        
        # Preview scroll area (now resizable)
        scroll_area = QScrollArea()
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #2d2d2d; border: 1px solid #555;")
        scroll_area.setWidget(self.preview_label)
        scroll_area.setWidgetResizable(True)
        # Removed setMaximumHeight to allow resizing
        preview_layout.addWidget(scroll_area)
        
        # Add content and preview to main vertical splitter
        main_splitter.addWidget(content_splitter)
        main_splitter.addWidget(preview_group)
        
        # Set initial size ratios (70% for content, 30% for preview)
        main_splitter.setStretchFactor(0, 7)
        main_splitter.setStretchFactor(1, 3)
        
        layout.addWidget(main_splitter)
        
        # Status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        
        # Dialog buttons
        button_box = QDialogButtonBox()
        
        self.export_btn = QPushButton("Export Arranged")
        self.export_btn.clicked.connect(self._export_arranged)
        self.export_btn.setEnabled(False)
        button_box.addButton(self.export_btn, QDialogButtonBox.ButtonRole.ActionRole)
        
        button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
        # Initial preview
        self._update_preview()
        
    def _populate_available_rows(self):
        """Populate the available rows list"""
        self.available_list.clear()
        
        for row_data in self.tile_rows:
            row_index = row_data['index']
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, row_index)
            
            # Create enhanced thumbnail widget (selection state will be updated by selection handler)
            thumbnail = RowPreviewWidget(
                row_index, 
                row_data['image'],
                row_data['tiles'],
                False  # Initial state, will be updated by selection handler
            )
            
            item.setSizeHint(thumbnail.sizeHint())
            self.available_list.addItem(item)
            self.available_list.setItemWidget(item, thumbnail)
            
    def _populate_arranged_rows(self):
        """Populate the arranged rows list"""
        self.arranged_list.clear()
        
        for row_index in self.arranged_rows:
            if row_index < len(self.tile_rows):
                row_data = self.tile_rows[row_index]
                item = QListWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, row_index)
                
                # Create thumbnail widget (selection state will be updated by selection handler)
                thumbnail = RowPreviewWidget(
                    row_index, 
                    row_data['image'],
                    row_data['tiles'],
                    False  # Initial state, will be updated by selection handler
                )
                
                item.setSizeHint(thumbnail.sizeHint())
                self.arranged_list.addItem(item)
                self.arranged_list.setItemWidget(item, thumbnail)
    
    def _on_available_selection_changed(self):
        """Handle selection change in available rows list"""
        self._update_row_selection_state(self.available_list)
    
    def _on_arranged_selection_changed(self):
        """Handle selection change in arranged rows list"""
        self._update_row_selection_state(self.arranged_list)
    
    def _update_row_selection_state(self, list_widget):
        """Update the visual selection state of row preview widgets"""
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            widget = list_widget.itemWidget(item)
            if widget and isinstance(widget, RowPreviewWidget):
                is_selected = item.isSelected()
                widget.set_selected(is_selected)
                
    def _add_row_to_arrangement(self, row_index):
        """Add a row to the arrangement"""
        if isinstance(row_index, QListWidgetItem):
            # Handle double-click from available list
            row_index = row_index.data(Qt.ItemDataRole.UserRole)
            
        if row_index not in self.arranged_rows:
            self.arranged_rows.append(row_index)
            self._refresh_ui()
            self._update_status(f"Added row {row_index} to arrangement")
            
    def _remove_row_from_arrangement(self, item):
        """Remove a row from the arrangement"""
        if isinstance(item, QListWidgetItem):
            row_index = item.data(Qt.ItemDataRole.UserRole)
            if row_index in self.arranged_rows:
                self.arranged_rows.remove(row_index)
                self._refresh_ui()
                self._update_status(f"Removed row {row_index} from arrangement")
                
    def _add_all_rows(self):
        """Add all rows to arrangement"""
        for row_data in self.tile_rows:
            row_index = row_data['index']
            if row_index not in self.arranged_rows:
                self.arranged_rows.append(row_index)
        self._refresh_ui()
        self._update_status("Added all rows to arrangement")
        
    def _add_selected_rows(self):
        """Add selected rows to arrangement"""
        selected_items = self.available_list.selectedItems()
        added_count = 0
        
        for item in selected_items:
            row_index = item.data(Qt.ItemDataRole.UserRole)
            if row_index not in self.arranged_rows:
                self.arranged_rows.append(row_index)
                added_count += 1
                
        if added_count > 0:
            self._refresh_ui()
            self._update_status(f"Added {added_count} selected rows to arrangement")
            
    def _remove_selected_rows(self):
        """Remove selected rows from arrangement"""
        selected_items = self.arranged_list.selectedItems()
        removed_count = 0
        
        for item in selected_items:
            row_index = item.data(Qt.ItemDataRole.UserRole)
            if row_index in self.arranged_rows:
                self.arranged_rows.remove(row_index)
                removed_count += 1
                
        if removed_count > 0:
            self._refresh_ui()
            self._update_status(f"Removed {removed_count} selected rows from arrangement")
            
    def _clear_arrangement(self):
        """Clear all arranged rows"""
        self.arranged_rows.clear()
        self._refresh_ui()
        self._update_status("Cleared all arranged rows")
        
    def _refresh_arrangement(self):
        """Refresh arrangement after internal reordering"""
        # Get current order from the list widget
        new_order = []
        for i in range(self.arranged_list.count()):
            item = self.arranged_list.item(i)
            row_index = item.data(Qt.ItemDataRole.UserRole)
            new_order.append(row_index)
        
        self.arranged_rows = new_order
        self._update_preview()
        self._update_status("Reordered rows")
        
    def _refresh_ui(self):
        """Refresh both lists and preview"""
        self._populate_available_rows()
        self._populate_arranged_rows()
        self._update_preview()
        
        # Update export button state
        self.export_btn.setEnabled(len(self.arranged_rows) > 0)
        
    def _update_preview(self):
        """Update the preview with current arrangement"""
        if not self.arranged_rows:
            self._show_original_preview()
            return
            
        # Create arranged image
        arranged_image = self._create_arranged_image()
        
        if arranged_image:
            # Convert to QPixmap
            if arranged_image.mode == "P":
                img_rgb = arranged_image.convert("L")
                qimage = QImage(img_rgb.tobytes(),
                              img_rgb.width, img_rgb.height,
                              img_rgb.width, QImage.Format.Format_Grayscale8)
            else:
                qimage = QImage(arranged_image.tobytes(),
                              arranged_image.width, arranged_image.height,
                              arranged_image.width, QImage.Format.Format_Grayscale8)
            
            pixmap = QPixmap.fromImage(qimage)
            
            # Scale for preview
            scaled_pixmap = pixmap.scaled(
                pixmap.width() * 3, pixmap.height() * 3,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            
            self.preview_label.setPixmap(scaled_pixmap)
            
    def _show_original_preview(self):
        """Show original sprite sheet in preview"""
        if self.original_image:
            # Convert to QPixmap
            if self.original_image.mode == "P":
                img_rgb = self.original_image.convert("L")
                qimage = QImage(img_rgb.tobytes(),
                              img_rgb.width, img_rgb.height,
                              img_rgb.width, QImage.Format.Format_Grayscale8)
            else:
                qimage = QImage(self.original_image.tobytes(),
                              self.original_image.width, self.original_image.height,
                              self.original_image.width, QImage.Format.Format_Grayscale8)
            
            pixmap = QPixmap.fromImage(qimage)
            
            # Scale for preview
            scaled_pixmap = pixmap.scaled(
                pixmap.width() * 3, pixmap.height() * 3,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation
            )
            
            self.preview_label.setPixmap(scaled_pixmap)
            
    def _create_arranged_image(self):
        """Create image with arranged rows"""
        if not self.arranged_rows:
            return None
            
        # Calculate total height using calculated tile dimensions
        new_height = len(self.arranged_rows) * self.tile_height
        new_width = self.original_image.width
        
        # Create new image
        if self.original_image.mode == "P":
            arranged = Image.new("P", (new_width, new_height))
            arranged.putpalette(self.original_image.getpalette())
        else:
            arranged = Image.new("L", (new_width, new_height))
            
        # Copy rows in new arrangement
        y_offset = 0
        for row_idx in self.arranged_rows:
            if row_idx < len(self.tile_rows):
                row_image = self.tile_rows[row_idx]['image']
                arranged.paste(row_image, (0, y_offset))
                y_offset += self.tile_height
                
        return arranged
        
    def _export_arranged(self):
        """Export the arranged sprite sheet"""
        if not self.arranged_rows:
            return
            
        # Create arranged image
        arranged_image = self._create_arranged_image()
        
        if arranged_image:
            # Generate output path
            base_name = os.path.splitext(self.sprite_path)[0]
            self.output_path = f"{base_name}_arranged.png"
            
            # Save arranged image
            arranged_image.save(self.output_path)
            
            self._update_status(f"Exported arranged sprite sheet to {os.path.basename(self.output_path)}")
            
            # Accept dialog
            self.accept()
            
    def _update_status(self, message):
        """Update the status bar message"""
        self.status_bar.showMessage(message)
        
    def get_arranged_path(self):
        """Get the path to the arranged sprite sheet"""
        return self.output_path
        
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key.Key_Delete:
            # Delete selected rows from arrangement
            self._remove_selected_rows()
        elif event.key() == Qt.Key.Key_A and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+A: Add all rows
            self._add_all_rows()
        elif event.key() == Qt.Key.Key_Escape:
            # Escape: Clear arrangement
            self._clear_arrangement()
        else:
            super().keyPressEvent(event)