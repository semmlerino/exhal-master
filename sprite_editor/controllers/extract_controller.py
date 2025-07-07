#!/usr/bin/env python3
"""
Controller for sprite extraction functionality
Manages interaction between extract tab view and sprite model
"""

import os
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from .base_controller import BaseController
from ..workers.extract_worker import ExtractWorker


class ExtractController(BaseController):
    """Controller for extraction operations"""
    
    def __init__(self, sprite_model, project_model, extract_view, parent=None):
        super().__init__(sprite_model, extract_view, parent)
        self.project_model = project_model
        self.extract_worker = None
    
    def connect_signals(self):
        """Connect signals between model and view"""
        # View signals
        self.view.extract_requested.connect(self.extract_sprites)
        self.view.browse_vram_requested.connect(self.browse_vram_file)
        self.view.browse_cgram_requested.connect(self.browse_cgram_file)
        
        # Model signals
        self.model.vram_file_changed.connect(self.view.set_vram_file)
        self.model.cgram_file_changed.connect(self.view.set_cgram_file)
    
    def browse_vram_file(self):
        """Browse for VRAM dump file"""
        # Get initial directory from last file
        initial_dir = ""
        if self.model.vram_file and os.path.exists(os.path.dirname(self.model.vram_file)):
            initial_dir = os.path.dirname(self.model.vram_file)
        
        file_name, _ = QFileDialog.getOpenFileName(
            self.view, "Select VRAM Dump",
            initial_dir,
            "Dump Files (*.dmp);;All Files (*.*)"
        )
        
        if file_name:
            self.model.vram_file = file_name
            self.project_model.add_recent_file(file_name, 'vram')
    
    def browse_cgram_file(self):
        """Browse for CGRAM dump file"""
        # Get initial directory from last file
        initial_dir = ""
        if self.model.cgram_file and os.path.exists(os.path.dirname(self.model.cgram_file)):
            initial_dir = os.path.dirname(self.model.cgram_file)
        
        file_name, _ = QFileDialog.getOpenFileName(
            self.view, "Select CGRAM Dump",
            initial_dir,
            "Dump Files (*.dmp);;All Files (*.*)"
        )
        
        if file_name:
            self.model.cgram_file = file_name
            self.project_model.add_recent_file(file_name, 'cgram')
    
    def extract_sprites(self):
        """Extract sprites from VRAM"""
        # Get parameters from view
        params = self.view.get_extraction_params()
        
        # Validate inputs
        if not params['vram_file'] or not os.path.exists(params['vram_file']):
            QMessageBox.warning(self.view, "Error", "Please select a valid VRAM file")
            return
        
        # Update model with parameters
        self.model.vram_file = params['vram_file']
        self.model.extraction_offset = params['offset']
        self.model.extraction_size = params['size']
        self.model.tiles_per_row = params['tiles_per_row']
        
        # Clear output
        self.view.clear_output()
        self.view.append_output("Starting extraction...")
        
        # Create worker thread
        self.extract_worker = ExtractWorker(
            params['vram_file'],
            params['offset'],
            params['size'],
            params['tiles_per_row'],
            params['palette_num'] if params['use_palette'] else None,
            params['cgram_file'] if params['use_palette'] else None
        )
        
        self.extract_worker.progress.connect(self.on_extract_progress)
        self.extract_worker.finished.connect(self.on_extract_finished)
        self.extract_worker.error.connect(self.on_extract_error)
        
        # Disable controls
        self.view.set_extract_enabled(False)
        
        # Start extraction
        self.extract_worker.start()
    
    def on_extract_progress(self, message):
        """Handle extraction progress"""
        self.view.append_output(message)
    
    def on_extract_finished(self, image, tile_count):
        """Handle extraction completion"""
        self.view.set_extract_enabled(True)
        
        # Update model
        self.model.current_image = image
        
        # Update view
        self.view.append_output(f"\nSuccess! Extracted {tile_count} tiles")
        self.view.append_output(f"Image size: {image.width}x{image.height} pixels")
        
        # Mark project as modified
        self.project_model.mark_modified()
    
    def on_extract_error(self, error):
        """Handle extraction error"""
        self.view.set_extract_enabled(True)
        self.view.append_output(f"\nError: {error}")
        QMessageBox.critical(self.view, "Extraction Error", error)
    
    def load_recent_vram(self, file_path):
        """Load a recent VRAM file"""
        if os.path.exists(file_path):
            self.model.vram_file = file_path
            self.project_model.add_recent_file(file_path, 'vram')
    
    def load_recent_cgram(self, file_path):
        """Load a recent CGRAM file"""
        if os.path.exists(file_path):
            self.model.cgram_file = file_path
            self.project_model.add_recent_file(file_path, 'cgram')