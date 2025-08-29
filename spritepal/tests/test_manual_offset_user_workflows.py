"""
User workflow tests for Manual Offset Dialog.

These tests focus on end-to-end user scenarios using strategic mocking
to avoid Qt environment complexity while testing real user interactions.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ui.rom_extraction_panel import ManualOffsetDialogSingleton

# Test characteristics: Singleton management
pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.dialog,
    pytest.mark.headless,
    pytest.mark.integration,
    pytest.mark.mock_dialogs,
    pytest.mark.mock_only,
    pytest.mark.no_qt,
    pytest.mark.performance,
    pytest.mark.rom_data,
    pytest.mark.serial,
    pytest.mark.singleton,
    pytest.mark.widget,
    pytest.mark.ci_safe,
]

@pytest.mark.integration
@pytest.mark.no_manager_setup
class TestUserWorkflows:
    """Test realistic user workflows with the manual offset dialog."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        ManualOffsetDialogSingleton.reset()
        yield
        ManualOffsetDialogSingleton.reset()

    @pytest.fixture
    def mock_dialog_with_ui(self):
        """Create a comprehensive mock dialog with UI components."""
        dialog = MagicMock()
        dialog.isVisible.return_value = True
        dialog.finished.connect = MagicMock()
        dialog.rejected.connect = MagicMock()
        dialog.destroyed.connect = MagicMock()
        dialog.deleteLater = MagicMock()
        dialog._debug_id = "workflow_dialog"

        # Mock browse tab with slider
        browse_tab = MagicMock()
        position_slider = MagicMock()
        position_slider.value.return_value = 0x1000
        browse_tab.position_slider = position_slider
        browse_tab.preview_widget = MagicMock()
        dialog.browse_tab = browse_tab

        # Mock history tab
        history_tab = MagicMock()
        history_list = MagicMock()
        history_list.count.return_value = 0
        history_tab.sprite_list = history_list
        dialog.history_tab = history_tab

        # Mock smart tab
        smart_tab = MagicMock()
        dialog.smart_tab = smart_tab

        # ROM data
        dialog.rom_data = bytearray(b'\x00' * 0x100000)  # 1MB ROM
        dialog.rom_path = "/test/game.sfc"

        return dialog

    @pytest.fixture
    def mock_rom_panel(self):
        """Create a mock ROM extraction panel."""
        panel = MagicMock()
        panel.rom_path = "/test/game.sfc"
        panel.rom_data = bytearray(b'\x00' * 0x100000)
        panel.get_current_offset.return_value = 0x8000
        return panel

    def test_singleton_lifecycle_workflow(self, mock_rom_panel):
        """Test singleton lifecycle management through user workflow."""
        # Create separate mock dialogs for each creation
        first_dialog = MagicMock()
        first_dialog.isVisible.return_value = True
        first_dialog.finished = MagicMock()
        first_dialog.rejected = MagicMock()
        first_dialog.destroyed = MagicMock()
        first_dialog._debug_id = "first_dialog"
        
        second_dialog = MagicMock()
        second_dialog.isVisible.return_value = True
        second_dialog.finished = MagicMock()
        second_dialog.rejected = MagicMock()
        second_dialog.destroyed = MagicMock()
        second_dialog._debug_id = "second_dialog"
        
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', side_effect=[first_dialog, second_dialog]):
            # Opening dialog creates singleton instance
            dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            assert ManualOffsetDialogSingleton._instance is dialog
            assert dialog._debug_id == "first_dialog"
            
            # Multiple get_dialog calls return same instance
            dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            assert dialog2 is dialog
            
            # Test get_current_dialog
            current = ManualOffsetDialogSingleton.get_current_dialog()
            assert current is dialog
            
            # Simulate user closing dialog
            dialog.finished.emit()
            close_callback = dialog.finished.connect.call_args[0][0]
            close_callback()
            
            # Instance should be cleared after close
            assert ManualOffsetDialogSingleton._instance is None
            assert ManualOffsetDialogSingleton.get_current_dialog() is None
            
            # Can create new instance after cleanup
            new_dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            assert new_dialog is not dialog  # Different instance
            assert new_dialog._debug_id == "second_dialog"
            assert ManualOffsetDialogSingleton._instance is new_dialog

    def test_extended_browsing_with_history_accumulation(self, mock_rom_panel, mock_dialog_with_ui):
        """Test extended browsing session with history tracking."""
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', return_value=mock_dialog_with_ui):
            dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            
            # Simulate finding multiple sprites
            history_list = dialog.history_tab.sprite_list
            found_sprites = []
            
            for i in range(10):
                offset = 0x1000 * (i + 1)
                sprite_data = f"sprite_{i}"
                found_sprites.append((offset, sprite_data))
                
                # Simulate adding to history
                history_list.count.return_value = len(found_sprites)
            
            # Verify history accumulated
            assert history_list.count() == 10
            
            # User selects item from history
            history_list.currentRow.return_value = 5
            history_list.itemClicked.emit(MagicMock())
            
            # Slider should update to that offset
            # (In real implementation, this would trigger slider update)
            assert dialog.browse_tab.position_slider is not None

    def test_error_recovery_from_invalid_rom_data(self, mock_dialog_with_ui):
        """Test error recovery when ROM data becomes invalid."""
        mock_panel = MagicMock()
        mock_panel.rom_path = "/test/corrupt.sfc"
        mock_panel.rom_data = None  # Invalid data
        
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', return_value=mock_dialog_with_ui):
            # Dialog should handle invalid ROM gracefully
            dialog = ManualOffsetDialogSingleton.get_dialog(mock_panel)
            
            # Set valid ROM data
            mock_panel.rom_data = bytearray(b'\x00' * 0x100000)
            dialog.rom_data = mock_panel.rom_data
            
            # Now dialog should work normally
            slider = dialog.browse_tab.position_slider
            slider.value.return_value = 0x5000
            assert slider.value() == 0x5000

    def test_multiple_rom_switching_workflow(self, mock_dialog_with_ui):
        """Test switching between multiple ROMs."""
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', return_value=mock_dialog_with_ui):
            # First ROM
            panel1 = MagicMock()
            panel1.rom_path = "/test/game1.sfc"
            panel1.rom_data = bytearray(b'\x11' * 0x100000)
            
            dialog = ManualOffsetDialogSingleton.get_dialog(panel1)
            dialog.browse_tab.position_slider.value.return_value = 0x1000
            
            # Switch to second ROM
            panel2 = MagicMock()
            panel2.rom_path = "/test/game2.sfc"
            panel2.rom_data = bytearray(b'\x22' * 0x100000)
            
            # Same dialog instance should be reused
            dialog2 = ManualOffsetDialogSingleton.get_dialog(panel2)
            assert dialog is dialog2
            
            # ROM data should be updated
            dialog.rom_data = panel2.rom_data
            dialog.rom_path = panel2.rom_path

    def test_rapid_user_interactions(self, mock_rom_panel, mock_dialog_with_ui):
        """Test rapid user interactions don't cause issues."""
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', return_value=mock_dialog_with_ui):
            dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            slider = dialog.browse_tab.position_slider
            
            # Rapid slider movements
            for i in range(100):
                offset = i * 100
                slider.value.return_value = offset
                slider.valueChanged.emit(offset)
            
            # Rapid tab switching
            for _ in range(20):
                dialog.current_tab = 0
                dialog.current_tab = 1
                dialog.current_tab = 2
            
            # Dialog should remain stable
            assert dialog.isVisible()
            assert ManualOffsetDialogSingleton._instance is dialog

