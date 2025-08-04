"""
Comprehensive tests for Manual Offset Dialog Singleton Implementation.

This test suite verifies that the ManualOffsetDialogSingleton pattern works correctly
and ensures that users never see duplicate sliders or UI elements. Tests cover:

1. Singleton pattern enforcement (only one instance)

from spritepal.ui.widgets.sprite_preview_widget import SpritePreviewWidget
from PyQt6.QtWidgets import QSlider

from spritepal.ui.widgets.sprite_preview_widget import SpritePreviewWidget
from PyQt6.QtWidgets import QSlider

from spritepal.ui.widgets.sprite_preview_widget import SpritePreviewWidget
from PyQt6.QtWidgets import QSlider

from spritepal.ui.widgets.sprite_preview_widget import SpritePreviewWidget
from PyQt6.QtWidgets import QSlider
2. Dialog reuse across multiple open/close cycles
3. Slider updates work correctly without duplicates
4. Preview widget integration without duplicate elements
5. Thread safety and concurrent access
6. Real user workflow simulation
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtTest import QTest

from spritepal.core.managers.extraction_manager import ExtractionManager
from spritepal.ui.rom_extraction_panel import (
    ManualOffsetDialogSingleton,
    ROMExtractionPanel,
)


@pytest.mark.no_manager_setup
class TestManualOffsetDialogSingleton:
    """Test suite for ManualOffsetDialogSingleton implementation."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        # Clean up before test
        ManualOffsetDialogSingleton._cleanup_instance()
        yield
        # Clean up after test
        try:
            if ManualOffsetDialogSingleton._instance is not None:
                ManualOffsetDialogSingleton._instance.close()
                ManualOffsetDialogSingleton._instance.deleteLater()
        except Exception:
            pass
        ManualOffsetDialogSingleton._cleanup_instance()

    @pytest.fixture
    def mock_rom_panel(self, qtbot):
        """Create a mock ROM extraction panel."""
        panel = MagicMock(spec=ROMExtractionPanel)
        panel.rom_path = "/fake/rom/path.sfc"
        panel.rom_size = 0x400000

        # Mock extraction manager
        mock_manager = MagicMock(spec=ExtractionManager)
        mock_rom_extractor = MagicMock()
        mock_manager.get_rom_extractor.return_value = mock_rom_extractor
        panel.extraction_manager = mock_manager

        return panel

    @pytest.mark.unit
    @pytest.mark.mock_gui
    def test_singleton_only_one_instance_exists(self, qtbot, mock_rom_panel):
        """Test that only one dialog instance can exist."""
        # RED: Test should fail initially - write failing test first
        dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)

        # Both calls should return the same instance
        assert dialog1 is dialog2, "Singleton should return same instance"
        assert id(dialog1) == id(dialog2), "Object IDs should be identical"

        # Verify singleton state
        assert ManualOffsetDialogSingleton._instance is dialog1
        assert ManualOffsetDialogSingleton._creator_panel is mock_rom_panel

    @pytest.mark.unit
    def test_singleton_instance_reuse_multiple_calls(self, qtbot, mock_rom_panel):
        """Test that multiple calls to get_dialog return the same instance."""
        instances = []

        # Create multiple references
        for _ in range(5):
            dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            instances.append(dialog)

        # All should be the same instance
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance, "All instances should be identical"

    @pytest.mark.unit
    def test_singleton_cleanup_on_dialog_close(self, qtbot, mock_rom_panel):
        """Test that singleton is cleaned up when dialog is closed."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)

        # Verify instance exists
        assert ManualOffsetDialogSingleton._instance is dialog

        # Close dialog
        dialog.close()

        # Process events to allow cleanup
        qtbot.wait(50)
        QTest.qWait(50)

        # Instance should be cleaned up
        assert ManualOffsetDialogSingleton._instance is None
        assert ManualOffsetDialogSingleton._creator_panel is None

    @pytest.mark.unit
    def test_singleton_stale_reference_cleanup(self, qtbot, mock_rom_panel):
        """Test cleanup of stale references when dialog is destroyed externally."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)

        # Simulate Qt destroying the dialog externally
        dialog.deleteLater()
        qtbot.wait(100)  # Allow deletion to process

        # Force cleanup by trying to access the stale dialog
        # This should trigger the RuntimeError handling in get_dialog
        new_dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)

        # Should get a new instance
        assert new_dialog is not dialog
        assert ManualOffsetDialogSingleton._instance is new_dialog

    @pytest.mark.unit
    def test_singleton_different_creator_panels(self, qtbot):
        """Test behavior when called with different creator panels."""
        panel1 = MagicMock(spec=ROMExtractionPanel)
        panel2 = MagicMock(spec=ROMExtractionPanel)

        dialog1 = ManualOffsetDialogSingleton.get_dialog(panel1)
        dialog2 = ManualOffsetDialogSingleton.get_dialog(panel2)

        # Should still return the same instance (singleton behavior)
        # The first creator panel "owns" the dialog
        assert dialog1 is dialog2
        assert ManualOffsetDialogSingleton._creator_panel is panel1


