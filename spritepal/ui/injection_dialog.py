"""
Injection dialog for SpritePal
Allows users to configure sprite injection parameters
"""

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QSpinBox,
    QDialogButtonBox,
    QFileDialog,
    QMessageBox,
    QTextEdit
)


class InjectionDialog(QDialog):
    """Dialog for configuring sprite injection parameters"""
    
    def __init__(self, parent=None, sprite_path: str = "", metadata_path: str = ""):
        super().__init__(parent)
        self.sprite_path = sprite_path
        self.metadata_path = metadata_path
        self.metadata = None
        
        self._setup_ui()
        self._load_metadata()
        
    def _setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Inject Sprite to VRAM")
        self.setModal(True)
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout(self)
        
        # Sprite file info
        sprite_group = QGroupBox("Sprite File")
        sprite_layout = QVBoxLayout()
        
        sprite_path_layout = QHBoxLayout()
        sprite_path_layout.addWidget(QLabel("Path:"))
        self.sprite_path_edit = QLineEdit(self.sprite_path)
        self.sprite_path_edit.setReadOnly(True)
        sprite_path_layout.addWidget(self.sprite_path_edit)
        
        self.browse_sprite_btn = QPushButton("Browse...")
        self.browse_sprite_btn.clicked.connect(self._browse_sprite)
        sprite_path_layout.addWidget(self.browse_sprite_btn)
        
        sprite_layout.addLayout(sprite_path_layout)
        sprite_group.setLayout(sprite_layout)
        layout.addWidget(sprite_group)
        
        # Extraction info (if metadata available)
        self.extraction_group = QGroupBox("Original Extraction Info")
        extraction_layout = QVBoxLayout()
        
        self.extraction_info = QTextEdit()
        self.extraction_info.setMaximumHeight(80)
        self.extraction_info.setReadOnly(True)
        extraction_layout.addWidget(self.extraction_info)
        
        self.extraction_group.setLayout(extraction_layout)
        layout.addWidget(self.extraction_group)
        
        # VRAM settings
        vram_group = QGroupBox("VRAM Settings")
        vram_layout = QVBoxLayout()
        
        # Input VRAM
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Input VRAM:"))
        self.input_vram_edit = QLineEdit()
        self.input_vram_edit.setPlaceholderText("Select VRAM file to modify...")
        input_layout.addWidget(self.input_vram_edit)
        
        self.browse_input_btn = QPushButton("Browse...")
        self.browse_input_btn.clicked.connect(self._browse_input_vram)
        input_layout.addWidget(self.browse_input_btn)
        
        vram_layout.addLayout(input_layout)
        
        # Output VRAM
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output VRAM:"))
        self.output_vram_edit = QLineEdit()
        self.output_vram_edit.setPlaceholderText("Save modified VRAM as...")
        output_layout.addWidget(self.output_vram_edit)
        
        self.browse_output_btn = QPushButton("Browse...")
        self.browse_output_btn.clicked.connect(self._browse_output_vram)
        output_layout.addWidget(self.browse_output_btn)
        
        vram_layout.addLayout(output_layout)
        
        # Offset
        offset_layout = QHBoxLayout()
        offset_layout.addWidget(QLabel("Injection Offset:"))
        
        self.offset_hex_edit = QLineEdit()
        self.offset_hex_edit.setPlaceholderText("0xC000")
        self.offset_hex_edit.setMaximumWidth(100)
        self.offset_hex_edit.textChanged.connect(self._on_offset_changed)
        offset_layout.addWidget(self.offset_hex_edit)
        
        offset_layout.addWidget(QLabel("(hex) = "))
        
        self.offset_dec_label = QLabel("49152")
        self.offset_dec_label.setMinimumWidth(60)
        offset_layout.addWidget(self.offset_dec_label)
        
        offset_layout.addWidget(QLabel("(decimal)"))
        offset_layout.addStretch()
        
        vram_layout.addLayout(offset_layout)
        
        vram_group.setLayout(vram_layout)
        layout.addWidget(vram_group)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Set initial focus
        self.input_vram_edit.setFocus()
        
    def _load_metadata(self):
        """Load metadata if available"""
        if self.metadata_path and os.path.exists(self.metadata_path):
            try:
                import json
                with open(self.metadata_path, 'r') as f:
                    self.metadata = json.load(f)
                
                # Display extraction info
                if 'extraction' in self.metadata:
                    extraction = self.metadata['extraction']
                    info_text = f"Original VRAM: {extraction.get('vram_source', 'Unknown')}\n"
                    info_text += f"Offset: {extraction.get('vram_offset', '0xC000')}\n"
                    info_text += f"Tiles: {extraction.get('tile_count', 'Unknown')}"
                    self.extraction_info.setText(info_text)
                    
                    # Set default offset
                    self.offset_hex_edit.setText(extraction.get('vram_offset', '0xC000'))
                else:
                    self.extraction_group.hide()
            except Exception:
                self.extraction_group.hide()
        else:
            self.extraction_group.hide()
            # Set default offset
            self.offset_hex_edit.setText("0xC000")
    
    def _browse_sprite(self):
        """Browse for sprite file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Sprite File",
            os.path.dirname(self.sprite_path) if self.sprite_path else "",
            "PNG Files (*.png);;All Files (*.*)"
        )
        if filename:
            self.sprite_path = filename
            self.sprite_path_edit.setText(filename)
    
    def _browse_input_vram(self):
        """Browse for input VRAM file"""
        # Try to suggest original VRAM if available
        suggested_dir = ""
        if self.metadata and 'extraction' in self.metadata:
            vram_source = self.metadata['extraction'].get('vram_source', '')
            if vram_source:
                # Look for the file in the sprite's directory
                sprite_dir = os.path.dirname(self.sprite_path)
                possible_path = os.path.join(sprite_dir, vram_source)
                if os.path.exists(possible_path):
                    suggested_dir = sprite_dir
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input VRAM File",
            suggested_dir,
            "VRAM Files (*.dmp *.bin);;All Files (*.*)"
        )
        if filename:
            self.input_vram_edit.setText(filename)
            
            # Auto-suggest output filename
            if not self.output_vram_edit.text():
                base = os.path.splitext(filename)[0]
                self.output_vram_edit.setText(f"{base}_injected.dmp")
    
    def _browse_output_vram(self):
        """Browse for output VRAM file"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Modified VRAM As",
            self.output_vram_edit.text() or "",
            "VRAM Files (*.dmp);;All Files (*.*)"
        )
        if filename:
            self.output_vram_edit.setText(filename)
    
    def _on_offset_changed(self, text):
        """Update decimal display when hex offset changes"""
        try:
            if text.startswith("0x") or text.startswith("0X"):
                value = int(text, 16)
            else:
                value = int(text, 16)
            self.offset_dec_label.setText(str(value))
        except ValueError:
            self.offset_dec_label.setText("Invalid")
    
    def get_parameters(self) -> Optional[dict]:
        """Get injection parameters if dialog accepted"""
        if self.result() != QDialog.DialogCode.Accepted:
            return None
        
        # Validate inputs
        if not self.sprite_path_edit.text():
            QMessageBox.warning(self, "Invalid Input", "Please select a sprite file")
            return None
        
        if not self.input_vram_edit.text():
            QMessageBox.warning(self, "Invalid Input", "Please select an input VRAM file")
            return None
        
        if not self.output_vram_edit.text():
            QMessageBox.warning(self, "Invalid Input", "Please specify an output VRAM file")
            return None
        
        # Parse offset
        try:
            offset_text = self.offset_hex_edit.text() or "0xC000"
            if offset_text.startswith("0x") or offset_text.startswith("0X"):
                offset = int(offset_text, 16)
            else:
                offset = int(offset_text, 16)
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Invalid offset value")
            return None
        
        return {
            "sprite_path": self.sprite_path_edit.text(),
            "input_vram": self.input_vram_edit.text(),
            "output_vram": self.output_vram_edit.text(),
            "offset": offset,
            "metadata_path": self.metadata_path if self.metadata else None
        }