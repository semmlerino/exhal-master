#!/usr/bin/env python3
"""
Controller for palette management functionality
Manages interaction between palette views and palette model
"""

import os

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from .base_controller import BaseController


class PaletteController(BaseController):
    """Controller for palette operations"""

    def __init__(self, sprite_model, palette_model,
                 project_model, multi_palette_view, parent=None):
        self.sprite_model = sprite_model
        self.project_model = project_model
        super().__init__(palette_model, multi_palette_view, parent)

    def connect_signals(self):
        """Connect signals between models and view"""
        # View signals
        self.view.browse_oam_requested.connect(self.browse_oam_file)
        self.view.generate_preview_requested.connect(
            self.generate_multi_palette_preview)
        self.view.palette_selected.connect(self.on_palette_selected)

        # Model signals
        self.sprite_model.oam_file_changed.connect(self.view.set_oam_file)

    def browse_oam_file(self):
        """Browse for OAM dump file"""
        # Get initial directory
        initial_dir = ""
        if self.sprite_model.oam_file and os.path.exists(
                os.path.dirname(self.sprite_model.oam_file)):
            initial_dir = os.path.dirname(self.sprite_model.oam_file)

        file_name, _ = QFileDialog.getOpenFileName(
            self.view, "Select OAM Dump",
            initial_dir,
            "Dump Files (*.dmp);;All Files (*.*)"
        )

        if file_name:
            self.sprite_model.oam_file = file_name
            self.project_model.add_recent_file(file_name, 'oam')

            # Load OAM data
            if self.sprite_model.load_oam_mapping():
                QMessageBox.information(
                    self.view, "Success", "OAM data loaded successfully")
            else:
                QMessageBox.warning(
                    self.view, "Error", "Failed to load OAM data")

    def load_palettes(self):
        """Load all palettes from CGRAM"""
        if self.sprite_model.cgram_file:
            count = self.palette_model.load_palettes_from_cgram(
                self.sprite_model.cgram_file)
            return count > 0
        return False

    def generate_multi_palette_preview(self):
        """Generate multi-palette preview"""
        # Check prerequisites
        if not self.sprite_model.vram_file:
            QMessageBox.warning(
                self.view,
                "Error",
                "Please load a VRAM file first")
            return

        if not self.sprite_model.cgram_file:
            QMessageBox.warning(
                self.view,
                "Error",
                "Please load a CGRAM file for palettes")
            return

        try:
            # Get preview size
            preview_tiles = self.view.get_preview_size()
            preview_size = preview_tiles * 32  # 32 bytes per tile

            # Use fewer tiles per row for preview
            preview_tiles_per_row = min(8, self.sprite_model.tiles_per_row)

            # Get OAM statistics if available
            oam_stats = None
            if self.sprite_model.core.oam_mapper:
                oam_stats = self.sprite_model.core.oam_mapper.get_palette_usage_stats()
                self.palette_model.set_oam_statistics(oam_stats)

            # Extract base sprite data
            base_img, total_tiles = self.sprite_model.core.extract_sprites(
                self.sprite_model.vram_file,
                self.sprite_model.extraction_offset,
                preview_size,
                preview_tiles_per_row
            )

            # Load all palettes
            self.load_palettes()
            palettes = self.palette_model.get_all_palettes()

            # Set images in multi-palette viewer
            self.view.set_single_image_all_palettes(base_img, palettes)

            # Set OAM statistics if available
            if oam_stats:
                self.view.set_oam_statistics(oam_stats)

            QMessageBox.information(self.view, "Success",
                                    f"Generated multi-palette preview ({total_tiles} tiles)")

        except Exception as e:
            QMessageBox.critical(self.view, "Error",
                                 f"Failed to generate preview: {str(e)}")

    def on_palette_selected(self, palette_num):
        """Handle palette selection in multi-palette viewer"""
        # Apply the selected palette to the current image
        if self.sprite_model.current_image:
            if self.palette_model.apply_palette_to_image(
                self.sprite_model.current_image, palette_num
            ):
                # Palette applied signal will trigger viewer update
                pass

    def export_palette(self, palette_index, format='act'):
        """Export a palette to file"""
        # Get file name
        filter_map = {
            'act': "Adobe Color Table (*.act)",
            'pal': "JASC Palette (*.pal)",
            'gpl': "GIMP Palette (*.gpl)"
        }

        file_name, _ = QFileDialog.getSaveFileName(
            self.view, "Export Palette",
            f"palette_{palette_index}.{format}",
            filter_map.get(format, "All Files (*.*)")
        )

        if file_name:
            data = self.palette_model.export_palette(palette_index, format)
            if data:
                if isinstance(data, bytes):
                    with open(file_name, 'wb') as f:
                        f.write(data)
                else:
                    with open(file_name, 'w') as f:
                        f.write(data)

                QMessageBox.information(self.view, "Success",
                                        f"Palette exported to {file_name}")
            else:
                QMessageBox.warning(self.view, "Error",
                                    "Failed to export palette")
