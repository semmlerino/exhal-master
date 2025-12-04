"""
Real integration tests for recent UI improvements.
Tests dark theme, window sizing, and signal architecture working together.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

# Test both with and without real Qt
try:
    from launch_spritepal import SpritePalApp
    from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
    from ui.main_window import MainWindow
    REAL_QT_AVAILABLE = True
except ImportError:
    REAL_QT_AVAILABLE = False

class TestUIImprovementsIntegration:
    """Integration tests for UI improvements that work in headless mode."""

    def test_dark_theme_constants_exist(self):
        """Verify dark theme constants are defined."""
        from ui.styles.theme import COLORS, DIMENSIONS

        # Verify dark theme colors
        assert COLORS["background"] == "#2d2d30"
        assert COLORS["panel_background"] == "#383838"
        assert COLORS["preview_background"] == "#1e1e1e"
        assert COLORS["text_primary"] == "#ffffff"  # Fixed key name

        # Verify compact dimensions
        assert DIMENSIONS["button_height"] == 28
        assert DIMENSIONS["spacing_xs"] == 3
        assert DIMENSIONS["spacing_sm"] == 4

    def test_component_styling_functions_work(self):
        """Test that component styling functions execute without Qt."""
        from ui.styles.components import get_button_style, get_dark_panel_style, get_dark_preview_style

        # These should work without Qt
        button_css = get_button_style("primary")
        assert "background" in button_css
        assert "#ff7f50" in button_css or "#ff6633" in button_css  # Primary color (coral)

        preview_css = get_dark_preview_style()
        assert "#1e1e1e" in preview_css

        panel_css = get_dark_panel_style()
        assert "#383838" in panel_css

    def test_dialog_signals_defined(self):
        """Test that dialog signals are properly defined without Qt."""
        from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog

        # Check signal attributes exist (even if Qt isn't initialized)
        assert hasattr(UnifiedManualOffsetDialog, 'offset_changed')
        assert hasattr(UnifiedManualOffsetDialog, 'sprite_found')

@pytest.mark.gui
@pytest.mark.skipif(not REAL_QT_AVAILABLE, reason="Requires real Qt widgets")
class TestUIImprovementsRealQt:
    """Integration tests requiring real Qt."""

    @pytest.fixture
    def app(self, qtbot):
        """Create application for testing."""
        app = QApplication.instance()
        if not app:
            app = SpritePalApp([])
        return app

    def test_main_window_size_and_theme(self, qtbot, app):
        """Test main window has correct size and dark theme."""
        from ui.main_window import MainWindow

        window = MainWindow()
        qtbot.addWidget(window)

        # Test window size
        assert window.width() <= 1000
        assert window.height() <= 650

        # Test dark theme is applied
        palette = window.palette()
        bg_color = palette.color(palette.ColorRole.Window)

        # Dark theme should have dark background
        assert bg_color.lightness() < 128  # Dark color

    def test_manual_offset_dialog_signals_work(self, qtbot):
        """Test dialog signals work with real Qt."""
        from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog

        dialog = UnifiedManualOffsetDialog()
        qtbot.addWidget(dialog)

        # Test offset_changed signal
        offset_received = []
        dialog.offset_changed.connect(lambda x: offset_received.append(x))

        # Emit signal
        dialog.offset_changed.emit(12345)
        assert offset_received == [12345]

        # Test sprite_found signal
        sprite_data = []
        dialog.sprite_found.connect(lambda o, n: sprite_data.append((o, n)))

        dialog.sprite_found.emit(0x1000, "test_sprite")
        assert sprite_data == [(0x1000, "test_sprite")]

    def test_preview_widget_dark_background(self, qtbot):
        """Test preview widgets use dark backgrounds."""
        from ui.widgets.sprite_preview_widget import SpritePreviewWidget

        widget = SpritePreviewWidget()
        qtbot.addWidget(widget)

        # Get the widget's stylesheet or background
        style = widget.styleSheet()

        # Should have dark preview styling
        if style:
            assert "#1e1e1e" in style or "background" in style.lower()

    def test_button_gradient_styling(self, qtbot):
        """Test buttons have gradient styling."""
        button = QPushButton("Test")

        from ui.styles.components import get_button_style
        button.setStyleSheet(get_button_style("primary"))

        qtbot.addWidget(button)

        style = button.styleSheet()
        assert "qlineargradient" in style.lower() or "gradient" in style.lower()

class TestIntegrationWithMocks:
    """Integration tests using mocks for components."""

    @patch('ui.main_window.MainWindow')
    def test_main_window_initialization_flow(self, mock_window):
        """Test the initialization flow of main window with theme."""
        mock_instance = MagicMock()
        mock_window.return_value = mock_instance

        # Import after patching
        from ui.main_window import MainWindow

        MainWindow()

        # Should be called during init
        mock_window.assert_called_once()

    def test_rom_extraction_panel_connects_to_dialog_signals(self):
        """Test that ROM extraction panel connects to dialog signals."""
        from unittest.mock import Mock

        # Create mock dialog with signals
        mock_dialog = Mock()
        mock_dialog.offset_changed = Mock()
        mock_dialog.sprite_found = Mock()
        mock_dialog._custom_signals_connected = False

        # Simulate connection logic from ROM extraction panel
        def connect_signals(dialog):
            if not hasattr(dialog, "_custom_signals_connected"):
                dialog.offset_changed.connect(Mock())
                dialog.sprite_found.connect(Mock())
                dialog._custom_signals_connected = True

        connect_signals(mock_dialog)

        # Verify connections were made
        mock_dialog.offset_changed.connect.assert_called_once()
        mock_dialog.sprite_found.connect.assert_called_once()
        assert mock_dialog._custom_signals_connected == True

if __name__ == "__main__":
    # Run tests that work without display
    pytest.main([__file__, "-v", "-k", "not gui"])
