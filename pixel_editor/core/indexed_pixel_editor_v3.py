#!/usr/bin/env python3
"""
Indexed Pixel Editor for SNES Sprites - Phase 3 Refactored Version
Uses MVC architecture with separated UI components and controller
"""

# Standard library imports
import os
import sys

# Third-party imports
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QAction, QKeyEvent, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .pixel_editor_canvas_v3 import PixelCanvasV3

# Import refactored components
from .pixel_editor_controller_v3 import PixelEditorController

# Re-export for backward compatibility
from .pixel_editor_utils import debug_color, debug_exception, debug_log
from .widgets import ZoomableScrollArea
from .views.dialogs import PaletteSwitcherDialog, StartupDialog
from .views.panels import (
    OptionsPanel,
    PalettePanel,
    PreviewPanel,
    ToolPanel,
)

__all__ = [
    "IndexedPixelEditor",
    "PaletteSwitcherDialog",
    "debug_color",
    "debug_exception",
    "debug_log",
]


class IndexedPixelEditor(QMainWindow):
    """Main window for the indexed pixel editor - Phase 3 refactored"""

    def __init__(self, initial_file=None):
        super().__init__()

        # Store initial file if provided
        self.initial_file = initial_file

        # Initialize controller
        self.controller = PixelEditorController(self)

        # Connect controller signals
        self._connect_controller_signals()

        # Initialize UI
        self.init_ui()

        # Show startup dialog or auto-load last file
        self.handle_startup()

    def _connect_controller_signals(self):
        """Connect all controller signals to UI updates"""
        self.controller.imageChanged.connect(self._on_image_changed)
        self.controller.paletteChanged.connect(self._on_palette_changed)
        self.controller.titleChanged.connect(self.setWindowTitle)
        self.controller.statusMessage.connect(self._show_status_message)
        # Progress dialogs removed - operations now run without blocking UI
        self.controller.error.connect(self._show_error)

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Indexed Pixel Editor")
        self.setGeometry(100, 100, 800, 600)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)

        # Left panel - Tools, palette, options, preview
        left_panel = self._create_left_panel()
        layout.addWidget(left_panel)

        # Right panel - Canvas
        right_panel = self._create_right_panel()
        layout.addWidget(right_panel, 1)

        # Create menu bar
        self.create_menu_bar()

        # Create toolbar
        self.create_toolbar()

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add zoom indicator to status bar
        from PyQt6.QtWidgets import QLabel
        self.zoom_label = QLabel("Zoom: 400%")
        self.status_bar.addPermanentWidget(self.zoom_label)

        # Progress dialogs removed

        # Start with a new 8x8 image
        self.controller.new_file()

    def _create_left_panel(self) -> QWidget:
        """Create the left panel with tools, palette, options, and preview"""
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(200)

        # Tool panel
        self.tool_panel = ToolPanel()
        self.tool_panel.toolChanged.connect(self.controller.set_tool)
        self.tool_panel.brushSizeChanged.connect(self.controller.set_brush_size)
        left_layout.addWidget(self.tool_panel)

        # Palette panel
        self.palette_panel = PalettePanel()
        self.palette_panel.colorSelected.connect(self.controller.set_drawing_color)
        left_layout.addWidget(self.palette_panel)

        # Options panel
        self.options_panel = OptionsPanel()
        self.options_panel.gridToggled.connect(self._on_grid_toggled)
        self.options_panel.paletteToggled.connect(self._on_palette_toggled)
        self.options_panel.zoomChanged.connect(self._on_zoom_changed)
        self.options_panel.zoomToFit.connect(self._zoom_to_fit)
        left_layout.addWidget(self.options_panel)

        # Preview panel
        self.preview_panel = PreviewPanel()
        left_layout.addWidget(self.preview_panel)

        left_layout.addStretch()
        return left_panel

    def _create_right_panel(self) -> QWidget:
        """Create the right panel with the canvas"""
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Scroll area for canvas
        scroll_area = ZoomableScrollArea()

        # Create canvas with refactored implementation
        self.canvas = PixelCanvasV3(self.controller)

        # Connect canvas signals
        self.canvas.pixelPressed.connect(self.controller.handle_canvas_press)
        self.canvas.pixelMoved.connect(self.controller.handle_canvas_move)
        self.canvas.pixelReleased.connect(self.controller.handle_canvas_release)
        self.canvas.zoomRequested.connect(self._on_canvas_zoom_request)

        # Connect tool manager for color picker
        self.controller.tool_manager.set_color_picked_callback(self._on_color_picked)

        # Set initial mode
        self.canvas.set_greyscale_mode(not self.options_panel.is_palette_applied())

        scroll_area.setWidget(self.canvas)
        scroll_area.setWidgetResizable(False)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        right_layout.addWidget(scroll_area)
        return right_panel

    def create_menu_bar(self):
        """Create the menu bar"""
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

        save_with_colors_action = QAction("Save with Color Palette...", self)
        save_with_colors_action.triggered.connect(self.save_file_with_colors)

        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(save_with_colors_action)
        file_menu.addSeparator()

        # Palette loading actions
        load_palette_action = QAction("Load Palette File...", self)
        load_palette_action.triggered.connect(self.load_palette_file)
        file_menu.addAction(load_palette_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")

        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.undo)

        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.redo)

        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)

        # View menu
        view_menu = menubar.addMenu("View")

        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self._zoom_in)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self._zoom_out)

        view_menu.addAction(zoom_in_action)
        view_menu.addAction(zoom_out_action)
        
        # Zoom reset action
        zoom_reset_action = QAction("Reset Zoom", self)
        zoom_reset_action.setShortcut("Ctrl+0")
        zoom_reset_action.triggered.connect(self._zoom_reset)
        
        # Zoom to fit action
        zoom_fit_action = QAction("Zoom to Fit", self)
        zoom_fit_action.setShortcut("Ctrl+Shift+0")
        zoom_fit_action.triggered.connect(self._zoom_to_fit)
        
        view_menu.addAction(zoom_reset_action)
        view_menu.addAction(zoom_fit_action)
        view_menu.addSeparator()

        # Switch palette action
        self.switch_palette_action = QAction("Switch &Palette...", self)
        self.switch_palette_action.setShortcut("P")
        self.switch_palette_action.triggered.connect(self.show_palette_switcher)
        self.switch_palette_action.setEnabled(False)
        view_menu.addAction(self.switch_palette_action)

        # Recent files menu
        self.recent_menu = file_menu.addMenu("Recent Files")
        self.update_recent_files_menu()

    def create_toolbar(self):
        """Create the toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        toolbar.addAction("New", self.new_file)
        toolbar.addAction("Open", self.open_file)
        toolbar.addAction("Save", self.save_file)
        toolbar.addSeparator()
        toolbar.addAction("Undo", self.undo)
        toolbar.addAction("Redo", self.redo)

    # File operations
    def new_file(self):
        """Create a new file"""
        if self.check_save():
            self.controller.new_file()

    def open_file(self):
        """Open a file"""
        if not self.check_save():
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Indexed PNG", "", "PNG Files (*.png);;All Files (*)"
        )

        if file_path:
            self.controller.open_file(file_path)

    def save_file(self):
        """Save the current file"""
        current_path = self.controller.get_current_file_path()
        if current_path:
            self.controller.save_file(current_path)
        else:
            self.save_file_as()

    def save_file_as(self):
        """Save with a new filename"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Indexed PNG", "", "PNG Files (*.png)"
        )

        if file_path:
            if not file_path.endswith(".png"):
                file_path += ".png"
            self.controller.save_file(file_path)

    def save_file_with_colors(self):
        """Save with color palette applied"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save PNG with Color Palette", "", "PNG Files (*.png)"
        )

        if file_path:
            if not file_path.endswith(".png"):
                file_path += ".png"
            self.controller.save_file_with_colors(file_path)

    def load_palette_file(self):
        """Load a palette file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Palette File",
            "",
            "Palette Files (*.pal.json);;JSON Files (*.json);;All Files (*)",
        )

        if file_path:
            self.controller.load_palette_file(file_path)

    # UI callbacks
    def _on_image_changed(self):
        """Handle image change from controller"""
        # Canvas will update automatically via its signal connection
        self.update_preview()

    def _on_palette_changed(self):
        """Handle palette change from controller"""
        # Update palette widget
        colors = self.controller.palette_model.colors
        name = self.controller.palette_model.name
        self.palette_panel.set_palette(colors, name)

        # Enable palette switching if we have metadata
        if self.controller.has_metadata_palettes():
            self.switch_palette_action.setEnabled(True)

        # Update preview
        self.update_preview()

    def _on_grid_toggled(self, checked: bool):
        """Handle grid toggle"""
        self.canvas.set_grid_visible(checked)

    def _on_palette_toggled(self, checked: bool):
        """Handle palette/grayscale toggle"""
        self.canvas.set_greyscale_mode(not checked)
        self.update_preview()

    def _on_zoom_changed(self, value: int):
        """Handle zoom slider change"""
        self.canvas.set_zoom(value)
        self._update_zoom_label(value)

    def _zoom_to_fit(self):
        """Zoom to fit the visible area"""
        # First check if we have an image loaded
        if not self.controller.has_image():
            return
            
        # Get image size to validate dimensions
        image_size = self.controller.get_image_size()
        if not image_size:
            return
            
        img_width, img_height = image_size
        
        # Get viewport with robust error checking
        canvas_parent = self.canvas.parent()
        if not canvas_parent:
            return
            
        viewport = canvas_parent.parent()  # ScrollArea's viewport
        if not viewport:
            return
            
        # Calculate available viewport space (with padding)
        viewport_width = max(1, viewport.width() - 20)
        viewport_height = max(1, viewport.height() - 20)
        
        # Calculate zoom to fit using float division for precision
        zoom_x = viewport_width / img_width
        zoom_y = viewport_height / img_height
        
        # Round to nearest integer and clamp to valid range
        optimal_zoom = max(1, min(round(min(zoom_x, zoom_y)), 64))
        
        # Bypass normal zoom workflow to avoid problematic centering
        # Call canvas.set_zoom directly with center_on_canvas=False
        self.canvas.set_zoom(optimal_zoom, center_on_canvas=False)
        
        # Calculate proper pan offset to center the entire image in viewport
        canvas_width = self.canvas.width()
        canvas_height = self.canvas.height()
        
        # Calculate the size of the image at the new zoom level
        scaled_img_width = img_width * optimal_zoom
        scaled_img_height = img_height * optimal_zoom
        
        # Calculate pan offset to center the image in the canvas
        pan_x = (canvas_width - scaled_img_width) / 2
        pan_y = (canvas_height - scaled_img_height) / 2
        
        # Set the pan offset directly on the canvas
        self.canvas.pan_offset = QPointF(pan_x, pan_y)
        
        # Update the options panel slider without triggering signals
        # Block signals temporarily to avoid triggering _on_zoom_changed
        self.options_panel.zoom_slider.blockSignals(True)
        self.options_panel.zoom_slider.setValue(optimal_zoom)
        self.options_panel.zoom_label.setText(f"{optimal_zoom}x")
        self.options_panel.zoom_slider.blockSignals(False)
        
        # Update the zoom label in the main window
        self._update_zoom_label(optimal_zoom)
        
        # Trigger canvas update to reflect the changes
        self.canvas.update()

    def _zoom_in(self):
        """Zoom in"""
        current = self.options_panel.get_zoom()
        if current < 64:
            self.options_panel.set_zoom(min(64, current + 2))

    def _zoom_out(self):
        """Zoom out"""
        current = self.options_panel.get_zoom()
        if current > 1:
            self.options_panel.set_zoom(max(1, current - 2))
    
    def _zoom_reset(self):
        """Reset zoom to default level (4x)"""
        from .pixel_editor_constants import ZOOM_DEFAULT
        self.options_panel.set_zoom(ZOOM_DEFAULT)
    
    def _update_zoom_label(self, zoom_value: int):
        """Update the zoom percentage in status bar"""
        percentage = zoom_value * 100
        self.zoom_label.setText(f"Zoom: {percentage}%")
    
    def _on_canvas_zoom_request(self, zoom_value: int):
        """Handle zoom request from canvas (mouse wheel)"""
        self.options_panel.set_zoom(zoom_value)
        self._update_zoom_label(zoom_value)

    def _on_color_picked(self, color_index: int):
        """Handle color picked by picker tool"""
        self.palette_panel.set_selected_color(color_index)
        # Automatically switch back to pencil mode after picking a color
        self.tool_panel.set_tool("pencil")

    # Undo/Redo operations
    def undo(self):
        """Undo last operation"""
        self.controller.undo()

    def redo(self):
        """Redo last operation"""
        self.controller.redo()

    # Preview
    def update_preview(self):
        """Update the preview panels"""
        # Get main preview (respects grayscale mode)
        main_preview = self.controller.get_preview_pixmap(
            self.options_panel.is_palette_applied()
        )
        if main_preview:
            self.preview_panel.set_main_preview(main_preview)

        # Get color preview (always colored)
        color_preview = self.controller.get_preview_pixmap(True)
        if color_preview:
            self.preview_panel.set_color_preview(color_preview)

    # Progress handling methods removed

    def _show_status_message(self, message: str, timeout: int):
        """Show status bar message"""
        self.status_bar.showMessage(message, timeout)

    def _show_error(self, message: str):
        """Show error dialog"""
        QMessageBox.critical(self, "Error", message)

    # Startup and utilities
    def handle_startup(self):
        """Handle application startup"""
        # If initial file was provided (e.g., from command line), load it directly
        if self.initial_file:
            debug_log("EDITOR", f"Loading initial file: {self.initial_file}")
            self.controller.open_file(self.initial_file)
            return

        if self.controller.should_auto_load_last():
            last_file = self.controller.get_last_file()
            if last_file:
                debug_log("EDITOR", f"Auto-loading last file: {last_file}")
                self.controller.open_file(last_file)
                return

        # Show startup dialog
        recent_files = self.controller.get_recent_files()
        if recent_files or not self.controller.should_auto_load_last():
            self.show_startup_dialog()

    def show_startup_dialog(self):
        """Show the startup dialog"""
        dialog = StartupDialog(self.controller.settings, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.action == "new_file":
                self.new_file()
            elif dialog.action == "open_file":
                self.open_file()
            elif dialog.action == "open_recent" and dialog.selected_file:
                self.controller.open_file(dialog.selected_file)

    def show_palette_switcher(self):
        """Show palette switcher dialog"""
        palettes = self.controller.get_available_palettes()
        if not palettes:
            return

        dialog = PaletteSwitcherDialog(
            palettes, self.controller.palette_manager.current_palette_index, self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_index = dialog.get_selected_palette()
            if selected_index is not None:
                self.controller.switch_palette(selected_index)

    def update_recent_files_menu(self):
        """Update the recent files menu"""
        self.recent_menu.clear()

        recent_files = self.controller.get_recent_files()
        if not recent_files:
            action = self.recent_menu.addAction("No recent files")
            action.setEnabled(False)
            return

        for file_path in recent_files:
            if os.path.exists(file_path):
                action = self.recent_menu.addAction(os.path.basename(file_path))
                action.setToolTip(file_path)
                action.triggered.connect(
                    lambda checked, path=file_path: self.controller.open_file(path)
                )

        self.recent_menu.addSeparator()
        clear_action = self.recent_menu.addAction("Clear Recent Files")
        clear_action.triggered.connect(self.clear_recent_files)

    def clear_recent_files(self):
        """Clear recent files list"""
        self.controller.settings.clear_recent_files()
        self.update_recent_files_menu()

    # ========== LEGACY COMPATIBILITY API ==========
    # These methods provide backward compatibility with the original IndexedPixelEditor

    def load_file_by_path(self, file_path: str):
        """Legacy API: Load an image file"""
        self.controller.open_file(file_path)

    def new_image(self, width: int = 8, height: int = 8):
        """Legacy API: Create a new image with specified dimensions"""
        if self.check_save():
            self.controller.new_file(width, height)

    def save_to_file(self, file_path: str):
        """Legacy API: Save current image to file"""
        self.controller.save_file(file_path)

    def apply_palette(self, palette_idx: int, colors: list):
        """Legacy API: Apply a palette with given colors"""
        # Convert flat list to RGB tuples
        rgb_colors = []
        for i in range(0, len(colors), 3):
            if i + 2 < len(colors):
                rgb_colors.append((colors[i], colors[i + 1], colors[i + 2]))

        # Update palette model
        self.controller.palette_model.colors = rgb_colors[:16]
        self.controller.palette_model.name = f"Palette {palette_idx}"
        self.controller.palette_manager.add_palette(
            palette_idx, self.controller.palette_model
        )
        self.controller.palette_manager.current_palette_index = palette_idx
        self.controller.paletteChanged.emit()

    def toggle_color_mode_shortcut(self):
        """Legacy API: Toggle between color and grayscale mode"""
        checked = self.options_panel.apply_palette_checkbox.isChecked()
        self.options_panel.apply_palette_checkbox.setChecked(not checked)

    def set_zoom_preset(self, zoom_value: int):
        """Legacy API: Set specific zoom level"""
        self.options_panel.set_zoom(zoom_value)

    def _handle_load_result(self, img_array, metadata):
        """Legacy API: Handle loaded image result (for tests)"""
        # Create a mock worker result and pass to controller
        self.controller._handle_load_result(img_array, metadata)

    # ========== LEGACY PROPERTY ACCESSORS ==========

    @property
    def metadata(self):
        """Legacy API: Get current metadata"""
        # Return metadata-like dict for compatibility
        metadata = {}
        if self.controller.palette_manager.get_palette_count() > 1:
            # Build palette list from manager
            palettes = []
            for idx in range(16):
                pal = self.controller.palette_manager.get_palette(idx)
                if pal:
                    palettes.append(
                        {
                            "colors": [c for rgb in pal.colors for c in rgb],
                            "name": pal.name,
                        }
                    )
            if palettes:
                metadata["palettes"] = palettes
        return metadata if metadata else None

    @property
    def current_palette_index(self):
        """Legacy API: Get current palette index"""
        return self.controller.palette_manager.current_palette_index

    @property
    def palette_widget(self):
        """Legacy API: Get palette widget for direct access"""
        # Return the internal palette widget from palette panel
        return self.palette_panel.palette_widget

    @property
    def apply_palette_checkbox(self):
        """Legacy API: Get apply palette checkbox"""
        return self.options_panel.apply_palette_checkbox

    def check_save(self) -> bool:
        """Check if we need to save before continuing"""
        if self.controller.is_modified():
            reply = QMessageBox.question(
                self,
                "Save Changes?",
                "The image has been modified. Do you want to save your changes?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )

            if reply == QMessageBox.StandardButton.Save:
                self.save_file()
                return not self.controller.is_modified()
            if reply == QMessageBox.StandardButton.Cancel:
                return False

        return True

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard shortcuts"""
        if (
            event.key() == Qt.Key.Key_C
            and event.modifiers() == Qt.KeyboardModifier.NoModifier
        ):
            # Toggle color mode
            checked = self.options_panel.apply_palette_checkbox.isChecked()
            self.options_panel.apply_palette_checkbox.setChecked(not checked)
        elif (
            event.key() == Qt.Key.Key_G
            and event.modifiers() == Qt.KeyboardModifier.NoModifier
        ):
            # Toggle grid visibility
            checked = self.options_panel.grid_checkbox.isChecked()
            self.options_panel.grid_checkbox.setChecked(not checked)
        elif (
            event.key() == Qt.Key.Key_I
            and event.modifiers() == Qt.KeyboardModifier.NoModifier
        ):
            # Switch to color picker tool
            self.tool_panel.set_tool("picker")
        elif (
            event.key() == Qt.Key.Key_P
            and event.modifiers() == Qt.KeyboardModifier.NoModifier
        ):
            # Show palette switcher
            if self.controller.has_metadata_palettes():
                self.show_palette_switcher()
        elif (
            event.key() == Qt.Key.Key_F
            and event.modifiers() == Qt.KeyboardModifier.NoModifier
        ):
            # Zoom to fit
            self._zoom_to_fit()
        elif (
            event.key() == Qt.Key.Key_Z
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            # Undo
            self.undo()
        elif (
            event.key() == Qt.Key.Key_Y
            and event.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            # Redo
            self.redo()
        elif (
            event.key() == Qt.Key.Key_1
            and event.modifiers() == Qt.KeyboardModifier.NoModifier
        ):
            # Set brush size to 1
            self.controller.set_brush_size(1)
            self.tool_panel.set_brush_size(1)
        elif (
            event.key() == Qt.Key.Key_2
            and event.modifiers() == Qt.KeyboardModifier.NoModifier
        ):
            # Set brush size to 2
            self.controller.set_brush_size(2)
            self.tool_panel.set_brush_size(2)
        elif event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            # Arrow key panning
            pan_delta = 20  # pixels to pan
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                pan_delta = 50  # larger pan with Shift
            
            if event.key() == Qt.Key.Key_Left:
                self.canvas.pan_offset.setX(self.canvas.pan_offset.x() + pan_delta)
            elif event.key() == Qt.Key.Key_Right:
                self.canvas.pan_offset.setX(self.canvas.pan_offset.x() - pan_delta)
            elif event.key() == Qt.Key.Key_Up:
                self.canvas.pan_offset.setY(self.canvas.pan_offset.y() + pan_delta)
            elif event.key() == Qt.Key.Key_Down:
                self.canvas.pan_offset.setY(self.canvas.pan_offset.y() - pan_delta)
            
            self.canvas.update()
        else:
            super().keyPressEvent(event)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    editor = IndexedPixelEditor()

    # Load file from command line if provided
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        palette_file = None

        # Check for palette file argument
        if len(sys.argv) > 3 and sys.argv[2] == "-p":
            palette_file = sys.argv[3]

        # Show the editor first
        editor.show()

        # Load the image
        if os.path.exists(file_path):
            editor.controller.open_file(file_path)
            # Load palette if specified
            if palette_file and os.path.exists(palette_file):
                editor.controller.load_palette_file(palette_file)
        else:
            debug_log("MAIN", f"File not found: {file_path}", "ERROR")
    else:
        editor.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
