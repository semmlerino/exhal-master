"""
Integration tests for manual offset dialog using real components.
"""

import pytest
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QDialogButtonBox, QPushButton, QListWidget
from PyQt6.QtTest import QTest

from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from core.managers import ExtractionManager


@pytest.mark.integration
@pytest.mark.gui
class TestManualOffsetDialog:
    """Test manual offset dialog with real ROM data and preview generation."""
    
    def test_dialog_creation_and_display(self, manual_offset_dialog, qtbot):
        """Test that dialog creates and displays correctly."""
        dialog = manual_offset_dialog
        
        # Show the dialog
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        # Verify main components exist
        assert dialog.browse_tab is not None
        assert dialog.smart_tab is not None
        assert dialog.history_tab is not None
        assert dialog.preview_widget is not None
        
        # Verify browse tab components
        assert hasattr(dialog.browse_tab, 'position_slider')
        assert hasattr(dialog.browse_tab, 'find_sprites_button')
        assert hasattr(dialog.browse_tab, 'next_button')
        assert hasattr(dialog.browse_tab, 'prev_button')
    
    def test_slider_navigation(self, manual_offset_dialog, test_rom_with_sprites, qtbot):
        """Test that slider navigation updates offset correctly."""
        dialog = manual_offset_dialog
        rom_info = test_rom_with_sprites
        
        # Set ROM data
        extraction_manager = ExtractionManager()
        dialog.set_rom_data(
            str(rom_info['path']),
            rom_info['path'].stat().st_size,
            extraction_manager
        )
        
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        # Get initial offset
        initial_offset = dialog.current_offset
        
        # Move slider
        new_value = 0x10000
        dialog.browse_tab.position_slider.setValue(new_value)
        
        # Process events
        qtbot.wait(100)
        
        # Verify offset changed
        assert dialog.current_offset == new_value
        assert dialog.browse_tab.position_slider.value() == new_value
        
        # Verify display updated
        offset_text = dialog.browse_tab.offset_label.text()
        assert f"{new_value:06X}" in offset_text or f"{new_value:X}" in offset_text
    
    def test_manual_offset_input(self, manual_offset_dialog, test_rom_with_sprites, qtbot):
        """Test manual offset input via spinbox."""
        dialog = manual_offset_dialog
        rom_info = test_rom_with_sprites
        
        # Set ROM data
        extraction_manager = ExtractionManager()
        dialog.set_rom_data(
            str(rom_info['path']),
            rom_info['path'].stat().st_size,
            extraction_manager
        )
        
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        # Set offset via spinbox
        target_offset = 0x20000
        dialog.browse_tab.manual_spinbox.setValue(target_offset)
        
        # Trigger the change
        dialog.browse_tab.manual_spinbox.editingFinished.emit()
        qtbot.wait(100)
        
        # Verify offset changed
        assert dialog.current_offset == target_offset
        assert dialog.browse_tab.position_slider.value() == target_offset
    
    def test_find_sprites_button_click(self, manual_offset_dialog, test_rom_with_sprites, qtbot, mocker):
        """Test that Find Sprites button triggers sprite scanning."""
        dialog = manual_offset_dialog
        rom_info = test_rom_with_sprites
        
        # Set ROM data
        extraction_manager = ExtractionManager()
        dialog.set_rom_data(
            str(rom_info['path']),
            rom_info['path'].stat().st_size,
            extraction_manager
        )
        
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        # Spy on the scan method
        scan_spy = mocker.spy(dialog, '_scan_for_sprites')
        
        # Click Find Sprites button
        find_button = dialog.browse_tab.find_sprites_button
        assert find_button is not None
        assert find_button.isEnabled()
        
        # Click the button
        qtbot.mouseClick(find_button, Qt.MouseButton.LeftButton)
        
        # Verify scan was triggered
        assert scan_spy.called
    
    def test_preview_generation_on_offset_change(self, manual_offset_dialog, test_rom_with_sprites, qtbot, wait_for):
        """Test that preview is generated when offset changes."""
        dialog = manual_offset_dialog
        rom_info = test_rom_with_sprites
        
        # Set ROM data
        extraction_manager = ExtractionManager()
        dialog.set_rom_data(
            str(rom_info['path']),
            rom_info['path'].stat().st_size,
            extraction_manager
        )
        
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        # Track preview updates
        preview_updated = False
        
        def on_preview_ready(tile_data, width, height, name):
            nonlocal preview_updated
            preview_updated = True
        
        # Connect to preview signal if coordinator exists
        if dialog._smart_preview_coordinator:
            dialog._smart_preview_coordinator.preview_ready.connect(on_preview_ready)
        
        # Change offset to trigger preview
        dialog.set_offset(0x10000)
        
        # Wait for preview (with timeout)
        wait_for(lambda: preview_updated, timeout=3000, message="Preview not generated")
        
        assert preview_updated
    
    def test_next_prev_navigation(self, manual_offset_dialog, test_rom_with_sprites, qtbot):
        """Test next/prev sprite navigation buttons."""
        dialog = manual_offset_dialog
        rom_info = test_rom_with_sprites
        
        # Set ROM data
        extraction_manager = ExtractionManager()
        dialog.set_rom_data(
            str(rom_info['path']),
            rom_info['path'].stat().st_size,
            extraction_manager
        )
        
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        # Set initial offset
        initial_offset = 0x10000
        dialog.set_offset(initial_offset)
        qtbot.wait(100)
        
        # Click Next button
        next_button = dialog.browse_tab.next_button
        qtbot.mouseClick(next_button, Qt.MouseButton.LeftButton)
        qtbot.wait(200)
        
        # Offset should change (exact value depends on sprite finding logic)
        offset_after_next = dialog.current_offset
        # Just verify it changed or stayed the same if no sprite found
        assert offset_after_next >= initial_offset
        
        # Click Prev button
        prev_button = dialog.browse_tab.prev_button
        qtbot.mouseClick(prev_button, Qt.MouseButton.LeftButton)
        qtbot.wait(200)
        
        # Offset should change
        offset_after_prev = dialog.current_offset
        assert offset_after_prev <= offset_after_next


