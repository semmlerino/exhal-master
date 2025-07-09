"""
Kirby Super Star Sprite Editor
A comprehensive tool for extracting, viewing, and editing SNES sprites
"""

from .multi_palette_viewer import MultiPaletteViewer
from .oam_palette_mapper import OAMPaletteMapper
from .sprite_editor_core import SpriteEditorCore
from .sprite_viewer_widget import PaletteViewerWidget, SpriteViewerWidget

__version__ = "1.0.0"
__all__ = [
    "MultiPaletteViewer",
    "OAMPaletteMapper",
    "PaletteViewerWidget",
    "SpriteEditorCore",
    "SpriteViewerWidget",
]
