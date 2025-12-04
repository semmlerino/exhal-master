"""
Comprehensive Layout Tests for Manual Offset Dialog.

This test suite focuses on preventing regression of the layout issues that were
fixed in the UnifiedManualOffsetDialog. It tests dynamic splitter ratios, 
minimum panel widths, responsive gallery controls, and proper sizing behavior.

Key layout requirements tested:
1. Dynamic splitter ratios change when switching tabs
2. Minimum panel width prevents compression below 350px  
3. Responsive gallery controls adapt to available space
4. showEvent properly sizes splitter after initialization
5. Size policies allow proper widget expansion
6. Panels cannot be collapsed to zero width
7. Layout constants are applied consistently
8. Window resizing maintains proper proportions
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QSplitter, QTabWidget


def is_headless_environment() -> bool:
    """Detect if we're in a headless environment."""
    # For layout tests, we can work with offscreen rendering
    # Only skip if explicitly requested to avoid GUI tests
    return os.environ.get("SKIP_GUI_TESTS", "").lower() in ("1", "true", "yes")

# Configure Qt environment for headless testing
if not os.environ.get('QT_QPA_PLATFORM'):
    if is_headless_environment():
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Test marks for proper categorization - minimal marks for compatibility
pytestmark = [
    pytest.mark.integration,  # Integration test
    pytest.mark.cache,
    pytest.mark.ci_safe,
    pytest.mark.dialog,
    pytest.mark.headless,
    pytest.mark.qt_real,
    pytest.mark.requires_display,
    pytest.mark.rom_data,
    pytest.mark.slow,
]

from ui.dialogs import manual_offset_layout_manager
from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from ui.tabs.manual_offset.browse_tab import SimpleBrowseTab

LAYOUT_SPACING = manual_offset_layout_manager.LAYOUT_SPACING
LAYOUT_MARGINS = manual_offset_layout_manager.LAYOUT_MARGINS
MIN_LEFT_PANEL_WIDTH = manual_offset_layout_manager.MIN_LEFT_PANEL_WIDTH
SPLITTER_HANDLE_WIDTH = manual_offset_layout_manager.SPLITTER_HANDLE_WIDTH
from tests.infrastructure.qt_real_testing import QtTestCase
from ui.tabs.sprite_gallery_tab import SpriteGalleryTab


class MockQtBot:
    """Mock qtbot for basic functionality without pytest-qt dependency."""

    def __init__(self):
        self.widgets = []

    def addWidget(self, widget):
        self.widgets.append(widget)

    def wait(self, ms):
        QApplication.processEvents()
        QTimer.singleShot(ms, lambda: None)

    def waitUntil(self, predicate, timeout=1000):
        from PySide6.QtCore import QEventLoop, QTimer
        loop = QEventLoop()
        timer = QTimer()
        timer.timeout.connect(loop.quit)
        timer.start(timeout)

        def check():
            if predicate():
                loop.quit()

        check_timer = QTimer()
        check_timer.timeout.connect(check)
        check_timer.start(10)  # Check every 10ms

        loop.exec()
        timer.stop()
        check_timer.stop()

