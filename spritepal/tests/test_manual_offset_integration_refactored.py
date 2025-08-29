"""
Real component integration tests for Manual Offset Dialog functionality.

Following the UNIFIED_TESTING_GUIDE principles:
- Uses real Qt components with qtbot instead of mocking entire dialogs
- Mocks only at system boundaries (file I/O, HAL compression)
- Provides better integration testing with actual component behavior
- Tests the real dialog singleton behavior with actual Qt widgets

Key improvements over mock-based version:
- Tests real Qt signal/slot connections
- Verifies actual widget state changes
- Validates real dialog lifecycle management
- Ensures proper Qt event handling
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from tests.infrastructure.real_component_factory import RealComponentFactory
from ui.rom_extraction_panel import ManualOffsetDialogSingleton

# Mark for real Qt testing
pytestmark = [
    pytest.mark.gui,  # Requires real Qt environment
    pytest.mark.integration,  # Integration test
    pytest.mark.dialog,  # Tests involving dialogs
    pytest.mark.real_components,  # Uses real Qt components
]

@pytest.mark.no_manager_setup
class TestManualOffsetDialogIntegrationReal:
    """Integration tests using real Qt components for Manual Offset Dialog."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        ManualOffsetDialogSingleton.reset()
        yield
        ManualOffsetDialogSingleton.reset()

    @pytest.fixture
    def real_factory(self):
        """Create real component factory for testing."""
        factory = RealComponentFactory()
        yield factory
        factory.cleanup()

    @pytest.fixture
    def real_rom_panel(self, qtbot, real_factory):
        """Create a real ROM extraction panel."""
        panel = real_factory.create_rom_extraction_panel()
        qtbot.addWidget(panel)
        
        # Set up with test ROM data
        test_rom = Path(tempfile.mktemp(suffix=".sfc"))
        test_rom.write_bytes(b'\x00' * 0x400000)  # 4MB test ROM
        
        panel.rom_path = str(test_rom)
        panel.rom_size = 0x400000
        
        yield panel
        
        # Cleanup
        if test_rom.exists():
            test_rom.unlink()

    @pytest.fixture
    def mock_hal_compression(self):
        """Mock only the HAL compression at system boundary."""
        with patch('core.decompressor.decompress_data') as mock_decomp:
            # Return predictable decompressed data
            mock_decomp.return_value = b'\xFF' * 0x8000  # 32KB of sprite data
            yield mock_decomp

    def test_user_opens_dialog_multiple_times_same_instance_real(self, qtbot, real_rom_panel):
        """Test user opening dialog multiple times gets same real instance."""
        # User opens dialog first time
        dialog1 = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
        qtbot.addWidget(dialog1)
        
        # Verify it's a real Qt dialog
        assert dialog1 is not None
        assert hasattr(dialog1, 'show')
        assert hasattr(dialog1, 'exec')
        
        # User opens dialog again (maybe clicked button multiple times)
        dialog2 = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
        dialog3 = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
        
        # All should be the same instance
        assert dialog1 is dialog2 is dialog3
        
        # Verify dialog is actually visible
        dialog1.show()
        qtbot.waitExposed(dialog1)
        assert dialog1.isVisible()

    def test_user_adjusts_slider_real_widget_updates(self, qtbot, real_rom_panel, mock_hal_compression):
        """Test that adjusting real slider updates actual widgets."""
        dialog = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)
        
        # Access real slider component
        if hasattr(dialog, 'browse_tab') and hasattr(dialog.browse_tab, 'position_slider'):
            slider = dialog.browse_tab.position_slider
            
            # Test real slider adjustments
            test_offsets = [0x250000, 0x300000, 0x280000]
            for offset in test_offsets:
                # Set slider value using real Qt signals
                slider.setValue(offset)
                
                # Process Qt events
                QApplication.processEvents()
                
                # Verify slider actually changed
                assert slider.value() == offset
                
                # Verify dialog is still the same instance
                dialog_ref = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
                assert dialog_ref is dialog

    def test_user_closes_and_reopens_dialog_real_lifecycle(self, qtbot, real_rom_panel):
        """Test real dialog lifecycle with proper Qt cleanup."""
        # User opens dialog
        dialog1 = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
        qtbot.addWidget(dialog1)
        dialog1.show()
        qtbot.waitExposed(dialog1)
        
        # Store dialog ID for comparison
        dialog1_id = id(dialog1)
        
        # User closes dialog - simulate real close event
        dialog1.close()
        QApplication.processEvents()
        
        # Trigger singleton cleanup
        ManualOffsetDialogSingleton._on_dialog_closed()
        
        # Verify cleanup
        assert ManualOffsetDialogSingleton._instance is None
        
        # User reopens dialog - should get new instance
        dialog2 = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
        qtbot.addWidget(dialog2)
        
        # Should be different instance
        assert id(dialog2) != dialog1_id
        assert ManualOffsetDialogSingleton._instance is dialog2

    def test_user_workflow_with_real_sprite_history(self, qtbot, real_rom_panel, mock_hal_compression):
        """Test user workflow with real sprite history components."""
        dialog = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)
        
        # Test with real history tab if available
        if hasattr(dialog, 'history_tab'):
            history_tab = dialog.history_tab
            
            # User finds sprites at different offsets
            sprite_data = [
                (0x200000, 0.95),
                (0x210000, 0.87),
                (0x220000, 0.92)
            ]
            
            for offset, quality in sprite_data:
                # Add sprite using real method
                if hasattr(dialog, 'add_found_sprite'):
                    dialog.add_found_sprite(offset, quality)
                    QApplication.processEvents()
                
                # Verify singleton consistency
                dialog_ref = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
                assert dialog_ref is dialog
            
            # Check if sprites were actually added to history
            if hasattr(history_tab, 'get_sprite_count'):
                # Real component should have actual sprite count
                assert history_tab.get_sprite_count() > 0

    def test_keyboard_navigation_real_qt_events(self, qtbot, real_rom_panel):
        """Test real keyboard navigation with Qt events."""
        dialog = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)
        
        # Test Tab key navigation
        qtbot.keyClick(dialog, Qt.Key.Key_Tab)
        QApplication.processEvents()
        
        # Test arrow key navigation if slider is focused
        if hasattr(dialog, 'browse_tab') and hasattr(dialog.browse_tab, 'position_slider'):
            slider = dialog.browse_tab.position_slider
            slider.setFocus()
            
            initial_value = slider.value()
            
            # Use arrow keys to adjust slider
            qtbot.keyClick(slider, Qt.Key.Key_Right)
            QApplication.processEvents()
            
            # Verify slider responded to keyboard input
            assert slider.value() != initial_value

    def test_dialog_state_persistence_across_show_hide(self, qtbot, real_rom_panel):
        """Test that dialog state persists when shown/hidden."""
        dialog = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
        qtbot.addWidget(dialog)
        
        # Set some state
        test_offset = 0x250000
        if hasattr(dialog, 'set_offset'):
            dialog.set_offset(test_offset)
        
        # Show dialog
        dialog.show()
        qtbot.waitExposed(dialog)
        assert dialog.isVisible()
        
        # Hide dialog
        dialog.hide()
        QApplication.processEvents()
        assert not dialog.isVisible()
        
        # Get dialog again - should be same instance
        dialog_ref = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
        assert dialog_ref is dialog
        
        # Show again and verify state persisted
        dialog.show()
        qtbot.waitExposed(dialog)
        if hasattr(dialog, 'get_current_offset'):
            assert dialog.get_current_offset() == test_offset

    def test_multiple_rom_panels_with_real_widgets(self, qtbot, real_factory):
        """Test multiple real ROM panels sharing dialog instance."""
        # Create multiple real panels
        panel1 = real_factory.create_rom_extraction_panel()
        panel2 = real_factory.create_rom_extraction_panel()
        panel3 = real_factory.create_rom_extraction_panel()
        
        qtbot.addWidget(panel1)
        qtbot.addWidget(panel2)
        qtbot.addWidget(panel3)
        
        # Set up test ROM paths
        for panel in [panel1, panel2, panel3]:
            panel.rom_path = "/test/rom.sfc"
            panel.rom_size = 0x400000
        
        # Different panels request dialog
        dialog1 = ManualOffsetDialogSingleton.get_dialog(panel1)
        dialog2 = ManualOffsetDialogSingleton.get_dialog(panel2)
        dialog3 = ManualOffsetDialogSingleton.get_dialog(panel3)
        
        # All should get the same instance
        assert dialog1 is dialog2 is dialog3
        
        # First panel should be the "creator"
        assert ManualOffsetDialogSingleton._creator_panel is panel1

    def test_dialog_focus_behavior_with_real_qt(self, qtbot, real_rom_panel):
        """Test real Qt focus behavior of dialog."""
        dialog = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
        qtbot.addWidget(dialog)
        
        # Show and activate dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        qtbot.waitExposed(dialog)
        
        # Verify dialog has focus
        qtbot.waitUntil(lambda: dialog.isActiveWindow(), timeout=1000)
        
        # Test that getting dialog again maintains focus
        dialog_ref = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
        assert dialog_ref is dialog
        assert dialog.isActiveWindow()

    def test_error_recovery_with_real_components(self, qtbot, real_rom_panel):
        """Test error recovery with real Qt components."""
        dialog = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
        qtbot.addWidget(dialog)
        dialog.show()
        qtbot.waitExposed(dialog)
        
        # Simulate error condition by passing invalid offset
        if hasattr(dialog, 'set_offset'):
            try:
                # This might raise an exception with invalid offset
                dialog.set_offset(-1)
            except (ValueError, Exception):
                pass  # Expected error
        
        # Dialog should still be accessible
        dialog_ref = ManualOffsetDialogSingleton.get_dialog(real_rom_panel)
        assert dialog_ref is dialog
        assert dialog.isVisible()
        
        # Should be able to work normally after error
        if hasattr(dialog, 'set_offset'):
            dialog.set_offset(0x250000)  # Valid offset
            assert dialog.get_current_offset() == 0x250000

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])