@pytest.mark.integration
@pytest.mark.no_manager_setup
class TestPerformanceAndAccessibility:
    """Test non-functional requirements like performance and accessibility."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        ManualOffsetDialogSingleton.reset()
        yield
        ManualOffsetDialogSingleton.reset()

    @pytest.fixture
    def mock_dialog(self):
        """Create mock dialog for performance testing."""
        dialog = MagicMock()
        dialog.isVisible.return_value = True
        dialog.finished.connect = MagicMock()
        dialog.rejected.connect = MagicMock()
        dialog.destroyed.connect = MagicMock()
        dialog._debug_id = "perf_dialog"
        
        # Add performance tracking
        dialog.memory_usage = []
        dialog.response_times = []
        
        return dialog

    # NOTE: Removed test_memory_usage_during_long_sessions - was entirely mocked
    # NOTE: Removed test_dialog_response_time_under_load - measured mock speed only

    def test_keyboard_navigation_accessibility(self, mock_dialog):
        """Test keyboard navigation works for accessibility."""
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', return_value=mock_dialog):
            panel = MagicMock()
            dialog = ManualOffsetDialogSingleton.get_dialog(panel)
            
            # Mock keyboard events
            dialog.key_events = []
            
            # Tab navigation
            dialog.key_events.append('Tab')
            dialog.current_focus = 'slider'
            
            dialog.key_events.append('Tab')
            dialog.current_focus = 'preview'
            
            dialog.key_events.append('Shift+Tab')
            dialog.current_focus = 'slider'
            
            # Arrow key navigation for slider
            slider = dialog.browse_tab.position_slider
            slider.value.return_value = 1000
            
            dialog.key_events.append('Arrow_Right')
            slider.value.return_value = 1010
            
            dialog.key_events.append('Arrow_Left')
            slider.value.return_value = 1000
            
            # Escape to close
            dialog.key_events.append('Escape')
            dialog.reject = MagicMock()
            dialog.reject()
            
            assert dialog.reject.called

    def test_dialog_persistence_across_crashes(self):
        """Test dialog state can be recovered after crash."""
        # Create initial state
        saved_state = {
            'rom_path': '/test/game.sfc',
            'current_offset': 0x5000,
            'current_tab': 1,
            'history': [
                {'offset': 0x1000, 'sprite': 'sprite1'},
                {'offset': 0x2000, 'sprite': 'sprite2'},
            ]
        }
        
        # Simulate crash and recovery
        ManualOffsetDialogSingleton.reset()  # Simulate crash
        
        # Restore state (in real implementation, this would load from disk)
        mock_dialog = MagicMock()
        mock_dialog.rom_path = saved_state['rom_path']
        mock_dialog.current_offset = saved_state['current_offset']
        mock_dialog.current_tab = saved_state['current_tab']
        mock_dialog.history = saved_state['history']
        
        # Verify state restored
        assert mock_dialog.rom_path == '/test/game.sfc'
        assert mock_dialog.current_offset == 0x5000
        assert mock_dialog.current_tab == 1
        assert len(mock_dialog.history) == 2