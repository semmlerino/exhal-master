#!/usr/bin/env python3
"""
API Contract Tests for Pixel Editor
Ensures all public methods match their expected signatures and usage patterns.
"""

import inspect

import pytest

from pixel_editor.core import pixel_editor_constants, pixel_editor_utils

# Import all modules to test
from pixel_editor.core.indexed_pixel_editor import IndexedPixelEditor
from pixel_editor.core.pixel_editor_commands import (
    DrawPixelCommand,
    UndoCommand,
    UndoManager,
)
from pixel_editor.core.widgets import ColorPaletteWidget
from pixel_editor.core.pixel_editor_canvas_v3 import PixelCanvasV3
from pixel_editor.core.pixel_editor_workers import (
    BaseWorker,
    FileLoadWorker,
    FileSaveWorker,
    PaletteLoadWorker,
)


class TestWorkerAPIs:
    """Test worker thread API contracts"""

    def test_base_worker_signals(self):
        """Verify BaseWorker has expected signals"""
        # Check signal attributes exist
        assert hasattr(BaseWorker, "progress")
        assert hasattr(BaseWorker, "error")
        assert hasattr(BaseWorker, "finished")

        # Check signal types (they should be class attributes)
        assert BaseWorker.progress is not None
        assert BaseWorker.error is not None
        assert BaseWorker.finished is not None

    def test_file_load_worker_api(self):
        """Test FileLoadWorker specific API"""
        # Check constructor
        sig = inspect.signature(FileLoadWorker.__init__)
        params = list(sig.parameters.keys())
        assert "file_path" in params

        # Check result signal exists
        assert hasattr(FileLoadWorker, "result")

    def test_worker_method_signatures(self):
        """Test common worker methods"""
        workers = [FileLoadWorker, FileSaveWorker, PaletteLoadWorker]

        for worker_class in workers:
            # All should have these methods
            assert hasattr(worker_class, "run")
            assert hasattr(worker_class, "cancel")
            assert hasattr(worker_class, "is_cancelled")

            # Check run method has no required parameters
            sig = inspect.signature(worker_class.run)
            required_params = [
                p
                for p in sig.parameters.values()
                if p.default == inspect.Parameter.empty and p.name != "self"
            ]
            assert (
                len(required_params) == 0
            ), f"{worker_class.__name__}.run() should not require parameters"


class TestPixelCanvasV3API:
    """Test PixelCanvasV3 API contracts
    
    NOTE: These tests have been moved to test_api_contracts_v3.py
    to reflect the new V3 architecture where drawing methods are 
    on the controller, not the canvas.
    """

    def test_drawing_methods(self):
        """Test drawing method signatures - DEPRECATED"""
        # Drawing methods are now on PixelEditorController, not PixelCanvasV3
        # See test_api_contracts_v3.py for updated tests
        pytest.skip("Drawing methods moved to controller in V3 architecture")

    def test_image_methods(self):
        """Test image manipulation methods - DEPRECATED"""
        # Image methods are now on PixelEditorController, not PixelCanvasV3
        # See test_api_contracts_v3.py for updated tests
        pytest.skip("Image methods moved to controller in V3 architecture")

    def test_optimization_methods(self):
        """Test V3 optimization methods exist"""
        # Check actual optimization methods in PixelCanvasV3
        optimization_methods = [
            "_update_qcolor_cache",  # Color caching
            "_update_color_lut",  # Color lookup table
            "_calculate_visible_image_region",  # Viewport culling
            "_update_hover_regions",  # Hover region optimization
            "_get_scaled_qimage",  # Cached scaled image
            "_update_qimage_buffer",  # QImage buffer caching
        ]

        for method_name in optimization_methods:
            assert hasattr(
                PixelCanvasV3, method_name
            ), f"Optimization method {method_name} not found"


class TestColorPaletteWidgetAPI:
    """Test ColorPaletteWidget API contracts"""

    def test_palette_methods(self):
        """Test palette manipulation methods"""
        methods = {
            "set_palette": ["self", "colors", "source"],
            "reset_to_default": ["self"],
        }

        for method_name, expected_params in methods.items():
            method = getattr(ColorPaletteWidget, method_name)
            sig = inspect.signature(method)
            actual_params = list(sig.parameters.keys())

            assert (
                actual_params[: len(expected_params)] == expected_params
            ), f"{method_name} has unexpected signature"

        # Check that colors attribute is set in __init__
        # We can check the source code or the __init__ method
        init_code = ColorPaletteWidget.__init__.__code__
        assert (
            "colors" in init_code.co_names
        ), "ColorPaletteWidget should initialize 'colors' attribute"

    def test_signals(self):
        """Test widget signals"""
        assert hasattr(ColorPaletteWidget, "colorSelected")


class TestIndexedPixelEditorAPI:
    """Test main editor API contracts"""

    def test_file_operations(self):
        """Test file operation method signatures"""
        file_methods = {
            "open_file": ["self"],
            "save_file": ["self"],
            "save_file_as": ["self"],  # Changed from save_as
            "load_file_by_path": ["self", "file_path"],
            "save_to_file": ["self", "file_path"],
        }

        for method_name, expected_params in file_methods.items():
            method = getattr(IndexedPixelEditor, method_name)
            sig = inspect.signature(method)
            actual_params = list(sig.parameters.keys())

            assert (
                actual_params[: len(expected_params)] == expected_params
            ), f"{method_name} has unexpected signature"

    def test_palette_operations(self):
        """Test palette operation methods"""
        # apply_palette has different signature than expected
        method = IndexedPixelEditor.apply_palette
        sig = inspect.signature(method)
        actual_params = list(sig.parameters.keys())
        assert actual_params == [
            "self",
            "palette_idx",
            "colors",
        ], f"apply_palette has unexpected signature: {actual_params}"

        # Test methods that don't exist in the V3 refactor
        # load_palette_by_path was removed, switch_palette exists
        # toggle_color_mode was replaced with toggle_color_mode_shortcut
        if hasattr(IndexedPixelEditor, "toggle_color_mode_shortcut"):
            method = IndexedPixelEditor.toggle_color_mode_shortcut
            sig = inspect.signature(method)
            actual_params = list(sig.parameters.keys())
            assert actual_params == [
                "self"
            ], "toggle_color_mode_shortcut has unexpected signature"


