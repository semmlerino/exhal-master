"""
Type aliases for SpritePal to improve type safety and readability.

This module defines common type aliases used throughout the codebase
to make type annotations more readable and consistent.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeAlias

# Python compatibility imports for typing
# These are re-exported for use in other modules
try:
    from typing_extensions import override
    __all__ = [
        "ImageMode", "ImageSize", "NotRequired", "PILImage", "Protocol", "TypeGuard", "TypedDict", "override", ]
except ImportError:
    # Fallback for older Python versions
    try:
        from typing import NotRequired, TypeGuard

        from typing_extensions import (
            Protocol,
            TypedDict,
        )
        __all__ = [
            "ImageMode",
            "ImageSize",
            "NotRequired",
            "PILImage",
            "Protocol",
            "TypeGuard",
            "TypedDict",
            "override",
        ]
    except ImportError:
        __all__ = ["ImageMode", "ImageSize", "PILImage"]

from PIL import Image
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget

# External library types for better type checking
# Use concrete PIL Image type to avoid forward reference issues
PILImage: TypeAlias = Image.Image
# Note: numpy is not currently used in the codebase, removing for now
# NumpyArray: TypeAlias = "numpy.ndarray[Any, Any]"
ImageMode: TypeAlias = str  # "RGB", "RGBA", "L", "P"
ImageSize: TypeAlias = tuple[int, int]

# Complex data structures for sprite manipulation
TileMatrix: TypeAlias = list[list[list[int]]]
SpriteData: TypeAlias = tuple[TileMatrix, int]
SimilarityScore: TypeAlias = float
# Core sprite and ROM data types (defined early to avoid forward references)
SpriteOffset: TypeAlias = int

# Complex search result types (now that SpriteOffset is defined)
SimilarityResult: TypeAlias = tuple[SpriteOffset, SimilarityScore]
SearchResults: TypeAlias = list[SimilarityResult]
PaletteData: TypeAlias = list[int]
RGBColor: TypeAlias = tuple[int, int, int]
ROMData: TypeAlias = bytes
TileData: TypeAlias = bytes

# Preview and image types
PreviewPixmap: TypeAlias = QPixmap | None
PreviewSize: TypeAlias = tuple[int, int]
TileCount: TypeAlias = int

# Worker and callback types
WorkerCallback: TypeAlias = Callable[[Any], None]
ProgressCallback: TypeAlias = Callable[[int, str], None]
ErrorCallback: TypeAlias = Callable[[str, Exception], None]

# UI and widget types
WidgetParent: TypeAlias = QWidget | None
DialogResult: TypeAlias = bool

# File path types
FilePath: TypeAlias = str
OutputPath: TypeAlias = str
CachePath: TypeAlias = str

# Configuration and settings types
ConfigDict: TypeAlias = dict[str, Any]
SettingsValue: TypeAlias = Any
ValidationResult: TypeAlias = tuple[bool, str | None]

# Signal types for Qt
StringSignal: TypeAlias = str
IntSignal: TypeAlias = int
BoolSignal: TypeAlias = bool
ListSignal: TypeAlias = list[Any]
DictSignal: TypeAlias = dict[str, Any]

# Manager operation types
OperationName: TypeAlias = str
OperationResult: TypeAlias = bool
OperationProgress: TypeAlias = tuple[int, int]  # (current, total)

# Cache types
CacheKey: TypeAlias = str
CacheData: TypeAlias = Any
CacheStats: TypeAlias = dict[str, int | float]

# Navigation types (for smart sprite discovery)
NavigationHint: TypeAlias = dict[str, Any]
SpriteLocation: TypeAlias = dict[str, Any]
RegionMap: TypeAlias = dict[str, Any]
