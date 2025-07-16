#!/usr/bin/env python3
"""
Simplified controller for the pixel editor Phase 3 refactoring
Handles all business logic and coordinates between models, managers, and views
"""

# Standard library imports
import json
import os
import traceback
from typing import Optional

# Third-party imports
import numpy as np
from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QImage, QPixmap

from .pixel_editor_commands import (
    BatchCommand,
    DrawPixelCommand,
    FloodFillCommand,
    UndoManager,
)
from .pixel_editor_managers import FileManager, PaletteManager, ToolManager
from .pixel_editor_models import ImageModel, PaletteModel, ProjectModel
from .pixel_editor_settings_adapter import PixelEditorSettingsAdapter
from .pixel_editor_utils import debug_log


class ImageModelAdapter:
    """Adapter to make ImageModel work with undo commands that expect PixelCanvas"""

    def __init__(self, image_model):
        self.image_model = image_model

    @property
    def image_data(self):
        return self.image_model.data

    @image_data.setter
    def image_data(self, value):
        self.image_model.data = value


class PixelEditorController(QObject):
    """Controller coordinating all pixel editor operations"""

    # Signals
    imageChanged = pyqtSignal()
    paletteChanged = pyqtSignal()
    titleChanged = pyqtSignal(str)
    statusMessage = pyqtSignal(str, int)  # message, timeout
    error = pyqtSignal(str)
    toolChanged = pyqtSignal(str)  # tool name

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize settings
        self.settings = PixelEditorSettingsAdapter()

        # Initialize models
        self.image_model = ImageModel()
        self.palette_model = PaletteModel()
        self.project_model = ProjectModel()

        # Initialize managers
        self.tool_manager = ToolManager()
        self.file_manager = FileManager()
        self.palette_manager = PaletteManager()
        self.undo_manager = UndoManager()

        # Add default palette to manager
        self.palette_manager.add_palette(8, self.palette_model)

        # Workers
        self.load_worker = None
        self.save_worker = None

        # Drawing state tracking for undo
        self._is_drawing = False
        self._drawing_pixels = []  # List of (x, y, old_color, new_color) tuples
        self.palette_worker = None
        
        # Update batching for performance optimization
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._emit_batched_update)
        self._update_pending = False
        self._batch_interval = 16  # ~60 FPS (16ms)
        
    def _request_update(self):
        """Request an update with batching for performance"""
        if not self._update_pending:
            self._update_pending = True
            self._update_timer.start(self._batch_interval)
    
    def _emit_batched_update(self):
        """Emit the batched update signal"""
        self._update_pending = False
        self.imageChanged.emit()

    # Tool operations
    def set_tool(self, tool_name: str):
        """Set the current drawing tool"""
        self.tool_manager.set_tool(tool_name)
        debug_log("CONTROLLER", f"Tool changed to: {tool_name}")
        self.toolChanged.emit(tool_name)

    def set_drawing_color(self, color_index: int):
        """Set the current drawing color"""
        self.tool_manager.set_color(color_index)
        debug_log("CONTROLLER", f"Drawing color set to: {color_index}")

    def get_current_tool_name(self) -> str:
        """Get the name of the current tool"""
        return self.tool_manager.current_tool_name

    # Undo/Redo operations
    def undo(self):
        """Undo the last operation"""
        if self.undo_manager.current_index >= 0:
            # Create adapter for the image model
            adapter = ImageModelAdapter(self.image_model)
            if self.undo_manager.undo(adapter):
                self._request_update()
                self.statusMessage.emit("Undo", 1000)
            else:
                self.statusMessage.emit("Nothing to undo", 1000)
        else:
            self.statusMessage.emit("Nothing to undo", 1000)

    def redo(self):
        """Redo the last undone operation"""
        if self.undo_manager.current_index < len(self.undo_manager.command_stack) - 1:
            # Create adapter for the image model
            adapter = ImageModelAdapter(self.image_model)
            if self.undo_manager.redo(adapter):
                self._request_update()
                self.statusMessage.emit("Redo", 1000)
            else:
                self.statusMessage.emit("Nothing to redo", 1000)
        else:
            self.statusMessage.emit("Nothing to redo", 1000)

    def execute_command(self, command):
        """Execute a command and add it to the undo stack"""
        # Create adapter for the image model
        adapter = ImageModelAdapter(self.image_model)
        self.undo_manager.execute_command(command, adapter)
        self._request_update()

    # File operations
    def new_file(self, width: int = 8, height: int = 8):
        """Create a new image"""
        # Create new image via file manager
        self.image_model = self.file_manager.new_file(width, height)

        # Clear undo history for new file
        self.undo_manager = UndoManager()

        # Reset palette to default
        self.palette_model = PaletteModel()
        self.palette_manager.clear_palettes()
        self.palette_manager.add_palette(8, self.palette_model)

        # Emit signals
        self._request_update()
        self.paletteChanged.emit()
        self.titleChanged.emit("Indexed Pixel Editor - New File")

        debug_log("CONTROLLER", f"Created new {width}x{height} image")

    def open_file(self, file_path: str):
        """Open an image file"""
        if not os.path.exists(file_path):
            self.error.emit(f"File not found: {file_path}")
            return

        # Create worker
        debug_log("CONTROLLER", f"Loading image: {os.path.basename(file_path)}", "INFO")
        self.load_worker = self.file_manager.load_file(file_path)
        if not self.load_worker:
            return

        # Connect signals
        self.load_worker.progress.connect(
            lambda p, msg: debug_log(
                "CONTROLLER", f"Load progress: {p}% - {msg}", "DEBUG"
            )
        )
        self.load_worker.error.connect(self._handle_load_error)
        self.load_worker.result.connect(self._handle_load_result)

        # Start loading
        self.load_worker.start()

    def save_file(self, file_path: str):
        """Save the current image with grayscale palette (default)"""
        # Check if image is loaded
        if self.image_model.data is None:
            self.error.emit("No image loaded to save")
            return

        # Create worker with grayscale palette
        debug_log(
            "CONTROLLER",
            f"Saving image (grayscale): {os.path.basename(file_path)}",
            "INFO",
        )
        self.save_worker = self.file_manager.save_file(
            self.image_model, self.palette_model, file_path, use_grayscale_palette=True
        )
        if not self.save_worker:
            return

        # Connect signals
        self.save_worker.progress.connect(
            lambda p, msg: debug_log(
                "CONTROLLER", f"Save progress: {p}% - {msg}", "DEBUG"
            )
        )
        self.save_worker.error.connect(self._handle_save_error)
        self.save_worker.saved.connect(self._handle_save_success)

        # Start saving
        self.save_worker.start()

    def save_file_with_colors(self, file_path: str):
        """Save the current image with color palette applied"""
        # Create worker with color palette
        debug_log(
            "CONTROLLER",
            f"Saving image (with colors): {os.path.basename(file_path)}",
            "INFO",
        )
        self.save_worker = self.file_manager.save_file(
            self.image_model, self.palette_model, file_path, use_grayscale_palette=False
        )
        if not self.save_worker:
            return

        # Connect signals
        self.save_worker.progress.connect(
            lambda p, msg: debug_log(
                "CONTROLLER", f"Save progress: {p}% - {msg}", "DEBUG"
            )
        )
        self.save_worker.error.connect(self._handle_save_error)
        self.save_worker.saved.connect(self._handle_save_success)

        # Start saving
        self.save_worker.start()

    def _handle_load_error(self, error_msg: str):
        """Handle file load error"""
        debug_log("CONTROLLER", f"Handling load error: {error_msg}", "ERROR")
        debug_log("CONTROLLER", f"Error type: {type(error_msg).__name__}", "DEBUG")
        self.error.emit(f"Failed to load file: {error_msg}")
        debug_log("CONTROLLER", "Load error emitted", "DEBUG")

    def _handle_load_result(self, image_array: np.ndarray, metadata: dict):
        """Handle successful file load"""
        debug_log(
            "CONTROLLER",
            f"Handling load result: array shape={image_array.shape}",
            "DEBUG",
        )
        debug_log("CONTROLLER", f"Metadata keys: {list(metadata.keys())}", "DEBUG")
        try:
            # Create PIL image for model
            img = Image.fromarray(image_array, mode="P")

            # Apply palette if in metadata
            if "palette" in metadata:
                img.putpalette(metadata["palette"])
                # Update palette model
                self.palette_model.from_flat_list(metadata["palette"])
                self.palette_manager.add_palette(8, self.palette_model)

            # Load into model
            self.image_model.load_from_pil(img)

            # Clear undo history for newly loaded file
            self.undo_manager = UndoManager()

            # Update project info
            if hasattr(self.load_worker, "file_path"):
                file_path = self.load_worker.file_path
                debug_log(
                    "CONTROLLER",
                    f"file_path type: {type(file_path)}, value: {file_path}",
                    "DEBUG",
                )
                # Store as strings to maintain consistency
                self.project_model.image_path = str(file_path)
                self.image_model.file_path = str(file_path)

                # Update settings (convert Path to string for JSON serialization)
                self.settings.add_recent_file(str(file_path))

                # Emit signals
                self._request_update()
                self.paletteChanged.emit()
                self.titleChanged.emit(
                    f"Indexed Pixel Editor - {os.path.basename(str(file_path))}"
                )
                self.statusMessage.emit(
                    f"Loaded {os.path.basename(str(file_path))}", 3000
                )

                # Check for metadata (ensure path is string)
                self._check_for_metadata(str(file_path))

                # Check for paired palette (ensure path is string)
                self._check_for_paired_palette(str(file_path))

        except Exception as e:
            debug_log(
                "CONTROLLER",
                f"Exception in _handle_load_result: {type(e).__name__}: {e}",
                "ERROR",
            )
            debug_log("CONTROLLER", f"Error type: {type(e)}", "DEBUG")
            debug_log("CONTROLLER", f"Traceback: {traceback.format_exc()}", "DEBUG")
            self._handle_load_error(str(e))

    def _handle_save_error(self, error_msg: str):
        """Handle file save error"""
        self.error.emit(f"Failed to save file: {error_msg}")
        debug_log("CONTROLLER", f"Save error: {error_msg}", "ERROR")

    def _handle_save_success(self, file_path: str):
        """Handle successful file save"""
        # Store as strings to maintain consistency
        self.project_model.image_path = str(file_path)
        self.image_model.file_path = str(file_path)
        self.image_model.modified = False

        # Update settings (convert Path to string for JSON serialization)
        self.settings.add_recent_file(str(file_path))

        # Emit signals
        self.titleChanged.emit(f"Indexed Pixel Editor - {os.path.basename(file_path)}")
        self.statusMessage.emit(f"Saved to {file_path}", 3000)

        debug_log("CONTROLLER", f"Successfully saved: {file_path}")

    # Palette operations
    def load_palette_file(self, file_path: str):
        """Load an external palette file"""
        if not os.path.exists(file_path):
            self.error.emit(f"Palette file not found: {file_path}")
            return

        # For JSON files, handle directly (PaletteLoadWorker expects different format)
        if file_path.endswith(".json"):
            self._load_json_palette(file_path)
        else:
            self._load_palette_with_worker(file_path)

    def _load_json_palette(self, file_path: str):
        """Load JSON palette file directly"""
        try:
            # Load and validate palette
            debug_log(
                "CONTROLLER",
                f"Loading JSON palette: {os.path.basename(file_path)}",
                "INFO",
            )
            palette = PaletteModel()
            palette.from_json_file(file_path)

            # Update models
            self.palette_model = palette
            self.palette_manager.add_palette(8, palette)
            # Store as string to maintain consistency
            self.project_model.palette_path = str(file_path)

            # Update settings (convert Path to string for JSON serialization)
            self.settings.add_recent_palette_file(str(file_path))
            if self.project_model.image_path:
                self.settings.associate_palette_with_image(
                    str(self.project_model.image_path), str(file_path)
                )

            # Emit signals
            self.paletteChanged.emit()
            self.statusMessage.emit(f"Loaded palette: {palette.name}", 3000)
            debug_log("CONTROLLER", "JSON palette loaded successfully", "INFO")

            debug_log("CONTROLLER", f"Successfully loaded palette: {palette.name}")

        except Exception as e:
            self.error.emit(f"Failed to load palette: {e!s}")

    def _load_palette_with_worker(self, file_path: str):
        """Load palette file using worker thread"""
        # Create worker
        debug_log(
            "CONTROLLER",
            f"Loading palette with worker: {os.path.basename(file_path)}",
            "INFO",
        )
        self.palette_worker = self.palette_manager.load_palette_file(file_path)
        if not self.palette_worker:
            return

        # Connect signals
        self.palette_worker.progress.connect(
            lambda p, msg: debug_log(
                "CONTROLLER", f"Palette load progress: {p}% - {msg}", "DEBUG"
            )
        )
        self.palette_worker.error.connect(self._handle_palette_error)
        self.palette_worker.result.connect(self._handle_palette_result)

        # Store path for later
        self._loading_palette_path = file_path

        # Start loading
        self.palette_worker.start()

    def _handle_palette_error(self, error_msg: str):
        """Handle palette load error"""
        self.error.emit(f"Failed to load palette: {error_msg}")
        debug_log("CONTROLLER", f"Palette error: {error_msg}", "ERROR")

    def _handle_palette_result(self, palette_data: dict):
        """Handle successful palette load from worker"""
        try:
            # Create palette model from data
            palette = PaletteModel()

            if "colors" in palette_data:
                # RGB format
                palette.from_rgb_list(palette_data["colors"])
            elif "palette" in palette_data and "colors" in palette_data["palette"]:
                # Nested format
                palette.from_rgb_list(palette_data["palette"]["colors"])
            else:
                self._handle_palette_error("Invalid palette format")
                return

            # Set name
            if "name" in palette_data:
                palette.name = palette_data["name"]
            elif hasattr(self, "_loading_palette_path"):
                palette.name = os.path.basename(self._loading_palette_path)

            # Update models
            self.palette_model = palette
            self.palette_manager.add_palette(8, palette)

            # Update project
            if hasattr(self, "_loading_palette_path"):
                # Store as string to maintain consistency
                self.project_model.palette_path = str(self._loading_palette_path)
                self.settings.add_recent_palette_file(str(self._loading_palette_path))

                # Associate with current image
                if self.project_model.image_path:
                    self.settings.associate_palette_with_image(
                        str(self.project_model.image_path),
                        str(self._loading_palette_path),
                    )

            # Emit signals
            self.paletteChanged.emit()
            self.statusMessage.emit(f"Loaded palette: {palette.name}", 3000)

            debug_log("CONTROLLER", f"Successfully loaded palette: {palette.name}")

        except Exception as e:
            self._handle_palette_error(str(e))

    def switch_palette(self, palette_index: int):
        """Switch to a different palette"""
        if self.palette_manager.set_current_palette(palette_index):
            palette = self.palette_manager.get_current_palette()
            if palette:
                self.palette_model = palette
                self.paletteChanged.emit()
                debug_log("CONTROLLER", f"Switched to palette {palette_index}")

    # Image operations
    def update_image_data(self, image_data: np.ndarray):
        """Update the image model with new data"""
        self.image_model.data = image_data
        self.image_model.modified = True
        self._request_update()

    def get_image_size(self) -> tuple[int, int]:
        """Get current image dimensions"""
        return (self.image_model.width, self.image_model.height)

    def is_modified(self) -> bool:
        """Check if the image has been modified"""
        return self.image_model.modified

    def get_current_file_path(self) -> Optional[str]:
        """Get the current file path if any"""
        # Ensure we return a string, not a Path object
        if self.project_model.image_path is None:
            return None
        return str(self.project_model.image_path)

    # Preview generation
    def get_preview_pixmap(self, apply_palette: bool = True) -> Optional[QPixmap]:
        """Generate preview pixmap of the current image"""
        if self.image_model.data is None:
            return None

        # Get image dimensions
        height, width = self.image_model.data.shape

        # Create QImage directly without going through PIL
        qimage = QImage(width, height, QImage.Format.Format_RGB32)

        # Get colors
        if apply_palette:
            colors = self.palette_model.colors
        else:
            # Grayscale colors
            colors = [(i * 17, i * 17, i * 17) for i in range(16)]

        # Fill the image
        for y in range(height):
            for x in range(width):
                color_idx = int(self.image_model.data[y, x])
                if 0 <= color_idx < len(colors):
                    r, g, b = colors[color_idx]
                    qimage.setPixel(x, y, QColor(r, g, b).rgb())
                else:
                    # Invalid index - use magenta
                    qimage.setPixel(x, y, QColor(255, 0, 255).rgb())

        return QPixmap.fromImage(qimage)

    # Helper methods
    def _check_for_metadata(self, image_path: str):
        """Check for associated metadata file"""
        metadata_path = self.file_manager.get_metadata_path(image_path)
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path) as f:
                    metadata = json.load(f)
                self.project_model.metadata_path = metadata_path

                # Load palettes from metadata
                if self.palette_manager.load_from_metadata(metadata):
                    self.paletteChanged.emit()
                    debug_log("CONTROLLER", "Loaded palettes from metadata")

            except Exception as e:
                debug_log("CONTROLLER", f"Failed to load metadata: {e}", "WARNING")

    def _check_for_paired_palette(self, image_path: str):
        """Check for paired .pal.json file"""
        base = os.path.splitext(image_path)[0]
        palette_path = f"{base}.pal.json"

        if os.path.exists(palette_path):
            # Automatically load the paired palette
            self.load_palette_file(palette_path)

    # Settings operations
    def get_recent_files(self) -> list[str]:
        """Get list of recent files"""
        return self.settings.get_recent_files()

    def should_auto_load_last(self) -> bool:
        """Check if should auto-load last file"""
        return self.settings.should_auto_load_last()

    def get_last_file(self) -> Optional[str]:
        """Get the last opened file"""
        return self.settings.get_last_file()

    # Palette metadata operations
    def has_metadata_palettes(self) -> bool:
        """Check if metadata contains multiple palettes"""
        return self.palette_manager.get_palette_count() > 1

    def get_available_palettes(self) -> list[tuple[int, str]]:
        """Get list of available palettes"""
        result = []
        for idx in range(16):  # Check all possible palette indices
            palette = self.palette_manager.get_palette(idx)
            if palette:
                result.append((idx, palette.name))
        return result

    # Drawing operations for Phase 3.3
    def handle_canvas_press(self, x: int, y: int):
        """Handle mouse press on canvas"""
        if self.image_model.data is None:
            return

        # Start tracking drawing for undo
        self._is_drawing = True
        self._drawing_pixels = []

        # Get current tool
        tool = self.tool_manager.get_tool()
        tool_name = self.tool_manager.current_tool_name

        if tool_name == "pencil":
            # For pencil, track pixel changes
            old_color = self.image_model.get_color_at(x, y)
            result = tool.on_press(
                x, y, self.tool_manager.current_color, self.image_model
            )
            if result:
                self._drawing_pixels.append(
                    (x, y, old_color, self.tool_manager.current_color)
                )
                self._request_update()
        elif tool_name == "fill":
            # For fill, we need to capture the state before filling
            old_color = self.image_model.get_color_at(x, y)
            if old_color != self.tool_manager.current_color:
                # Get the affected region before filling
                # First, find the bounds of the fill area
                min_x = max_x = x
                min_y = max_y = y

                # Store the old image data before filling
                old_data = self.image_model.data.copy()

                # Execute the fill
                result = tool.on_press(
                    x, y, self.tool_manager.current_color, self.image_model
                )

                if result and len(result) > 0:
                    # Calculate affected region from result
                    for px, py in result:
                        min_x = min(min_x, px)
                        max_x = max(max_x, px)
                        min_y = min(min_y, py)
                        max_y = max(max_y, py)

                    # Create command with proper data
                    command = FloodFillCommand()
                    command.affected_region = (
                        min_x,
                        min_y,
                        max_x - min_x + 1,
                        max_y - min_y + 1,
                    )
                    command.new_color = self.tool_manager.current_color

                    # Store only the affected region from old data
                    command.old_data = np.full(
                        (max_y - min_y + 1, max_x - min_x + 1), 255, dtype=np.uint8
                    )
                    for px, py in result:
                        command.old_data[py - min_y, px - min_x] = old_data[py, px]

                    # The fill has already been executed, so we just need to track it
                    self.undo_manager.command_stack.append(command)
                    self.undo_manager.current_index += 1

                    # Limit stack size
                    if (
                        len(self.undo_manager.command_stack)
                        > self.undo_manager.max_commands
                    ):
                        self.undo_manager.command_stack.pop(0)
                        self.undo_manager.current_index -= 1

                    self._request_update()
            self._is_drawing = False  # Fill is a single action
        elif tool_name == "picker":
            # Color picker doesn't need undo
            result = tool.on_press(
                x, y, self.tool_manager.current_color, self.image_model
            )
            self._is_drawing = False

    def handle_canvas_move(self, x: int, y: int):
        """Handle mouse move on canvas (for continuous drawing)"""
        if self.image_model.data is None or not self._is_drawing:
            return

        # Only pencil tool supports continuous drawing
        if self.tool_manager.current_tool_name == "pencil":
            old_color = self.image_model.get_color_at(x, y)
            tool = self.tool_manager.get_tool()
            result = tool.on_move(
                x, y, self.tool_manager.current_color, self.image_model
            )

            if result:
                # Track this pixel change
                self._drawing_pixels.append(
                    (x, y, old_color, self.tool_manager.current_color)
                )
                self._request_update()

    def handle_canvas_release(self, x: int, y: int):
        """Handle mouse release on canvas"""
        if self.image_model.data is None:
            return

        # Create undo command for pencil drawing
        if (
            self._is_drawing
            and self.tool_manager.current_tool_name == "pencil"
            and self._drawing_pixels
        ):
            # Create individual commands for each pixel and batch them
            batch = BatchCommand()
            for px, py, old_color, new_color in self._drawing_pixels:
                cmd = DrawPixelCommand(
                    x=px, y=py, old_color=old_color, new_color=new_color
                )
                batch.add_command(cmd)

            # The pixels are already drawn, so we don't execute, just add to history
            self.undo_manager.command_stack.append(batch)
            self.undo_manager.current_index += 1
            # Clear redo stack
            if (
                self.undo_manager.current_index
                < len(self.undo_manager.command_stack) - 1
            ):
                self.undo_manager.command_stack = self.undo_manager.command_stack[
                    : self.undo_manager.current_index + 1
                ]

        # Reset drawing state
        self._is_drawing = False
        self._drawing_pixels = []

        # Get current tool and delegate to it
        tool = self.tool_manager.get_tool()
        tool.on_release(x, y, self.tool_manager.current_color, self.image_model)

    def has_image(self) -> bool:
        """Check if an image is loaded"""
        return self.image_model.data is not None

    def get_current_colors(self) -> list[tuple[int, int, int]]:
        """Get current palette colors as RGB tuples"""
        return [(r, g, b) for r, g, b in self.palette_model.colors]
