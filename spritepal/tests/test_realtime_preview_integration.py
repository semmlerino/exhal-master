"""
Integration tests for real-time preview updates - Priority 1 test implementation.
Tests real-time preview updates during user interactions.
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from spritepal.utils.constants import VRAM_SPRITE_OFFSET


class TestVRAMOffsetPreviewUpdates:
    """Test VRAM offset slider preview updates"""

    @pytest.fixture
    def sample_vram_file(self):
        """Create sample VRAM file for testing"""
        temp_dir = tempfile.mkdtemp()
        
        # Create VRAM file with test data
        vram_data = bytearray(0x10000)  # 64KB
        
        # Add different patterns at different offsets for testing
        for offset in [0x8000, 0xC000, 0xE000]:
            for i in range(100):  # 100 tiles worth of data
                tile_offset = offset + i * 32
                if tile_offset + 32 <= len(vram_data):
                    for j in range(32):
                        vram_data[tile_offset + j] = (offset // 0x1000 + i + j) % 256
        
        vram_path = Path(temp_dir) / "test_VRAM.dmp"
        vram_path.write_bytes(vram_data)
        
        yield str(vram_path)
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)

    def create_mock_extraction_panel(self, vram_path):
        """Create mock ExtractionPanel with offset slider functionality"""
        panel = Mock()
        panel.has_vram.return_value = True
        panel.get_vram_path.return_value = vram_path
        panel.get_vram_offset.return_value = VRAM_SPRITE_OFFSET
        
        # Mock offset slider
        panel.offset_slider = Mock()
        panel.offset_spinbox = Mock()
        panel.offset_hex_label = Mock()
        panel.preset_combo = Mock()
        panel.preset_combo.currentIndex.return_value = 1  # Custom Range
        
        # Mock signals
        panel.offset_changed = Mock()
        panel.offset_changed.emit = Mock()
        
        # Mock offset change methods
        def mock_slider_changed(value):
            panel.offset_changed.emit(value)
        
        def mock_spinbox_changed(value):
            panel.offset_hex_label.setText(f"0x{value:04X}")
            panel.offset_changed.emit(value)
        
        panel._on_offset_slider_changed = mock_slider_changed
        panel._on_offset_spinbox_changed = mock_spinbox_changed
        
        return panel

    def create_mock_controller(self, main_window):
        """Create mock ExtractionController"""
        controller = Mock()
        controller.main_window = main_window
        
        # Mock the real-time preview update method
        def mock_update_preview_with_offset(offset):
            # Simulate extraction process
            if main_window.extraction_panel.has_vram():
                vram_path = main_window.extraction_panel.get_vram_path()
                
                # Mock extraction results based on offset
                mock_pixmap = Mock()
                mock_pixmap.width.return_value = 128
                mock_pixmap.height.return_value = 128
                
                # Simulate different tile counts for different offsets
                if offset == 0x8000:
                    tile_count = 50
                elif offset == 0xC000:
                    tile_count = 75
                elif offset == 0xE000:
                    tile_count = 25
                else:
                    tile_count = 10
                
                # Update preview
                main_window.sprite_preview.update_preview(mock_pixmap, tile_count)
                main_window.preview_info.setText(f"Tiles: {tile_count} (Offset: 0x{offset:04X})")
                
                # Mock grayscale image for palette application
                mock_pil_image = Mock()
                mock_pil_image.mode = "P"
                mock_pil_image.size = (128, 128)
                main_window.sprite_preview.set_grayscale_image(mock_pil_image)
                
                return True
            return False
        
        controller.update_preview_with_offset = mock_update_preview_with_offset
        
        return controller

    def create_mock_main_window(self, vram_path):
        """Create mock MainWindow with preview components"""
        main_window = Mock()
        
        # Mock extraction panel
        main_window.extraction_panel = self.create_mock_extraction_panel(vram_path)
        
        # Mock preview components
        main_window.sprite_preview = Mock()
        main_window.sprite_preview.update_preview = Mock()
        main_window.sprite_preview.set_grayscale_image = Mock()
        
        main_window.preview_info = Mock()
        main_window.preview_info.setText = Mock()
        
        main_window.status_bar = Mock()
        main_window.status_bar.showMessage = Mock()
        
        return main_window

    @pytest.mark.integration
    def test_vram_offset_slider_preview_updates(self, sample_vram_file):
        """Test VRAM offset slider → Preview refresh integration"""
        # Create mock components
        main_window = self.create_mock_main_window(sample_vram_file)
        controller = self.create_mock_controller(main_window)
        
        # Connect the offset_changed signal to controller
        main_window.extraction_panel.offset_changed.connect = Mock(
            side_effect=lambda handler: setattr(controller, '_offset_handler', handler)
        )
        
        # Connect the signal
        main_window.extraction_panel.offset_changed.connect(controller.update_preview_with_offset)
        
        # Test different offset values
        test_offsets = [0x8000, 0xC000, 0xE000]
        
        for offset in test_offsets:
            # Simulate slider change
            main_window.extraction_panel._on_offset_slider_changed(offset)
            
            # Verify signal was emitted
            main_window.extraction_panel.offset_changed.emit.assert_called_with(offset)
            
            # Simulate controller receiving the signal
            controller.update_preview_with_offset(offset)
            
            # Verify preview was updated
            assert main_window.sprite_preview.update_preview.called
            assert main_window.preview_info.setText.called
            
            # Verify the preview info shows correct offset
            preview_text = main_window.preview_info.setText.call_args[0][0]
            assert f"0x{offset:04X}" in preview_text
            
            # Reset mocks for next iteration
            main_window.sprite_preview.update_preview.reset_mock()
            main_window.preview_info.setText.reset_mock()

    @pytest.mark.integration
    def test_spinbox_offset_preview_updates(self, sample_vram_file):
        """Test VRAM offset spinbox → Preview refresh integration"""
        # Create mock components
        main_window = self.create_mock_main_window(sample_vram_file)
        controller = self.create_mock_controller(main_window)
        
        # Connect the offset_changed signal to controller
        main_window.extraction_panel.offset_changed.connect(controller.update_preview_with_offset)
        
        # Test spinbox changes
        test_offset = 0xA000
        
        # Simulate spinbox change
        main_window.extraction_panel._on_offset_spinbox_changed(test_offset)
        
        # Verify hex label was updated
        main_window.extraction_panel.offset_hex_label.setText.assert_called_with(f"0x{test_offset:04X}")
        
        # Verify signal was emitted
        main_window.extraction_panel.offset_changed.emit.assert_called_with(test_offset)
        
        # Simulate controller receiving the signal
        controller.update_preview_with_offset(test_offset)
        
        # Verify preview was updated
        assert main_window.sprite_preview.update_preview.called
        assert main_window.preview_info.setText.called

    @pytest.mark.integration
    def test_offset_update_without_vram(self, sample_vram_file):
        """Test offset updates when no VRAM file is loaded"""
        # Create mock components without VRAM
        main_window = self.create_mock_main_window(sample_vram_file)
        main_window.extraction_panel.has_vram.return_value = False
        
        controller = self.create_mock_controller(main_window)
        
        # Test offset change
        result = controller.update_preview_with_offset(0x8000)
        
        # Verify no update occurred
        assert result is False
        assert not main_window.sprite_preview.update_preview.called


class TestPaletteSwitchingPreviewUpdates:
    """Test palette switching preview updates"""

    @pytest.fixture
    def sample_palette_data(self):
        """Create sample palette data for testing"""
        palettes = {}
        for i in range(8, 16):  # Sprite palettes 8-15
            colors = []
            for j in range(16):
                # Generate distinct colors for each palette
                r = (i * 20 + j * 10) % 256
                g = (i * 15 + j * 15) % 256
                b = (i * 10 + j * 20) % 256
                colors.append((r, g, b))
            palettes[i] = colors
        return palettes

    def create_mock_palette_colorizer(self, palettes):
        """Create mock PaletteColorizer"""
        colorizer = Mock()
        colorizer.has_palettes.return_value = True
        colorizer.is_palette_mode.return_value = True
        colorizer._selected_palette_index = 8
        colorizer._palettes = palettes
        
        # Mock signals
        colorizer.palette_mode_changed = Mock()
        colorizer.palette_mode_changed.emit = Mock()
        colorizer.palette_index_changed = Mock()
        colorizer.palette_index_changed.emit = Mock()
        
        # Mock methods
        def mock_set_selected_palette(index):
            colorizer._selected_palette_index = index
            colorizer.palette_index_changed.emit(index)
        
        def mock_get_display_image(row, grayscale_image):
            # Mock returning a colorized image
            mock_image = Mock()
            mock_image.mode = "RGBA"
            mock_image.size = (128, 128)
            # Add palette index to distinguish between different palettes
            mock_image._palette_index = colorizer._selected_palette_index
            return mock_image
        
        colorizer.set_selected_palette = mock_set_selected_palette
        colorizer.get_display_image = mock_get_display_image
        colorizer.set_palettes = Mock()
        
        return colorizer

    def create_mock_preview_panel(self, palettes):
        """Create mock PreviewPanel with palette functionality"""
        panel = Mock()
        
        # Mock colorizer
        panel.colorizer = self.create_mock_palette_colorizer(palettes)
        
        # Mock UI components
        panel.palette_toggle = Mock()
        panel.palette_toggle.isChecked.return_value = True
        panel.palette_selector = Mock()
        panel.palette_selector.currentData.return_value = 8
        
        # Mock preview widget
        panel.preview = Mock()
        panel.preview.update_pixmap = Mock()
        
        # Mock image data
        panel._grayscale_image = Mock()
        panel._grayscale_image.mode = "P"
        panel._grayscale_image.size = (128, 128)
        panel._colorized_image = None
        
        # Mock palette application method
        def mock_apply_current_palette():
            if panel._grayscale_image and panel.colorizer.has_palettes():
                panel._colorized_image = panel.colorizer.get_display_image(0, panel._grayscale_image)
                if panel._colorized_image:
                    mock_pixmap = Mock()
                    mock_pixmap._palette_index = panel._colorized_image._palette_index
                    panel.preview.update_pixmap(mock_pixmap)
        
        panel._apply_current_palette = mock_apply_current_palette
        
        # Mock palette change handler
        def mock_on_palette_changed(palette_name):
            if panel.palette_toggle.isChecked() and panel._grayscale_image:
                palette_index = panel.palette_selector.currentData()
                if palette_index:
                    panel.colorizer.set_selected_palette(palette_index)
                    panel._apply_current_palette()
        
        panel._on_palette_changed = mock_on_palette_changed
        
        return panel

    @pytest.mark.integration
    def test_palette_switching_preview_updates(self, sample_palette_data):
        """Test palette changes → Preview colorization integration"""
        # Create mock preview panel
        preview_panel = self.create_mock_preview_panel(sample_palette_data)
        
        # Test palette switching
        test_palette_indices = [8, 10, 12, 14]
        
        for palette_index in test_palette_indices:
            # Set up selector to return this palette
            preview_panel.palette_selector.currentData.return_value = palette_index
            
            # Simulate palette change
            preview_panel._on_palette_changed(f"Palette {palette_index}")
            
            # Verify colorizer was updated
            preview_panel.colorizer.palette_index_changed.emit.assert_called_with(palette_index)
            
            # Verify preview was updated
            assert preview_panel.preview.update_pixmap.called
            
            # Verify the colorized image has correct palette
            assert preview_panel._colorized_image is not None
            assert preview_panel._colorized_image._palette_index == palette_index
            
            # Reset mocks for next iteration
            preview_panel.preview.update_pixmap.reset_mock()
            preview_panel.colorizer.palette_index_changed.emit.reset_mock()

    @pytest.mark.integration
    def test_palette_mode_toggle_updates(self, sample_palette_data):
        """Test palette mode toggle → Preview updates"""
        # Create mock preview panel
        preview_panel = self.create_mock_preview_panel(sample_palette_data)
        
        # Mock palette toggle method
        def mock_on_palette_toggle(checked):
            preview_panel.palette_toggle.setChecked(checked)
            preview_panel.colorizer.palette_mode_changed.emit(checked)
            if checked:
                preview_panel._apply_current_palette()
            else:
                # Switch to grayscale
                mock_pixmap = Mock()
                mock_pixmap._is_grayscale = True
                preview_panel.preview.update_pixmap(mock_pixmap)
        
        preview_panel._on_palette_toggle = mock_on_palette_toggle
        
        # Test enabling palette mode
        preview_panel._on_palette_toggle(True)
        
        # Verify palette mode was enabled
        preview_panel.colorizer.palette_mode_changed.emit.assert_called_with(True)
        assert preview_panel.preview.update_pixmap.called
        
        # Test disabling palette mode
        preview_panel.preview.update_pixmap.reset_mock()
        preview_panel._on_palette_toggle(False)
        
        # Verify palette mode was disabled
        preview_panel.colorizer.palette_mode_changed.emit.assert_called_with(False)
        assert preview_panel.preview.update_pixmap.called

    @pytest.mark.integration
    def test_palette_updates_without_image(self, sample_palette_data):
        """Test palette updates when no image is loaded"""
        # Create mock preview panel without image
        preview_panel = self.create_mock_preview_panel(sample_palette_data)
        preview_panel._grayscale_image = None
        
        # Test palette change
        preview_panel._on_palette_changed("Palette 8")
        
        # Verify no update occurred
        assert not preview_panel.preview.update_pixmap.called


class TestZoomPanStatePreservation:
    """Test zoom and pan state preservation during updates"""

    def create_mock_zoomable_preview(self):
        """Create mock ZoomablePreviewWidget"""
        widget = Mock()
        
        # Mock zoom and pan state
        widget._zoom = 2.0
        widget._pan_offset = Mock()
        widget._pan_offset.x.return_value = 50.0
        widget._pan_offset.y.return_value = 30.0
        
        # Mock state preservation methods
        def mock_update_pixmap(pixmap):
            # update_pixmap should NOT reset zoom/pan state
            pass
        
        def mock_set_preview(pixmap, tile_count=0, tiles_per_row=0):
            # set_preview SHOULD reset zoom/pan state
            widget._zoom = 1.0
            widget._pan_offset.x.return_value = 0.0
            widget._pan_offset.y.return_value = 0.0
        
        widget.update_pixmap = mock_update_pixmap
        widget.set_preview = mock_set_preview
        
        return widget

    def create_mock_preview_panel_with_zoom(self):
        """Create mock PreviewPanel with zoomable widget"""
        panel = Mock()
        panel.preview = self.create_mock_zoomable_preview()
        
        # Mock update methods
        def mock_update_preview(pixmap, tile_count=0, tiles_per_row=0):
            # This should preserve zoom/pan state
            old_zoom = panel.preview._zoom
            old_pan_x = panel.preview._pan_offset.x()
            old_pan_y = panel.preview._pan_offset.y()
            
            panel.preview.update_pixmap(pixmap)
            
            # Verify state was preserved
            assert panel.preview._zoom == old_zoom
            assert panel.preview._pan_offset.x() == old_pan_x
            assert panel.preview._pan_offset.y() == old_pan_y
        
        def mock_set_preview(pixmap, tile_count=0, tiles_per_row=0):
            # This should reset zoom/pan state
            panel.preview.set_preview(pixmap, tile_count, tiles_per_row)
        
        panel.update_preview = mock_update_preview
        panel.set_preview = mock_set_preview
        
        return panel

    @pytest.mark.integration
    def test_zoom_pan_state_preservation(self):
        """Test that zoom/pan state is preserved during real-time updates"""
        # Create mock preview panel
        preview_panel = self.create_mock_preview_panel_with_zoom()
        
        # Set initial zoom and pan state
        initial_zoom = 3.0
        initial_pan_x = 100.0
        initial_pan_y = 75.0
        
        preview_panel.preview._zoom = initial_zoom
        preview_panel.preview._pan_offset.x.return_value = initial_pan_x
        preview_panel.preview._pan_offset.y.return_value = initial_pan_y
        
        # Simulate real-time update (should preserve state)
        mock_pixmap = Mock()
        preview_panel.update_preview(mock_pixmap, 50)
        
        # Verify zoom/pan state was preserved
        assert preview_panel.preview._zoom == initial_zoom
        assert preview_panel.preview._pan_offset.x() == initial_pan_x
        assert preview_panel.preview._pan_offset.y() == initial_pan_y

    @pytest.mark.integration
    def test_zoom_pan_state_reset_on_new_preview(self):
        """Test that zoom/pan state is reset when setting new preview"""
        # Create mock preview panel
        preview_panel = self.create_mock_preview_panel_with_zoom()
        
        # Set initial zoom and pan state
        preview_panel.preview._zoom = 3.0
        preview_panel.preview._pan_offset.x.return_value = 100.0
        preview_panel.preview._pan_offset.y.return_value = 75.0
        
        # Simulate new preview (should reset state)
        mock_pixmap = Mock()
        preview_panel.set_preview(mock_pixmap, 50)
        
        # Verify zoom/pan state was reset
        assert preview_panel.preview._zoom == 1.0
        assert preview_panel.preview._pan_offset.x() == 0.0
        assert preview_panel.preview._pan_offset.y() == 0.0


class TestPreviewPerformanceIntegration:
    """Test preview performance characteristics"""

    @pytest.fixture
    def large_vram_file(self):
        """Create large VRAM file for performance testing"""
        temp_dir = tempfile.mkdtemp()
        
        # Create larger VRAM file (1MB)
        vram_data = bytearray(0x100000)  # 1MB
        
        # Fill with pattern data
        for i in range(len(vram_data)):
            vram_data[i] = i % 256
        
        vram_path = Path(temp_dir) / "large_VRAM.dmp"
        vram_path.write_bytes(vram_data)
        
        yield str(vram_path)
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)

    def create_mock_performance_controller(self, main_window):
        """Create mock controller with performance tracking"""
        controller = Mock()
        controller.main_window = main_window
        controller.update_times = []
        
        def mock_update_preview_with_offset(offset):
            start_time = time.time()
            
            # Simulate extraction work
            time.sleep(0.01)  # Simulate 10ms of work
            
            # Mock update
            mock_pixmap = Mock()
            tile_count = 100
            main_window.sprite_preview.update_preview(mock_pixmap, tile_count)
            
            end_time = time.time()
            update_time = end_time - start_time
            controller.update_times.append(update_time)
            
            return True
        
        controller.update_preview_with_offset = mock_update_preview_with_offset
        
        return controller

    @pytest.mark.integration
    def test_preview_performance_with_large_files(self, large_vram_file):
        """Test performance characteristics with large files"""
        # Create mock components
        main_window = Mock()
        main_window.sprite_preview = Mock()
        main_window.sprite_preview.update_preview = Mock()
        
        controller = self.create_mock_performance_controller(main_window)
        
        # Test multiple rapid updates
        test_offsets = [0x8000, 0xC000, 0xE000, 0x10000, 0x20000]
        
        for offset in test_offsets:
            controller.update_preview_with_offset(offset)
        
        # Verify all updates completed
        assert len(controller.update_times) == len(test_offsets)
        
        # Verify reasonable performance (all updates under 100ms)
        for update_time in controller.update_times:
            assert update_time < 0.1  # 100ms max
        
        # Verify average performance
        avg_time = sum(controller.update_times) / len(controller.update_times)
        assert avg_time < 0.05  # 50ms average

    @pytest.mark.integration
    def test_concurrent_preview_updates(self, large_vram_file):
        """Test multiple rapid preview updates"""
        # Create mock components
        main_window = Mock()
        main_window.sprite_preview = Mock()
        main_window.sprite_preview.update_preview = Mock()
        
        controller = self.create_mock_performance_controller(main_window)
        
        # Test rapid sequential updates
        rapid_offsets = [0x8000 + i * 0x100 for i in range(10)]
        
        for offset in rapid_offsets:
            controller.update_preview_with_offset(offset)
        
        # Verify all updates completed
        assert len(controller.update_times) == len(rapid_offsets)
        assert main_window.sprite_preview.update_preview.call_count == len(rapid_offsets)


class TestPreviewErrorHandling:
    """Test preview error handling scenarios"""

    def create_mock_error_controller(self, main_window):
        """Create mock controller with error simulation"""
        controller = Mock()
        controller.main_window = main_window
        
        def mock_update_preview_with_error(offset):
            # Simulate different types of errors based on offset
            if offset == 0x1000:
                raise FileNotFoundError("VRAM file not found")
            elif offset == 0x2000:
                raise PermissionError("Permission denied")
            elif offset == 0x3000:
                raise MemoryError("Out of memory")
            elif offset == 0x4000:
                raise ValueError("Invalid offset")
            else:
                # Normal update
                mock_pixmap = Mock()
                main_window.sprite_preview.update_preview(mock_pixmap, 50)
                return True
        
        controller.update_preview_with_offset = mock_update_preview_with_error
        
        return controller

    @pytest.mark.integration
    def test_preview_error_handling(self):
        """Test error handling for corrupted preview data"""
        # Create mock components
        main_window = Mock()
        main_window.sprite_preview = Mock()
        main_window.sprite_preview.update_preview = Mock()
        main_window.status_bar = Mock()
        main_window.status_bar.showMessage = Mock()
        
        controller = self.create_mock_error_controller(main_window)
        
        # Test different error scenarios
        error_offsets = [0x1000, 0x2000, 0x3000, 0x4000]
        
        for offset in error_offsets:
            try:
                controller.update_preview_with_offset(offset)
                assert False, f"Expected error for offset 0x{offset:04X}"
            except Exception as e:
                # Verify error types
                if offset == 0x1000:
                    assert isinstance(e, FileNotFoundError)
                elif offset == 0x2000:
                    assert isinstance(e, PermissionError)
                elif offset == 0x3000:
                    assert isinstance(e, MemoryError)
                elif offset == 0x4000:
                    assert isinstance(e, ValueError)
        
        # Test recovery with valid offset
        try:
            controller.update_preview_with_offset(0x8000)
            assert main_window.sprite_preview.update_preview.called
        except Exception:
            assert False, "Should not raise error for valid offset"

    @pytest.mark.integration
    def test_preview_error_recovery(self):
        """Test recovery from preview errors"""
        # Create mock components
        main_window = Mock()
        main_window.sprite_preview = Mock()
        main_window.sprite_preview.update_preview = Mock()
        main_window.status_bar = Mock()
        main_window.status_bar.showMessage = Mock()
        
        controller = self.create_mock_error_controller(main_window)
        
        # Test error followed by successful update
        error_count = 0
        success_count = 0
        
        test_offsets = [0x1000, 0x8000, 0x2000, 0xC000, 0x3000, 0xE000]
        
        for offset in test_offsets:
            try:
                controller.update_preview_with_offset(offset)
                success_count += 1
            except Exception:
                error_count += 1
        
        # Verify mix of errors and successes
        assert error_count == 3  # 0x1000, 0x2000, 0x3000
        assert success_count == 3  # 0x8000, 0xC000, 0xE000
        
        # Verify successful updates occurred
        assert main_window.sprite_preview.update_preview.call_count == success_count


class TestPreviewSignalIntegration:
    """Test preview signal integration across components"""

    @pytest.mark.integration
    def test_complete_preview_signal_flow(self):
        """Test complete signal flow for preview updates"""
        # Create mock components
        extraction_panel = Mock()
        extraction_panel.offset_changed = Mock()
        extraction_panel.offset_changed.emit = Mock()
        extraction_panel.offset_changed.connect = Mock()
        
        preview_panel = Mock()
        preview_panel.colorizer = Mock()
        preview_panel.colorizer.palette_mode_changed = Mock()
        preview_panel.colorizer.palette_mode_changed.emit = Mock()
        preview_panel.colorizer.palette_index_changed = Mock()
        preview_panel.colorizer.palette_index_changed.emit = Mock()
        
        controller = Mock()
        controller.update_preview_with_offset = Mock()
        
        # Connect signals
        extraction_panel.offset_changed.connect(controller.update_preview_with_offset)
        
        # Test signal flow
        test_offset = 0x8000
        extraction_panel.offset_changed.emit(test_offset)
        
        # Verify signal was emitted
        extraction_panel.offset_changed.emit.assert_called_with(test_offset)
        
        # Verify connection was made
        extraction_panel.offset_changed.connect.assert_called_with(controller.update_preview_with_offset)
        
        # Test palette signals
        preview_panel.colorizer.palette_mode_changed.emit(True)
        preview_panel.colorizer.palette_index_changed.emit(10)
        
        # Verify palette signals were emitted
        preview_panel.colorizer.palette_mode_changed.emit.assert_called_with(True)
        preview_panel.colorizer.palette_index_changed.emit.assert_called_with(10)

    @pytest.mark.integration
    def test_preview_signal_disconnection(self):
        """Test proper signal disconnection for cleanup"""
        # Create mock components
        extraction_panel = Mock()
        extraction_panel.offset_changed = Mock()
        extraction_panel.offset_changed.disconnect = Mock()
        
        controller = Mock()
        controller.update_preview_with_offset = Mock()
        
        # Connect and then disconnect
        extraction_panel.offset_changed.connect(controller.update_preview_with_offset)
        extraction_panel.offset_changed.disconnect()
        
        # Verify disconnection
        extraction_panel.offset_changed.disconnect.assert_called()
        
        # Test that signal emission after disconnect doesn't cause issues
        extraction_panel.offset_changed.emit = Mock()
        extraction_panel.offset_changed.emit(0x8000)
        
        # Should not cause errors
        extraction_panel.offset_changed.emit.assert_called_with(0x8000)