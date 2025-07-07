#!/usr/bin/env python3
"""
Main application class for Kirby Super Star Sprite Editor
Implements dependency injection and coordinates MVC components
"""

import sys
from PyQt6.QtWidgets import QApplication

from .models.sprite_model import SpriteModel
from .models.project_model import ProjectModel
from .models.palette_model import PaletteModel

from .views.main_window import MainWindow

from .controllers.main_controller import MainController


class SpriteEditorApplication:
    """Main application class using MVC architecture"""
    
    def __init__(self):
        """Initialize the application"""
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Kirby Sprite Editor")
        self.app.setStyle("Fusion")
        
        # Create models
        self.models = self._create_models()
        
        # Create views
        self.views = self._create_views()
        
        # Create controllers
        self.controllers = self._create_controllers()
        
        # Connect MVC components
        self._connect_mvc()
        
        # Initialize application state
        self._initialize()
    
    def _create_models(self):
        """Create all model instances"""
        models = {
            'sprite': SpriteModel(),
            'project': ProjectModel(),
            'palette': PaletteModel()
        }
        return models
    
    def _create_views(self):
        """Create all view instances"""
        main_window = MainWindow()
        tabs = main_window.get_tabs()
        
        views = {
            'main_window': main_window,
            'extract_tab': tabs['extract'],
            'inject_tab': tabs['inject'],
            'viewer_tab': tabs['viewer'],
            'multi_palette_tab': tabs['multi_palette']
        }
        return views
    
    def _create_controllers(self):
        """Create all controller instances"""
        # Main controller handles sub-controllers
        main_controller = MainController(self.models, self.views)
        
        controllers = {
            'main': main_controller,
            'extract': main_controller.extract_controller,
            'inject': main_controller.inject_controller,
            'viewer': main_controller.viewer_controller,
            'palette': main_controller.palette_controller
        }
        return controllers
    
    def _connect_mvc(self):
        """Connect MVC components together"""
        # Connect main window closing to save state
        self.views['main_window'].closing.connect(self._on_closing)
        
        # Connect project model to update recent files menu
        self.models['project'].recent_files_changed.connect(
            self._update_recent_files_menu
        )
        
        # Connect toolbar actions
        self.views['main_window'].action_quick_extract.triggered.connect(
            self.controllers['main'].quick_extract
        )
        
        self.views['main_window'].action_quick_inject.triggered.connect(
            self.controllers['main'].quick_inject
        )
        
        # Update status bar from models
        self.models['sprite'].extraction_started.connect(
            lambda: self.views['main_window'].show_status_message("Extracting sprites...")
        )
        
        self.models['sprite'].extraction_completed.connect(
            lambda img, count: self.views['main_window'].show_status_message(
                f"Extraction complete - {count} tiles", 5000
            )
        )
        
        self.models['sprite'].injection_started.connect(
            lambda: self.views['main_window'].show_status_message("Injecting sprites...")
        )
        
        self.models['sprite'].injection_completed.connect(
            lambda path: self.views['main_window'].show_status_message(
                f"Injection complete - {path}", 5000
            )
        )
    
    def _initialize(self):
        """Initialize application state"""
        # Update recent files menu
        self._update_recent_files_menu()
        
        # Restore window geometry if preference is set
        if self.models['project'].remember_window_position:
            geometry = self.models['project'].settings.get('window_geometry')
            if geometry and isinstance(geometry, dict):
                self.views['main_window'].move(
                    geometry.get('x', 100),
                    geometry.get('y', 100)
                )
                self.views['main_window'].resize(
                    geometry.get('width', 1200),
                    geometry.get('height', 800)
                )
    
    def _update_recent_files_menu(self):
        """Update recent files menu"""
        recent_files = {
            'vram': self.models['project'].recent_vram_files,
            'cgram': self.models['project'].recent_cgram_files,
            'oam': self.models['project'].recent_oam_files
        }
        self.views['main_window'].update_recent_files_menu(recent_files)
    
    def _on_closing(self):
        """Handle application closing"""
        # Save window geometry if preference is set
        if self.models['project'].remember_window_position:
            window = self.views['main_window']
            self.models['project'].settings.set('window_geometry', {
                'x': window.x(),
                'y': window.y(),
                'width': window.width(),
                'height': window.height()
            })
        
        # Save all settings
        self.controllers['main'].save_state()
    
    def run(self):
        """Run the application"""
        self.views['main_window'].show()
        return self.app.exec()


def main():
    """Main entry point"""
    app = SpriteEditorApplication()
    sys.exit(app.run())


if __name__ == "__main__":
    main()