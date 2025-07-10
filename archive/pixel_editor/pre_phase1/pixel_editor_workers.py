"""
Worker threads for async file operations in the pixel editor.

This module provides thread-based workers for handling file I/O operations
asynchronously, preventing UI freezing during long operations.
"""

from typing import Optional, Dict, Any, Tuple
from pathlib import Path
import json
import traceback

from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PIL import Image
import numpy as np


class BaseWorker(QThread):
    """Base worker class for async operations.
    
    Signals:
        progress: Emitted with progress percentage (0-100)
        error: Emitted with error message when operation fails
        finished: Emitted when operation completes successfully
    """
    
    progress = pyqtSignal(int)  # Progress percentage 0-100
    error = pyqtSignal(str)     # Error message
    finished = pyqtSignal()     # Operation completed
    
    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the base worker.
        
        Args:
            parent: Parent QObject for proper cleanup
        """
        super().__init__(parent)
        self._is_cancelled = False
        
    def cancel(self) -> None:
        """Cancel the operation."""
        self._is_cancelled = True
        
    def is_cancelled(self) -> bool:
        """Check if operation was cancelled.
        
        Returns:
            True if operation was cancelled
        """
        return self._is_cancelled
        
    def emit_progress(self, value: int) -> None:
        """Emit progress signal if not cancelled.
        
        Args:
            value: Progress percentage (0-100)
        """
        if not self._is_cancelled:
            self.progress.emit(value)
            
    def emit_error(self, message: str) -> None:
        """Emit error signal with formatted message.
        
        Args:
            message: Error message to emit
        """
        if not self._is_cancelled:
            self.error.emit(message)
            
    def emit_finished(self) -> None:
        """Emit finished signal if not cancelled."""
        if not self._is_cancelled:
            self.finished.emit()


class FileLoadWorker(BaseWorker):
    """Worker for loading image files asynchronously.
    
    Signals:
        result: Emitted with loaded image data and metadata
    """
    
    result = pyqtSignal(object, dict)  # Image array, metadata
    
    def __init__(self, file_path: str, parent: Optional[QObject] = None):
        """Initialize the file load worker.
        
        Args:
            file_path: Path to the image file to load
            parent: Parent QObject for proper cleanup
        """
        super().__init__(parent)
        self.file_path = Path(file_path)
        
    def run(self) -> None:
        """Load the image file in background thread."""
        try:
            self.emit_progress(0)
            
            # Check if file exists
            if not self.file_path.exists():
                self.emit_error(f"File not found: {self.file_path}")
                return
                
            if self.is_cancelled():
                return
                
            self.emit_progress(20)
            
            # Load image
            try:
                image = Image.open(str(self.file_path))
            except Exception as e:
                self.emit_error(f"Failed to open image: {str(e)}")
                return
                
            if self.is_cancelled():
                return
                
            self.emit_progress(40)
            
            # Convert to indexed color if necessary
            if image.mode != 'P':
                try:
                    # Convert to indexed color with 256 colors
                    image = image.convert('P', palette=Image.ADAPTIVE, colors=256)
                except Exception as e:
                    self.emit_error(f"Failed to convert image to indexed color: {str(e)}")
                    return
                    
            if self.is_cancelled():
                return
                
            self.emit_progress(60)
            
            # Extract image data
            image_array = np.array(image, dtype=np.uint8)
            
            # Extract palette
            palette_data = image.getpalette()
            if palette_data is None:
                self.emit_error("Image has no palette data")
                return
                
            if self.is_cancelled():
                return
                
            self.emit_progress(80)
            
            # Prepare metadata
            metadata = {
                'width': image.width,
                'height': image.height,
                'mode': image.mode,
                'format': image.format,
                'palette': palette_data,
                'file_path': str(self.file_path),
                'file_name': self.file_path.name
            }
            
            # Extract additional info if available
            if hasattr(image, 'info'):
                metadata['info'] = image.info
                
            if self.is_cancelled():
                return
                
            self.emit_progress(100)
            
            # Emit results
            self.result.emit(image_array, metadata)
            self.emit_finished()
            
        except Exception as e:
            self.emit_error(f"Unexpected error loading file: {str(e)}\n{traceback.format_exc()}")


class FileSaveWorker(BaseWorker):
    """Worker for saving image files asynchronously.
    
    Signals:
        saved: Emitted when file is successfully saved
    """
    
    saved = pyqtSignal(str)  # Saved file path
    
    def __init__(self, 
                 image_array: np.ndarray,
                 palette: list,
                 file_path: str,
                 parent: Optional[QObject] = None):
        """Initialize the file save worker.
        
        Args:
            image_array: Indexed image data to save
            palette: Color palette (768 RGB values)
            file_path: Path where to save the image
            parent: Parent QObject for proper cleanup
        """
        super().__init__(parent)
        self.image_array = image_array
        self.palette = palette
        self.file_path = Path(file_path)
        
    def run(self) -> None:
        """Save the image file in background thread."""
        try:
            self.emit_progress(0)
            
            # Validate input data
            if self.image_array is None or len(self.image_array) == 0:
                self.emit_error("No image data to save")
                return
                
            if self.palette is None or len(self.palette) != 768:
                self.emit_error("Invalid palette data")
                return
                
            if self.is_cancelled():
                return
                
            self.emit_progress(20)
            
            # Create PIL image from array
            try:
                image = Image.fromarray(self.image_array, mode='P')
            except Exception as e:
                self.emit_error(f"Failed to create image from data: {str(e)}")
                return
                
            if self.is_cancelled():
                return
                
            self.emit_progress(40)
            
            # Apply palette
            try:
                image.putpalette(self.palette)
            except Exception as e:
                self.emit_error(f"Failed to apply palette: {str(e)}")
                return
                
            if self.is_cancelled():
                return
                
            self.emit_progress(60)
            
            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save image
            try:
                # Determine format from extension
                format_map = {
                    '.png': 'PNG',
                    '.gif': 'GIF',
                    '.bmp': 'BMP',
                    '.tiff': 'TIFF',
                    '.tif': 'TIFF'
                }
                
                file_format = format_map.get(self.file_path.suffix.lower(), 'PNG')
                
                # Save with appropriate options
                save_kwargs = {}
                if file_format == 'PNG':
                    save_kwargs['optimize'] = True
                    
                image.save(str(self.file_path), format=file_format, **save_kwargs)
                
            except Exception as e:
                self.emit_error(f"Failed to save image: {str(e)}")
                return
                
            if self.is_cancelled():
                return
                
            self.emit_progress(100)
            
            # Emit success
            self.saved.emit(str(self.file_path))
            self.emit_finished()
            
        except Exception as e:
            self.emit_error(f"Unexpected error saving file: {str(e)}\n{traceback.format_exc()}")


class PaletteLoadWorker(BaseWorker):
    """Worker for loading palette files asynchronously.
    
    Signals:
        result: Emitted with loaded palette data
    """
    
    result = pyqtSignal(dict)  # Palette data dictionary
    
    def __init__(self, file_path: str, parent: Optional[QObject] = None):
        """Initialize the palette load worker.
        
        Args:
            file_path: Path to the palette file to load
            parent: Parent QObject for proper cleanup
        """
        super().__init__(parent)
        self.file_path = Path(file_path)
        
    def run(self) -> None:
        """Load the palette file in background thread."""
        try:
            self.emit_progress(0)
            
            # Check if file exists
            if not self.file_path.exists():
                self.emit_error(f"Palette file not found: {self.file_path}")
                return
                
            if self.is_cancelled():
                return
                
            self.emit_progress(30)
            
            # Determine file type and load accordingly
            suffix = self.file_path.suffix.lower()
            
            palette_data = {}
            
            if suffix == '.json':
                # Load JSON palette
                try:
                    with open(self.file_path, 'r') as f:
                        data = json.load(f)
                        
                    if self.is_cancelled():
                        return
                        
                    self.emit_progress(60)
                    
                    # Validate JSON structure
                    if 'colors' not in data:
                        self.emit_error("Invalid palette JSON: missing 'colors' field")
                        return
                        
                    palette_data = data
                    
                except json.JSONDecodeError as e:
                    self.emit_error(f"Invalid JSON format: {str(e)}")
                    return
                except Exception as e:
                    self.emit_error(f"Failed to load JSON palette: {str(e)}")
                    return
                    
            elif suffix == '.pal':
                # Load ACT/PAL palette (raw RGB data)
                try:
                    with open(self.file_path, 'rb') as f:
                        raw_data = f.read()
                        
                    if self.is_cancelled():
                        return
                        
                    self.emit_progress(60)
                    
                    # Convert to color list
                    if len(raw_data) < 768:
                        self.emit_error(f"Invalid palette file: expected 768 bytes, got {len(raw_data)}")
                        return
                        
                    colors = []
                    for i in range(0, min(768, len(raw_data)), 3):
                        r = raw_data[i]
                        g = raw_data[i + 1]
                        b = raw_data[i + 2]
                        colors.append([r, g, b])
                        
                    palette_data = {
                        'name': self.file_path.stem,
                        'colors': colors,
                        'format': 'ACT'
                    }
                    
                except Exception as e:
                    self.emit_error(f"Failed to load PAL/ACT palette: {str(e)}")
                    return
                    
            elif suffix == '.gpl':
                # Load GIMP palette
                try:
                    colors = []
                    name = self.file_path.stem
                    
                    with open(self.file_path, 'r') as f:
                        lines = f.readlines()
                        
                    if self.is_cancelled():
                        return
                        
                    self.emit_progress(60)
                    
                    # Parse GIMP palette format
                    if not lines or not lines[0].strip().startswith('GIMP Palette'):
                        self.emit_error("Invalid GIMP palette file")
                        return
                        
                    for line in lines[1:]:
                        line = line.strip()
                        if line.startswith('#') or not line:
                            continue
                        if line.startswith('Name:'):
                            name = line[5:].strip()
                            continue
                            
                        # Parse color line
                        parts = line.split()
                        if len(parts) >= 3:
                            try:
                                r = int(parts[0])
                                g = int(parts[1])
                                b = int(parts[2])
                                colors.append([r, g, b])
                            except ValueError:
                                continue
                                
                    palette_data = {
                        'name': name,
                        'colors': colors,
                        'format': 'GIMP'
                    }
                    
                except Exception as e:
                    self.emit_error(f"Failed to load GIMP palette: {str(e)}")
                    return
                    
            else:
                self.emit_error(f"Unsupported palette format: {suffix}")
                return
                
            if self.is_cancelled():
                return
                
            self.emit_progress(90)
            
            # Add file metadata
            palette_data['file_path'] = str(self.file_path)
            palette_data['file_name'] = self.file_path.name
            
            self.emit_progress(100)
            
            # Emit results
            self.result.emit(palette_data)
            self.emit_finished()
            
        except Exception as e:
            self.emit_error(f"Unexpected error loading palette: {str(e)}\n{traceback.format_exc()}")