"""
Grid Arrangement Dialog for SpritePal
Flexible sprite arrangement supporting rows, columns, and custom tile groups
"""

import os
from enum import Enum

from PIL import Image
from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QImage,
    QKeyEvent,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .row_arrangement import PaletteColorizer
from .row_arrangement.grid_arrangement_manager import (
    ArrangementType,
    GridArrangementManager,
    TilePosition,
)
from .row_arrangement.grid_image_processor import GridImageProcessor
from .row_arrangement.grid_preview_generator import GridPreviewGenerator


class SelectionMode(Enum):
    """Selection modes for grid interaction"""

    TILE = "tile"
    ROW = "row"
    COLUMN = "column"
    RECTANGLE = "rectangle"


class GridGraphicsView(QGraphicsView):
    """Custom graphics view for grid-based sprite selection"""

    # Signals
    tile_clicked = pyqtSignal(TilePosition)
    tiles_selected = pyqtSignal(list)  # List of TilePosition
    selection_completed = pyqtSignal()
    zoom_changed = pyqtSignal(float)  # Zoom level changed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tile_width = 8
        self.tile_height = 8
        self.grid_cols = 0
        self.grid_rows = 0

        self.selection_mode = SelectionMode.TILE
        self.selecting = False
        self.selection_start: TilePosition | None = None
        self.current_selection: set[TilePosition] = set()

        # Zoom and pan state
        self.zoom_level = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 20.0
        self.is_panning = False
        self.last_pan_point = None

        # Visual elements
        self.grid_lines: list[QGraphicsLineItem] = []
        self.selection_rects: dict[TilePosition, QGraphicsRectItem] = {}
        self.hover_rect: QGraphicsRectItem | None = None

        # Colors
        self.grid_color = QColor(128, 128, 128, 64)
        self.selection_color = QColor(255, 255, 0, 128)
        self.hover_color = QColor(0, 255, 255, 64)
        self.arranged_color = QColor(0, 255, 0, 64)
        self.group_colors = [
            QColor(255, 0, 0, 64),
            QColor(0, 0, 255, 64),
            QColor(255, 128, 0, 64),
            QColor(128, 0, 255, 64),
        ]

        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)

    def set_grid_dimensions(
        self, cols: int, rows: int, tile_width: int, tile_height: int
    ):
        """Set the grid dimensions"""
        self.grid_cols = cols
        self.grid_rows = rows
        self.tile_width = tile_width
        self.tile_height = tile_height
        self._update_grid_lines()

    def set_selection_mode(self, mode: SelectionMode):
        """Set the selection mode"""
        self.selection_mode = mode
        self.clear_selection()

    def clear_selection(self):
        """Clear current selection"""
        self.current_selection.clear()
        scene = self.scene()
        if scene:
            for rect in self.selection_rects.values():
                scene.removeItem(rect)
        self.selection_rects.clear()

    def highlight_arranged_tiles(
        self, tiles: list[TilePosition], color: QColor | None = None
    ):
        """Highlight arranged tiles"""
        if color is None:
            color = self.arranged_color

        scene = self.scene()
        if scene:
            for tile_pos in tiles:
                if tile_pos not in self.selection_rects:
                    rect = self._create_tile_rect(tile_pos, color)
                    scene.addItem(rect)
                    self.selection_rects[tile_pos] = rect

    def mousePressEvent(self, event):  # noqa: N802
        """Handle mouse press"""
        if event and event.button() == Qt.MouseButton.LeftButton:
            # Check if we should pan instead of select
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.is_panning = True
                self.last_pan_point = event.pos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            else:
                pos = self.mapToScene(event.pos())
                tile_pos = self._pos_to_tile(pos)

                if tile_pos and self._is_valid_tile(tile_pos):
                    self.selecting = True
                    self.selection_start = tile_pos

                    if self.selection_mode == SelectionMode.TILE:
                        self.current_selection = {tile_pos}
                        self.tile_clicked.emit(tile_pos)
                    elif self.selection_mode == SelectionMode.ROW:
                        self._select_row(tile_pos.row)
                    elif self.selection_mode == SelectionMode.COLUMN:
                        self._select_column(tile_pos.col)
                    elif self.selection_mode == SelectionMode.RECTANGLE:
                        self.current_selection = {tile_pos}

                    self._update_selection_display()
        elif event and event.button() == Qt.MouseButton.MiddleButton:
            # Middle mouse button for panning
            self.is_panning = True
            self.last_pan_point = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802
        """Handle mouse move"""
        if event and self.is_panning and self.last_pan_point is not None:
            # Pan the view
            delta = event.pos() - self.last_pan_point
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            if h_bar:
                h_bar.setValue(h_bar.value() - delta.x())
            if v_bar:
                v_bar.setValue(v_bar.value() - delta.y())
            self.last_pan_point = event.pos()
        elif event:
            pos = self.mapToScene(event.pos())
            tile_pos = self._pos_to_tile(pos)

            # Update hover
            if tile_pos and self._is_valid_tile(tile_pos):
                self._update_hover(tile_pos)

            # Update rectangle selection
            if (self.selecting and self.selection_mode == SelectionMode.RECTANGLE and
                tile_pos and self._is_valid_tile(tile_pos) and self.selection_start):
                self._update_rectangle_selection(self.selection_start, tile_pos)

        super().mouseMoveEvent(event)

    def wheelEvent(self, event):  # noqa: N802
        """Handle mouse wheel for zooming"""
        if event and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Zoom with Ctrl+Wheel
            zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
            self._zoom_at_point(event.position().toPoint(), zoom_factor)
        else:
            # Default scroll behavior
            super().wheelEvent(event)

    def keyPressEvent(self, event):  # noqa: N802
        """Handle keyboard shortcuts for zoom"""
        if event and event.key() == Qt.Key.Key_F:
            # F: Zoom to fit
            self.zoom_to_fit()
        elif event and (
            event.key() == Qt.Key.Key_0
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            # Ctrl+0: Reset zoom
            self.reset_zoom()
        elif event and (
            event.key() == Qt.Key.Key_Plus
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            # Ctrl++: Zoom in
            self.zoom_in()
        elif event and (
            event.key() == Qt.Key.Key_Minus
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            # Ctrl+-: Zoom out
            self.zoom_out()
        else:
            super().keyPressEvent(event)

    def _zoom_at_point(self, point, zoom_factor):
        """Zoom at a specific point"""
        # Calculate new zoom level
        new_zoom = self.zoom_level * zoom_factor
        new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))

        if new_zoom != self.zoom_level:
            # Convert point to QPoint if needed
            point_as_qpoint = point.toPoint() if hasattr(point, "toPoint") else point

            # Get the scene position before zoom
            scene_pos = self.mapToScene(point_as_qpoint)

            # Apply zoom
            zoom_change = new_zoom / self.zoom_level
            self.scale(zoom_change, zoom_change)
            self.zoom_level = new_zoom

            # Adjust view to keep the point under cursor
            new_viewport_pos = self.mapFromScene(scene_pos)
            delta = point_as_qpoint - new_viewport_pos
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            if h_bar:
                h_bar.setValue(h_bar.value() - delta.x())
            if v_bar:
                v_bar.setValue(v_bar.value() - delta.y())

            # Emit zoom change signal
            self.zoom_changed.emit(self.zoom_level)

    def zoom_in(self):
        """Zoom in by a fixed factor"""
        viewport = self.viewport()
        if viewport:
            center = viewport.rect().center()
            self._zoom_at_point(center, 1.25)

    def zoom_out(self):
        """Zoom out by a fixed factor"""
        viewport = self.viewport()
        if viewport:
            center = viewport.rect().center()
            self._zoom_at_point(center, 0.8)

    def zoom_to_fit(self):
        """Zoom to fit the scene content"""
        if self.scene():
            # Reset zoom first
            self.resetTransform()
            self.zoom_level = 1.0

            # Fit the scene in view
            scene = self.scene()
            if scene:
                self.fitInView(
                    scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio
                )

            # Calculate the actual zoom level
            transform = self.transform()
            self.zoom_level = transform.m11()  # Get scale factor

            # Emit zoom change signal
            self.zoom_changed.emit(self.zoom_level)

    def reset_zoom(self):
        """Reset zoom to 1:1"""
        self.resetTransform()
        self.zoom_level = 1.0

        # Emit zoom change signal
        self.zoom_changed.emit(self.zoom_level)

    def get_zoom_level(self):
        """Get current zoom level"""
        return self.zoom_level

    def mouseReleaseEvent(self, event):  # noqa: N802
        """Handle mouse release"""
        if event and event.button() == Qt.MouseButton.LeftButton:
            if self.is_panning:
                self.is_panning = False
                self.last_pan_point = None
                self.setCursor(Qt.CursorShape.CrossCursor)
            elif self.selecting:
                self.selecting = False
                if self.current_selection:
                    self.tiles_selected.emit(list(self.current_selection))
                    self.selection_completed.emit()
        elif event and event.button() == Qt.MouseButton.MiddleButton and self.is_panning:
            self.is_panning = False
            self.last_pan_point = None
            self.setCursor(Qt.CursorShape.CrossCursor)

        super().mouseReleaseEvent(event)

    def _pos_to_tile(self, pos: QPointF) -> TilePosition | None:
        """Convert scene position to tile position"""
        if pos.x() < 0 or pos.y() < 0:
            return None

        col = int(pos.x() // self.tile_width)
        row = int(pos.y() // self.tile_height)

        return TilePosition(row, col)

    def _is_valid_tile(self, tile_pos: TilePosition) -> bool:
        """Check if tile position is valid"""
        return 0 <= tile_pos.row < self.grid_rows and 0 <= tile_pos.col < self.grid_cols

    def _create_tile_rect(
        self, tile_pos: TilePosition, color: QColor
    ) -> QGraphicsRectItem:
        """Create a rectangle for a tile"""
        x = tile_pos.col * self.tile_width
        y = tile_pos.row * self.tile_height
        rect = QGraphicsRectItem(x, y, self.tile_width, self.tile_height)
        rect.setPen(QPen(Qt.PenStyle.NoPen))
        rect.setBrush(QBrush(color))
        rect.setZValue(1)  # Above grid lines
        return rect

    def _update_grid_lines(self):
        """Update grid line display"""
        # Clear existing grid lines
        scene = self.scene()
        if scene:
            for line in self.grid_lines:
                if line.scene():
                    scene.removeItem(line)
        self.grid_lines.clear()

        if not scene:
            return

        pen = QPen(self.grid_color, 1)

        # Vertical lines
        for col in range(self.grid_cols + 1):
            x = col * self.tile_width
            line = scene.addLine(x, 0, x, self.grid_rows * self.tile_height, pen)
            if line:
                self.grid_lines.append(line)

        # Horizontal lines
        for row in range(self.grid_rows + 1):
            y = row * self.tile_height
            line = scene.addLine(0, y, self.grid_cols * self.tile_width, y, pen)
            if line:
                self.grid_lines.append(line)

    def _select_row(self, row: int):
        """Select an entire row"""
        self.current_selection = {
            TilePosition(row, col) for col in range(self.grid_cols)
        }

    def _select_column(self, col: int):
        """Select an entire column"""
        self.current_selection = {
            TilePosition(row, col) for row in range(self.grid_rows)
        }

    def _update_rectangle_selection(self, start: TilePosition, end: TilePosition):
        """Update rectangle selection"""
        min_row = min(start.row, end.row)
        max_row = max(start.row, end.row)
        min_col = min(start.col, end.col)
        max_col = max(start.col, end.col)

        self.current_selection = {
            TilePosition(row, col)
            for row in range(min_row, max_row + 1)
            for col in range(min_col, max_col + 1)
        }
        self._update_selection_display()

    def _update_selection_display(self):
        """Update visual display of selection"""
        # Clear existing selection rects
        scene = self.scene()
        if scene:
            for rect in self.selection_rects.values():
                if rect.scene():
                    scene.removeItem(rect)
        self.selection_rects.clear()

        # Add new selection rects
        if scene:
            for tile_pos in self.current_selection:
                rect = self._create_tile_rect(tile_pos, self.selection_color)
                scene.addItem(rect)
                self.selection_rects[tile_pos] = rect

    def _update_hover(self, tile_pos: TilePosition):
        """Update hover display"""
        scene = self.scene()
        if self.hover_rect:
            if self.hover_rect.scene() and scene:
                scene.removeItem(self.hover_rect)
            self.hover_rect = None

        if tile_pos not in self.current_selection and scene:
            self.hover_rect = self._create_tile_rect(tile_pos, self.hover_color)
            self.hover_rect.setZValue(0.5)  # Below selection
            scene.addItem(self.hover_rect)


class GridArrangementDialog(QDialog):
    """Dialog for grid-based sprite arrangement with row and column support"""

    def __init__(self, sprite_path: str, tiles_per_row: int = 16, parent=None):
        super().__init__(parent)
        self.sprite_path = sprite_path
        self.tiles_per_row = tiles_per_row
        self.output_path = None

        # Initialize components
        self.processor = GridImageProcessor()
        self.colorizer = PaletteColorizer()
        self.preview_generator = GridPreviewGenerator(self.colorizer)

        # Load and process sprite
        try:
            self.original_image, self.tiles = (
                self.processor.process_sprite_sheet_as_grid(sprite_path, tiles_per_row)
            )
        except Exception as e:
            # Show error dialog and close
            QMessageBox.critical(
                parent, "Error Loading Sprite", f"Failed to load sprite file:\n{e!s}"
            )
            # Set up minimal state to prevent crashes
            self.original_image = None
            self.tiles = {}
            self.processor.grid_rows = 1
            self.processor.grid_cols = 1
            # Don't return here - continue with dialog setup but in error state

        # Create arrangement manager
        self.arrangement_manager = GridArrangementManager(
            self.processor.grid_rows, self.processor.grid_cols
        )

        # Connect signals
        self.arrangement_manager.arrangement_changed.connect(
            self._on_arrangement_changed
        )
        self.colorizer.palette_mode_changed.connect(self._on_palette_mode_changed)

        # Set up UI
        self.setWindowTitle("Grid-Based Sprite Arrangement")
        self.setModal(True)
        self.resize(1600, 900)
        self._setup_ui()

        # Initial update (only if we have valid data)
        if self.original_image is not None:
            self._update_displays()
            self._update_status(
                "Select tiles, rows, or columns to arrange. Ctrl+Wheel or F to zoom."
            )
        else:
            self._update_status("Error: Unable to load sprite file")

    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QVBoxLayout(self)

        # Create main splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Grid view and controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # Selection mode controls
        mode_group = QGroupBox("Selection Mode")
        mode_layout = QHBoxLayout()

        self.mode_buttons = QButtonGroup()
        for mode in SelectionMode:
            btn = QRadioButton(mode.value.capitalize())
            btn.setProperty("mode", mode)
            self.mode_buttons.addButton(btn)
            mode_layout.addWidget(btn)
            if mode == SelectionMode.TILE:
                btn.setChecked(True)

        self.mode_buttons.buttonClicked.connect(self._on_mode_changed)
        mode_group.setLayout(mode_layout)
        left_layout.addWidget(mode_group)

        # Grid view
        grid_group = QGroupBox("Sprite Grid")
        grid_layout = QVBoxLayout()

        # Create graphics scene and view
        self.scene = QGraphicsScene()
        self.grid_view = GridGraphicsView()
        self.grid_view.setScene(self.scene)

        # Set up grid view (only if we have valid data)
        if self.original_image is not None:
            pixmap = self._create_pixmap_from_image(self.original_image)
            self.pixmap_item = self.scene.addPixmap(pixmap)
            self.grid_view.set_grid_dimensions(
                self.processor.grid_cols,
                self.processor.grid_rows,
                self.processor.tile_width,
                self.processor.tile_height,
            )
        else:
            # Create placeholder for error state
            self.pixmap_item = None

        # Connect grid view signals
        self.grid_view.tile_clicked.connect(self._on_tile_clicked)
        self.grid_view.tiles_selected.connect(self._on_tiles_selected)

        # Connect zoom level updates
        self.grid_view.zoom_changed.connect(self._on_zoom_changed)
        self._update_zoom_level_display()

        grid_layout.addWidget(self.grid_view)
        grid_group.setLayout(grid_layout)
        left_layout.addWidget(grid_group, 1)

        # Action buttons
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Selection")
        self.add_btn.clicked.connect(self._add_selection)
        actions_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("Remove Selection")
        self.remove_btn.clicked.connect(self._remove_selection)
        actions_layout.addWidget(self.remove_btn)

        self.create_group_btn = QPushButton("Create Group")
        self.create_group_btn.clicked.connect(self._create_group)
        actions_layout.addWidget(self.create_group_btn)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self._clear_arrangement)
        actions_layout.addWidget(self.clear_btn)

        # Separator
        actions_layout.addWidget(QLabel("|"))

        # Zoom controls
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.clicked.connect(self.grid_view.zoom_out)
        self.zoom_out_btn.setMaximumWidth(30)
        actions_layout.addWidget(self.zoom_out_btn)

        self.zoom_level_label = QLabel("100%")
        self.zoom_level_label.setMinimumWidth(50)
        self.zoom_level_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        actions_layout.addWidget(self.zoom_level_label)

        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.clicked.connect(self.grid_view.zoom_in)
        self.zoom_in_btn.setMaximumWidth(30)
        actions_layout.addWidget(self.zoom_in_btn)

        self.zoom_fit_btn = QPushButton("Fit")
        self.zoom_fit_btn.clicked.connect(self.grid_view.zoom_to_fit)
        self.zoom_fit_btn.setMaximumWidth(40)
        actions_layout.addWidget(self.zoom_fit_btn)

        self.zoom_reset_btn = QPushButton("1:1")
        self.zoom_reset_btn.clicked.connect(self.grid_view.reset_zoom)
        self.zoom_reset_btn.setMaximumWidth(40)
        actions_layout.addWidget(self.zoom_reset_btn)

        actions_group.setLayout(actions_layout)
        left_layout.addWidget(actions_group)

        # Right panel - Arrangement list and preview
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # Arrangement list
        list_group = QGroupBox("Current Arrangement")
        list_layout = QVBoxLayout()

        self.arrangement_list = QListWidget()
        list_layout.addWidget(self.arrangement_list)

        list_group.setLayout(list_layout)
        right_layout.addWidget(list_group)

        # Preview
        preview_group = QGroupBox("Arrangement Preview")
        preview_layout = QVBoxLayout()

        scroll_area = QScrollArea()
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll_area.setWidget(self.preview_label)
        scroll_area.setWidgetResizable(True)
        preview_layout.addWidget(scroll_area)

        preview_group.setLayout(preview_layout)
        right_layout.addWidget(preview_group, 1)

        # Add panels to splitter
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setStretchFactor(0, 2)
        main_splitter.setStretchFactor(1, 1)

        layout.addWidget(main_splitter)

        # Status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)

        # Dialog buttons
        button_box = QDialogButtonBox()

        self.export_btn = QPushButton("Export Arrangement")
        self.export_btn.clicked.connect(self._export_arrangement)
        self.export_btn.setEnabled(False)
        button_box.addButton(self.export_btn, QDialogButtonBox.ButtonRole.ActionRole)

        button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

    def _on_mode_changed(self, button) -> None:
        """Handle selection mode change"""
        mode = button.property("mode")
        self.grid_view.set_selection_mode(mode)
        self._update_status(f"Selection mode: {mode.value}")

    def _on_tile_clicked(self, tile_pos: TilePosition) -> None:
        """Handle single tile click"""
        # In tile mode, immediately add/remove the tile
        if self.grid_view.selection_mode == SelectionMode.TILE:
            if self.arrangement_manager.is_tile_arranged(tile_pos):
                self.arrangement_manager.remove_tile(tile_pos)
            else:
                self.arrangement_manager.add_tile(tile_pos)

    def _on_tiles_selected(self, tiles: list[TilePosition]) -> None:
        """Handle tile selection"""
        self._update_status(f"Selected {len(tiles)} tiles")

    def _add_selection(self):
        """Add current selection to arrangement"""
        selection = list(self.grid_view.current_selection)

        if not selection:
            return

        if self.grid_view.selection_mode == SelectionMode.ROW:
            # Add as row
            row = selection[0].row
            self.arrangement_manager.add_row(row)
        elif self.grid_view.selection_mode == SelectionMode.COLUMN:
            # Add as column
            col = selection[0].col
            self.arrangement_manager.add_column(col)
        else:
            # Add individual tiles
            for tile_pos in selection:
                self.arrangement_manager.add_tile(tile_pos)

        self.grid_view.clear_selection()

    def _remove_selection(self):
        """Remove current selection from arrangement"""
        selection = list(self.grid_view.current_selection)

        for tile_pos in selection:
            self.arrangement_manager.remove_tile(tile_pos)

        self.grid_view.clear_selection()

    def _create_group(self):
        """Create a group from current selection"""
        selection = list(self.grid_view.current_selection)

        if len(selection) < 2:
            self._update_status("Select at least 2 tiles to create a group")
            return

        # Generate group ID
        group_id = f"group_{len(self.arrangement_manager.get_groups())}"

        # Create group
        group = self.arrangement_manager.create_group_from_selection(
            selection,
            group_id,
            f"Custom Group {len(self.arrangement_manager.get_groups()) + 1}",
        )

        if group:
            self._update_status(f"Created group with {len(selection)} tiles")
            self.grid_view.clear_selection()
        else:
            self._update_status("Some tiles are already arranged")

    def _clear_arrangement(self):
        """Clear all arrangements"""
        self.arrangement_manager.clear()
        self.grid_view.clear_selection()
        self._update_status("Cleared all arrangements")

    def _on_arrangement_changed(self):
        """Handle arrangement change"""
        self._update_displays()
        self.export_btn.setEnabled(self.arrangement_manager.get_arranged_count() > 0)

    def _on_palette_mode_changed(self, enabled: bool):
        """Handle palette mode change"""
        self._update_displays()

    def _update_displays(self):
        """Update all display elements"""
        # Update grid view highlights
        arranged_tiles = self.arrangement_manager.get_arranged_tiles()
        self.grid_view.highlight_arranged_tiles(arranged_tiles)

        # Update arrangement list
        self._update_arrangement_list()

        # Update preview
        self._update_preview()

    def _update_arrangement_list(self):
        """Update the arrangement list widget"""
        self.arrangement_list.clear()

        for arr_type, key in self.arrangement_manager.get_arrangement_order():
            if arr_type == ArrangementType.ROW:
                item_text = f"Row {key}"
            elif arr_type == ArrangementType.COLUMN:
                item_text = f"Column {key}"
            elif arr_type == ArrangementType.TILE:
                row, col = key.split(",")
                item_text = f"Tile ({row}, {col})"
            elif arr_type == ArrangementType.GROUP:
                group = self.arrangement_manager.get_groups().get(key)
                item_text = group.name if group else f"Group {key}"
            else:
                item_text = str(key)

            self.arrangement_list.addItem(item_text)

    def _update_preview(self):
        """Update the arrangement preview"""
        arranged_image = self.preview_generator.create_grid_arranged_image(
            self.processor, self.arrangement_manager, spacing=2
        )

        if arranged_image:
            pixmap = self._create_pixmap_from_image(arranged_image)
            # Scale for preview
            scaled = pixmap.scaled(
                pixmap.width() * 2,
                pixmap.height() * 2,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
            self.preview_label.setPixmap(scaled)
        else:
            self.preview_label.clear()
            self.preview_label.setText("No arrangement")

    def _create_pixmap_from_image(self, image: Image.Image) -> QPixmap:
        """Convert PIL Image to QPixmap"""
        if image.mode == "RGBA":
            qimage = QImage(
                image.tobytes(),
                image.width,
                image.height,
                image.width * 4,
                QImage.Format.Format_RGBA8888,
            )
        elif image.mode == "RGB":
            qimage = QImage(
                image.tobytes(),
                image.width,
                image.height,
                image.width * 3,
                QImage.Format.Format_RGB888,
            )
        elif image.mode == "L":
            qimage = QImage(
                image.tobytes(),
                image.width,
                image.height,
                image.width,
                QImage.Format.Format_Grayscale8,
            )
        elif image.mode == "P":
            # Convert palette mode to RGB
            rgb_image = image.convert("RGB")
            qimage = QImage(
                rgb_image.tobytes(),
                rgb_image.width,
                rgb_image.height,
                rgb_image.width * 3,
                QImage.Format.Format_RGB888,
            )
        else:
            # Fallback conversion
            rgb_image = image.convert("RGB")
            qimage = QImage(
                rgb_image.tobytes(),
                rgb_image.width,
                rgb_image.height,
                rgb_image.width * 3,
                QImage.Format.Format_RGB888,
            )

        return QPixmap.fromImage(qimage)

    def _export_arrangement(self):
        """Export the current arrangement"""
        if self.arrangement_manager.get_arranged_count() == 0:
            self._update_status("No tiles arranged for export")
            return

        # Check if we have valid data
        if self.original_image is None:
            self._update_status("Cannot export: No valid sprite data")
            return

        try:
            # Create arranged image
            arranged_image = self.preview_generator.create_grid_arranged_image(
                self.processor, self.arrangement_manager
            )

            if arranged_image:
                self.output_path = self.preview_generator.export_grid_arrangement(
                    self.sprite_path, arranged_image, "grid"
                )

                # Save arrangement data
                self.preview_generator.create_arrangement_preview_data(
                    self.arrangement_manager, self.processor
                )

                self._update_status(f"Exported to {os.path.basename(self.output_path)}")
                self.accept()
            else:
                self._update_status("Error: Failed to create arranged image")

        except Exception as e:
            self._update_status(f"Export failed: {e!s}")
            QMessageBox.warning(
                self, "Export Error", f"Failed to export arrangement:\n{e!s}"
            )

    def _update_status(self, message: str):
        """Update status bar message"""
        self.status_bar.showMessage(message)

    def _update_zoom_level_display(self):
        """Update the zoom level display"""
        if hasattr(self, "zoom_level_label"):
            zoom_percent = int(self.grid_view.get_zoom_level() * 100)
            self.zoom_level_label.setText(f"{zoom_percent}%")

    def _on_zoom_changed(self, zoom_level):
        """Handle zoom level change"""
        self._update_zoom_level_display()

    def keyPressEvent(self, a0: QKeyEvent | None):  # noqa: N802
        """Handle keyboard shortcuts"""
        if a0 and a0.key() == Qt.Key.Key_G:
            # Toggle grid (already handled by view)
            pass
        elif a0 and a0.key() == Qt.Key.Key_C:
            # Toggle palette
            self.colorizer.toggle_palette_mode()
        elif a0 and a0.key() == Qt.Key.Key_P and self.colorizer.is_palette_mode():
            # Cycle palette
            self.colorizer.cycle_palette()
        elif a0 and a0.key() == Qt.Key.Key_Delete:
            # Remove selection
            self._remove_selection()
        elif a0 and a0.key() == Qt.Key.Key_Escape:
            # Clear selection
            self.grid_view.clear_selection()
        elif a0:
            # Let the grid view handle zoom shortcuts
            self.grid_view.keyPressEvent(a0)
            self._update_zoom_level_display()
            super().keyPressEvent(a0)

    def set_palettes(self, palettes_dict: dict):
        """Set available palettes for colorization"""
        self.colorizer.set_palettes(palettes_dict)
        self._update_displays()

    def get_arranged_path(self) -> str | None:
        """Get the path to the exported arrangement"""
        return self.output_path

    def closeEvent(self, a0) -> None:  # noqa: N802
        """Handle dialog close event with proper cleanup"""
        self._cleanup_resources()
        super().closeEvent(a0)

    def _cleanup_resources(self) -> None:
        """Clean up resources to prevent memory leaks"""
        # Clear colorizer cache
        if hasattr(self, "colorizer"):
            self.colorizer.clear_cache()

        # Clear graphics scene items
        if hasattr(self, "scene"):
            self.scene.clear()

        # Clear grid view selections
        if hasattr(self, "grid_view"):
            self.grid_view.clear_selection()
            if hasattr(self.grid_view, "selection_rects"):
                self.grid_view.selection_rects.clear()

        # Clear processor data
        if hasattr(self, "processor"):
            self.processor.tiles.clear()
            self.processor.original_image = None

        # Clear arrangement manager
        if hasattr(self, "arrangement_manager"):
            self.arrangement_manager.clear()
