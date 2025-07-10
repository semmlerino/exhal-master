#!/usr/bin/env python3
"""
Type definitions for the pixel editor module.
Provides type aliases, protocols, and TypedDict definitions for better type safety.
"""

from typing import TypedDict, Literal, Union, Protocol, Optional, Any
import numpy as np
from numpy.typing import NDArray

# Basic type aliases
ColorIndex = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
RGB = tuple[int, int, int]
RGBA = tuple[int, int, int, int]
Color = Union[RGB, RGBA]

# Tool types
ToolType = Literal["pencil", "fill", "picker"]

# Log levels
LogLevel = Literal["INFO", "DEBUG", "WARNING", "ERROR"]

# Image data type - 2D array of color indices (0-15 for 4bpp)
ImageData = NDArray[np.uint8]

# Zoom levels
ZoomLevel = Literal[1, 2, 4, 8, 16, 32, 64]


class PaletteData(TypedDict):
    """Structure for palette file data."""
    palette: dict[str, Union[str, list[list[int]]]]
    colors: list[list[int]]
    name: str


class SettingsDict(TypedDict, total=False):
    """Application settings structure."""
    last_file: str
    recent_files: list[str]
    max_recent_files: int
    auto_load_last: bool
    window_geometry: Optional[dict[str, int]]
    last_palette_file: str
    recent_palette_files: list[str]
    max_recent_palette_files: int
    auto_offer_palette_loading: bool
    palette_file_associations: dict[str, str]


class MetadataDict(TypedDict, total=False):
    """Sprite metadata structure."""
    palette_colors: dict[str, list[list[int]]]
    sprite_width: int
    sprite_height: int
    source_file: str
    format: str
    version: str


class PaletteWidget(Protocol):
    """Protocol for palette widget interface."""
    colors: list[tuple[int, int, int]]
    selected_index: int
    is_external_palette: bool
    palette_source: str
    
    def set_palette(self, colors: list[tuple[int, int, int]], source: str = "External Palette") -> None: ...
    def reset_to_default(self) -> None: ...
    def set_color_mode(self, use_colors: bool) -> None: ...
    def update(self) -> None: ...


class EditorParent(Protocol):
    """Protocol for parent editor that supports zoom control and palettes."""
    external_palette_colors: Optional[list[tuple[int, int, int]]]
    
    def set_zoom_preset(self, zoom: int) -> None: ...
    def update_preview(self) -> None: ...


# File type filters for dialogs
FileFilter = Literal[
    "PNG Files (*.png);;All Files (*)",
    "Palette Files (*.pal.json);;JSON Files (*.json);;All Files (*)",
    "PNG Files (*.png)",
    "Palette Files (*.pal.json)",
]

# Dialog actions
DialogAction = Literal["new_file", "open_file", "open_recent"]

# Coordinate types
PixelCoord = tuple[int, int]  # (x, y) in pixel space
CanvasCoord = tuple[float, float]  # (x, y) in canvas space (with zoom)


class ImageInfo(TypedDict):
    """Information about a loaded image."""
    width: int
    height: int
    mode: str
    has_palette: bool
    palette_colors: Optional[list[RGB]]


class DrawingState(TypedDict):
    """Current drawing state."""
    tool: ToolType
    color_index: ColorIndex
    drawing: bool
    last_point: Optional[PixelCoord]


# Type guards
def is_valid_color_index(value: int) -> bool:
    """Check if a value is a valid 4bpp color index."""
    return 0 <= value <= 15


def is_valid_rgb(color: tuple[int, ...]) -> bool:
    """Check if a tuple is a valid RGB color."""
    return (
        len(color) >= 3 and
        all(isinstance(v, int) and 0 <= v <= 255 for v in color[:3])
    )


def is_valid_palette(colors: list[Any]) -> bool:
    """Check if a list contains a valid 16-color palette."""
    return (
        len(colors) >= 16 and
        all(is_valid_rgb(c) if isinstance(c, (list, tuple)) else False for c in colors[:16])
    )