#!/usr/bin/env python3
"""
Unit tests for MVC controllers - Using real objects where possible
Tests initialization, signal connections, and controller interactions
"""

from unittest.mock import Mock

import pytest

from sprite_editor.controllers.extract_controller import ExtractController
from sprite_editor.controllers.main_controller import MainController
from sprite_editor.controllers.palette_controller import PaletteController
from sprite_editor.controllers.viewer_controller import ViewerController
from sprite_editor.models.palette_model import PaletteModel
from sprite_editor.models.project_model import ProjectModel
from sprite_editor.models.sprite_model import SpriteModel


class TestViewerControllerWithRealModels:
    """Test ViewerController with real model objects"""

    def test_viewer_controller_initialization_order_with_real_models(self):
        """Test that would have caught the initialization order bug using real models"""
        # Use real models
        sprite_model = SpriteModel()
        palette_model = PaletteModel()

        # Only mock the view since it requires PyQt widgets
        view = Mock()
        view.zoom_in_requested = Mock()
        view.zoom_out_requested = Mock()
        view.zoom_fit_requested = Mock()
        view.grid_toggled = Mock()
        view.save_requested = Mock()
        view.open_editor_requested = Mock()

        # This would have raised AttributeError before the fix
        controller = ViewerController(sprite_model, palette_model, view)

        # Verify controller was created successfully
        assert controller.palette_model == palette_model
        assert controller.model == sprite_model
        assert controller.view == view

        # Verify connections were made
        view.zoom_in_requested.connect.assert_called_once()
        view.save_requested.connect.assert_called_once()


class TestPaletteControllerWithRealModels:
    """Test PaletteController with real model objects"""

    def test_palette_controller_creation_with_real_models(self):
        """Test PaletteController can be created with real models"""
        # Use real models
        sprite_model = SpriteModel()
        palette_model = PaletteModel()
        project_model = ProjectModel()

        # Only mock the view
        view = Mock()
        view.browse_oam_requested = Mock()
        view.generate_preview_requested = Mock()
        view.palette_selected = Mock()
        view.set_oam_file = Mock()

        # This would have raised AttributeError before the fix
        controller = PaletteController(
            sprite_model, palette_model, project_model, view)

        assert controller.model == palette_model
        assert controller.sprite_model == sprite_model
        assert controller.project_model == project_model
        assert controller.view == view


class TestExtractControllerWithRealModels:
    """Test ExtractController with real model objects"""

    def test_extract_controller_creation_with_real_models(self):
        """Test ExtractController with real models"""
        # Use real models
        sprite_model = SpriteModel()
        project_model = ProjectModel()

        # Only mock the view
        view = Mock()
        view.extract_requested = Mock()
        view.browse_vram_requested = Mock()
        view.browse_cgram_requested = Mock()
        view.set_vram_file = Mock()
        view.set_cgram_file = Mock()

        controller = ExtractController(sprite_model, project_model, view)

        assert controller.model == sprite_model
        assert controller.project_model == project_model
        assert controller.view == view

        # Verify signal connections
        view.extract_requested.connect.assert_called_once()
        view.browse_vram_requested.connect.assert_called_once()


class TestMainControllerWithRealModels:
    """Test MainController with real model objects"""

    def test_main_controller_initialization_with_real_models(self):
        """Test MainController can be initialized with real models"""
        # Create real models
        models = {
            'sprite': SpriteModel(),
            'palette': PaletteModel(),
            'project': ProjectModel()
        }

        # Create minimal mock views
        views = {
            'main_window': Mock(),
            'extract_tab': self._create_mock_extract_tab(),
            'inject_tab': self._create_mock_inject_tab(),
            'viewer_tab': self._create_mock_viewer_tab(),
            'multi_palette_tab': self._create_mock_palette_tab()
        }

        # Create controller - this tests the full initialization
        controller = MainController(models, views)

        # Verify all sub-controllers were created
        assert hasattr(controller, 'extract_controller')
        assert hasattr(controller, 'inject_controller')
        assert hasattr(controller, 'viewer_controller')
        assert hasattr(controller, 'palette_controller')

        # Verify viewer controller has palette_model (the bug we fixed)
        assert controller.viewer_controller.palette_model == models['palette']

        # Verify models are correctly assigned
        assert controller.sprite_model == models['sprite']
        assert controller.palette_model == models['palette']
        assert controller.project_model == models['project']

    def _create_mock_extract_tab(self):
        """Create a mock extract tab with required signals"""
        tab = Mock()
        tab.extract_requested = Mock()
        tab.browse_vram_requested = Mock()
        tab.browse_cgram_requested = Mock()
        tab.set_vram_file = Mock()
        tab.set_cgram_file = Mock()
        tab.offset_changed = Mock()
        tab.tile_count_changed = Mock()
        tab.multi_palette_toggled = Mock()
        return tab

    def _create_mock_inject_tab(self):
        """Create a mock inject tab with required signals"""
        tab = Mock()
        tab.inject_requested = Mock()
        tab.browse_source_requested = Mock()
        tab.browse_target_requested = Mock()
        tab.set_source_file = Mock()
        tab.set_target_file = Mock()
        tab.set_offset = Mock()
        return tab

    def _create_mock_viewer_tab(self):
        """Create a mock viewer tab with required signals"""
        tab = Mock()
        tab.zoom_in_requested = Mock()
        tab.zoom_out_requested = Mock()
        tab.zoom_fit_requested = Mock()
        tab.grid_toggled = Mock()
        tab.save_requested = Mock()
        tab.open_editor_requested = Mock()
        return tab

    def _create_mock_palette_tab(self):
        """Create a mock palette tab with required signals"""
        tab = Mock()
        tab.browse_oam_requested = Mock()
        tab.generate_preview_requested = Mock()
        tab.palette_selected = Mock()
        tab.set_oam_file = Mock()
        return tab