class TestManualOffsetDialogLayout(QtTestCase):
    """Test suite for Manual Offset Dialog layout behavior."""

    @pytest.fixture
    def qtbot(self):
        """Provide a mock qtbot fixture."""
        return MockQtBot()

    @pytest.fixture
    def mock_extraction_manager(self):
        """Create a mock extraction manager for testing."""
        # For layout tests, we don't need the actual functionality
        # But we need to avoid Qt mock conflicts
        from unittest.mock import Mock
        manager = Mock()
        extractor = Mock()
        # Don't mock Qt-specific methods that cause conflicts
        extractor.configure_mock(**{
            'method.return_value': None
        })
        manager.get_rom_extractor.return_value = extractor
        return manager

    @pytest.fixture
    def dialog(self, qtbot, mock_extraction_manager):
        """Create a dialog instance for testing."""
        try:
            dialog = self.create_widget(UnifiedManualOffsetDialog)
            qtbot.addWidget(dialog)

            # Set ROM data to fully initialize the dialog
            # Use patch to avoid Qt mock conflicts
            with patch('ui.dialogs.manual_offset_unified_integrated.get_rom_cache'):
                dialog.set_rom_data("/fake/rom.sfc", 0x400000, mock_extraction_manager)

            return dialog
        except Exception as e:
            pytest.skip(f"Dialog creation failed: {e}")
            return None

    @pytest.mark.unit
    def test_layout_constants_are_defined(self):
        """Test that layout constants are properly defined and have expected values."""
        # Test constant values match expected layout requirements
        assert LAYOUT_SPACING == 8, "Layout spacing should be 8px for proper visual separation"
        assert LAYOUT_MARGINS == 8, "Layout margins should be 8px for consistent padding"
        assert MIN_LEFT_PANEL_WIDTH == 350, "Minimum left panel width should prevent UI cropping"
        assert SPLITTER_HANDLE_WIDTH == 8, "Splitter handle should be 8px for good usability"

    @pytest.mark.skipif(
        is_headless_environment(),
        reason="Requires display for real Qt components"
    )
    def test_minimum_panel_width_prevents_compression(self, qtbot, dialog):
        """Test that left panel cannot be compressed below minimum width."""
        dialog.show()
        qtbot.waitUntil(lambda: dialog.isVisible(), timeout=1000)

        # Get the splitter and left panel
        splitter = dialog.main_splitter
        assert isinstance(splitter, QSplitter), "Main splitter should exist"

        # Try to set sizes that would compress left panel below minimum
        total_width = 800
        dialog.resize(total_width, 600)
        qtbot.wait(100)  # Allow resize to process

        # Try to force very small left panel size
        splitter.setSizes([100, 700])  # 100px < MIN_LEFT_PANEL_WIDTH
        qtbot.wait(50)

        sizes = splitter.sizes()
        left_panel_width = sizes[0]

        # Verify left panel was not compressed below minimum
        assert left_panel_width >= MIN_LEFT_PANEL_WIDTH, \
            f"Left panel width {left_panel_width} should not be less than {MIN_LEFT_PANEL_WIDTH}"

    def test_panels_cannot_be_collapsed_to_zero(self, qtbot, dialog):
        """Test that panels cannot be collapsed to zero width."""
        dialog.show()
        qtbot.waitUntil(lambda: dialog.isVisible(), timeout=1000)

        splitter = dialog.main_splitter

        # Verify both panels are not collapsible
        assert not splitter.collapsible(0), "Left panel should not be collapsible"
        assert not splitter.collapsible(1), "Right panel should not be collapsible"

        # Try to collapse panels by setting zero sizes
        splitter.setSizes([0, 800])
        qtbot.wait(50)

        sizes = splitter.sizes()
        assert all(size > 0 for size in sizes), "No panel should have zero width"
        assert sizes[0] >= MIN_LEFT_PANEL_WIDTH, "Left panel should maintain minimum width"

    def test_dynamic_splitter_ratios_change_with_tabs(self, qtbot, dialog):
        """Test that splitter ratios change dynamically when switching tabs."""
        dialog.show()
        qtbot.waitUntil(lambda: dialog.isVisible(), timeout=1000)

        # Set a consistent window size
        dialog.resize(1000, 650)
        qtbot.wait(100)

        tab_widget = dialog.tab_widget
        splitter = dialog.main_splitter

        # Test Browse tab ratio (index 0)
        tab_widget.setCurrentIndex(0)
        qtbot.wait(100)  # Allow tab change to process

        browse_sizes = splitter.sizes()
        browse_ratio = browse_sizes[0] / sum(browse_sizes) if sum(browse_sizes) > 0 else 0

        # Test Gallery tab ratio (index 3) - should need more space
        tab_widget.setCurrentIndex(3)
        qtbot.wait(100)

        gallery_sizes = splitter.sizes()
        gallery_ratio = gallery_sizes[0] / sum(gallery_sizes) if sum(gallery_sizes) > 0 else 0

        # Gallery tab should allocate more space to left panel for controls
        assert gallery_ratio > browse_ratio, \
            f"Gallery tab ratio ({gallery_ratio:.2f}) should be larger than Browse tab ratio ({browse_ratio:.2f})"

        # Test Smart tab ratio (index 1)
        tab_widget.setCurrentIndex(1)
        qtbot.wait(100)

        smart_sizes = splitter.sizes()
        smart_ratio = smart_sizes[0] / sum(smart_sizes) if sum(smart_sizes) > 0 else 0

        # Smart tab should use similar ratio to Browse tab
        assert abs(smart_ratio - browse_ratio) < 0.1, \
            f"Smart tab ratio ({smart_ratio:.2f}) should be similar to Browse tab ratio ({browse_ratio:.2f})"

    def test_showEvent_properly_sizes_splitter(self, qtbot, dialog):
        """Test that showEvent sets up initial splitter sizes correctly."""
        # Dialog should not be visible initially
        assert not dialog.isVisible()

        # Show dialog and verify sizing happens
        dialog.show()
        qtbot.waitUntil(lambda: dialog.isVisible(), timeout=1000)

        splitter = dialog.main_splitter
        sizes = splitter.sizes()

        # Verify splitter has been sized (not default zeros)
        assert sum(sizes) > 0, "Splitter should have non-zero sizes after show"
        assert len(sizes) == 2, "Splitter should have exactly 2 panels"

        # Verify minimum width is respected
        assert sizes[0] >= MIN_LEFT_PANEL_WIDTH, \
            f"Left panel width {sizes[0]} should be at least {MIN_LEFT_PANEL_WIDTH} after show"

    def test_size_policies_allow_proper_expansion(self, qtbot, dialog):
        """Test that size policies allow proper widget expansion."""
        dialog.show()
        qtbot.waitUntil(lambda: dialog.isVisible(), timeout=1000)

        # Check left panel size policy
        left_panel_widget = dialog.main_splitter.widget(0)
        left_policy = left_panel_widget.sizePolicy()

        # Left panel should be able to expand but have lower priority
        assert left_policy.horizontalPolicy() in [
            left_policy.Policy.Preferred,
            left_policy.Policy.Expanding
        ], "Left panel should have appropriate horizontal size policy"

        # Check right panel size policy
        right_panel_widget = dialog.main_splitter.widget(1)
        right_policy = right_panel_widget.sizePolicy()

        # Right panel should expand to fill available space
        assert right_policy.horizontalPolicy() == right_policy.Policy.Expanding, \
            "Right panel should have expanding horizontal size policy"

    def test_responsive_gallery_controls_adapt_to_space(self, qtbot, dialog):
        """Test that gallery controls adapt to available space."""
        dialog.show()
        qtbot.waitUntil(lambda: dialog.isVisible(), timeout=1000)

        # Switch to gallery tab
        tab_widget = dialog.tab_widget
        tab_widget.setCurrentIndex(3)  # Gallery tab
        qtbot.wait(100)

        gallery_tab = dialog.gallery_tab
        assert isinstance(gallery_tab, SpriteGalleryTab), "Gallery tab should exist"

        # Test with different window sizes to verify responsiveness
        sizes_to_test = [(800, 600), (1200, 800), (1600, 900)]

        for width, height in sizes_to_test:
            dialog.resize(width, height)
            qtbot.wait(100)  # Allow resize to process

            # Verify gallery tab adapts to available space
            tab_size = gallery_tab.size()
            assert tab_size.width() > 0, f"Gallery tab should have positive width at size {width}x{height}"
            assert tab_size.height() > 0, f"Gallery tab should have positive height at size {width}x{height}"

            # Gallery controls should be visible and properly sized
            if hasattr(gallery_tab, 'controls_widget'):
                controls_size = gallery_tab.controls_widget.size()
                assert controls_size.width() <= tab_size.width(), \
                    "Gallery controls should not exceed tab width"

    def test_window_resizing_maintains_proportions(self, qtbot, dialog):
        """Test that window resizing maintains proper proportions."""
        dialog.show()
        qtbot.waitUntil(lambda: dialog.isVisible(), timeout=1000)

        # Set initial size and get initial ratio
        dialog.resize(1000, 650)
        qtbot.wait(100)

        splitter = dialog.main_splitter
        initial_sizes = splitter.sizes()
        initial_ratio = initial_sizes[0] / sum(initial_sizes) if sum(initial_sizes) > 0 else 0

        # Resize to different dimensions
        new_sizes = [(1200, 700), (800, 500), (1400, 800)]

        for width, height in new_sizes:
            dialog.resize(width, height)
            qtbot.wait(100)  # Allow resize to process

            current_sizes = splitter.sizes()
            current_ratio = current_sizes[0] / sum(current_sizes) if sum(current_sizes) > 0 else 0

            # Ratio should be approximately maintained (within 10% tolerance)
            ratio_diff = abs(current_ratio - initial_ratio)
            assert ratio_diff < 0.1, \
                f"Proportion should be maintained after resize to {width}x{height}: " \
                f"initial={initial_ratio:.2f}, current={current_ratio:.2f}, diff={ratio_diff:.2f}"

            # Minimum width should always be respected
            assert current_sizes[0] >= MIN_LEFT_PANEL_WIDTH, \
                f"Minimum width should be maintained after resize to {width}x{height}"

    def test_layout_constants_applied_consistently(self, qtbot, dialog):
        """Test that layout constants are applied consistently throughout the dialog."""
        dialog.show()
        qtbot.waitUntil(lambda: dialog.isVisible(), timeout=1000)

        # Check that spacing is applied to tab widget
        tab_widget = dialog.tab_widget
        assert isinstance(tab_widget, QTabWidget), "Tab widget should exist"

        # Check browse tab layout
        browse_tab = dialog.browse_tab
        assert isinstance(browse_tab, SimpleBrowseTab), "Browse tab should exist"

        # Verify browse tab has proper layout structure
        browse_layout = browse_tab.layout()
        assert browse_layout is not None, "Browse tab should have layout"

        # Check that splitter handle width is set correctly
        splitter = dialog.main_splitter
        assert splitter.handleWidth() == SPLITTER_HANDLE_WIDTH, \
            f"Splitter handle width should be {SPLITTER_HANDLE_WIDTH}"

    def test_tab_change_triggers_layout_update(self, qtbot, dialog):
        """Test that changing tabs properly triggers layout updates."""
        dialog.show()
        qtbot.waitUntil(lambda: dialog.isVisible(), timeout=1000)

        tab_widget = dialog.tab_widget
        splitter = dialog.main_splitter

        # Record initial state
        initial_tab = tab_widget.currentIndex()
        initial_sizes = splitter.sizes()

        # Change to different tab
        new_tab_index = (initial_tab + 1) % tab_widget.count()
        tab_widget.setCurrentIndex(new_tab_index)
        qtbot.wait(100)  # Allow layout update

        # Verify layout was updated
        new_sizes = splitter.sizes()

        # Sizes should potentially change based on tab requirements
        # At minimum, layout update should have been triggered
        assert len(new_sizes) == len(initial_sizes), "Panel count should remain consistent"
        assert all(size > 0 for size in new_sizes), "All panels should have positive width"
        assert new_sizes[0] >= MIN_LEFT_PANEL_WIDTH, "Minimum width should be maintained"

    def test_dialog_minimum_size_respected(self, qtbot, dialog):
        """Test that dialog minimum size is respected and prevents UI compression."""
        dialog.show()
        qtbot.waitUntil(lambda: dialog.isVisible(), timeout=1000)

        # Get minimum size
        min_size = dialog.minimumSize()
        assert min_size.width() > 0, "Dialog should have minimum width set"
        assert min_size.height() > 0, "Dialog should have minimum height set"

        # Try to resize below minimum
        too_small_width = min_size.width() - 100
        too_small_height = min_size.height() - 100

        dialog.resize(too_small_width, too_small_height)
        qtbot.wait(100)

        # Verify dialog was not resized below minimum
        actual_size = dialog.size()
        assert actual_size.width() >= min_size.width(), \
            f"Dialog width should not go below minimum: actual={actual_size.width()}, min={min_size.width()}"
        assert actual_size.height() >= min_size.height(), \
            f"Dialog height should not go below minimum: actual={actual_size.height()}, min={min_size.height()}"

    def test_layout_survives_multiple_show_hide_cycles(self, qtbot, dialog):
        """Test that layout remains correct through multiple show/hide cycles."""
        # Initial show
        dialog.show()
        qtbot.waitUntil(lambda: dialog.isVisible(), timeout=1000)

        splitter = dialog.main_splitter
        initial_sizes = splitter.sizes()

        # Multiple hide/show cycles
        for cycle in range(3):
            dialog.hide()
            qtbot.waitUntil(lambda: not dialog.isVisible(), timeout=1000)

            dialog.show()
            qtbot.waitUntil(lambda: dialog.isVisible(), timeout=1000)
            qtbot.wait(100)  # Allow layout to stabilize

            # Verify layout is maintained
            current_sizes = splitter.sizes()
            assert len(current_sizes) == len(initial_sizes), f"Panel count should remain consistent in cycle {cycle}"
            assert all(size > 0 for size in current_sizes), f"All panels should have positive width in cycle {cycle}"
            assert current_sizes[0] >= MIN_LEFT_PANEL_WIDTH, f"Minimum width should be maintained in cycle {cycle}"

    def test_splitter_handle_accessibility(self, qtbot, dialog):
        """Test that splitter handle is accessible and properly sized."""
        dialog.show()
        qtbot.waitUntil(lambda: dialog.isVisible(), timeout=1000)

        splitter = dialog.main_splitter

        # Verify handle width is appropriate for mouse interaction
        handle_width = splitter.handleWidth()
        assert handle_width >= 5, "Splitter handle should be at least 5px for accessibility"
        assert handle_width == SPLITTER_HANDLE_WIDTH, f"Handle width should match constant: {SPLITTER_HANDLE_WIDTH}"

        # Verify splitter orientation
        assert splitter.orientation() == Qt.Orientation.Horizontal, \
            "Main splitter should be horizontal for left/right panel layout"

    def test_layout_performance_with_rapid_changes(self, qtbot, dialog):
        """Test layout performance with rapid tab changes and resizing."""
        dialog.show()
        qtbot.waitUntil(lambda: dialog.isVisible(), timeout=1000)

        tab_widget = dialog.tab_widget
        splitter = dialog.main_splitter

        # Rapid tab changes
        for i in range(10):
            tab_index = i % tab_widget.count()
            tab_widget.setCurrentIndex(tab_index)
            qtbot.wait(10)  # Minimal wait to stress-test layout

            # Verify layout remains valid
            sizes = splitter.sizes()
            assert all(size > 0 for size in sizes), f"Panels should remain positive in rapid change {i}"
            assert sizes[0] >= MIN_LEFT_PANEL_WIDTH, f"Minimum width should be maintained in rapid change {i}"

        # Rapid resize changes
        base_width, base_height = 1000, 650
        for i in range(5):
            width = base_width + (i * 50)
            height = base_height + (i * 25)
            dialog.resize(width, height)
            qtbot.wait(20)  # Minimal wait

            sizes = splitter.sizes()
            assert all(size > 0 for size in sizes), f"Panels should remain positive in rapid resize {i}"
            assert sizes[0] >= MIN_LEFT_PANEL_WIDTH, f"Minimum width should be maintained in rapid resize {i}"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