class TestUndoSystemAPI:
    """Test undo system API contracts"""

    def test_undo_command_interface(self):
        """Test UndoCommand abstract interface"""
        # Should have these abstract methods
        assert hasattr(UndoCommand, "execute")
        assert hasattr(UndoCommand, "unexecute")
        assert hasattr(UndoCommand, "get_memory_size")

        # Test DrawPixelCommand matches expected signature
        # DrawPixelCommand is a dataclass, so check its fields
        import dataclasses

        assert dataclasses.is_dataclass(DrawPixelCommand)

        fields = [f.name for f in dataclasses.fields(DrawPixelCommand)]
        expected_fields = ["x", "y", "old_color", "new_color"]

        for field in expected_fields:
            assert field in fields, f"DrawPixelCommand missing field: {field}"

        # Check that execute/unexecute take canvas parameter
        exec_sig = inspect.signature(DrawPixelCommand.execute)
        exec_params = list(exec_sig.parameters.keys())
        assert exec_params == [
            "self",
            "canvas",
        ], f"DrawPixelCommand.execute has unexpected signature: {exec_params}"

    def test_undo_manager_api(self):
        """Test UndoManager public API"""
        # Methods that take canvas parameter
        canvas_methods = {
            "execute_command": ["self", "command", "canvas"],
            "undo": ["self", "canvas"],
            "redo": ["self", "canvas"],
        }

        for method_name, expected_params in canvas_methods.items():
            method = getattr(UndoManager, method_name)
            sig = inspect.signature(method)
            actual_params = list(sig.parameters.keys())

            assert (
                actual_params == expected_params
            ), f"{method_name} has unexpected signature: {actual_params}"

        # Methods without canvas parameter
        other_methods = {
            "clear": ["self"],
            "get_memory_usage": ["self"],
        }

        for method_name, expected_params in other_methods.items():
            method = getattr(UndoManager, method_name)
            sig = inspect.signature(method)
            actual_params = list(sig.parameters.keys())

            assert (
                actual_params == expected_params
            ), f"{method_name} has unexpected signature: {actual_params}"

        # Test that can_undo and can_redo are available via get_memory_usage
        manager = UndoManager()
        usage = manager.get_memory_usage()
        assert "can_undo" in usage
        assert "can_redo" in usage


class TestUtilityAPIs:
    """Test utility module APIs"""

    def test_debug_functions(self):
        """Test debug utility functions"""
        debug_functions = {
            "debug_log": ["category", "message", "level"],
            "debug_color": ["color_index", "rgb"],
            "debug_exception": ["category", "exception"],
        }

        for func_name, expected_params in debug_functions.items():
            func = getattr(pixel_editor_utils, func_name)
            sig = inspect.signature(func)
            actual_params = list(sig.parameters.keys())

            assert (
                actual_params[: len(expected_params)] == expected_params
            ), f"{func_name} has unexpected signature"

    def test_validation_functions(self):
        """Test validation utility functions"""
        validation_functions = {
            "validate_color_index": ["index", "max_colors"],
            "validate_rgb_color": ["color"],
            "is_grayscale_color": ["rgb"],
            "validate_palette_file": ["data"],
        }

        for func_name, expected_params in validation_functions.items():
            if hasattr(pixel_editor_utils, func_name):
                func = getattr(pixel_editor_utils, func_name)
                sig = inspect.signature(func)
                actual_params = list(sig.parameters.keys())

                assert (
                    actual_params[: len(expected_params)] == expected_params
                ), f"{func_name} has unexpected signature"


class TestConstantsExist:
    """Test that expected constants are defined"""

    def test_critical_constants(self):
        """Test critical constants exist"""
        critical_constants = [
            "PALETTE_COLORS_COUNT",  # Instead of MAX_COLORS
            "BITS_PER_PIXEL",
            "ZOOM_DEFAULT",  # Instead of DEFAULT_ZOOM
            "ZOOM_MAX",  # Instead of MAX_ZOOM_LEVEL
            "ZOOM_MIN",  # Instead of MIN_ZOOM_LEVEL
            "PALETTE_CELL_SIZE",
            "UNDO_STACK_SIZE",
            "MAX_IMAGE_WIDTH",
            "MAX_IMAGE_HEIGHT",
        ]

        for const_name in critical_constants:
            assert hasattr(
                pixel_editor_constants, const_name
            ), f"Critical constant {const_name} not found"

            # Verify it's actually a constant (not a function)
            value = getattr(pixel_editor_constants, const_name)
            assert not callable(
                value
            ), f"{const_name} should be a constant, not callable"


class TestSignatureCompatibility:
    """Test that connected signals match slot signatures"""

    def test_palette_widget_to_canvas(self):
        """Test palette widget colorSelected signal compatibility with controller"""
        # In V3 architecture:
        # - colorSelected emits: int  
        # - Controller.set_drawing_color(int) receives it
        # - Controller's ToolManager stores current_color
        
        # This test has been moved to test_api_contracts_v3.py
        pytest.skip("Color selection handled by controller in V3 architecture")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