class TestControllerInteractionsWithRealModels:
    """Test controller interactions using real models"""

    def test_sprite_extraction_flow(self):
        """Test sprite extraction flow with real models"""
        # Create real models
        sprite_model = SpriteModel()
        project_model = ProjectModel()

        # Mock view
        extract_view = Mock()
        extract_view.extract_requested = Mock()
        extract_view.browse_vram_requested = Mock()
        extract_view.browse_cgram_requested = Mock()
        extract_view.set_vram_file = Mock()
        extract_view.set_cgram_file = Mock()

        # Create controller
        controller = ExtractController(
            sprite_model, project_model, extract_view)

        # Test file path updates
        sprite_model.vram_file = "/test/vram.bin"
        extract_view.set_vram_file.assert_called_with("/test/vram.bin")

        sprite_model.cgram_file = "/test/cgram.bin"
        extract_view.set_cgram_file.assert_called_with("/test/cgram.bin")

    def test_palette_application_flow(self):
        """Test palette application with real models"""
        # Create real models
        sprite_model = SpriteModel()
        palette_model = PaletteModel()

        # Mock view
        viewer_view = Mock()
        viewer_view.zoom_in_requested = Mock()
        viewer_view.zoom_out_requested = Mock()
        viewer_view.zoom_fit_requested = Mock()
        viewer_view.grid_toggled = Mock()
        viewer_view.save_requested = Mock()
        viewer_view.open_editor_requested = Mock()
        viewer_view.set_image = Mock()

        # Create controller
        controller = ViewerController(sprite_model, palette_model, viewer_view)

        # Mock image
        mock_image = Mock()
        mock_image.mode = 'P'
        mock_image.getpalette = Mock(return_value=None)

        # Set image
        sprite_model.current_image = mock_image
        viewer_view.set_image.assert_called_with(mock_image)


class TestInitializationOrderBugSpecific:
    """Specific test for the initialization order bug"""

    def test_initialization_order_matters(self):
        """Test that demonstrates why initialization order matters"""
        # Track when methods are called
        call_order = []

        class TrackedViewerController(ViewerController):
            def __init__(self, sprite_model, palette_model,
                         viewer_view, parent=None):
                call_order.append('start_init')
                super().__init__(sprite_model, palette_model, viewer_view, parent)
                call_order.append('end_init')

            def connect_signals(self):
                call_order.append('connect_signals')
                if hasattr(self, 'palette_model'):
                    call_order.append('has_palette_model')
                else:
                    call_order.append('NO_palette_model')
                super().connect_signals()

        # Create real models
        sprite_model = SpriteModel()
        palette_model = PaletteModel()

        # Mock view
        view = Mock()
        view.zoom_in_requested = Mock()
        view.zoom_out_requested = Mock()
        view.zoom_fit_requested = Mock()
        view.grid_toggled = Mock()
        view.save_requested = Mock()
        view.open_editor_requested = Mock()

        # Create controller
        controller = TrackedViewerController(sprite_model, palette_model, view)

        # Verify order
        assert 'has_palette_model' in call_order
        assert 'NO_palette_model' not in call_order

        # The order should be:
        # start_init -> connect_signals -> has_palette_model -> end_init
        assert call_order.index(
            'connect_signals') < call_order.index('end_init')
        assert call_order.index(
            'has_palette_model') < call_order.index('end_init')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
