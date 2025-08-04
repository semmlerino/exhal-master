"""
Unit tests for refactored UI components
"""

import sys

from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget
from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget

from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget
from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget

from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget
from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget

from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget
from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from spritepal.core.managers import cleanup_managers, initialize_managers
from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget


class TestROMMapWidget:
    """Test ROMMapWidget functionality"""

    @pytest.fixture(autouse=True)
    def setup_managers(self):
        """Setup managers for all tests"""
        initialize_managers("TestApp")
        yield
        cleanup_managers()

    # Using parent_widget fixture from qt_test_helpers instead of mock_parent

    def test_rom_map_widget_creation(self, parent_widget):
        """Test ROMMapWidget can be created with proper Qt parent"""
        # Test component creation with real Qt parent

        # Create widget with proper parent
        widget = ROMMapWidget(parent_widget)

        # Verify basic initialization with actual attributes
        assert hasattr(widget, "found_sprites")
        assert hasattr(widget, "current_offset")
        assert hasattr(widget, "rom_size")
        assert widget.parent() == parent_widget

    def test_add_sprite_data(self, parent_widget):
        """Test adding sprite data to ROM map"""
        from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget

        widget = ROMMapWidget(parent_widget)

        # Test adding sprite with quality
        offset = 0x1000
        quality = 0.95

        widget.add_found_sprite(offset, quality)

        # Verify sprite was added
        assert len(widget.found_sprites) == 1
        assert widget.found_sprites[0] == (offset, quality)

    def test_sprite_count_limits(self, parent_widget):
        """Test sprite count limits prevent memory leaks"""
        from spritepal.ui.components.visualization.rom_map_widget import (
            SPRITE_CLEANUP_TARGET,
            SPRITE_CLEANUP_THRESHOLD,
            ROMMapWidget,
        )

        widget = ROMMapWidget(parent_widget)

        # Add many sprites to test limits
        for i in range(SPRITE_CLEANUP_THRESHOLD + 100):  # More than the cleanup threshold
            widget.add_found_sprite(0x1000 + i * 32, 1.0)

        # Should have cleaned up to around target count (allow small variation)
        # The cleanup happens when exceeding threshold, so count should be close to target
        assert len(widget.found_sprites) <= SPRITE_CLEANUP_TARGET + 100  # Allow small buffer
        assert len(widget.found_sprites) < SPRITE_CLEANUP_THRESHOLD  # But definitely below threshold

    def test_cleanup_method(self, parent_widget):
        """Test cleanup method clears resources"""
        from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget

        widget = ROMMapWidget(parent_widget)

        # Add some sprite data
        widget.add_found_sprite(0x1000, 1.0)
        widget.add_found_sprite(0x2000, 0.8)
        assert len(widget.found_sprites) > 0

        # Clear sprites
        widget.clear_sprites()

        # Verify resources cleared
        assert len(widget.found_sprites) == 0


class TestScanControlsPanel:
    """Test ScanControlsPanel functionality"""

    @pytest.fixture(autouse=True)
    def setup_managers(self):
        """Setup managers for all tests"""
        initialize_managers("TestApp")
        yield
        cleanup_managers()

    # Using parent_widget fixture from qt_test_helpers instead of mock_parent

    def test_scan_controls_creation(self, parent_widget):
        """Test ScanControlsPanel creation"""
        from spritepal.ui.components.panels.scan_controls_panel import ScanControlsPanel

        panel = ScanControlsPanel(parent_widget)

        # Verify initialization
        assert hasattr(panel, "start_button")
        assert hasattr(panel, "stop_button")
        assert hasattr(panel, "range_start_spinbox")
        assert hasattr(panel, "range_end_spinbox")

    def test_scan_parameters_validation(self, parent_widget):
        """Test scan parameter validation"""
        from spritepal.ui.components.panels.scan_controls_panel import ScanControlsPanel

        panel = ScanControlsPanel(parent_widget)

        # Mock spinbox values
        panel.range_start_spinbox = Mock()
        panel.range_end_spinbox = Mock()
        panel.range_start_spinbox.value.return_value = 0x1000
        panel.range_end_spinbox.value.return_value = 0x2000

        # Test parameter validation
        params = panel.get_scan_parameters()

        assert params["start_offset"] == 0x1000
        assert params["end_offset"] == 0x2000
        assert params["end_offset"] > params["start_offset"]


