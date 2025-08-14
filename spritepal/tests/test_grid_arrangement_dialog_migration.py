"""
Test GridArrangementDialog migration to SplitterDialog

Validates that the migrated GridArrangementDialog maintains all original functionality
while using the new SplitterDialog architecture.

This is a real Qt integration test that requires a GUI environment.
"""

import contextlib
import os
import tempfile

import pytest
from PIL import Image

from ui.components import SplitterDialog
from ui.grid_arrangement_dialog import GridArrangementDialog


# Skip in headless environments - this tests real Qt dialog behavior
pytestmark = [
    pytest.mark.skipif(
        "DISPLAY" not in os.environ,
        reason="Requires GUI environment - this is a real Qt integration test"
    ),
    pytest.mark.serial,
    pytest.mark.qt_integration,
    pytest.mark.ci_safe,
    pytest.mark.dialog,
    pytest.mark.headless,
    pytest.mark.integration,
    pytest.mark.qt_real,
    pytest.mark.requires_display,
    pytest.mark.rom_data,
]


class TestGridArrangementDialogMigration:
    """Test GridArrangementDialog migration to SplitterDialog architecture"""

    @pytest.fixture
    def test_sprite_image(self):
        """Create a test sprite image"""
        # Create a simple test image (16x16 tiles, 4x4 grid)
        test_image = Image.new("L", (128, 128), 0)  # Grayscale image

        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        test_image.save(temp_file.name)
        temp_file.close()

        yield temp_file.name

        # Cleanup
        import os
        with contextlib.suppress(Exception):
            os.unlink(temp_file.name)

    def test_grid_arrangement_dialog_inherits_from_splitter_dialog(self, test_sprite_image, qtbot):
        """Test that GridArrangementDialog properly inherits from SplitterDialog"""
        dialog = GridArrangementDialog(test_sprite_image, tiles_per_row=16)
        qtbot.addWidget(dialog)

        # Verify inheritance
        assert isinstance(dialog, SplitterDialog)

        # Verify SplitterDialog features are available
        assert dialog.main_splitter is not None
        assert dialog.status_bar is not None
        assert dialog.button_box is not None

        # Verify dialog configuration
        assert dialog.windowTitle() == "Grid-Based Sprite Arrangement"
        assert dialog.isModal() is True

    def test_grid_arrangement_dialog_has_correct_panels(self, test_sprite_image, qtbot):
        """Test that GridArrangementDialog has the correct panel structure"""
        dialog = GridArrangementDialog(test_sprite_image, tiles_per_row=16)
        qtbot.addWidget(dialog)

        # Should have 2 main panels (left and right)
        assert dialog.main_splitter.count() == 2

        # Verify main components exist
        assert hasattr(dialog, "grid_view")  # Grid graphics view
        assert hasattr(dialog, "arrangement_list")  # Arrangement list
        assert hasattr(dialog, "preview_label")  # Preview area
        assert hasattr(dialog, "mode_buttons")  # Selection mode buttons

    def test_grid_arrangement_dialog_status_bar_integration(self, test_sprite_image, qtbot):
        """Test that status bar integration works with SplitterDialog"""
        dialog = GridArrangementDialog(test_sprite_image, tiles_per_row=16)
        qtbot.addWidget(dialog)

        # Test status update functionality
        test_message = "Test status message"
        dialog._update_status(test_message)

        # Verify status is displayed
        assert dialog.status_bar.currentMessage() == test_message

    def test_grid_arrangement_dialog_button_integration(self, test_sprite_image, qtbot):
        """Test that button integration works with SplitterDialog"""
        dialog = GridArrangementDialog(test_sprite_image, tiles_per_row=16)
        qtbot.addWidget(dialog)

        # Verify export button was added
        assert hasattr(dialog, "export_btn")
        assert dialog.export_btn is not None

        # Verify button box exists and is functional
        assert dialog.button_box is not None

        # Export button should be initially disabled (no arrangement)
        assert not dialog.export_btn.isEnabled()

    def test_grid_arrangement_dialog_maintains_functionality(self, test_sprite_image, qtbot):
        """Test that migrated dialog maintains all original functionality"""
        dialog = GridArrangementDialog(test_sprite_image, tiles_per_row=16)
        qtbot.addWidget(dialog)

        # Test that all key attributes are present
        assert hasattr(dialog, "sprite_path")
        assert hasattr(dialog, "tiles_per_row")
        assert hasattr(dialog, "processor")
        assert hasattr(dialog, "arrangement_manager")
        assert hasattr(dialog, "colorizer")
        assert hasattr(dialog, "preview_generator")

        # Test that the dialog loads sprite data
        assert dialog.sprite_path == test_sprite_image
        assert dialog.tiles_per_row == 16

    def test_grid_arrangement_dialog_graphics_view_integration(self, test_sprite_image, qtbot):
        """Test that graphics view integration is maintained after migration"""
        dialog = GridArrangementDialog(test_sprite_image, tiles_per_row=16)
        qtbot.addWidget(dialog)

        # Verify graphics components exist
        assert hasattr(dialog, "scene")
        assert hasattr(dialog, "grid_view")
        assert hasattr(dialog, "pixmap_item")

        # Verify grid view has expected properties
        assert dialog.grid_view is not None
        assert dialog.grid_view.scene() == dialog.scene

    def test_grid_arrangement_dialog_selection_modes(self, test_sprite_image, qtbot):
        """Test that selection mode functionality is preserved"""
        dialog = GridArrangementDialog(test_sprite_image, tiles_per_row=16)
        qtbot.addWidget(dialog)

        # Verify selection mode components exist
        assert hasattr(dialog, "mode_buttons")
        assert dialog.mode_buttons is not None

        # Verify action buttons exist
        assert hasattr(dialog, "add_btn")
        assert hasattr(dialog, "remove_btn")
        assert hasattr(dialog, "create_group_btn")
        assert hasattr(dialog, "clear_btn")

    def test_grid_arrangement_dialog_splitter_configuration(self, test_sprite_image, qtbot):
        """Test that splitter configuration is correct"""
        dialog = GridArrangementDialog(test_sprite_image, tiles_per_row=16)
        qtbot.addWidget(dialog)

        # Main splitter should be horizontal
        from PySide6.QtCore import Qt
        assert dialog.main_splitter.orientation() == Qt.Orientation.Horizontal

        # Handle width should be set correctly
        assert dialog.main_splitter.handleWidth() == 8

        # Should have 2 panels with appropriate stretch factors
        assert dialog.main_splitter.count() == 2

    def test_grid_arrangement_dialog_zoom_controls(self, test_sprite_image, qtbot):
        """Test that zoom control integration is maintained"""
        dialog = GridArrangementDialog(test_sprite_image, tiles_per_row=16)
        qtbot.addWidget(dialog)

        # Verify zoom controls exist
        assert hasattr(dialog, "zoom_in_btn")
        assert hasattr(dialog, "zoom_out_btn")
        assert hasattr(dialog, "zoom_fit_btn")
        assert hasattr(dialog, "zoom_reset_btn")
        assert hasattr(dialog, "zoom_level_label")

        # Verify zoom functionality is connected
        assert dialog.grid_view is not None
        zoom_level = dialog.grid_view.get_zoom_level()
        assert isinstance(zoom_level, float)
        assert zoom_level > 0

    def test_grid_arrangement_dialog_error_state_handling(self, qtbot):
        """Test that error state handling works correctly"""
        # Test with non-existent file
        # Patch QMessageBox to prevent blocking dialogs during GridArrangementDialog initialization
        from unittest.mock import patch
        with patch("ui.grid_arrangement_dialog.QMessageBox.critical"):
            dialog = GridArrangementDialog("/non/existent/file.png", tiles_per_row=16)
        qtbot.addWidget(dialog)

        # Should handle error gracefully and maintain SplitterDialog structure
        assert isinstance(dialog, SplitterDialog)
        assert dialog.main_splitter is not None
        assert dialog.status_bar is not None

        # Status should reflect error state
        status_message = dialog.status_bar.currentMessage()
        assert "Error" in status_message or "Unable to load" in status_message