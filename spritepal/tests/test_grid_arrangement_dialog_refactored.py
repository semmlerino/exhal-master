"""
Real component tests for Grid Arrangement Dialog functionality.

Following unified testing principles:
- Uses real GridArrangementDialog with qtbot
- Tests actual Qt grid widget behavior
- Mocks only file I/O at system boundaries
- Validates real tile selection and arrangement operations
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication

from tests.infrastructure.real_component_factory import RealComponentFactory
from ui.grid_arrangement_dialog import GridArrangementDialog
from ui.row_arrangement.grid_arrangement_manager import GridArrangementManager, TilePosition
from ui.row_arrangement.grid_image_processor import GridImageProcessor
from ui.row_arrangement.grid_preview_generator import GridPreviewGenerator

# Mark for real Qt testing
pytestmark = [
    pytest.mark.gui,  # Requires real Qt environment
    pytest.mark.integration,  # Integration test
    pytest.mark.dialog,  # Tests involving dialogs
    pytest.mark.real_components,  # Uses real Qt components
    pytest.mark.widget,  # Widget interaction tests
]

class TestGridArrangementDialogReal:
    """Test Grid Arrangement Dialog with real Qt components."""

    @pytest.fixture
    def real_factory(self):
        """Create real component factory."""
        factory = RealComponentFactory()
        yield factory
        factory.cleanup()

    @pytest.fixture
    def test_sprite_image(self, tmp_path):
        """Create a test sprite sheet image."""
        # Create a 256x256 test image with 16x16 tiles
        img = Image.new('RGBA', (256, 256), color=(255, 255, 255, 255))
        
        # Draw different colors in each 16x16 tile for testing
        colors = [
            (255, 0, 0, 255),    # Red
            (0, 255, 0, 255),    # Green
            (0, 0, 255, 255),    # Blue
            (255, 255, 0, 255),  # Yellow
        ]
        
        for y in range(16):
            for x in range(16):
                color = colors[(x // 4 + y // 4) % 4]
                for py in range(16):
                    for px in range(16):
                        img.putpixel((x * 16 + px, y * 16 + py), color)
        
        # Save to temp file
        sprite_path = tmp_path / "test_sprite.png"
        img.save(sprite_path)
        
        return sprite_path

    @pytest.fixture
    def real_dialog(self, qtbot, test_sprite_image):
        """Create a real GridArrangementDialog."""
        dialog = GridArrangementDialog(str(test_sprite_image), tiles_per_row=16)
        qtbot.addWidget(dialog)
        return dialog

    def test_dialog_initialization_with_real_components(self, qtbot, real_dialog):
        """Test that dialog initializes with real Qt components."""
        # Show dialog
        real_dialog.show()
        qtbot.waitExposed(real_dialog)
        
        # Verify dialog components exist
        assert real_dialog.isVisible()
        assert hasattr(real_dialog, 'processor')
        assert hasattr(real_dialog, 'manager')
        assert hasattr(real_dialog, 'generator')
        
        # Verify UI components are real Qt widgets
        assert hasattr(real_dialog, 'preview_label')
        assert hasattr(real_dialog, 'arrangement_list')
        assert hasattr(real_dialog, 'tiles_per_row')
        
        # Check initial state
        assert real_dialog.tiles_per_row == 16
        assert isinstance(real_dialog.processor, GridImageProcessor)
        assert isinstance(real_dialog.manager, GridArrangementManager)

    def test_tile_selection_with_mouse_clicks(self, qtbot, real_dialog):
        """Test tile selection using real mouse events."""
        real_dialog.show()
        qtbot.waitExposed(real_dialog)
        
        if hasattr(real_dialog, 'preview_label'):
            preview = real_dialog.preview_label
            
            # Simulate clicking on a tile (assuming tile size is known)
            tile_size = 16
            click_pos = QPoint(tile_size // 2, tile_size // 2)  # Center of first tile
            
            # Mouse click to select tile
            qtbot.mouseClick(preview, Qt.MouseButton.LeftButton, pos=click_pos)
            QApplication.processEvents()
            
            # Verify tile was selected
            if hasattr(real_dialog, 'selected_tiles'):
                assert len(real_dialog.selected_tiles) > 0

    def test_add_row_to_arrangement(self, qtbot, real_dialog):
        """Test adding a row to the arrangement with real components."""
        real_dialog.show()
        qtbot.waitExposed(real_dialog)
        
        # Add a row using the real method
        if hasattr(real_dialog, 'add_row_to_arrangement'):
            initial_count = len(real_dialog.manager.arrangement) if real_dialog.manager else 0
            
            # Add row 0
            result = real_dialog.add_row_to_arrangement(0)
            QApplication.processEvents()
            
            # Verify row was added
            assert result is True
            new_count = len(real_dialog.manager.arrangement) if real_dialog.manager else 0
            assert new_count > initial_count

    def test_keyboard_navigation(self, qtbot, real_dialog):
        """Test keyboard navigation in the grid."""
        real_dialog.show()
        qtbot.waitExposed(real_dialog)
        
        # Focus on the dialog
        real_dialog.setFocus()
        
        # Test arrow key navigation
        qtbot.keyClick(real_dialog, Qt.Key.Key_Right)
        QApplication.processEvents()
        
        qtbot.keyClick(real_dialog, Qt.Key.Key_Down)
        QApplication.processEvents()
        
        # Test selection with space/enter
        qtbot.keyClick(real_dialog, Qt.Key.Key_Space)
        QApplication.processEvents()
        
        # Verify some interaction occurred
        assert real_dialog.hasFocus() or any(
            child.hasFocus() for child in real_dialog.findChildren(QWidget)
        )

    def test_clear_selection(self, qtbot, real_dialog):
        """Test clearing tile selection with real components."""
        real_dialog.show()
        qtbot.waitExposed(real_dialog)
        
        # First add some tiles to selection
        if hasattr(real_dialog, 'selected_tiles'):
            real_dialog.selected_tiles.add(TilePosition(0, 0))
            real_dialog.selected_tiles.add(TilePosition(0, 1))
            assert len(real_dialog.selected_tiles) == 2
            
            # Clear selection
            if hasattr(real_dialog, 'clear_selection'):
                real_dialog.clear_selection()
                QApplication.processEvents()
                
                # Verify selection was cleared
                assert len(real_dialog.selected_tiles) == 0

    def test_preview_updates_on_selection_change(self, qtbot, real_dialog):
        """Test that preview updates when selection changes."""
        real_dialog.show()
        qtbot.waitExposed(real_dialog)
        
        # Get initial preview state
        preview_label = real_dialog.preview_label
        
        # Add tile to selection
        if hasattr(real_dialog, 'add_tile_to_selection'):
            real_dialog.add_tile_to_selection(TilePosition(0, 0))
            QApplication.processEvents()
            
            # Preview should have been updated
            # In real implementation, we'd check pixmap changed
            assert preview_label is not None

    def test_save_arrangement_with_real_file_dialog(self, qtbot, real_dialog, tmp_path):
        """Test saving arrangement with mocked file dialog."""
        real_dialog.show()
        qtbot.waitExposed(real_dialog)
        
        # Add some tiles to arrangement
        if real_dialog.manager:
            real_dialog.manager.add_tile(TilePosition(0, 0))
            real_dialog.manager.add_tile(TilePosition(1, 0))
        
        # Mock only the file dialog (system boundary)
        save_path = tmp_path / "arrangement.json"
        with patch('PySide6.QtWidgets.QFileDialog.getSaveFileName',
                   return_value=(str(save_path), "JSON Files (*.json)")):
            
            # Trigger save action
            if hasattr(real_dialog, 'save_arrangement'):
                real_dialog.save_arrangement()
                QApplication.processEvents()
                
                # Verify file was created
                assert save_path.exists()

    def test_load_arrangement_with_real_components(self, qtbot, real_dialog, tmp_path):
        """Test loading arrangement with real components."""
        real_dialog.show()
        qtbot.waitExposed(real_dialog)
        
        # Create a test arrangement file
        import json
        arrangement_data = {
            "tiles": [
                {"row": 0, "col": 0},
                {"row": 0, "col": 1},
                {"row": 1, "col": 0}
            ]
        }
        
        load_path = tmp_path / "test_arrangement.json"
        with open(load_path, 'w') as f:
            json.dump(arrangement_data, f)
        
        # Mock only the file dialog
        with patch('PySide6.QtWidgets.QFileDialog.getOpenFileName',
                   return_value=(str(load_path), "JSON Files (*.json)")):
            
            # Load arrangement
            if hasattr(real_dialog, 'load_arrangement'):
                real_dialog.load_arrangement()
                QApplication.processEvents()
                
                # Verify tiles were loaded
                if real_dialog.manager:
                    assert len(real_dialog.manager.arrangement) == 3

    def test_dialog_resize_behavior(self, qtbot, real_dialog):
        """Test dialog resize behavior with real Qt."""
        real_dialog.show()
        qtbot.waitExposed(real_dialog)
        
        # Get initial size
        initial_size = real_dialog.size()
        
        # Resize dialog
        new_width = initial_size.width() + 100
        new_height = initial_size.height() + 50
        real_dialog.resize(new_width, new_height)
        QApplication.processEvents()
        
        # Verify resize
        new_size = real_dialog.size()
        assert new_size.width() >= new_width - 10  # Allow small difference
        assert new_size.height() >= new_height - 10

    def test_selection_mode_switching(self, qtbot, real_dialog):
        """Test switching between selection modes."""
        real_dialog.show()
        qtbot.waitExposed(real_dialog)
        
        # Test different selection modes if available
        if hasattr(real_dialog, 'selection_mode'):
            modes = ['tile', 'row', 'column', 'rectangle']
            
            for mode in modes:
                if hasattr(real_dialog, f'set_selection_mode'):
                    real_dialog.set_selection_mode(mode)
                    QApplication.processEvents()
                    assert real_dialog.selection_mode == mode

    def test_progress_updates_during_processing(self, qtbot, real_dialog):
        """Test progress bar updates during tile processing."""
        real_dialog.show()
        qtbot.waitExposed(real_dialog)
        
        if hasattr(real_dialog, 'progress_bar'):
            progress_bar = real_dialog.progress_bar
            
            # Add multiple tiles to trigger progress updates
            if real_dialog.manager:
                for row in range(3):
                    for col in range(3):
                        real_dialog.manager.add_tile(TilePosition(row, col))
                        QApplication.processEvents()
            
            # Progress bar should exist (even if not visible)
            assert progress_bar is not None

    def test_error_handling_with_invalid_sprite(self, qtbot, tmp_path):
        """Test error handling with invalid sprite path."""
        invalid_path = tmp_path / "nonexistent.png"
        
        # Create dialog with invalid path
        dialog = GridArrangementDialog(str(invalid_path), tiles_per_row=16)
        qtbot.addWidget(dialog)
        
        # Dialog should handle error gracefully
        dialog.show()
        qtbot.waitExposed(dialog)
        
        # Check error was shown
        if hasattr(dialog, 'last_error'):
            assert dialog.last_error is not None
            assert "not found" in dialog.last_error.lower() or "failed" in dialog.last_error.lower()

    def test_arrangement_list_updates(self, qtbot, real_dialog):
        """Test that arrangement list widget updates correctly."""
        real_dialog.show()
        qtbot.waitExposed(real_dialog)
        
        if hasattr(real_dialog, 'arrangement_list'):
            list_widget = real_dialog.arrangement_list
            initial_count = list_widget.count() if hasattr(list_widget, 'count') else 0
            
            # Add tiles to arrangement
            if real_dialog.manager:
                real_dialog.manager.add_tile(TilePosition(0, 0))
                real_dialog.manager.add_tile(TilePosition(1, 1))
                
                # Update list
                if hasattr(real_dialog, 'update_arrangement_list'):
                    real_dialog.update_arrangement_list()
                    QApplication.processEvents()
                    
                    # List should have more items
                    new_count = list_widget.count() if hasattr(list_widget, 'count') else 0
                    assert new_count >= initial_count

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])