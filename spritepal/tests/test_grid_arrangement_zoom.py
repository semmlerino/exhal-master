"""
Test zoom functionality in grid arrangement dialog
"""

import os
import sys
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QGraphicsRectItem, QGraphicsScene

from ui.grid_arrangement_dialog import GridGraphicsView, SelectionMode
from ui.row_arrangement.grid_arrangement_manager import TilePosition


# Serial execution required: QApplication management
pytestmark = [
    
    pytest.mark.serial,
    pytest.mark.qt_application
]


@pytest.mark.gui
class TestGridGraphicsViewZoom:
    """Test zoom functionality in GridGraphicsView"""

    def setup_method(self):
        """Setup test fixtures"""
        # Skip if we're in a headless environment that can't support Qt widgets

        # Check for headless environment indicators
        is_headless = (
            not os.environ.get("DISPLAY")
            or os.environ.get("CI")
            or "microsoft" in os.uname().release.lower()
            or (sys.platform.startswith("linux") and not os.environ.get("DISPLAY"))
        )

        if is_headless:
            pytest.skip("GUI tests skipped in headless environment")

        # Try to create QApplication and handle any failures
        try:
            if not QApplication.instance():
                self.app = QApplication([])
            else:
                self.app = QApplication.instance()

            # Create view
            self.view = GridGraphicsView()
            self.view.set_grid_dimensions(16, 16, 8, 8)

            # Create real scene for tests that need it
            self.scene = QGraphicsScene()
            self.view.setScene(self.scene)
        except Exception as e:
            pytest.skip(f"GUI tests skipped due to Qt initialization error: {e}")

    def test_zoom_initialization(self):
        """Test zoom initialization"""
        assert self.view.zoom_level == 1.0
        assert self.view.min_zoom == 0.1
        assert self.view.max_zoom == 20.0
        assert self.view.is_panning is False
        assert self.view.last_pan_point is None

    def test_zoom_in_functionality(self):
        """Test zoom in functionality"""
        initial_zoom = self.view.zoom_level

        # Test zoom in
        self.view.zoom_in()

        # Should be zoomed in (zoom level increased)
        assert self.view.zoom_level > initial_zoom
        assert self.view.zoom_level == initial_zoom * 1.25

    def test_zoom_out_functionality(self):
        """Test zoom out functionality"""
        # Start with zoomed in state
        self.view.zoom_level = 2.0
        initial_zoom = self.view.zoom_level

        # Test zoom out
        self.view.zoom_out()

        # Should be zoomed out (zoom level decreased)
        assert self.view.zoom_level < initial_zoom
        assert self.view.zoom_level == initial_zoom * 0.8

    def test_zoom_limits(self):
        """Test zoom limits are enforced"""
        # Test minimum zoom limit
        self.view.zoom_level = 0.2
        self.view.zoom_out()
        assert self.view.zoom_level >= self.view.min_zoom

        # Test maximum zoom limit
        self.view.zoom_level = 19.0
        self.view.zoom_in()
        assert self.view.zoom_level <= self.view.max_zoom

    def test_reset_zoom(self):
        """Test reset zoom functionality"""
        # Zoom to some other level
        self.view.zoom_level = 3.5

        # Reset zoom
        self.view.reset_zoom()

        # Should be back to 1.0
        assert self.view.zoom_level == 1.0

    def test_zoom_to_fit(self):
        """Test zoom to fit functionality"""
        # Add a simple item to the scene for testing

        rect_item = QGraphicsRectItem(0, 0, 100, 100)
        self.scene.addItem(rect_item)

        # Test zoom to fit
        self.view.zoom_to_fit()

        # Should have adjusted zoom level
        # The actual zoom level depends on the view size vs scene size
        assert self.view.zoom_level >= 0.1

    def test_get_zoom_level(self):
        """Test get zoom level method"""
        test_levels = [0.5, 1.0, 2.0, 5.0]

        for level in test_levels:
            self.view.zoom_level = level
            assert self.view.get_zoom_level() == level

    def test_zoom_changed_signal(self):
        """Test zoom changed signal emission"""
        # Mock the signal
        self.view.zoom_changed = Mock()

        # Test zoom operations emit signal
        self.view.zoom_in()
        self.view.zoom_changed.emit.assert_called()

        self.view.zoom_out()
        self.view.zoom_changed.emit.assert_called()

        self.view.reset_zoom()
        self.view.zoom_changed.emit.assert_called()

    def test_wheel_event_zoom(self):
        """Test wheel event zoom functionality"""
        # Test _zoom_at_point method directly since wheel event is complex to construct

        initial_zoom = self.view.zoom_level

        # Test zoom in at a specific point
        self.view._zoom_at_point(QPointF(50, 50), 1.15)

        # Should zoom in
        assert self.view.zoom_level > initial_zoom

        # Test zoom out
        current_zoom = self.view.zoom_level
        self.view._zoom_at_point(QPointF(50, 50), 1.0 / 1.15)

        # Should zoom out
        assert self.view.zoom_level < current_zoom

    def test_keyboard_shortcuts(self):
        """Test keyboard shortcuts for zoom"""
        # Test F key (zoom to fit)
        f_event = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_F, Qt.KeyboardModifier.NoModifier
        )
        self.view.keyPressEvent(f_event)
        # Should call zoom_to_fit - we can't easily test this without mocking

        # Test Ctrl+0 (reset zoom)
        initial_zoom = self.view.zoom_level = 2.0
        ctrl_0_event = QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_0, Qt.KeyboardModifier.ControlModifier
        )
        self.view.keyPressEvent(ctrl_0_event)
        assert self.view.zoom_level == 1.0

        # Test Ctrl+Plus (zoom in)
        initial_zoom = self.view.zoom_level
        ctrl_plus_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Plus,
            Qt.KeyboardModifier.ControlModifier,
        )
        self.view.keyPressEvent(ctrl_plus_event)
        assert self.view.zoom_level > initial_zoom

        # Test Ctrl+Minus (zoom out)
        initial_zoom = self.view.zoom_level
        ctrl_minus_event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Minus,
            Qt.KeyboardModifier.ControlModifier,
        )
        self.view.keyPressEvent(ctrl_minus_event)
        assert self.view.zoom_level < initial_zoom

    def test_pan_functionality(self):
        """Test pan functionality"""
        # Test pan state initialization
        assert self.view.is_panning is False
        assert self.view.last_pan_point is None

        # Create real mouse press event with Ctrl modifier

        press_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(50, 50),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ControlModifier,
        )

        # Start panning
        self.view.mousePressEvent(press_event)

        # Should be in panning state
        assert self.view.is_panning is True
        assert self.view.last_pan_point is not None

        # Create real mouse release event
        release_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(50, 50),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.ControlModifier,
        )

        # Test mouse release
        self.view.mouseReleaseEvent(release_event)

        # Should exit panning state
        assert self.view.is_panning is False
        assert self.view.last_pan_point is None

    def test_tile_selection_with_zoom(self):
        """Test that tile selection works correctly when zoomed"""
        # Set up tile selection
        self.view.selection_mode = SelectionMode.TILE

        # Test tile click at different zoom levels
        zoom_levels = [0.5, 1.0, 2.0, 4.0]

        for zoom_level in zoom_levels:
            self.view.zoom_level = zoom_level

            # Create real mouse event

            click_event = QMouseEvent(
                QMouseEvent.Type.MouseButtonPress,
                QPointF(16, 16),  # Click at position that should be tile (2, 2)
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )

            # Test tile selection - this will test the coordinate conversion
            self.view.mousePressEvent(click_event)

            # The test passes if no exception is thrown
            # Actual tile selection behavior depends on mapToScene working correctly

    def test_zoom_preserves_tile_selection_accuracy(self):
        """Test that zoom preserves tile selection accuracy"""
        # This test verifies that the tile position calculation
        # (_pos_to_tile) works correctly at different zoom levels

        # Test positions at different zoom levels
        test_positions = [
            QPointF(8, 8),  # Should be tile (1, 1)
            QPointF(16, 16),  # Should be tile (2, 2)
            QPointF(24, 24),  # Should be tile (3, 3)
        ]

        for pos in test_positions:
            expected_tile = TilePosition(int(pos.y() // 8), int(pos.x() // 8))

            # Test at different zoom levels
            zoom_levels = [0.5, 1.0, 2.0, 4.0]
            for zoom_level in zoom_levels:
                self.view.zoom_level = zoom_level

                # Get tile position
                tile_pos = self.view._pos_to_tile(pos)

                # Should be the same regardless of zoom level
                assert tile_pos == expected_tile

    def teardown_method(self):
        """Clean up test fixtures"""
        if hasattr(self, "app"):
            self.app.quit()


@pytest.mark.gui
class TestGridArrangementDialogZoomIntegration:
    """Test zoom integration with GridArrangementDialog"""

    def setup_method(self):
        """Setup test fixtures"""
        # Skip if we're in a headless environment that can't support Qt widgets

        # Check for headless environment indicators
        is_headless = (
            not os.environ.get("DISPLAY")
            or os.environ.get("CI")
            or "microsoft" in os.uname().release.lower()
            or (sys.platform.startswith("linux") and not os.environ.get("DISPLAY"))
        )

        if is_headless:
            pytest.skip("GUI tests skipped in headless environment")

        # Try to create QApplication and handle any failures
        try:
            if not QApplication.instance():
                self.app = QApplication([])
            else:
                self.app = QApplication.instance()
        except Exception as e:
            pytest.skip(f"GUI tests skipped due to Qt initialization error: {e}")

    def test_zoom_controls_integration(self):
        """Test that zoom controls are properly integrated"""
        # We can't easily test the full dialog without a display
        # But we can test that the zoom methods exist and work

        view = GridGraphicsView()

        # Test that all zoom methods exist
        assert hasattr(view, "zoom_in")
        assert hasattr(view, "zoom_out")
        assert hasattr(view, "zoom_to_fit")
        assert hasattr(view, "reset_zoom")
        assert hasattr(view, "get_zoom_level")
        assert hasattr(view, "zoom_changed")

        # Test that they are callable
        assert callable(view.zoom_in)
        assert callable(view.zoom_out)
        assert callable(view.zoom_to_fit)
        assert callable(view.reset_zoom)
        assert callable(view.get_zoom_level)

        # Test basic functionality
        initial_zoom = view.get_zoom_level()
        view.zoom_in()
        assert view.get_zoom_level() > initial_zoom

        view.reset_zoom()
        assert view.get_zoom_level() == 1.0

    def teardown_method(self):
        """Clean up test fixtures"""
        if hasattr(self, "app"):
            self.app.quit()


class TestGridArrangementDialogZoomIntegrationHeadless:
    """Test zoom integration logic without Qt dependencies"""

    def test_zoom_controls_interface_exists(self):
        """Test that zoom interface exists on GridGraphicsView class"""
        # Test that all zoom methods exist as attributes on the class
        assert hasattr(GridGraphicsView, "zoom_in")
        assert hasattr(GridGraphicsView, "zoom_out")
        assert hasattr(GridGraphicsView, "zoom_to_fit")
        assert hasattr(GridGraphicsView, "reset_zoom")
        assert hasattr(GridGraphicsView, "get_zoom_level")

        # Test that they are callable
        assert callable(GridGraphicsView.zoom_in)
        assert callable(GridGraphicsView.zoom_out)
        assert callable(GridGraphicsView.zoom_to_fit)
        assert callable(GridGraphicsView.reset_zoom)
        assert callable(GridGraphicsView.get_zoom_level)
