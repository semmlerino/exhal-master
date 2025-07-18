#!/usr/bin/env python3
"""
Manager classes for pixel editor
Handle coordination between models and provide business logic
"""

# Standard library imports
import os
from abc import ABC, abstractmethod
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple, Union

from .pixel_editor_constants import DEFAULT_GRAYSCALE_PALETTE
from .pixel_editor_exceptions import (
    FileOperationError,
    PaletteError,
    ResourceError,
    ToolError,
    ValidationError,
    format_error_message,
)
from .pixel_editor_models import ImageModel, PaletteModel, ProjectModel
from .pixel_editor_utils import debug_exception, debug_log
from .pixel_editor_workers import FileLoadWorker, FileSaveWorker, PaletteLoadWorker


class ToolType(Enum):
    """Available drawing tools"""

    PENCIL = auto()
    FILL = auto()
    PICKER = auto()


class Tool(ABC):
    """Abstract base class for drawing tools"""

    @abstractmethod
    def on_press(self, x: int, y: int, color: int, image_model: ImageModel) -> Any:
        """Handle mouse press event"""

    @abstractmethod
    def on_move(self, x: int, y: int, color: int, image_model: ImageModel) -> Any:
        """Handle mouse move event"""

    @abstractmethod
    def on_release(self, x: int, y: int, color: int, image_model: ImageModel) -> Any:
        """Handle mouse release event"""


