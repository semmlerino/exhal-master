"""
Fixed Manual Offset Dialog Singleton Tests.

This test suite follows Qt Testing Best Practices by properly mocking Qt object creation
to avoid fatal errors in headless environments. Tests focus on singleton behavior
rather than Qt GUI details.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from ui.rom_extraction_panel import (
    ManualOffsetDialogSingleton,
    ROMExtractionPanel,
)

pytestmark = [
    pytest.mark.serial,
    pytest.mark.thread_safety,
    pytest.mark.ci_safe,
    pytest.mark.dialog,
    pytest.mark.headless,
    pytest.mark.mock_dialogs,
    pytest.mark.rom_data,
]

@pytest.fixture
def mock_dialog():
    """Create a mock dialog that behaves like a Qt dialog."""
    dialog = MagicMock()
    dialog.isVisible.return_value = False
    dialog.windowTitle.return_value = "Manual Offset Dialog"
    dialog.close.return_value = None
    dialog.show.return_value = None
    dialog.hide.return_value = None
    dialog.finished = MagicMock()
    dialog.finished.connect = MagicMock()
    dialog.rejected = MagicMock()
    dialog.rejected.connect = MagicMock()
    dialog.destroyed = MagicMock()
    dialog.destroyed.connect = MagicMock()
    dialog.set_rom_data = MagicMock()
    dialog.set_offset = MagicMock()
    dialog.get_current_offset = MagicMock(return_value=0x200000)
    dialog.add_found_sprite = MagicMock()
    dialog.preview_widget = MagicMock()
    dialog.browse_tab = MagicMock()
    dialog.history_tab = MagicMock()
    return dialog

@pytest.mark.unit
class TestManualOffsetDialogSingleton:
    """Test suite for ManualOffsetDialogSingleton implementation with proper mocking."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        ManualOffsetDialogSingleton.reset()
        yield
        try:
            if ManualOffsetDialogSingleton._instance is not None:
                ManualOffsetDialogSingleton._instance.close()
        except Exception:
            pass
        ManualOffsetDialogSingleton.reset()

    @pytest.fixture
    def mock_rom_panel(self, manager_context_factory):
        """Create a mock ROM extraction panel with proper manager context."""
        panel = MagicMock(spec=ROMExtractionPanel)
        panel.rom_path = "/fake/rom/path.sfc"
        panel.rom_size = 0x400000
        with manager_context_factory() as context:
            mock_manager = context.get_manager("extraction", object)
            mock_rom_extractor = MagicMock()
            mock_manager.get_rom_extractor.return_value = mock_rom_extractor
            panel.extraction_manager = mock_manager
        return panel

    @pytest.mark.unit
    @pytest.mark.mock_gui
    def test_singleton_only_one_instance_exists(self, mock_rom_panel, mock_dialog):
        """Test that only one dialog instance can exist."""
        # Mock the UnifiedManualOffsetDialog constructor instead of _create_instance
        # This allows the singleton logic to run but avoids Qt object creation
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', return_value=mock_dialog):
            dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)

            # Both calls should return the same instance
            assert dialog1 is dialog2, "Singleton should return same instance"
            assert id(dialog1) == id(dialog2), "Object IDs should be identical"

            # Verify singleton state - now _creator_panel should be set
            assert ManualOffsetDialogSingleton._instance is dialog1
            assert ManualOffsetDialogSingleton._creator_panel is mock_rom_panel

    @pytest.mark.unit
    def test_singleton_instance_reuse_multiple_calls(self, mock_rom_panel, mock_dialog):
        """Test that multiple calls to get_dialog return the same instance."""
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', return_value=mock_dialog):
            instances = []
            for _ in range(5):
                dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
                instances.append(dialog)
            first_instance = instances[0]
            for instance in instances[1:]:
                assert instance is first_instance, "All instances should be identical"

    @pytest.mark.unit
    def test_singleton_cleanup_on_dialog_close(self, mock_rom_panel, mock_dialog):
        """Test that singleton is cleaned up when dialog is closed."""
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog', return_value=mock_dialog):
            dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            assert ManualOffsetDialogSingleton._instance is dialog

            # Simulate dialog close triggering cleanup
            ManualOffsetDialogSingleton._on_dialog_closed()

            # Instance should be cleaned up
            assert ManualOffsetDialogSingleton._instance is None
            assert ManualOffsetDialogSingleton._creator_panel is None

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
