#!/usr/bin/env python3
"""
Application initialization tests with proper mocking
Focuses on testing initialization order bugs
"""

import tempfile
from unittest.mock import Mock, patch

import pytest

from sprite_editor.application import SpriteEditorApplication


class TestApplicationInitialization:
    """Test application initialization focusing on the bugs we fixed"""

    @patch('sprite_editor.application.QApplication')
    @patch('sprite_editor.application.MainWindow')
    def test_viewer_controller_initialization_bug(
            self, mock_window_class, mock_qapp):
        """Test that would have caught the ViewerController initialization bug"""
        # Create mock window with required tabs
        mock_window = self._create_mock_window()
        mock_window_class.return_value = mock_window

        # Create app with temporary settings directory
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict('os.environ', {'APPDATA': temp_dir}):
                app = SpriteEditorApplication()

        # This would have failed with AttributeError before the fix:
        # AttributeError: 'ViewerController' object has no attribute
        # 'palette_model'
        main_controller = app.controllers['main']
        viewer_controller = main_controller.viewer_controller

        # Verify the fix worked
        assert hasattr(viewer_controller, 'palette_model')
        assert viewer_controller.palette_model is not None

    @patch('sprite_editor.application.QApplication')
    @patch('sprite_editor.application.MainWindow')
    def test_palette_controller_initialization_bug(
            self, mock_window_class, mock_qapp):
        """Test that would have caught the PaletteController initialization bug"""
        # Create mock window
        mock_window = self._create_mock_window()
        mock_window_class.return_value = mock_window

        # Create app with temporary settings
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict('os.environ', {'APPDATA': temp_dir}):
                app = SpriteEditorApplication()

        # This would have failed with AttributeError before the fix:
        # AttributeError: 'PaletteController' object has no attribute
        # 'sprite_model'
        main_controller = app.controllers['main']
        palette_controller = main_controller.palette_controller

        # Verify the fix worked
        assert hasattr(palette_controller, 'sprite_model')
        assert palette_controller.sprite_model is not None

    @patch('sprite_editor.application.QApplication')
    @patch('sprite_editor.application.MainWindow')
    def test_all_controllers_initialized(self, mock_window_class, mock_qapp):
        """Test all controllers are initialized without errors"""
        # Create mock window
        mock_window = self._create_mock_window()
        mock_window_class.return_value = mock_window

        # Create app with temporary settings
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict('os.environ', {'APPDATA': temp_dir}):
                app = SpriteEditorApplication()

        # Verify all controllers exist
        main = app.controllers['main']
        assert hasattr(main, 'extract_controller')
        assert hasattr(main, 'inject_controller')
        assert hasattr(main, 'viewer_controller')
        assert hasattr(main, 'palette_controller')

        # Verify models are connected
        assert main.sprite_model == app.models['sprite']
        assert main.palette_model == app.models['palette']
        assert main.project_model == app.models['project']

    def _create_mock_window(self):
        """Create a properly mocked window"""
        window = Mock()

        # Create tabs
        extract_tab = self._create_mock_tab()
        inject_tab = self._create_mock_tab()
        viewer_tab = self._create_mock_tab()
        multi_palette_tab = self._create_mock_tab()

        # Set up get_tabs to return a dict
        window.get_tabs = Mock(return_value={
            'extract': extract_tab,
            'inject': inject_tab,
            'viewer': viewer_tab,
            'multi_palette': multi_palette_tab
        })

        # Window methods
        window.setWindowTitle = Mock()
        window.show = Mock()

        return window

    def _create_mock_tab(self):
        """Create a tab with all required signals"""
        tab = Mock()

        # All possible signals a tab might have
        signals = [
            'extract_requested', 'browse_vram_requested', 'browse_cgram_requested',
            'browse_oam_requested', 'inject_requested', 'browse_source_requested',
            'browse_target_requested', 'zoom_in_requested', 'zoom_out_requested',
            'zoom_fit_requested', 'grid_toggled', 'save_requested',
            'open_editor_requested', 'generate_preview_requested', 'palette_selected',
            'offset_changed', 'tile_count_changed', 'multi_palette_toggled'
        ]

        for signal in signals:
            setattr(tab, signal, Mock())

        # Methods
        methods = [
            'set_vram_file', 'set_cgram_file', 'set_oam_file',
            'set_source_file', 'set_target_file', 'set_offset'
        ]

        for method in methods:
            setattr(tab, method, Mock())

        return tab


class TestRealWorldScenario:
    """Test a real-world usage scenario"""

    @patch('sprite_editor.application.QApplication')
    @patch('sprite_editor.application.MainWindow')
    def test_file_path_updates(self, mock_window_class, mock_qapp):
        """Test that file paths update correctly through MVC"""
        # Create mock window
        mock_window = Mock()

        # Create tabs
        extract_tab = Mock()
        inject_tab = Mock()
        viewer_tab = Mock()
        multi_palette_tab = Mock()

        # Add all required signals to each tab
        for tab in [extract_tab, inject_tab, viewer_tab, multi_palette_tab]:
            # All possible signals
            signals = [
                'extract_requested', 'browse_vram_requested', 'browse_cgram_requested',
                'browse_oam_requested', 'inject_requested', 'browse_source_requested',
                'browse_target_requested', 'zoom_in_requested', 'zoom_out_requested',
                'zoom_fit_requested', 'grid_toggled', 'save_requested',
                'open_editor_requested', 'generate_preview_requested', 'palette_selected',
                'offset_changed', 'tile_count_changed', 'multi_palette_toggled'
            ]
            for signal in signals:
                setattr(tab, signal, Mock())

            # Methods
            methods = [
                'set_vram_file', 'set_cgram_file', 'set_oam_file',
                'set_source_file', 'set_target_file', 'set_offset'
            ]
            for method in methods:
                setattr(tab, method, Mock())

        # Set up get_tabs to return a dict
        mock_window.get_tabs = Mock(return_value={
            'extract': extract_tab,
            'inject': inject_tab,
            'viewer': viewer_tab,
            'multi_palette': multi_palette_tab
        })

        # Window methods
        mock_window.setWindowTitle = Mock()
        mock_window.show = Mock()

        mock_window_class.return_value = mock_window

        # Create app with temporary settings
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict('os.environ', {'APPDATA': temp_dir}):
                app = SpriteEditorApplication()

        # Update file paths
        sprite_model = app.models['sprite']
        sprite_model.vram_file = "/test/vram.bin"
        sprite_model.cgram_file = "/test/cgram.bin"

        # Verify views were updated
        extract_tab.set_vram_file.assert_called_with("/test/vram.bin")
        extract_tab.set_cgram_file.assert_called_with("/test/cgram.bin")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