class TestImportExportPanel:
    """Test ImportExportPanel functionality"""

    @pytest.fixture(autouse=True)
    def setup_managers(self):
        """Setup managers for all tests"""
        initialize_managers("TestApp")
        yield
        cleanup_managers()

    # Using parent_widget fixture from qt_test_helpers instead of mock_parent

    def test_import_export_creation(self, parent_widget):
        """Test ImportExportPanel creation"""
        from spritepal.ui.components.panels.import_export_panel import ImportExportPanel

        panel = ImportExportPanel(parent_widget)

        # Verify initialization
        assert hasattr(panel, "import_button")
        assert hasattr(panel, "export_button")

    def test_file_operations(self, parent_widget):
        """Test file import/export operations"""
        from spritepal.ui.components.panels.import_export_panel import ImportExportPanel

        with patch("PyQt6.QtWidgets.QFileDialog") as mock_file_dialog:
            panel = ImportExportPanel(parent_widget)

            # Mock file dialog
            mock_file_dialog.getOpenFileName.return_value = ("/path/to/file.json", "")
            mock_file_dialog.getSaveFileName.return_value = ("/path/to/save.json", "")

            # Test import operation
            import_file = panel.get_import_file()
            assert import_file == "/path/to/file.json"

            # Test export operation
            export_file = panel.get_export_file()
            assert export_file == "/path/to/save.json"


class TestStatusPanel:
    """Test StatusPanel functionality"""

    @pytest.fixture(autouse=True)
    def setup_managers(self):
        """Setup managers for all tests"""
        initialize_managers("TestApp")
        yield
        cleanup_managers()

    # Using parent_widget fixture from qt_test_helpers instead of mock_parent

    def test_status_panel_creation(self, parent_widget):
        """Test StatusPanel creation"""
        from spritepal.ui.components.panels.status_panel import StatusPanel

        panel = StatusPanel(parent_widget)

        # Verify initialization
        assert hasattr(panel, "status_label")
        assert hasattr(panel, "progress_bar")

    def test_status_updates(self, parent_widget):
        """Test status message updates"""
        from spritepal.ui.components.panels.status_panel import StatusPanel

        panel = StatusPanel(parent_widget)

        # Mock the label
        panel.status_label = Mock()
        panel.progress_bar = Mock()

        # Test status update
        panel.update_status("Scanning ROM...", 50)

        # Verify methods were called
        panel.status_label.setText.assert_called_with("Scanning ROM...")
        panel.progress_bar.setValue.assert_called_with(50)


class TestRangeScanDialog:
    """Test RangeScanDialog functionality"""

    @pytest.fixture(autouse=True)
    def setup_managers(self):
        """Setup managers for all tests"""
        initialize_managers("TestApp")
        yield
        cleanup_managers()

    # Using parent_widget fixture from qt_test_helpers instead of mock_parent

    def test_range_scan_dialog_creation(self, parent_widget):
        """Test RangeScanDialog creation"""
        from spritepal.ui.components.dialogs.range_scan_dialog import RangeScanDialog

        dialog = RangeScanDialog(parent_widget)

        # Verify initialization
        assert hasattr(dialog, "start_offset_spinbox")
        assert hasattr(dialog, "end_offset_spinbox")
        assert hasattr(dialog, "scan_button")

    def test_scan_parameters(self, parent_widget):
        """Test scan parameter collection"""
        from spritepal.ui.components.dialogs.range_scan_dialog import RangeScanDialog

        dialog = RangeScanDialog(parent_widget)

        # Mock spinboxes
        dialog.start_offset_spinbox = Mock()
        dialog.end_offset_spinbox = Mock()
        dialog.start_offset_spinbox.value.return_value = 0x10000
        dialog.end_offset_spinbox.value.return_value = 0x20000

        # Test parameter collection
        params = dialog.get_scan_parameters()

        assert params["start_offset"] == 0x10000
        assert params["end_offset"] == 0x20000

    def test_validation_with_large_range(self, parent_widget):
        """Test validation prevents excessively large scan ranges"""
        from spritepal.ui.components.dialogs.range_scan_dialog import RangeScanDialog

        with patch("PyQt6.QtWidgets.QMessageBox") as mock_msgbox:
            dialog = RangeScanDialog(parent_widget)

            # Mock spinboxes with large range
            dialog.start_offset_spinbox = Mock()
            dialog.end_offset_spinbox = Mock()
            dialog.start_offset_spinbox.value.return_value = 0x0
            dialog.end_offset_spinbox.value.return_value = 0x200000  # 2MB range

            # Test validation
            is_valid = dialog.validate_parameters()

            # Should warn about large range
            assert not is_valid or mock_msgbox.warning.called