class PencilTool(Tool):
    """Basic drawing tool with line interpolation"""

    def __init__(self) -> None:
        self.last_x: Optional[int] = None
        self.last_y: Optional[int] = None

    def on_press(self, x: int, y: int, color: int, image_model: ImageModel) -> bool:
        """Draw a single pixel and start tracking position"""
        self.last_x = x
        self.last_y = y
        return image_model.set_pixel(x, y, color)

    def on_move(self, x: int, y: int, color: int, image_model: ImageModel) -> List[Tuple[int, int]]:
        """Continue drawing with line interpolation"""
        if self.last_x is None or self.last_y is None:
            # First move without a previous position
            self.last_x = x
            self.last_y = y
            return [(x, y)]

        # Get all points between last position and current position
        line_points = self._get_line_points(self.last_x, self.last_y, x, y)
        
        # Update last position
        self.last_x = x
        self.last_y = y
        
        # Return the line points for the controller to handle
        return line_points

    def on_release(self, x: int, y: int, color: int, image_model: ImageModel) -> None:
        """Clear tracking state"""
        self.last_x = None
        self.last_y = None

    def _get_line_points(self, x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
        """Get all points on a line using Bresenham's algorithm"""
        points = []
        
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        
        # Determine direction
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        
        err = dx - dy
        x, y = x0, y0
        
        while True:
            points.append((x, y))
            
            if x == x1 and y == y1:
                break
                
            e2 = 2 * err
            
            if e2 > -dy:
                err -= dy
                x += sx
                
            if e2 < dx:
                err += dx
                y += sy
                
        return points


class FillTool(Tool):
    """Flood fill tool"""

    def on_press(
        self, x: int, y: int, color: int, image_model: ImageModel
    ) -> list[tuple[int, int]]:
        """Perform flood fill"""
        return image_model.fill(x, y, color)

    def on_move(self, x: int, y: int, color: int, image_model: ImageModel) -> None:
        """No action on move"""

    def on_release(self, x: int, y: int, color: int, image_model: ImageModel) -> None:
        """Nothing to do on release"""


class ColorPickerTool(Tool):
    """Color picker tool"""

    def __init__(self) -> None:
        self.picked_callback: Optional[Callable[[int], None]] = None

    def on_press(self, x: int, y: int, color: int, image_model: ImageModel) -> int:
        """Pick color at position"""
        picked_color = image_model.get_color_at(x, y)
        if self.picked_callback:
            self.picked_callback(picked_color)
        return picked_color

    def on_move(self, x: int, y: int, color: int, image_model: ImageModel) -> None:
        """No action on move"""

    def on_release(self, x: int, y: int, color: int, image_model: ImageModel) -> None:
        """Nothing to do on release"""


class ToolManager:
    """Manages drawing tools and tool state"""

    def __init__(self) -> None:
        self.tools = {
            ToolType.PENCIL: PencilTool(),
            ToolType.FILL: FillTool(),
            ToolType.PICKER: ColorPickerTool(),
        }
        self.current_tool = ToolType.PENCIL
        self.current_color = 0
        self.current_brush_size = 1  # Default to 1x1 brush
        self.max_brush_size = 5      # Allow future expansion

    def set_tool(self, tool_type: Union[ToolType, str]) -> None:
        """Set the current tool (accepts ToolType enum or string)"""
        # Convert string to enum if needed
        if isinstance(tool_type, str):
            tool_map = {
                "pencil": ToolType.PENCIL,
                "fill": ToolType.FILL,
                "picker": ToolType.PICKER,
            }
            mapped_type = tool_map.get(tool_type.lower())
            if not mapped_type:
                return
            tool_type = mapped_type

        if tool_type in self.tools:
            self.current_tool = tool_type
            debug_log("TOOL", f"Tool changed to {tool_type.name}")

    @property
    def current_tool_name(self) -> str:
        """Get the name of the current tool"""
        return self.current_tool.name.lower()

    def get_tool(self, tool_type: Optional[Union[ToolType, str]] = None) -> Optional[Tool]:
        """Get tool instance (current tool if no type specified)"""
        if tool_type is None:
            return self.tools[self.current_tool]

        # Convert string to enum if needed
        if isinstance(tool_type, str):
            tool_map = {
                "pencil": ToolType.PENCIL,
                "fill": ToolType.FILL,
                "picker": ToolType.PICKER,
            }
            orig_tool_type = tool_type
            tool_type = tool_map.get(orig_tool_type.lower())
            if not tool_type:
                raise ValueError(f"Unknown tool: {orig_tool_type}")

        return self.tools.get(tool_type) if tool_type else None

    def set_color(self, color: int) -> None:
        """Set the current drawing color"""
        self.current_color = max(0, min(15, color))

    def set_brush_size(self, size: int) -> None:
        """Set brush size with validation"""
        if 1 <= size <= self.max_brush_size:
            self.current_brush_size = size
            debug_log("BRUSH", f"Brush size changed to {size}")
        else:
            debug_log("BRUSH", f"Invalid brush size {size}, must be 1-{self.max_brush_size}")

    def get_brush_size(self) -> int:
        """Get current brush size"""
        return self.current_brush_size

    def get_brush_pixels(self, center_x: int, center_y: int) -> List[Tuple[int, int]]:
        """Calculate pixels affected by brush at given position"""
        pixels = []
        size = self.current_brush_size
        
        # Use top-left positioning for consistency with pixel editor conventions
        for dy in range(size):
            for dx in range(size):
                pixels.append((center_x + dx, center_y + dy))
        
        return pixels

    def set_color_picked_callback(self, callback: Callable[[int], None]) -> None:
        """Set callback for color picker tool"""
        picker = self.tools[ToolType.PICKER]
        if isinstance(picker, ColorPickerTool):
            picker.picked_callback = callback


class FileManager:
    """Manages file operations for the pixel editor"""

    def __init__(self) -> None:
        self.project_model = ProjectModel()
        self.load_callback: Optional[Callable[[ImageModel, dict], None]] = None
        self.save_callback: Optional[Callable[[str], None]] = None
        self.error_callback: Optional[Callable[[str], None]] = None

    def new_file(self, width: int = 8, height: int = 8) -> ImageModel:
        """Create a new image"""
        try:
            # Validate dimensions
            if width <= 0 or height <= 0:
                raise ValidationError("Image dimensions must be positive")
            if width > 4096 or height > 4096:
                raise ValidationError("Image dimensions too large (max 4096x4096)")
            if width * height > 1048576:  # 1M pixels
                raise ResourceError("Image too large (max 1 million pixels)")
                
            self.project_model.clear()
            image_model = ImageModel(width=width, height=height)
            debug_log("FILE", f"Created new image {width}x{height}")
            return image_model
        except Exception as e:
            debug_exception("FILE", e)
            if self.error_callback:
                self.error_callback(format_error_message("create new image", e))
            raise

    def load_file(self, file_path: Union[str, Path]) -> Optional[FileLoadWorker]:
        """
        Start async file loading
        Returns worker thread for progress tracking
        """
        try:
            # Convert Path to string if needed
            file_path_str = str(file_path) if isinstance(file_path, Path) else file_path
            
            # Validate file path
            if not file_path_str:
                raise ValidationError("File path cannot be empty")
                
            # Check file existence
            if not os.path.exists(file_path_str):
                raise FileNotFoundError(f"File not found: {file_path_str}")
                
            # Check file access
            if not os.access(file_path_str, os.R_OK):
                raise PermissionError(f"Cannot read file: {file_path_str}")
                
            # Check file size
            file_size = os.path.getsize(file_path_str)
            if file_size > 100 * 1024 * 1024:  # 100MB limit
                raise ResourceError(f"File too large: {file_size / 1024 / 1024:.1f}MB (max 100MB)")

            # Create worker - let caller handle threading
            worker = FileLoadWorker(file_path_str)
            self.project_model.image_path = file_path_str

            debug_log("FILE", f"Loading file: {file_path_str}")
            return worker
            
        except Exception as e:
            debug_exception("FILE", e)
            if self.error_callback:
                self.error_callback(format_error_message("load file", e))
            return None

    def save_file(
        self,
        image_model: ImageModel,
        palette_model: PaletteModel,
        file_path: Union[str, Path],
        use_grayscale_palette: bool = True,
    ) -> Optional[FileSaveWorker]:
        """
        Start async file saving
        Returns worker thread for progress tracking

        Args:
            image_model: The image data to save
            palette_model: The color palette model
            file_path: Path where to save the image
            use_grayscale_palette: If True, save with grayscale palette (default)
                                   If False, save with color palette
        """
        try:
            # Validate inputs
            if not image_model or image_model.data is None:
                raise ValidationError("No image data to save")
                
            # Convert Path to string if needed
            file_path_str = str(file_path) if isinstance(file_path, Path) else file_path
            
            if not file_path_str:
                raise ValidationError("File path cannot be empty")
                
            # Check directory exists and is writable
            directory = os.path.dirname(file_path_str)
            if directory and not os.path.exists(directory):
                raise FileNotFoundError(f"Directory does not exist: {directory}")
            if directory and not os.access(directory, os.W_OK):
                raise PermissionError(f"Cannot write to directory: {directory}")

            # Get image data
            image_array = image_model.data

            # Choose palette based on save mode
            if use_grayscale_palette:
                # Create grayscale palette flat list (768 values)
                palette_data = []
                for r, g, b in DEFAULT_GRAYSCALE_PALETTE:
                    palette_data.extend([r, g, b])
                # Pad to 256 colors (768 values total) if needed
                while len(palette_data) < 768:
                    palette_data.extend([0, 0, 0])
                debug_log("FILE", "Using grayscale palette for saving")
            else:
                # Use the color palette
                if not palette_model:
                    raise ValidationError("No palette model provided for color save")
                palette_data = palette_model.to_flat_list()
                debug_log("FILE", f"Using color palette '{palette_model.name}' for saving")

            # Create worker - let caller handle threading
            worker = FileSaveWorker(image_array, palette_data, file_path_str)
            self.project_model.image_path = file_path_str
            image_model.file_path = file_path_str
            image_model.modified = False

            debug_log("FILE", f"Saving file: {file_path_str}")
            return worker
            
        except Exception as e:
            debug_exception("FILE", e)
            if self.error_callback:
                self.error_callback(format_error_message("save file", e))
            return None

    def get_metadata_path(self, image_path: str) -> str:
        """Get metadata file path for an image"""
        return self.project_model.get_metadata_path(image_path)


class PaletteManager:
    """Manages palette operations and switching"""

    def __init__(self) -> None:
        self.palettes: dict[int, PaletteModel] = {}
        self.current_palette_index = 8  # Default SNES sprite palette
        self.load_callback: Optional[Callable[[PaletteModel], None]] = None
        self.error_callback: Optional[Callable[[str], None]] = None

    def add_palette(self, index: int, palette_model: PaletteModel) -> None:
        """Add a palette at the specified index"""
        palette_model.index = index
        self.palettes[index] = palette_model

    def get_palette(self, index: int) -> Optional[PaletteModel]:
        """Get palette by index"""
        return self.palettes.get(index)

    def get_current_palette(self) -> Optional[PaletteModel]:
        """Get the current active palette"""
        return self.palettes.get(self.current_palette_index)

    def set_current_palette(self, index: int) -> bool:
        """
        Set the current palette index
        Returns True if palette exists
        """
        if index in self.palettes:
            self.current_palette_index = index
            debug_log("PALETTE", f"Switched to palette {index}")
            return True
        return False

    def load_palette_file(
        self, file_path: Union[str, Path]
    ) -> Optional[PaletteLoadWorker]:
        """
        Start async palette loading
        Returns worker thread for progress tracking
        """
        try:
            # Convert Path to string if needed
            file_path_str = str(file_path) if isinstance(file_path, Path) else file_path
            
            # Validate file path
            if not file_path_str:
                raise ValidationError("Palette file path cannot be empty")

            if not os.path.exists(file_path_str):
                raise FileNotFoundError(f"Palette file not found: {file_path_str}")
                
            # Check file access
            if not os.access(file_path_str, os.R_OK):
                raise PermissionError(f"Cannot read palette file: {file_path_str}")
                
            # Check file extension
            valid_extensions = [".json", ".pal", ".png", ".gif", ".bmp"]
            file_ext = os.path.splitext(file_path_str)[1].lower()
            if file_ext not in valid_extensions:
                raise PaletteError(f"Unsupported palette file format: {file_ext}")

            # Create worker - let caller handle threading
            worker = PaletteLoadWorker(file_path_str)
            debug_log("PALETTE", f"Loading palette: {file_path_str}")
            return worker
            
        except Exception as e:
            debug_exception("PALETTE", e)
            if self.error_callback:
                self.error_callback(format_error_message("load palette", e))
            return None

    def load_from_metadata(self, metadata: dict) -> bool:
        """
        Load multiple palettes from metadata
        Returns True if any palettes were loaded
        """
        try:
            if not isinstance(metadata, dict):
                raise ValidationError("Invalid metadata format")
                
            loaded_count = 0

            # Check for multiple palettes
            if "palettes" in metadata:
                for pal_idx_str, pal_data in metadata["palettes"].items():
                    try:
                        pal_idx = int(pal_idx_str)
                        if pal_idx < 0 or pal_idx > 255:
                            debug_log("PALETTE", f"Invalid palette index: {pal_idx}", "WARNING")
                            continue
                            
                        if "colors" in pal_data:
                            palette = PaletteModel()
                            colors = [tuple(c) for c in pal_data["colors"]]
                            if len(colors) != 16:
                                debug_log("PALETTE", f"Palette {pal_idx} has {len(colors)} colors, expected 16", "WARNING")
                            palette.from_rgb_list(colors)
                            palette.name = pal_data.get("name", f"Palette {pal_idx}")
                            self.add_palette(pal_idx, palette)
                            loaded_count += 1
                    except (ValueError, KeyError, TypeError) as e:
                        debug_log("PALETTE", f"Error loading palette {pal_idx_str}: {e}", "WARNING")
                        continue

            # Check for single palette
            elif "palette" in metadata:
                try:
                    palette = PaletteModel()
                    palette.from_flat_list(metadata["palette"])
                    palette.name = "Loaded Palette"
                    self.add_palette(self.current_palette_index, palette)
                    loaded_count += 1
                except Exception as e:
                    debug_log("PALETTE", f"Error loading single palette: {e}", "WARNING")

            debug_log("PALETTE", f"Loaded {loaded_count} palettes from metadata")
            return loaded_count > 0
            
        except Exception as e:
            debug_exception("PALETTE", e)
            if self.error_callback:
                self.error_callback(format_error_message("load palettes from metadata", e))
            return False

    def get_palette_count(self) -> int:
        """Get number of loaded palettes"""
        return len(self.palettes)

    def clear_palettes(self) -> None:
        """Clear all loaded palettes"""
        self.palettes.clear()
        # Always have a default palette
        default = PaletteModel()
        self.add_palette(self.current_palette_index, default)
