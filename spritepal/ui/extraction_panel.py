"""
Extraction panel with drag & drop zones for dump files
"""

import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFileDialog, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QColor, QPen


class DropZone(QWidget):
    """Drag and drop zone for file input"""
    
    file_dropped = pyqtSignal(str)
    
    def __init__(self, file_type, parent=None):
        super().__init__(parent)
        self.file_type = file_type
        self.file_path = ""
        self.setAcceptDrops(True)
        self.setMinimumHeight(80)
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #666;
                border-radius: 8px;
                background-color: #2b2b2b;
            }
        """)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon and label
        self.label = QLabel(f"Drop {file_type} file here")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #999;")
        layout.addWidget(self.label)
        
        # File path label
        self.path_label = QLabel("")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.path_label.setStyleSheet("color: #0078d4; font-size: 11px;")
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)
        
        # Browse button
        self.browse_button = QPushButton("Browse")
        self.browse_button.setMaximumWidth(100)
        self.browse_button.clicked.connect(self._browse_file)
        layout.addWidget(self.browse_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("""
                DropZone {
                    border: 2px solid #0078d4;
                    border-radius: 8px;
                    background-color: #383838;
                }
            """)
            
    def dragLeaveEvent(self, event):
        """Handle drag leave events"""
        self.setStyleSheet("""
            DropZone {
                border: 2px dashed #666;
                border-radius: 8px;
                background-color: #2b2b2b;
            }
        """)
        
    def dropEvent(self, event: QDropEvent):
        """Handle drop events"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files:
            self.set_file(files[0])
        self.dragLeaveEvent(event)
        
    def paintEvent(self, event):
        """Custom paint event to show status"""
        super().paintEvent(event)
        
        if self.file_path:
            # Draw green checkmark
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw circle
            painter.setPen(QPen(QColor(16, 124, 65), 2))
            painter.setBrush(QColor(16, 124, 65, 30))
            painter.drawEllipse(self.width() - 35, 10, 25, 25)
            
            # Draw checkmark
            painter.setPen(QPen(QColor(16, 124, 65), 3))
            painter.drawLine(self.width() - 28, 22, self.width() - 23, 27)
            painter.drawLine(self.width() - 23, 27, self.width() - 15, 19)
            
    def _browse_file(self):
        """Browse for file"""
        file_filter = f"{self.file_type} Files (*.dmp);;All Files (*)"
        filename, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {self.file_type} File",
            "",
            file_filter
        )
        
        if filename:
            self.set_file(filename)
            
    def set_file(self, file_path):
        """Set the file path"""
        if os.path.exists(file_path):
            self.file_path = file_path
            self.label.setText(f"✓ {self.file_type}")
            self.label.setStyleSheet("color: #107c41; font-weight: bold;")
            
            # Show filename
            filename = Path(file_path).name
            self.path_label.setText(filename)
            
            self.file_dropped.emit(file_path)
            self.update()  # Trigger repaint
            
    def clear(self):
        """Clear the current file"""
        self.file_path = ""
        self.label.setText(f"Drop {self.file_type} file here")
        self.label.setStyleSheet("color: #999;")
        self.path_label.setText("")
        self.update()
        
    def has_file(self):
        """Check if a file is loaded"""
        return bool(self.file_path)
        
    def get_file_path(self):
        """Get the current file path"""
        return self.file_path


