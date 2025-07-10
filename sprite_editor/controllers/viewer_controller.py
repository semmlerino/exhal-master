#!/usr/bin/env python3
"""
Controller for sprite viewer functionality
Manages interaction between viewer tab and sprite/palette models
"""

import os
import subprocess
import sys
import tempfile

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from .base_controller import BaseController


class ViewerController(BaseController):
    """Controller for viewer operations"""

    def __init__(self, sprite_model, palette_model, viewer_view, parent=None):
        self.palette_model = palette_model
        super().__init__(sprite_model, viewer_view, parent)

    def connect_signals(self):
        """Connect signals between model and view"""
        # View signals
        self.view.zoom_in_requested.connect(self.zoom_in)
        self.view.zoom_out_requested.connect(self.zoom_out)
        self.view.zoom_fit_requested.connect(self.zoom_fit)
        self.view.grid_toggled.connect(self.toggle_grid)
        self.view.save_requested.connect(self.save_current_view)
        self.view.open_editor_requested.connect(self.open_in_editor)

        # Model signals
        self.model.current_image_changed.connect(self.set_image)
        self.palette_model.palette_applied.connect(self._on_palette_applied)

    def set_image(self, image):
        """Set the image in the viewer"""
        if image:
            self.view.set_image(image)
            self.update_image_info()

            # Update palette viewer if image has palette
            if hasattr(image, "getpalette") and image.getpalette():
                self.view.set_palette(image.getpalette())

    def zoom_in(self):
        """Zoom in the viewer"""
        viewer = self.view.get_sprite_viewer()
        viewer.zoom_in()
        self.view.update_zoom_label(viewer.get_current_zoom())

    def zoom_out(self):
        """Zoom out the viewer"""
        viewer = self.view.get_sprite_viewer()
        viewer.zoom_out()
        self.view.update_zoom_label(viewer.get_current_zoom())

    def zoom_fit(self):
        """Fit image to window"""
        viewer = self.view.get_sprite_viewer()
        viewer.zoom_fit()
        self.view.update_zoom_label(viewer.get_current_zoom())

    def toggle_grid(self, checked):
        """Toggle grid overlay"""
        viewer = self.view.get_sprite_viewer()
        viewer.set_show_grid(checked)

    def update_image_info(self):
        """Update image information display"""
        viewer = self.view.get_sprite_viewer()
        info = viewer.get_image_info()
        self.view.update_image_info(info)

    def save_current_view(self):
        """Save the current view to file"""
        if not self.model.current_image:
            QMessageBox.warning(self.view, "Error", "No image to save")
            return

        file_name, _ = QFileDialog.getSaveFileName(
            self.view, "Save Image", "sprites.png", "PNG Files (*.png);;All Files (*.*)"
        )

        if file_name:
            self.model.current_image.save(file_name)
            QMessageBox.information(self.view, "Success", f"Image saved to {file_name}")

    def open_in_editor(self):
        """Open current image in external editor"""
        if not self.model.current_image:
            QMessageBox.warning(self.view, "Error", "No image to edit")
            return

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            self.model.current_image.save(tmp.name)

            # Open with default editor
            if sys.platform == "win32":
                os.startfile(tmp.name)
            elif sys.platform == "darwin":
                subprocess.run(["open", tmp.name], check=False)
            else:
                subprocess.run(["xdg-open", tmp.name], check=False)

    def _on_palette_applied(self, palette_index):
        """Handle palette application"""
        # Refresh the image display
        if self.model.current_image:
            self.set_image(self.model.current_image)