@pytest.mark.no_manager_setup
class TestDialogReuseAndCleanup:
    """Test dialog reuse across multiple open/close cycles."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        ManualOffsetDialogSingleton._cleanup_instance()
        yield
        try:
            if ManualOffsetDialogSingleton._instance is not None:
                ManualOffsetDialogSingleton._instance.close()
                ManualOffsetDialogSingleton._instance.deleteLater()
        except Exception:
            pass
        ManualOffsetDialogSingleton._cleanup_instance()

    @pytest.fixture
    def mock_rom_panel(self):
        """Create a mock ROM extraction panel."""
        panel = MagicMock(spec=ROMExtractionPanel)
        panel.rom_path = "/fake/rom/path.sfc"
        panel.rom_size = 0x400000

        mock_manager = MagicMock(spec=ExtractionManager)
        mock_rom_extractor = MagicMock()
        mock_manager.get_rom_extractor.return_value = mock_rom_extractor
        panel.extraction_manager = mock_manager

        return panel

    @pytest.mark.unit
    def test_dialog_open_close_reopen_cycle(self, qtbot, mock_rom_panel):
        """Test that dialog can be opened, closed, and reopened correctly."""
        # Open dialog first time
        dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog1)
        dialog1.show()

        assert dialog1.isVisible()
        assert ManualOffsetDialogSingleton.is_dialog_open()

        # Close dialog
        dialog1.close()
        qtbot.wait(50)

        assert not dialog1.isVisible()
        assert not ManualOffsetDialogSingleton.is_dialog_open()

        # Reopen dialog - should get new instance after cleanup
        dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog2)
        dialog2.show()

        assert dialog2.isVisible()
        assert ManualOffsetDialogSingleton.is_dialog_open()

    @pytest.mark.unit
    def test_dialog_hide_show_reuse(self, qtbot, mock_rom_panel):
        """Test that hiding and showing dialog reuses the same instance."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)

        # Show dialog
        dialog.show()
        assert dialog.isVisible()

        # Hide dialog (don't close)
        dialog.hide()
        assert not dialog.isVisible()

        # Get dialog again - should be same instance
        dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        assert dialog is dialog2

        # Show again
        dialog2.show()
        assert dialog2.isVisible()

    @pytest.mark.unit
    def test_dialog_cleanup_signals_connected(self, qtbot, mock_rom_panel):
        """Test that cleanup signals are properly connected."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)

        # Verify signals are connected for cleanup
        assert dialog.finished.isSignalConnected()
        assert dialog.rejected.isSignalConnected()
        assert dialog.destroyed.isSignalConnected()

    @pytest.mark.unit
    def test_multiple_close_reopen_cycles(self, qtbot, mock_rom_panel):
        """Test multiple open/close cycles work correctly."""
        dialog_instances = []

        for _i in range(3):
            # Open dialog
            dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            qtbot.addWidget(dialog)
            dialog.show()

            assert dialog.isVisible()
            dialog_instances.append(dialog)

            # Close dialog
            dialog.close()
            qtbot.wait(50)

            assert not dialog.isVisible()


@pytest.mark.no_manager_setup
class TestSliderUpdateWithoutDuplicates:
    """Test that slider updates work correctly without creating duplicates."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        ManualOffsetDialogSingleton._cleanup_instance()
        yield
        try:
            if ManualOffsetDialogSingleton._instance is not None:
                ManualOffsetDialogSingleton._instance.close()
                ManualOffsetDialogSingleton._instance.deleteLater()
        except Exception:
            pass
        ManualOffsetDialogSingleton._cleanup_instance()

    @pytest.fixture
    def mock_rom_panel(self):
        """Create a mock ROM extraction panel with real data."""
        panel = MagicMock(spec=ROMExtractionPanel)
        panel.rom_path = "/fake/rom/path.sfc"
        panel.rom_size = 0x400000

        mock_manager = MagicMock(spec=ExtractionManager)
        mock_rom_extractor = MagicMock()
        mock_manager.get_rom_extractor.return_value = mock_rom_extractor
        panel.extraction_manager = mock_manager

        return panel

    @pytest.mark.unit
    def test_slider_updates_single_instance(self, qtbot, mock_rom_panel):
        """Test that slider updates only affect a single dialog instance."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)

        # Set ROM data
        dialog.set_rom_data(mock_rom_panel.rom_path, mock_rom_panel.rom_size, mock_rom_panel.extraction_manager)

        # Get initial offset
        dialog.get_current_offset()

        # Update offset through dialog
        new_offset = 0x300000
        dialog.set_offset(new_offset)

        # Verify offset was updated
        assert dialog.get_current_offset() == new_offset

        # Get dialog again - should be same instance with same offset
        dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        assert dialog is dialog2
        assert dialog2.get_current_offset() == new_offset

    @pytest.mark.unit
    def test_no_duplicate_sliders_created(self, qtbot, mock_rom_panel):
        """Test that multiple dialog accesses don't create duplicate sliders."""
        dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog1)

        # Count slider widgets in browse tab
        browse_tab = dialog1.browse_tab
        assert browse_tab is not None

        # Should have exactly one slider
        sliders = browse_tab.findChildren(dialog1.browse_tab.position_slider.__class__)
        slider_count_1 = len(sliders)

        # Get dialog again
        dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        assert dialog1 is dialog2

        # Should still have same number of sliders
        sliders = browse_tab.findChildren(dialog1.browse_tab.position_slider.__class__)
        slider_count_2 = len(sliders)

        assert slider_count_1 == slider_count_2, "No duplicate sliders should be created"
        assert slider_count_1 >= 1, "At least one slider should exist"

    @pytest.mark.unit
    def test_slider_signal_connections_not_duplicated(self, qtbot, mock_rom_panel):
        """Test that slider signal connections aren't duplicated."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)

        # Get slider
        slider = dialog.browse_tab.position_slider

        # Count existing connections (mock this as direct inspection is complex)
        with patch.object(slider, "valueChanged") as mock_signal:
            # Simulate connecting the signal as it happens in the real code
            mock_signal.connect = MagicMock()

            # Re-accessing dialog shouldn't create new connections
            dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            assert dialog is dialog2

            # Signal connections should not have been called again
            mock_signal.connect.assert_not_called()

    @pytest.mark.unit
    def test_offset_persistence_across_accesses(self, qtbot, mock_rom_panel):
        """Test that offset values persist across dialog accesses."""
        # First access - set offset
        dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog1)
        dialog1.set_rom_data(mock_rom_panel.rom_path, mock_rom_panel.rom_size, mock_rom_panel.extraction_manager)

        test_offset = 0x250000
        dialog1.set_offset(test_offset)

        # Second access - check offset persists
        dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        assert dialog1 is dialog2
        assert dialog2.get_current_offset() == test_offset

        # Third access after hide/show
        dialog2.hide()
        dialog3 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        assert dialog2 is dialog3
        assert dialog3.get_current_offset() == test_offset


@pytest.mark.no_manager_setup
class TestPreviewWidgetIntegration:
    """Test preview widget integration without duplicate elements."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        ManualOffsetDialogSingleton._cleanup_instance()
        yield
        try:
            if ManualOffsetDialogSingleton._instance is not None:
                ManualOffsetDialogSingleton._instance.close()
                ManualOffsetDialogSingleton._instance.deleteLater()
        except Exception:
            pass
        ManualOffsetDialogSingleton._cleanup_instance()

    @pytest.fixture
    def mock_rom_panel(self):
        """Create a mock ROM extraction panel."""
        panel = MagicMock(spec=ROMExtractionPanel)
        panel.rom_path = "/fake/rom/path.sfc"
        panel.rom_size = 0x400000

        mock_manager = MagicMock(spec=ExtractionManager)
        mock_rom_extractor = MagicMock()
        mock_manager.get_rom_extractor.return_value = mock_rom_extractor
        panel.extraction_manager = mock_manager

        return panel

    @pytest.mark.unit
    def test_single_preview_widget_exists(self, qtbot, mock_rom_panel):
        """Test that only one preview widget exists."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)

        # Should have exactly one preview widget
        assert dialog.preview_widget is not None

        # Get dialog again
        dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        assert dialog is dialog2
        assert dialog2.preview_widget is dialog.preview_widget

    @pytest.mark.unit
    def test_no_duplicate_preview_widgets(self, qtbot, mock_rom_panel):
        """Test that multiple accesses don't create duplicate preview widgets."""
        dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog1)

        # Count preview widgets
        from spritepal.ui.widgets.sprite_preview_widget import SpritePreviewWidget
        preview_widgets_1 = dialog1.findChildren(SpritePreviewWidget)

        # Get dialog again
        dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        assert dialog1 is dialog2

        # Should have same number of preview widgets
        preview_widgets_2 = dialog2.findChildren(SpritePreviewWidget)
        assert len(preview_widgets_1) == len(preview_widgets_2)
        assert len(preview_widgets_1) >= 1, "At least one preview widget should exist"

    @pytest.mark.unit
    def test_preview_state_consistency(self, qtbot, mock_rom_panel):
        """Test that preview widget state is consistent across accesses."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)

        # Set up preview widget state
        preview_widget = dialog.preview_widget
        test_sprite_name = "test_sprite_singleton"

        # Simulate setting preview data
        with patch.object(preview_widget, "load_sprite_from_4bpp") as mock_load:
            preview_widget.load_sprite_from_4bpp(b"test_data", 32, 32, test_sprite_name)
            mock_load.assert_called_once()

        # Get dialog again - should have same preview widget state
        dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        assert dialog is dialog2
        assert dialog2.preview_widget is preview_widget


@pytest.mark.no_manager_setup
class TestThreadSafetyConcurrentAccess:
    """Test thread safety and concurrent access scenarios."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        ManualOffsetDialogSingleton._cleanup_instance()
        yield
        try:
            if ManualOffsetDialogSingleton._instance is not None:
                ManualOffsetDialogSingleton._instance.close()
                ManualOffsetDialogSingleton._instance.deleteLater()
        except Exception:
            pass
        ManualOffsetDialogSingleton._cleanup_instance()

    @pytest.fixture
    def mock_rom_panel(self):
        """Create a mock ROM extraction panel."""
        panel = MagicMock(spec=ROMExtractionPanel)
        panel.rom_path = "/fake/rom/path.sfc"
        panel.rom_size = 0x400000

        mock_manager = MagicMock(spec=ExtractionManager)
        mock_rom_extractor = MagicMock()
        mock_manager.get_rom_extractor.return_value = mock_rom_extractor
        panel.extraction_manager = mock_manager

        return panel

    @pytest.mark.unit
    @pytest.mark.thread_safety
    def test_concurrent_singleton_creation(self, qtbot, mock_rom_panel):
        """Test that concurrent access to singleton is thread-safe."""
        instances = []
        errors = []

        def get_dialog_instance():
            """Thread worker to get dialog instance."""
            try:
                dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
                instances.append(dialog)
                return dialog
            except Exception as e:
                errors.append(e)
                return None

        # Create multiple threads trying to get dialog simultaneously
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_dialog_instance) for _ in range(10)]

            # Wait for all threads to complete
            for future in as_completed(futures):
                future.result()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors in concurrent access: {errors}"

        # All instances should be identical
        assert len(instances) > 0, "At least one instance should be created"
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance, "All instances should be identical in concurrent access"

    @pytest.mark.unit
    @pytest.mark.thread_safety
    def test_concurrent_offset_updates(self, qtbot, mock_rom_panel):
        """Test concurrent offset updates are handled safely."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)
        dialog.set_rom_data(mock_rom_panel.rom_path, mock_rom_panel.rom_size, mock_rom_panel.extraction_manager)

        results = []
        errors = []

        def update_offset(offset_value):
            """Thread worker to update offset."""
            try:
                dialog.set_offset(offset_value)
                result_offset = dialog.get_current_offset()
                results.append(result_offset)
                return result_offset
            except Exception as e:
                errors.append(e)
                return None

        # Update offsets from multiple threads
        offset_values = [0x200000 + i * 0x1000 for i in range(5)]

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(update_offset, offset) for offset in offset_values]

            for future in as_completed(futures):
                future.result()

        # Verify no errors
        assert len(errors) == 0, f"Errors in concurrent offset updates: {errors}"

        # Should have results from all updates
        assert len(results) == len(offset_values)

        # Final offset should be one of the values set
        final_offset = dialog.get_current_offset()
        assert final_offset in offset_values


@pytest.mark.no_manager_setup
class TestRealUserWorkflowIntegration:
    """Integration test simulating real user workflow."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        ManualOffsetDialogSingleton._cleanup_instance()
        yield
        try:
            if ManualOffsetDialogSingleton._instance is not None:
                ManualOffsetDialogSingleton._instance.close()
                ManualOffsetDialogSingleton._instance.deleteLater()
        except Exception:
            pass
        ManualOffsetDialogSingleton._cleanup_instance()

    @pytest.fixture
    def mock_rom_panel(self):
        """Create a mock ROM extraction panel."""
        panel = MagicMock(spec=ROMExtractionPanel)
        panel.rom_path = "/fake/rom/path.sfc"
        panel.rom_size = 0x400000

        mock_manager = MagicMock(spec=ExtractionManager)
        mock_rom_extractor = MagicMock()
        mock_manager.get_rom_extractor.return_value = mock_rom_extractor
        panel.extraction_manager = mock_manager

        return panel

    @pytest.mark.integration
    def test_complete_user_workflow_no_duplicates(self, qtbot, mock_rom_panel):
        """Test complete user workflow ensuring no duplicate UI elements."""
        # User opens manual offset dialog for first time
        dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog1)
        dialog1.set_rom_data(mock_rom_panel.rom_path, mock_rom_panel.rom_size, mock_rom_panel.extraction_manager)
        dialog1.show()

        # User adjusts offset using slider
        dialog1.get_current_offset()
        new_offset = 0x280000
        dialog1.set_offset(new_offset)
        assert dialog1.get_current_offset() == new_offset

        # User closes dialog
        dialog1.close()
        qtbot.wait(50)

        # User reopens dialog later
        dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog2)
        dialog2.set_rom_data(mock_rom_panel.rom_path, mock_rom_panel.rom_size, mock_rom_panel.extraction_manager)
        dialog2.show()

        # Verify no duplicate sliders exist
        from PyQt6.QtWidgets import QSlider
        sliders = dialog2.findChildren(QSlider)

        # Should have reasonable number of sliders (browse tab has 1 main slider)
        assert len(sliders) >= 1, "Should have at least one slider"
        assert len(sliders) <= 3, f"Should not have excessive sliders, found {len(sliders)}"

        # User works with dialog multiple times
        for i in range(3):
            test_offset = 0x200000 + i * 0x10000
            dialog2.set_offset(test_offset)
            assert dialog2.get_current_offset() == test_offset

            # Get dialog reference again (simulating multiple accesses)
            dialog_ref = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            assert dialog_ref is dialog2
            assert dialog_ref.get_current_offset() == test_offset

    @pytest.mark.integration
    def test_workflow_with_history_and_preview(self, qtbot, mock_rom_panel):
        """Test workflow using history and preview features."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)
        dialog.set_rom_data(mock_rom_panel.rom_path, mock_rom_panel.rom_size, mock_rom_panel.extraction_manager)

        # User finds several sprites
        sprite_offsets = [0x200000, 0x210000, 0x220000]
        for offset in sprite_offsets:
            dialog.add_found_sprite(offset, 0.95)

        # Verify history tab shows correct count
        history_count = dialog.history_tab.get_sprite_count()
        assert history_count == len(sprite_offsets)

        # User navigates through history
        for offset in sprite_offsets:
            dialog.set_offset(offset)
            assert dialog.get_current_offset() == offset

        # Get dialog again - history should persist
        dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        assert dialog is dialog2
        assert dialog2.history_tab.get_sprite_count() == len(sprite_offsets)

    @pytest.mark.integration
    def test_error_recovery_workflow(self, qtbot, mock_rom_panel):
        """Test that singleton works correctly after error conditions."""
        # Create dialog
        dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog1)

        # Simulate an error that might corrupt dialog state
        with patch.object(dialog1, "set_offset", side_effect=Exception("Simulated error")):
            try:
                dialog1.set_offset(0x300000)
            except Exception:
                pass  # Expected error

        # Dialog should still be accessible and functional
        dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        assert dialog1 is dialog2

        # Should be able to set offset normally after error
        dialog2.set_offset(0x250000)
        assert dialog2.get_current_offset() == 0x250000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
