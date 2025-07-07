"""
Kirby Super Star Sprite Editor
A comprehensive tool for extracting, viewing, and editing SNES sprites
"""

from .sprite_editor_core import SpriteEditorCore
from .sprite_viewer_widget import SpriteViewerWidget, PaletteViewerWidget
from .multi_palette_viewer import MultiPaletteViewer
from .oam_palette_mapper import OAMPaletteMapper

__version__ = "1.0.0"
__all__ = [
    'SpriteEditorCore',
    'SpriteViewerWidget',
    'PaletteViewerWidget',
    'MultiPaletteViewer',
    'OAMPaletteMapper'
]