"""
Integration tests for smart offset control feature.
"""

import pytest

from spritepal.ui.components.panels.scan_controls_panel import ScanControlsPanel
from spritepal.ui.components.visualization.rom_map_widget import ROMMapWidget
from spritepal.ui.rom_extraction.widgets.manual_offset_widget import ManualOffsetWidget


class TestSmartModeIntegration:
    """Test the smart mode integration between widgets"""

    def test_manual_offset_widget_smart_mode_ui(self, qtbot):
        """Test that smart mode UI elements are created"""
        widget = ManualOffsetWidget()
        qtbot.addWidget(widget)
        widget.show()  # Ensure widget is shown for visibility tests

        # Check UI elements exist
        assert hasattr(widget, "smart_mode_checkbox")
        assert hasattr(widget, "region_indicator_label")
        assert hasattr(widget, "region_nav_widget")
        assert hasattr(widget, "prev_region_btn")
        assert hasattr(widget, "next_region_btn")
        assert hasattr(widget, "region_info_label")

        # Check initial state
        assert not widget.smart_mode_checkbox.isChecked()
        assert not widget.smart_mode_checkbox.isEnabled()  # Disabled until sprites detected
        assert widget.region_indicator_label.text() == "Linear Mode"
        assert not widget.region_nav_widget.isVisible()

    def test_sprite_regions_detection(self, qtbot):
        """Test sprite region detection from scan results"""
        widget = ManualOffsetWidget()
        qtbot.addWidget(widget)
        widget.show()  # Ensure widget is shown for visibility tests

        # Simulate sprite scan results
        sprites = [
            (0x100000, 0.8),
            (0x100100, 0.9),
            (0x100200, 0.7),
            # Gap
            (0x200000, 0.8),
            (0x200100, 0.9),
            # Gap
            (0x300000, 0.6),
            (0x300100, 0.7),
        ]

        # Set sprite regions
        widget.set_sprite_regions(sprites)

        # Check regions were detected
        regions = widget.get_sprite_regions()
        assert len(regions) > 0
        assert widget.smart_mode_checkbox.isEnabled()

        # Check auto-enable didn't trigger (only 7 sprites)
        assert not widget.smart_mode_checkbox.isChecked()

    def test_smart_mode_toggle(self, qtbot):
        """Test toggling smart mode on/off"""
        widget = ManualOffsetWidget()
        qtbot.addWidget(widget)
        widget.show()  # Ensure widget is shown for visibility tests

        # Setup sprites first
        sprites = [(0x100000 + i * 0x1000, 0.8) for i in range(20)]
        widget.set_sprite_regions(sprites)

        # Enable smart mode
        smart_mode_changed = []
        widget.smart_mode_changed.connect(lambda enabled: smart_mode_changed.append(enabled))

        widget.smart_mode_checkbox.setChecked(True)

        # Check UI updated
        assert widget._smart_mode_enabled
        assert "Smart Mode" in widget.region_indicator_label.text()
        assert widget.region_nav_widget.isVisible()
        assert len(smart_mode_changed) == 1
        assert smart_mode_changed[0] is True

        # Disable smart mode
        widget.smart_mode_checkbox.setChecked(False)

        assert not widget._smart_mode_enabled
        assert widget.region_indicator_label.text() == "Linear Mode"
        assert not widget.region_nav_widget.isVisible()
        assert len(smart_mode_changed) == 2
        assert smart_mode_changed[1] is False

    def test_region_navigation(self, qtbot):
        """Test navigating between regions"""
        widget = ManualOffsetWidget()
        qtbot.addWidget(widget)
        widget.show()  # Ensure widget is shown for visibility tests

        # Setup multiple regions
        sprites = []
        for region in range(3):
            base = 0x100000 * (region + 1)
            for i in range(5):
                sprites.append((base + i * 0x100, 0.8))

        widget.set_sprite_regions(sprites)

        # Track region changes (connect before enabling smart mode)
        region_changes = []
        widget.region_changed.connect(region_changes.append)

        widget.smart_mode_checkbox.setChecked(True)

        # Should start at region 0
        assert widget._current_region_index == 0

        # Navigate to next region
        widget._navigate_next_region()
        assert widget._current_region_index == 1
        assert len(region_changes) == 1  # Only navigation signal (already at region 0)

        # Navigate to next region again
        widget._navigate_next_region()
        assert widget._current_region_index == 2

        # Try to go beyond last region
        widget._navigate_next_region()
        assert widget._current_region_index == 2  # Should stay at last

        # Navigate back
        widget._navigate_prev_region()
        assert widget._current_region_index == 1

        widget._navigate_prev_region()
        assert widget._current_region_index == 0

        # Try to go before first region
        widget._navigate_prev_region()
        assert widget._current_region_index == 0  # Should stay at first

    def test_slider_mapping_smart_mode(self, qtbot):
        """Test slider to offset mapping in smart mode"""
        widget = ManualOffsetWidget()
        qtbot.addWidget(widget)
        widget.show()  # Ensure widget is shown for visibility tests

        # Setup regions
        sprites = [
            # Region 1: 0x100000-0x110000 (64KB)
            (0x100000, 0.8),
            (0x108000, 0.8),
            # Region 2: 0x200000-0x210000 (64KB)
            (0x200000, 0.8),
            (0x208000, 0.8),
        ]

        widget.set_sprite_regions(sprites)
        widget.smart_mode_checkbox.setChecked(True)

        # Test mapping at different slider positions
        # Slider at 0 should map to start of first region
        offset = widget._map_slider_to_offset(0)
        assert offset == 0x100000

        # Slider at max should map to end of last region
        slider_max = widget.offset_slider.maximum()
        offset = widget._map_slider_to_offset(slider_max)
        assert offset >= 0x200000  # Should be in or after last region

        # Test reverse mapping
        slider_pos = widget._map_offset_to_slider(0x100000)
        assert slider_pos == 0

        # Offset in second region should map to appropriate slider position
        slider_pos = widget._map_offset_to_slider(0x200000)
        assert slider_pos > 0
        assert slider_pos < slider_max

    def test_rom_map_region_visualization(self, qtbot):
        """Test ROM map widget region visualization"""
        rom_map = ROMMapWidget()
        qtbot.addWidget(rom_map)
        rom_map.show()  # Ensure widget is shown for visibility tests

        # Create dummy regions
        from spritepal.utils.sprite_regions import SpriteRegion
        regions = [
            SpriteRegion(
                region_id=0,
                start_offset=0x100000,
                end_offset=0x110000,
                sprite_offsets=[0x100000, 0x108000],
                sprite_qualities=[0.8, 0.8],
                average_quality=0.8,
                sprite_count=2,
                size_bytes=0x10000,
                density=0.125
            ),
            SpriteRegion(
                region_id=1,
                start_offset=0x200000,
                end_offset=0x210000,
                sprite_offsets=[0x200000, 0x208000],
                sprite_qualities=[0.8, 0.8],
                average_quality=0.8,
                sprite_count=2,
                size_bytes=0x10000,
                density=0.125
            ),
        ]

        # Set regions
        rom_map.set_sprite_regions(regions)
        assert len(rom_map.sprite_regions) == 2

        # Set current region
        rom_map.set_current_region(0)
        assert rom_map.current_region_index == 0

        # Toggle region highlighting
        rom_map.toggle_region_highlight(False)
        assert not rom_map.highlight_regions

        rom_map.toggle_region_highlight(True)
        assert rom_map.highlight_regions

        # Trigger paint event to ensure no crashes
        rom_map.update()

    def test_scan_controls_sprites_detected_signal(self, qtbot):
        """Test that scan controls emit sprites_detected signal"""
        panel = ScanControlsPanel()
        qtbot.addWidget(panel)
        panel.show()  # Ensure widget is shown for visibility tests

        # Track signal emissions
        sprites_detected = []
        panel.sprites_detected.connect(sprites_detected.append)

        # Simulate some found sprites
        panel.found_sprites = [
            (0x100000, 0.8),
            (0x200000, 0.9),
            (0x300000, 0.7),
        ]

        # Trigger finish scan
        panel._finish_scan()

        # Check signal was emitted with sprites
        assert len(sprites_detected) == 1
        assert len(sprites_detected[0]) == 3
        assert sprites_detected[0] == panel.found_sprites

    def test_full_integration_flow(self, qtbot):
        """Test the full integration flow from scan to smart navigation"""
        # Create widgets
        offset_widget = ManualOffsetWidget()
        rom_map = ROMMapWidget()
        qtbot.addWidget(offset_widget)
        qtbot.addWidget(rom_map)
        offset_widget.show()  # Ensure widgets are shown for visibility tests
        rom_map.show()

        # Simulate scan results being passed to offset widget
        scan_results = []
        for i in range(3):  # 3 regions
            base = 0x100000 * (i + 1)
            for j in range(5):  # 5 sprites per region
                scan_results.append((base + j * 0x1000, 0.8))

        # Process sprites
        offset_widget.set_sprite_regions(scan_results)
        regions = offset_widget.get_sprite_regions()

        # Update ROM map
        rom_map.set_sprite_regions(regions)

        # Enable smart mode
        offset_widget.smart_mode_checkbox.setChecked(True)

        # Verify integration
        assert offset_widget._smart_mode_enabled
        assert len(offset_widget._sprite_regions) == 3
        assert len(rom_map.sprite_regions) == 3

        # Navigate and verify ROM map updates
        offset_widget.region_changed.connect(
            lambda idx: rom_map.set_current_region(idx)
        )

        offset_widget._navigate_next_region()
        assert offset_widget._current_region_index == 1

        # Verify offset is in correct region
        current_offset = offset_widget.get_current_offset()
        region = offset_widget._sprite_regions[1]
        assert region.start_offset <= current_offset <= region.end_offset


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