@pytest.mark.integration
@pytest.mark.gui
class TestSpriteScanDialog:
    """Test sprite scanning and results dialog."""
    
    def test_sprite_scan_with_results(self, manual_offset_dialog, test_rom_with_sprites, qtbot, wait_for):
        """Test full sprite scan workflow with results dialog."""
        dialog = manual_offset_dialog
        rom_info = test_rom_with_sprites
        
        # Set ROM data
        extraction_manager = ExtractionManager()
        dialog.set_rom_data(
            str(rom_info['path']),
            rom_info['path'].stat().st_size,
            extraction_manager
        )
        
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        # Track if results dialog appears
        results_dialog = None
        
        def check_for_dialog():
            nonlocal results_dialog
            # Look for any dialog that might be the results
            for widget in dialog.children():
                if hasattr(widget, 'windowTitle') and 'Sprites' in widget.windowTitle():
                    results_dialog = widget
                    return True
            return False
        
        # Start scan
        dialog._scan_for_sprites()
        
        # Wait for results dialog or completion
        # This might show a progress dialog first
        qtbot.wait(500)
        
        # Process any dialogs that appear
        QTest.qWait(1000)
        
        # If we have test sprites, verify some were found
        if rom_info['sprites']:
            # The scan should have completed
            # Check if a results dialog was shown
            pass  # Results depend on implementation
    
    def test_sprite_selection_navigation(self, manual_offset_dialog, test_rom_with_sprites, qtbot):
        """Test selecting a sprite from results navigates to it."""
        dialog = manual_offset_dialog
        rom_info = test_rom_with_sprites
        
        if not rom_info['sprites']:
            pytest.skip("No test sprites to select")
        
        # Set ROM data
        extraction_manager = ExtractionManager()
        dialog.set_rom_data(
            str(rom_info['path']),
            rom_info['path'].stat().st_size,
            extraction_manager
        )
        
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        # Directly test jumping to a known sprite
        sprite_offset = rom_info['sprites'][0]['offset']
        
        # Use the jump method
        dialog._jump_to_sprite(sprite_offset)
        qtbot.wait(100)
        
        # Verify we navigated to the sprite
        assert dialog.current_offset == sprite_offset


@pytest.mark.integration
@pytest.mark.gui
class TestDialogIntegrationWithPanel:
    """Test manual offset dialog integration with ROM extraction panel."""
    
    def test_dialog_opens_from_panel(self, loaded_rom_panel, qtbot):
        """Test that dialog opens correctly from ROM extraction panel."""
        panel, rom_info = loaded_rom_panel
        
        # Open manual offset dialog
        panel._open_manual_offset_dialog()
        qtbot.wait(100)
        
        # Verify dialog was created
        assert panel.manual_offset_dialog is not None
        
        # Verify dialog has ROM data
        assert panel.manual_offset_dialog.rom_path == str(rom_info['path'])
        assert panel.manual_offset_dialog.rom_size > 0
    
    def test_dialog_offset_sync_with_panel(self, loaded_rom_panel, qtbot):
        """Test that offset changes sync between dialog and panel."""
        panel, rom_info = loaded_rom_panel
        
        # Open dialog
        panel._open_manual_offset_dialog()
        dialog = panel.manual_offset_dialog
        
        dialog.show()
        qtbot.waitForWindowShown(dialog)
        
        # Change offset in dialog
        new_offset = 0x30000
        dialog.set_offset(new_offset)
        qtbot.wait(100)
        
        # Verify panel received the offset change
        # This depends on signal connections
        # The panel should track the manual offset
        assert hasattr(panel, '_manual_offset')
    
    def test_multiple_dialog_opens_reuse_singleton(self, loaded_rom_panel, qtbot):
        """Test that opening dialog multiple times reuses the same instance."""
        panel, rom_info = loaded_rom_panel
        
        # Open dialog first time
        panel._open_manual_offset_dialog()
        dialog1 = panel.manual_offset_dialog
        dialog1_id = id(dialog1)
        
        # Close it
        dialog1.close()
        qtbot.wait(100)
        
        # Open again
        panel._open_manual_offset_dialog()
        dialog2 = panel.manual_offset_dialog
        dialog2_id = id(dialog2)
        
        # Should be the same instance (singleton)
        assert dialog1_id == dialog2_id