#!/usr/bin/env python3
"""
Main controller for coordinating all sub-controllers
Acts as the central coordinator for the application
"""

from PyQt6.QtCore import QObject

from .extract_controller import ExtractController
from .inject_controller import InjectController
from .palette_controller import PaletteController
from .viewer_controller import ViewerController


class MainController(QObject):
    """Main controller coordinating all application controllers"""

    def __init__(self, models, views, parent=None):
        super().__init__(parent)

        # Store models
        self.sprite_model = models["sprite"]
        self.project_model = models["project"]
        self.palette_model = models["palette"]

        # Store views
        self.main_window = views["main_window"]
        self.extract_tab = views["extract_tab"]
        self.inject_tab = views["inject_tab"]
        self.viewer_tab = views["viewer_tab"]
        self.multi_palette_tab = views["multi_palette_tab"]

        # Create sub-controllers
        self.extract_controller = ExtractController(
            self.sprite_model, self.project_model, self.extract_tab, self
        )

        self.inject_controller = InjectController(
            self.sprite_model, self.project_model, self.inject_tab, self
        )

        self.viewer_controller = ViewerController(
            self.sprite_model, self.palette_model, self.viewer_tab, self
        )

        self.palette_controller = PaletteController(
            self.sprite_model,
            self.palette_model,
            self.project_model,
            self.multi_palette_tab,
            self,
        )

        # Connect main window signals
        self._connect_main_window_signals()

        # Connect cross-controller signals
        self._connect_cross_controller_signals()

        # Initialize from saved state
        self._initialize_from_settings()

    def _connect_main_window_signals(self):
        """Connect main window signals"""
        # Menu actions
        if hasattr(self.main_window, "action_open_vram"):
            self.main_window.action_open_vram.triggered.connect(
                self.extract_controller.browse_vram_file
            )

        if hasattr(self.main_window, "action_open_cgram"):
            self.main_window.action_open_cgram.triggered.connect(
                self.extract_controller.browse_cgram_file
            )

        # Recent files
        if hasattr(self.main_window, "recent_vram_selected"):
            self.main_window.recent_vram_selected.connect(
                self.extract_controller.load_recent_vram
            )

        if hasattr(self.main_window, "recent_cgram_selected"):
            self.main_window.recent_cgram_selected.connect(
                self.extract_controller.load_recent_cgram
            )

        # Settings actions
        if hasattr(self.main_window, "reset_settings_requested"):
            self.main_window.reset_settings_requested.connect(
                self.project_model.reset_settings
            )

        if hasattr(self.main_window, "clear_recent_requested"):
            self.main_window.clear_recent_requested.connect(
                self.project_model.clear_recent_files
            )

    def _connect_cross_controller_signals(self):
        """Connect signals between controllers"""
        # When extraction completes, update viewer
        self.sprite_model.extraction_completed.connect(self._on_extraction_completed)

        # When palette changes, update viewer
        self.palette_model.palette_applied.connect(self._on_palette_applied)

        # When files change, update inject tab
        self.sprite_model.vram_file_changed.connect(
            lambda path: self.inject_tab.set_vram_file(path)
        )

    def _initialize_from_settings(self):
        """Initialize application from saved settings"""
        # Get last used files
        last_files = self.project_model.get_last_used_files()

        # Restore file paths
        if last_files["vram"]:
            self.sprite_model.vram_file = last_files["vram"]

        if last_files["cgram"]:
            self.sprite_model.cgram_file = last_files["cgram"]

        if last_files["oam"]:
            self.sprite_model.oam_file = last_files["oam"]

        # Auto-load if preference is set
        if self.project_model.auto_load_files and last_files["vram"]:
            # Could trigger auto-extraction here if desired
            pass

    def _on_extraction_completed(self, image, tile_count):
        """Handle extraction completion"""
        # Switch to viewer tab
        if hasattr(self.main_window, "show_viewer_tab"):
            self.main_window.show_viewer_tab()

        # Update viewer
        self.viewer_controller.set_image(image)

        # Load palettes if available
        if self.sprite_model.cgram_file:
            self.palette_controller.load_palettes()

    def _on_palette_applied(self, palette_index):
        """Handle palette application"""
        # Update viewer with new palette
        if self.sprite_model.current_image:
            self.viewer_controller.set_image(self.sprite_model.current_image)

    def save_state(self):
        """Save application state"""
        self.project_model.save_settings()

    def quick_extract(self):
        """Perform quick extraction with current settings"""
        if self.sprite_model.vram_file:
            self.extract_controller.extract_sprites()
        else:
            self.extract_controller.browse_vram_file()

    def quick_inject(self):
        """Open inject tab and prompt for PNG"""
        if hasattr(self.main_window, "show_inject_tab"):
            self.main_window.show_inject_tab()
        self.inject_controller.browse_png_file()
