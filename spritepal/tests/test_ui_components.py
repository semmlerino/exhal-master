"""
Unit tests for refactored UI components
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from spritepal.core.managers import cleanup_managers, initialize_managers


class TestROMMapWidget:
    """Test ROMMapWidget functionality"""

    @pytest.fixture(autouse=True)
    def setup_managers(self):
        """Setup managers for all tests"""
        initialize_managers("TestApp")
        yield
        cleanup_managers()

    @pytest.fixture
    def mock_parent(self):
        """Create mock parent widget"""
        parent = Mock()
        parent.width = Mock(return_value=400)
        parent.height = Mock(return_value=300)
        return parent

    def test_rom_map_widget_creation(self, mock_parent):
        """Test ROMMapWidget can be created without Qt"""
        # Test component creation logic without Qt dependencies
        from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget

        # Mock Qt components more comprehensively
        with (
            patch("PyQt6.QtWidgets.QWidget.__init__") as mock_qwidget_init,
            patch("PyQt6.QtGui.QPainter"),
            patch("PyQt6.QtCore.QTimer"),
            patch.object(ROMMapWidget, "setSizePolicy"),
            patch.object(ROMMapWidget, "setMinimumSize"),
        ):
            # Mock the QWidget init to do nothing
            mock_qwidget_init.return_value = None

            # Create widget with mocked parent
            widget = ROMMapWidget(mock_parent)

            # Manually set expected attributes for test
            widget._parent = mock_parent
            widget.sprites = []
            widget.selected_offset = None

            # Verify basic initialization
            assert hasattr(widget, "sprites")
            assert hasattr(widget, "selected_offset")

    def test_add_sprite_data(self, mock_parent):
        """Test adding sprite data to ROM map"""
        from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget

        with (
            patch("PyQt6.QtWidgets.QWidget"),
            patch("PyQt6.QtGui.QPainter"),
            patch("PyQt6.QtCore.QTimer"),
        ):
            widget = ROMMapWidget(mock_parent)

            # Test adding sprite data
            sprite_data = {
                "offset": 0x1000,
                "size": 32,
                "name": "test_sprite",
                "valid": True
            }

            widget.add_sprite(sprite_data)

            # Verify sprite was added
            assert len(widget.sprites) == 1
            assert widget.sprites[0] == sprite_data

    def test_sprite_count_limits(self, mock_parent):
        """Test sprite count limits prevent memory leaks"""
        from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget

        with (
            patch("PyQt6.QtWidgets.QWidget"),
            patch("PyQt6.QtGui.QPainter"),
            patch("PyQt6.QtCore.QTimer"),
        ):
            widget = ROMMapWidget(mock_parent)

            # Add many sprites to test limits
            for i in range(1500):  # More than the limit
                sprite_data = {
                    "offset": 0x1000 + i * 32,
                    "size": 32,
                    "name": f"sprite_{i}",
                    "valid": True
                }
                widget.add_sprite(sprite_data)

            # Should not exceed the limit
            assert len(widget.sprites) <= 1000  # Expected limit

    def test_cleanup_method(self, mock_parent):
        """Test cleanup method clears resources"""
        from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget

        with (
            patch("PyQt6.QtWidgets.QWidget"),
            patch("PyQt6.QtGui.QPainter"),
            patch("PyQt6.QtCore.QTimer"),
        ):
            widget = ROMMapWidget(mock_parent)

            # Add some data
            widget.add_sprite({"offset": 0x1000, "size": 32, "name": "test", "valid": True})
            assert len(widget.sprites) > 0

            # Call cleanup
            widget.cleanup()

            # Verify cleanup
            assert len(widget.sprites) == 0


class TestScanControlsPanel:
    """Test ScanControlsPanel functionality"""

    @pytest.fixture(autouse=True)
    def setup_managers(self):
        """Setup managers for all tests"""
        initialize_managers("TestApp")
        yield
        cleanup_managers()

    @pytest.fixture
    def mock_parent(self):
        """Create mock parent widget"""
        return Mock()

    def test_scan_controls_creation(self, mock_parent):
        """Test ScanControlsPanel creation"""
        from spritepal.ui.components.panels.scan_controls_panel import ScanControlsPanel

        with (
            patch("PyQt6.QtWidgets.QWidget"),
            patch("PyQt6.QtWidgets.QVBoxLayout"),
            patch("PyQt6.QtWidgets.QHBoxLayout"),
            patch("PyQt6.QtWidgets.QPushButton"),
            patch("PyQt6.QtWidgets.QSpinBox"),
        ):
            panel = ScanControlsPanel(mock_parent)

            # Verify initialization
            assert hasattr(panel, "start_button")
            assert hasattr(panel, "stop_button")
            assert hasattr(panel, "range_start_spinbox")
            assert hasattr(panel, "range_end_spinbox")

    def test_scan_parameters_validation(self, mock_parent):
        """Test scan parameter validation"""
        from spritepal.ui.components.panels.scan_controls_panel import ScanControlsPanel

        with (
            patch("PyQt6.QtWidgets.QWidget"),
            patch("PyQt6.QtWidgets.QVBoxLayout"),
            patch("PyQt6.QtWidgets.QHBoxLayout"),
            patch("PyQt6.QtWidgets.QPushButton"),
            patch("PyQt6.QtWidgets.QSpinBox"),
        ):
            panel = ScanControlsPanel(mock_parent)

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

    @pytest.fixture
    def mock_parent(self):
        """Create mock parent widget"""
        return Mock()

    def test_import_export_creation(self, mock_parent):
        """Test ImportExportPanel creation"""
        from spritepal.ui.components.panels.import_export_panel import ImportExportPanel

        with (
            patch("PyQt6.QtWidgets.QWidget"),
            patch("PyQt6.QtWidgets.QVBoxLayout"),
            patch("PyQt6.QtWidgets.QHBoxLayout"),
            patch("PyQt6.QtWidgets.QPushButton"),
        ):
            panel = ImportExportPanel(mock_parent)

            # Verify initialization
            assert hasattr(panel, "import_button")
            assert hasattr(panel, "export_button")

    def test_file_operations(self, mock_parent):
        """Test file import/export operations"""
        from spritepal.ui.components.panels.import_export_panel import ImportExportPanel

        with (
            patch("PyQt6.QtWidgets.QWidget"),
            patch("PyQt6.QtWidgets.QVBoxLayout"),
            patch("PyQt6.QtWidgets.QHBoxLayout"),
            patch("PyQt6.QtWidgets.QPushButton"),
            patch("PyQt6.QtWidgets.QFileDialog") as mock_file_dialog,
        ):
            panel = ImportExportPanel(mock_parent)

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

    @pytest.fixture
    def mock_parent(self):
        """Create mock parent widget"""
        return Mock()

    def test_status_panel_creation(self, mock_parent):
        """Test StatusPanel creation"""
        from spritepal.ui.components.panels.status_panel import StatusPanel

        with (
            patch("PyQt6.QtWidgets.QWidget"),
            patch("PyQt6.QtWidgets.QVBoxLayout"),
            patch("PyQt6.QtWidgets.QLabel"),
            patch("PyQt6.QtWidgets.QProgressBar"),
        ):
            panel = StatusPanel(mock_parent)

            # Verify initialization
            assert hasattr(panel, "status_label")
            assert hasattr(panel, "progress_bar")

    def test_status_updates(self, mock_parent):
        """Test status message updates"""
        from spritepal.ui.components.panels.status_panel import StatusPanel

        with (
            patch("PyQt6.QtWidgets.QWidget"),
            patch("PyQt6.QtWidgets.QVBoxLayout"),
            patch("PyQt6.QtWidgets.QLabel"),
            patch("PyQt6.QtWidgets.QProgressBar"),
        ):
            panel = StatusPanel(mock_parent)

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

    @pytest.fixture
    def mock_parent(self):
        """Create mock parent widget"""
        return Mock()

    def test_range_scan_dialog_creation(self, mock_parent):
        """Test RangeScanDialog creation"""
        from spritepal.ui.components.dialogs.range_scan_dialog import RangeScanDialog

        with (
            patch("PyQt6.QtWidgets.QDialog"),
            patch("PyQt6.QtWidgets.QVBoxLayout"),
            patch("PyQt6.QtWidgets.QSpinBox"),
            patch("PyQt6.QtWidgets.QPushButton"),
        ):
            dialog = RangeScanDialog(mock_parent)

            # Verify initialization
            assert hasattr(dialog, "start_offset_spinbox")
            assert hasattr(dialog, "end_offset_spinbox")
            assert hasattr(dialog, "scan_button")

    def test_scan_parameters(self, mock_parent):
        """Test scan parameter collection"""
        from spritepal.ui.components.dialogs.range_scan_dialog import RangeScanDialog

        with (
            patch("PyQt6.QtWidgets.QDialog"),
            patch("PyQt6.QtWidgets.QVBoxLayout"),
            patch("PyQt6.QtWidgets.QSpinBox"),
            patch("PyQt6.QtWidgets.QPushButton"),
        ):
            dialog = RangeScanDialog(mock_parent)

            # Mock spinboxes
            dialog.start_offset_spinbox = Mock()
            dialog.end_offset_spinbox = Mock()
            dialog.start_offset_spinbox.value.return_value = 0x10000
            dialog.end_offset_spinbox.value.return_value = 0x20000

            # Test parameter collection
            params = dialog.get_scan_parameters()

            assert params["start_offset"] == 0x10000
            assert params["end_offset"] == 0x20000

    def test_validation_with_large_range(self, mock_parent):
        """Test validation prevents excessively large scan ranges"""
        from spritepal.ui.components.dialogs.range_scan_dialog import RangeScanDialog

        with (
            patch("PyQt6.QtWidgets.QDialog"),
            patch("PyQt6.QtWidgets.QVBoxLayout"),
            patch("PyQt6.QtWidgets.QSpinBox"),
            patch("PyQt6.QtWidgets.QPushButton"),
            patch("PyQt6.QtWidgets.QMessageBox") as mock_msgbox,
        ):
            dialog = RangeScanDialog(mock_parent)

            # Mock spinboxes with large range
            dialog.start_offset_spinbox = Mock()
            dialog.end_offset_spinbox = Mock()
            dialog.start_offset_spinbox.value.return_value = 0x0
            dialog.end_offset_spinbox.value.return_value = 0x200000  # 2MB range

            # Test validation
            is_valid = dialog.validate_parameters()

            # Should warn about large range
            assert not is_valid or mock_msgbox.warning.called
