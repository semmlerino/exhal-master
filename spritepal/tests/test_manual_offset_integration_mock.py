"""
Mock-based integration tests for Manual Offset Dialog functionality.

These tests verify the key user-facing behaviors that prevent duplicate sliders
while using mocks to avoid complex Qt environment setup requirements.
"""

from unittest.mock import MagicMock, patch

import pytest

from ui.rom_extraction_panel import ManualOffsetDialogSingleton

# Mark this entire module for fast, mock-based testing
pytestmark = [
    pytest.mark.headless,  # Can run without display
    pytest.mark.mock_only,  # Uses only mocked components
    pytest.mark.integration,  # Integration test
    pytest.mark.qt_mock,  # Uses mocked Qt components
    pytest.mark.parallel_safe,  # Safe for parallel execution
    pytest.mark.dialog,  # Tests involving dialogs
    pytest.mark.mock_dialogs,  # Tests that mock dialog exec() methods
    pytest.mark.ci_safe,
    pytest.mark.rom_data,
]


@pytest.mark.no_manager_setup
class TestManualOffsetDialogIntegrationMock:
    """Integration tests using mocks to verify key user workflows."""

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

        # Mock browse tab with slider
        browse_tab = MagicMock()
        position_slider = MagicMock()
        position_slider.value.return_value = 0x200000
        position_slider.setValue = MagicMock()
        browse_tab.position_slider = position_slider
        browse_tab.get_current_offset.return_value = 0x200000
        browse_tab.set_offset = MagicMock()
        dialog.browse_tab = browse_tab

        # Mock preview widget
        preview_widget = MagicMock()
        dialog.preview_widget = preview_widget

        # Mock history tab
        history_tab = MagicMock()
        history_tab.get_sprite_count.return_value = 0
        history_tab.add_sprite = MagicMock()
        dialog.history_tab = history_tab

        # Mock dialog methods
        dialog.get_current_offset.return_value = 0x200000
        dialog.set_offset = MagicMock()
        dialog.set_rom_data = MagicMock()
        dialog.add_found_sprite = MagicMock()

        return dialog

    @pytest.fixture
    def mock_panel(self):
        """Create a mock ROM panel."""
        panel = MagicMock()
        panel.rom_path = "/fake/rom.sfc"
        panel.rom_size = 0x400000
        panel.extraction_manager = MagicMock()
        return panel

    def test_user_opens_dialog_multiple_times_same_instance(self, mock_panel, mock_dialog_with_ui):
        """Test user opening dialog multiple times gets same instance."""
        with patch("ui.rom_extraction_panel.UnifiedManualOffsetDialog", return_value=mock_dialog_with_ui):
            # User opens dialog first time
            dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_panel)

            # User opens dialog again (maybe clicked button multiple times)
            dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_panel)
            dialog3 = ManualOffsetDialogSingleton.get_dialog(mock_panel)

            # All should be the same instance
            assert dialog1 is dialog2 is dialog3
            assert dialog1 is mock_dialog_with_ui

    def test_user_adjusts_slider_no_duplicate_created(self, mock_panel, mock_dialog_with_ui):
        """Test that adjusting slider doesn't create duplicates."""
        with patch("ui.rom_extraction_panel.UnifiedManualOffsetDialog", return_value=mock_dialog_with_ui):
            dialog = ManualOffsetDialogSingleton.get_dialog(mock_panel)

            # User adjusts slider multiple times
            test_offsets = [0x250000, 0x300000, 0x280000]
            for offset in test_offsets:
                # Simulate user setting offset
                dialog.set_offset(offset)
                mock_dialog_with_ui.set_offset.assert_called_with(offset)

                # Get dialog reference during use - should be same instance
                dialog_ref = ManualOffsetDialogSingleton.get_dialog(mock_panel)
                assert dialog_ref is dialog
                assert dialog_ref is mock_dialog_with_ui

    def test_user_closes_and_reopens_dialog_workflow(self, mock_panel, mock_dialog_with_ui):
        """Test user workflow of closing and reopening dialog."""
        with patch("ui.rom_extraction_panel.UnifiedManualOffsetDialog", return_value=mock_dialog_with_ui):
            # User opens dialog
            dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_panel)
            assert dialog1 is mock_dialog_with_ui

            # User closes dialog
            ManualOffsetDialogSingleton._on_dialog_closed()

            # Verify cleanup was called
            mock_dialog_with_ui.deleteLater.assert_called_once()
            assert ManualOffsetDialogSingleton._instance is None

            # Reset mock for second dialog creation
            new_mock_dialog = MagicMock()
            new_mock_dialog.isVisible.return_value = True
            new_mock_dialog.finished.connect = MagicMock()
            new_mock_dialog.rejected.connect = MagicMock()
            new_mock_dialog.destroyed.connect = MagicMock()

            with patch("ui.rom_extraction_panel.UnifiedManualOffsetDialog", return_value=new_mock_dialog):
                # User reopens dialog - should get new instance
                dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_panel)
                assert dialog2 is new_mock_dialog
                assert dialog2 is not mock_dialog_with_ui

    def test_user_workflow_with_sprite_history(self, mock_panel, mock_dialog_with_ui):
        """Test user workflow involving sprite history."""
        with patch("ui.rom_extraction_panel.UnifiedManualOffsetDialog", return_value=mock_dialog_with_ui):
            dialog = ManualOffsetDialogSingleton.get_dialog(mock_panel)

            # User finds sprites at different offsets
            sprite_data = [
                (0x200000, 0.95),
                (0x210000, 0.87),
                (0x220000, 0.92)
            ]

            for offset, quality in sprite_data:
                dialog.add_found_sprite(offset, quality)
                mock_dialog_with_ui.add_found_sprite.assert_called_with(offset, quality)

                # Getting dialog reference should return same instance
                dialog_ref = ManualOffsetDialogSingleton.get_dialog(mock_panel)
                assert dialog_ref is dialog

    def test_user_workflow_error_recovery(self, mock_panel, mock_dialog_with_ui):
        """Test that singleton works after error conditions."""
        with patch("ui.rom_extraction_panel.UnifiedManualOffsetDialog", return_value=mock_dialog_with_ui):
            dialog = ManualOffsetDialogSingleton.get_dialog(mock_panel)

            # Simulate error in dialog operation
            mock_dialog_with_ui.set_offset.side_effect = Exception("Test error")

            try:
                dialog.set_offset(0x300000)
            except Exception:
                pass  # Expected error

            # Clear the error
            mock_dialog_with_ui.set_offset.side_effect = None

            # Dialog should still be accessible and the same instance
            dialog_ref = ManualOffsetDialogSingleton.get_dialog(mock_panel)
            assert dialog_ref is dialog
            assert dialog_ref is mock_dialog_with_ui

            # Should be able to work normally after error
            dialog.set_offset(0x250000)
            mock_dialog_with_ui.set_offset.assert_called_with(0x250000)

    def test_multiple_rom_panels_same_dialog_instance(self, mock_dialog_with_ui):
        """Test that multiple ROM panels get the same dialog instance."""
        panel1 = MagicMock()
        panel2 = MagicMock()
        panel3 = MagicMock()

        with patch("ui.rom_extraction_panel.UnifiedManualOffsetDialog", return_value=mock_dialog_with_ui):
            # Different panels request dialog
            dialog1 = ManualOffsetDialogSingleton.get_dialog(panel1)
            dialog2 = ManualOffsetDialogSingleton.get_dialog(panel2)
            dialog3 = ManualOffsetDialogSingleton.get_dialog(panel3)

            # All should get the same instance
            assert dialog1 is dialog2 is dialog3
            assert dialog1 is mock_dialog_with_ui

            # First panel should be the "creator"
            assert ManualOffsetDialogSingleton._creator_panel is panel1

    def test_ui_element_consistency_across_accesses(self, mock_panel, mock_dialog_with_ui):
        """Test that UI elements remain consistent across multiple accesses."""
        with patch("ui.rom_extraction_panel.UnifiedManualOffsetDialog", return_value=mock_dialog_with_ui):
            dialog = ManualOffsetDialogSingleton.get_dialog(mock_panel)

            # Get references to UI components
            browse_tab1 = dialog.browse_tab
            preview_widget1 = dialog.preview_widget
            history_tab1 = dialog.history_tab

            # Get dialog multiple times
            for _i in range(5):
                dialog_ref = ManualOffsetDialogSingleton.get_dialog(mock_panel)
                assert dialog_ref is dialog

                # UI components should be the same objects
                assert dialog_ref.browse_tab is browse_tab1
                assert dialog_ref.preview_widget is preview_widget1
                assert dialog_ref.history_tab is history_tab1

    def test_dialog_visibility_state_consistency(self, mock_panel, mock_dialog_with_ui):
        """Test dialog visibility state is consistent."""
        with patch("ui.rom_extraction_panel.UnifiedManualOffsetDialog", return_value=mock_dialog_with_ui):
            # Dialog starts visible
            mock_dialog_with_ui.isVisible.return_value = True

            dialog = ManualOffsetDialogSingleton.get_dialog(mock_panel)
            assert ManualOffsetDialogSingleton.is_dialog_open()

            # Hide dialog
            mock_dialog_with_ui.isVisible.return_value = False
            assert not ManualOffsetDialogSingleton.is_dialog_open()

            # Getting dialog should still return same instance
            dialog_ref = ManualOffsetDialogSingleton.get_dialog(mock_panel)
            assert dialog_ref is dialog

    def test_rom_data_persistence_across_accesses(self, mock_panel, mock_dialog_with_ui):
        """Test that ROM data persists across dialog accesses."""
        with patch("ui.rom_extraction_panel.UnifiedManualOffsetDialog", return_value=mock_dialog_with_ui):
            dialog = ManualOffsetDialogSingleton.get_dialog(mock_panel)

            # Set ROM data
            rom_path = "/test/rom.sfc"
            rom_size = 0x400000
            extraction_manager = MagicMock()

            dialog.set_rom_data(rom_path, rom_size, extraction_manager)
            mock_dialog_with_ui.set_rom_data.assert_called_once_with(rom_path, rom_size, extraction_manager)

            # Get dialog again - should be same instance with same data
            dialog_ref = ManualOffsetDialogSingleton.get_dialog(mock_panel)
            assert dialog_ref is dialog

            # ROM data setting should not be called again
            assert mock_dialog_with_ui.set_rom_data.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])