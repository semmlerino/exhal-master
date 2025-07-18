#!/usr/bin/env python3
"""
API Contract Tests for Pixel Editor V3 Architecture
Tests the actual API of the refactored components
"""

import inspect

from pixel_editor.core.pixel_editor_canvas_v3 import PixelCanvasV3
from pixel_editor.core.pixel_editor_controller_v3 import PixelEditorController
from pixel_editor.core.widgets import ColorPaletteWidget, ZoomableScrollArea


class TestPixelCanvasV3API:
    """Test PixelCanvasV3 API contracts - tests actual canvas methods"""

    def test_canvas_view_methods(self):
        """Test canvas view control methods"""
        view_methods = {
            "set_zoom": ["self", "zoom", "center_on_canvas"],
            "set_grid_visible": ["self", "visible"],
            "set_greyscale_mode": ["self", "greyscale"],
        }

        for method_name, expected_params in view_methods.items():
            method = getattr(PixelCanvasV3, method_name)
            sig = inspect.signature(method)
            actual_params = list(sig.parameters.keys())

            # Check if the required params match (allowing for defaults)
            assert actual_params[: len(expected_params)] == expected_params or (
                all(p in actual_params for p in expected_params if p != "self")
            ), f"{method_name} has unexpected signature: {actual_params}"

    def test_canvas_event_methods(self):
        """Test canvas event handling methods"""
        event_methods = [
            "paintEvent",
            "mousePressEvent",
            "mouseMoveEvent",
            "mouseReleaseEvent",
            "wheelEvent",
            "leaveEvent",
            "enterEvent",
        ]

        for method_name in event_methods:
            assert hasattr(
                PixelCanvasV3, method_name
            ), f"Event method {method_name} not found"

    def test_canvas_signals(self):
        """Test canvas emits proper signals"""
        signals = [
            "pixelPressed",
            "pixelMoved",
            "pixelReleased",
            "zoomRequested",
        ]

        # Check class has these signal attributes
        for signal_name in signals:
            assert hasattr(
                PixelCanvasV3, signal_name
            ), f"Signal {signal_name} not found"

    def test_canvas_requires_controller(self):
        """Test that canvas requires a controller in __init__"""
        init_sig = inspect.signature(PixelCanvasV3.__init__)
        params = list(init_sig.parameters.keys())
        
        # Should have self, controller, and optional parent
        assert "controller" in params, "PixelCanvasV3 should require a controller"


class TestPixelEditorControllerAPI:
    """Test PixelEditorController API contracts - where drawing logic lives"""

    def test_drawing_operations(self):
        """Test drawing operations are on the controller"""
        drawing_methods = {
            "handle_canvas_press": ["self", "x", "y"],
            "handle_canvas_move": ["self", "x", "y"],
            "handle_canvas_release": ["self", "x", "y"],
        }

        for method_name, expected_params in drawing_methods.items():
            method = getattr(PixelEditorController, method_name)
            sig = inspect.signature(method)
            actual_params = list(sig.parameters.keys())

            assert (
                actual_params[: len(expected_params)] == expected_params
            ), f"{method_name} has unexpected signature"

    def test_file_operations(self):
        """Test file operation methods"""
        file_methods = {
            "new_file": ["self", "width", "height"],
            "open_file": ["self", "file_path"],
            "save_file": ["self", "file_path"],
        }

        for method_name, expected_params in file_methods.items():
            method = getattr(PixelEditorController, method_name)
            sig = inspect.signature(method)
            actual_params = list(sig.parameters.keys())

            # Check required params (some may have defaults)
            for param in expected_params:
                if param != "self":
                    assert param in actual_params, f"{method_name} missing {param} parameter"

    def test_tool_operations(self):
        """Test tool-related methods"""
        tool_methods = {
            "set_tool": ["self", "tool_name"],
            "set_drawing_color": ["self", "color_index"],
            "set_brush_size": ["self", "size"],
        }

        for method_name, expected_params in tool_methods.items():
            method = getattr(PixelEditorController, method_name)
            sig = inspect.signature(method)
            actual_params = list(sig.parameters.keys())

            assert (
                actual_params[: len(expected_params)] == expected_params
            ), f"{method_name} has unexpected signature"

    def test_undo_redo_operations(self):
        """Test undo/redo methods"""
        assert hasattr(PixelEditorController, "undo"), "Controller should have undo"
        assert hasattr(PixelEditorController, "redo"), "Controller should have redo"

    def test_controller_signals(self):
        """Test controller emits proper signals"""
        signals = [
            "imageChanged",
            "paletteChanged", 
            "toolChanged",
            "titleChanged",
            "statusMessage",
            "error",
        ]

        for signal_name in signals:
            assert hasattr(
                PixelEditorController, signal_name
            ), f"Signal {signal_name} not found"


class TestColorPaletteWidgetAPI:
    """Test ColorPaletteWidget API contracts"""

    def test_palette_methods(self):
        """Test palette manipulation methods"""
        methods = {
            "set_palette": ["self", "colors", "source"],
            "reset_to_default": ["self"],
            "set_color_mode": ["self", "use_colors"],
            "get_palette": ["self"],
        }

        for method_name, expected_params in methods.items():
            method = getattr(ColorPaletteWidget, method_name)
            sig = inspect.signature(method)
            actual_params = list(sig.parameters.keys())

            # Check required params
            for param in expected_params:
                if param != "self":
                    assert param in actual_params or (
                        # Allow optional params
                        param in sig.parameters and 
                        sig.parameters[param].default != inspect.Parameter.empty
                    ), f"{method_name} missing {param} parameter"

    def test_palette_properties(self):
        """Test palette widget properties"""
        # Check current_color property
        assert hasattr(ColorPaletteWidget, "current_color"), "Should have current_color property"

    def test_signals(self):
        """Test widget signals"""
        assert hasattr(ColorPaletteWidget, "colorSelected")


class TestZoomableScrollAreaAPI:
    """Test ZoomableScrollArea API"""

    def test_scroll_area_methods(self):
        """Test scroll area overrides"""
        methods = ["setWidget", "wheelEvent"]

        for method_name in methods:
            assert hasattr(
                ZoomableScrollArea, method_name
            ), f"Method {method_name} not found"