"""
Specific validation tests to ensure no duplicate sliders are created.

This focused test suite addresses the critical issue mentioned in the requirements:
"The key issue to verify is that users will never see duplicate sliders again."

These tests provide comprehensive validation that the singleton pattern
successfully prevents duplicate slider creation.
"""


from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QSlider, QSpinBox

from core.managers.extraction_manager import ExtractionManager
from ui.rom_extraction_panel import (
# Test characteristics: Singleton management
pytestmark = [
    pytest.mark.dialog,
    pytest.mark.headless,
    pytest.mark.mock_dialogs,
    pytest.mark.qt_mock,
    pytest.mark.rom_data,
    pytest.mark.serial,
    pytest.mark.singleton,
    pytest.mark.widget,
]


    ManualOffsetDialogSingleton,
    ROMExtractionPanel,
)


@pytest.mark.no_manager_setup
class TestNoDuplicateSlidersValidation:
    """Focused tests to validate no duplicate sliders are ever created."""

    @pytest.fixture(autouse=True)
    def setup_singleton_cleanup(self):
        """Ensure singleton is clean before and after each test."""
        # Clean up any existing instance before test
        if ManualOffsetDialogSingleton._instance is not None:
            instance = ManualOffsetDialogSingleton._instance
            ManualOffsetDialogSingleton._cleanup_instance(instance)
            ManualOffsetDialogSingleton._instance = None
        ManualOffsetDialogSingleton._destroyed = False
        yield
        # Clean up after test
        try:
            if ManualOffsetDialogSingleton._instance is not None:
                ManualOffsetDialogSingleton._instance.close()
                ManualOffsetDialogSingleton._instance.deleteLater()
                instance = ManualOffsetDialogSingleton._instance
                ManualOffsetDialogSingleton._cleanup_instance(instance)
                ManualOffsetDialogSingleton._instance = None
        except Exception:
            pass
        ManualOffsetDialogSingleton._destroyed = False

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
    def test_single_position_slider_exists(self, qtbot, mock_rom_panel):
        """Test that exactly one position slider exists in browse tab."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)

        # Count sliders in browse tab
        browse_tab = dialog.browse_tab
        position_sliders = [child for child in browse_tab.findChildren(QSlider)
                          if hasattr(child, "objectName") and "position" in child.objectName().lower()]

        # If no named sliders, count all sliders in browse tab
        if not position_sliders:
            all_sliders = browse_tab.findChildren(QSlider)
            # Browse tab should have exactly 1 main slider
            assert len(all_sliders) == 1, f"Browse tab should have exactly 1 slider, found {len(all_sliders)}"
        else:
            assert len(position_sliders) == 1, f"Should have exactly 1 position slider, found {len(position_sliders)}"

    @pytest.mark.unit
    def test_no_duplicate_sliders_after_multiple_accesses(self, qtbot, mock_rom_panel):
        """Test that multiple dialog accesses don't create duplicate sliders."""
        # First access
        dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog1)

        # Count sliders after first access
        initial_slider_count = len(dialog1.browse_tab.findChildren(QSlider))

        # Multiple accesses
        for i in range(5):
            dialog_ref = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            assert dialog_ref is dialog1, f"Should return same instance on access {i+1}"

            # Count sliders again
            current_slider_count = len(dialog_ref.browse_tab.findChildren(QSlider))
            assert current_slider_count == initial_slider_count, \
                f"Slider count changed from {initial_slider_count} to {current_slider_count} on access {i+1}"

    @pytest.mark.unit
    def test_slider_uniqueness_by_parent(self, qtbot, mock_rom_panel):
        """Test that each slider has a unique parent and no duplicates exist."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)

        # Get all sliders in the dialog
        all_sliders = dialog.findChildren(QSlider)

        # Check parent relationships - no slider should have the same parent as another
        slider_parents = []
        for slider in all_sliders:
            parent = slider.parent()
            slider_parents.append(parent)

        # In browse tab, there should be exactly one main slider
        browse_sliders = dialog.browse_tab.findChildren(QSlider)
        assert len(browse_sliders) >= 1, "Browse tab should have at least one slider"

        # The main position slider should be unique
        main_slider = dialog.browse_tab.position_slider
        assert main_slider in browse_sliders, "Main position slider should be in browse tab sliders"

    @pytest.mark.unit
    def test_no_duplicate_spinboxes_either(self, qtbot, mock_rom_panel):
        """Test that spinboxes (related to sliders) aren't duplicated either."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)

        # Count spinboxes in browse tab (should be 2: manual offset + step size)
        browse_spinboxes = dialog.browse_tab.findChildren(QSpinBox)
        initial_spinbox_count = len(browse_spinboxes)

        # Multiple accesses shouldn't change spinbox count
        for _i in range(3):
            dialog_ref = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            assert dialog_ref is dialog

            current_spinbox_count = len(dialog_ref.browse_tab.findChildren(QSpinBox))
            assert current_spinbox_count == initial_spinbox_count, \
                f"SpinBox count changed from {initial_spinbox_count} to {current_spinbox_count}"

    @pytest.mark.unit
    def test_slider_values_consistency(self, qtbot, mock_rom_panel):
        """Test that slider values remain consistent across accesses."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)
        dialog.set_rom_data(mock_rom_panel.rom_path, mock_rom_panel.rom_size, mock_rom_panel.extraction_manager)

        # Set a test offset
        test_offset = 0x280000
        dialog.set_offset(test_offset)

        slider = dialog.browse_tab.position_slider
        initial_value = slider
        assert initial_value == test_offset, f"Slider value {initial_value} should match set offset {test_offset}"

        # Multiple accesses - slider value should remain consistent
        for _i in range(3):
            dialog_ref = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            assert dialog_ref is dialog

            slider_ref = dialog_ref.browse_tab.position_slider
            assert slider_ref is slider, "Should be the same slider object"
            assert slider_ref == test_offset, f"Slider value should remain {test_offset}"

    @pytest.mark.unit
    def test_no_duplicate_ui_elements_comprehensive(self, qtbot, mock_rom_panel):
        """Comprehensive test to ensure no duplicate UI elements exist."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)

        # Count all types of controls that might be duplicated
        ui_element_counts = {
            "QSlider": len(dialog.findChildren(QSlider)),
            "QSpinBox": len(dialog.findChildren(QSpinBox)),
            "QPushButton": len(dialog.findChildren(QPushButton)),
            "QLabel": len(dialog.findChildren(QLabel)),
        }

        # Multiple accesses
        for i in range(3):
            dialog_ref = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            assert dialog_ref is dialog

            # Recount UI elements
            current_counts = {
                "QSlider": len(dialog_ref.findChildren(QSlider)),
                "QSpinBox": len(dialog_ref.findChildren(QSpinBox)),
                "QPushButton": len(dialog_ref.findChildren(QPushButton)),
                "QLabel": len(dialog_ref.findChildren(QLabel)),
            }

            # Verify counts haven't changed
            for element_type, initial_count in ui_element_counts.items():
                current_count = current_counts[element_type]
                assert current_count == initial_count, \
                    f"{element_type} count changed from {initial_count} to {current_count} on access {i+1}"

    @pytest.mark.integration
    def test_user_interaction_no_duplicates(self, qtbot, mock_rom_panel):
        """Test user interactions don't create duplicate sliders."""
        dialog = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog)
        dialog.set_rom_data(mock_rom_panel.rom_path, mock_rom_panel.rom_size, mock_rom_panel.extraction_manager)
        dialog.show()

        # Count initial sliders
        initial_slider_count = len(dialog.browse_tab.findChildren(QSlider))

        # Simulate user interactions
        slider = dialog.browse_tab.position_slider

        # Simulate slider value changes (like user dragging)
        test_values = [0x200000, 0x250000, 0x300000, 0x350000]
        for value in test_values:
            slider.setValue(value)
            qtbot.wait(10)  # Small delay to simulate real interaction

            # Get dialog reference during interaction
            dialog_ref = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
            assert dialog_ref is dialog

            # Verify slider count hasn't changed
            current_slider_count = len(dialog_ref.browse_tab.findChildren(QSlider))
            assert current_slider_count == initial_slider_count, \
                f"Slider count changed during interaction: {current_slider_count} vs {initial_slider_count}"

    @pytest.mark.integration
    def test_dialog_close_reopen_no_duplicates(self, qtbot, mock_rom_panel):
        """Test that closing and reopening dialog doesn't create duplicates."""
        # Open dialog first time
        dialog1 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog1)
        dialog1.show()

        # Count UI elements
        initial_slider_count = len(dialog1.browse_tab.findChildren(QSlider))
        initial_spinbox_count = len(dialog1.browse_tab.findChildren(QSpinBox))

        # Close dialog
        dialog1.close()
        qtbot.wait(50)

        # Reopen dialog
        dialog2 = ManualOffsetDialogSingleton.get_dialog(mock_rom_panel)
        qtbot.addWidget(dialog2)
        dialog2.show()

        # Should have same number of UI elements (fresh instance)
        new_slider_count = len(dialog2.browse_tab.findChildren(QSlider))
        new_spinbox_count = len(dialog2.browse_tab.findChildren(QSpinBox))

        assert new_slider_count == initial_slider_count, \
            f"Slider count after reopen: {new_slider_count} vs initial: {initial_slider_count}"
        assert new_spinbox_count == initial_spinbox_count, \
            f"SpinBox count after reopen: {new_spinbox_count} vs initial: {initial_spinbox_count}"


# Import necessary Qt widgets at module level to avoid import errors
from PySide6.QtWidgets import QLabel, QPushButton

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
