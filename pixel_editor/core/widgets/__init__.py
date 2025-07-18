#!/usr/bin/env python3
"""
Widgets module for the pixel editor
Provides reusable UI components
"""

from .color_palette_widget import ColorPaletteWidget
from .zoomable_scroll_area import ZoomableScrollArea

__all__ = [
    "ColorPaletteWidget",
    "ZoomableScrollArea",
]