class ExtractionPanel(QGroupBox):
    """Panel for managing extraction inputs"""
    
    files_changed = pyqtSignal()
    extraction_ready = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__("Input Files")
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Set up the UI"""
        layout = QVBoxLayout()
        
        # Preset selector
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "Kirby Sprites (0xC000)",
            "Custom Range"
        ])
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        
        layout.addLayout(preset_layout)
        
        # Drop zones
        self.vram_drop = DropZone("VRAM")
        layout.addWidget(self.vram_drop)
        
        self.cgram_drop = DropZone("CGRAM")
        layout.addWidget(self.cgram_drop)
        
        self.oam_drop = DropZone("OAM (Optional)")
        layout.addWidget(self.oam_drop)
        
        # Auto-detect button
        self.auto_detect_button = QPushButton("Auto-detect Files")
        self.auto_detect_button.clicked.connect(self._auto_detect_files)
        layout.addWidget(self.auto_detect_button)
        
        self.setLayout(layout)
        
    def _connect_signals(self):
        """Connect internal signals"""
        self.vram_drop.file_dropped.connect(self._on_file_changed)
        self.cgram_drop.file_dropped.connect(self._on_file_changed)
        self.oam_drop.file_dropped.connect(self._on_file_changed)
        
    def _on_file_changed(self, file_path):
        """Handle when a file is dropped"""
        self.files_changed.emit()
        self._check_extraction_ready()
        
        # Try to auto-detect related files
        self._auto_detect_related(file_path)
        
    def _check_extraction_ready(self):
        """Check if we're ready to extract"""
        ready = self.vram_drop.has_file() and self.cgram_drop.has_file()
        self.extraction_ready.emit(ready)
        
    def _auto_detect_related(self, file_path):
        """Try to auto-detect related dump files"""
        path = Path(file_path)
        directory = path.parent
        base_name = path.stem
        
        # Remove common suffixes to get base name
        for suffix in ["_VRAM", "_CGRAM", "_OAM", ".SnesVideoRam", ".SnesCgRam", ".SnesSpriteRam"]:
            if base_name.endswith(suffix):
                base_name = base_name[:-len(suffix)]
                break
                
        # Look for related files
        patterns = [
            # Standard patterns
            (f"{base_name}_VRAM.dmp", self.vram_drop),
            (f"{base_name}_CGRAM.dmp", self.cgram_drop),
            (f"{base_name}_OAM.dmp", self.oam_drop),
            # SNES patterns
            (f"{base_name}.SnesVideoRam.dmp", self.vram_drop),
            (f"{base_name}.SnesCgRam.dmp", self.cgram_drop),
            (f"{base_name}.SnesSpriteRam.dmp", self.oam_drop),
            # Simple patterns
            (f"{base_name}.VRAM.dmp", self.vram_drop),
            (f"{base_name}.CGRAM.dmp", self.cgram_drop),
            (f"{base_name}.OAM.dmp", self.oam_drop),
        ]
        
        for filename, drop_zone in patterns:
            file_path = directory / filename
            if file_path.exists() and not drop_zone.has_file():
                drop_zone.set_file(str(file_path))
                
    def _auto_detect_files(self):
        """Auto-detect dump files in current directory"""
        # Start from current directory
        directory = Path.cwd()
        
        # Common dump file patterns
        vram_patterns = ["*VRAM*.dmp", "*VideoRam*.dmp"]
        cgram_patterns = ["*CGRAM*.dmp", "*CgRam*.dmp"]
        oam_patterns = ["*OAM*.dmp", "*SpriteRam*.dmp"]
        
        # Find files
        found_any = False
        
        for pattern in vram_patterns:
            if not self.vram_drop.has_file():
                files = list(directory.glob(pattern))
                if files:
                    self.vram_drop.set_file(str(files[0]))
                    found_any = True
                    break
                    
        for pattern in cgram_patterns:
            if not self.cgram_drop.has_file():
                files = list(directory.glob(pattern))
                if files:
                    self.cgram_drop.set_file(str(files[0]))
                    found_any = True
                    break
                    
        for pattern in oam_patterns:
            if not self.oam_drop.has_file():
                files = list(directory.glob(pattern))
                if files:
                    self.oam_drop.set_file(str(files[0]))
                    found_any = True
                    break
                    
        if found_any:
            self.files_changed.emit()
            self._check_extraction_ready()
            
    def _on_preset_changed(self, index):
        """Handle preset change"""
        # For now, presets just provide information
        # In the future, this could adjust extraction parameters
        pass
        
    def clear_files(self):
        """Clear all loaded files"""
        self.vram_drop.clear()
        self.cgram_drop.clear()
        self.oam_drop.clear()
        self._check_extraction_ready()
        
    def has_vram(self):
        """Check if VRAM is loaded"""
        return self.vram_drop.has_file()
        
    def has_cgram(self):
        """Check if CGRAM is loaded"""
        return self.cgram_drop.has_file()
        
    def has_oam(self):
        """Check if OAM is loaded"""
        return self.oam_drop.has_file()
        
    def get_vram_path(self):
        """Get VRAM file path"""
        return self.vram_drop.get_file_path()
        
    def get_cgram_path(self):
        """Get CGRAM file path"""
        return self.cgram_drop.get_file_path()
        
    def get_oam_path(self):
        """Get OAM file path"""
        return self.oam_drop.get_file_path()
        
    def restore_session_files(self, file_paths):
        """Restore file paths from session data"""
        if file_paths.get("vram_path") and os.path.exists(file_paths["vram_path"]):
            self.vram_drop.set_file(file_paths["vram_path"])
            
        if file_paths.get("cgram_path") and os.path.exists(file_paths["cgram_path"]):
            self.cgram_drop.set_file(file_paths["cgram_path"])
            
        if file_paths.get("oam_path") and os.path.exists(file_paths["oam_path"]):
            self.oam_drop.set_file(file_paths["oam_path"])
            
        self.files_changed.emit()
        self._check_extraction_ready()
        
    def get_session_data(self):
        """Get current session data for saving"""
        return {
            "vram_path": self.get_vram_path(),
            "cgram_path": self.get_cgram_path(),
            "oam_path": self.get_oam_path()
        }