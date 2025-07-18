#!/usr/bin/env python3
"""
Zoomable scroll area widget for the pixel editor
Forwards wheel events to canvas for zooming functionality
"""

# Standard library imports
from typing import Optional

# Third-party imports
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QScrollArea, QWidget

# Import common utilities
from ..pixel_editor_utils import debug_log


class ZoomableScrollArea(QScrollArea):
    """Custom scroll area that forwards wheel events to canvas for zooming"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.canvas = None

    def setWidget(self, widget: QWidget) -> None:
        """Override to store canvas reference"""
        super().setWidget(widget)
        if hasattr(widget, "wheelEvent"):
            self.canvas = widget

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Forward wheel events to canvas for zooming, unless Ctrl is held for scrolling"""
        debug_log(
            "SCROLL_AREA",
            f"Wheel event: delta={event.angleDelta().y()}, modifiers={event.modifiers()}",
            "DEBUG",
        )

        # If Ctrl is held, use normal scroll behavior
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            debug_log("SCROLL_AREA", "Ctrl held, using scroll behavior")
            super().wheelEvent(event)
            return

        # Otherwise, forward to canvas for zooming
        if self.canvas and hasattr(self.canvas, "wheelEvent"):
            debug_log("SCROLL_AREA", "Forwarding to canvas for zooming", "DEBUG")
            self.canvas.wheelEvent(event)
        else:
            debug_log("SCROLL_AREA", "No canvas, using default behavior", "WARNING")
            super().wheelEvent(event)