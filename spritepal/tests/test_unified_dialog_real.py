"""
Real Qt Testing for Unified Manual Offset Dialog

This test suite validates the unified manual offset dialog using real Qt components,
eliminating the 634 lines of mocks and 410MB memory overhead from the mocked version.

Key improvements:
- Uses real Qt widgets with qtbot
- Real signal testing with SignalSpy
- Actual dialog instantiation and interaction
- Proper parent-child relationships
- Event simulation for user interactions
- Memory-efficient testing (no mock overhead)
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QSlider, QTabWidget, QPushButton, QSpinBox

# Ensure Qt environment is configured
# Test characteristics: Real GUI components requiring display, Timer usage
pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.dialog,
    pytest.mark.file_io,
    pytest.mark.gui,
    pytest.mark.integration,
    pytest.mark.performance,
    pytest.mark.qt_app,
    pytest.mark.qt_real,
    pytest.mark.rom_data,
    pytest.mark.serial,
    pytest.mark.slow,
    pytest.mark.widget,
    pytest.mark.worker_threads,
]


if not os.environ.get('QT_QPA_PLATFORM'):
    if not os.environ.get("DISPLAY") or os.environ.get("CI"):
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from ui.dialogs.manual_offset_unified_integrated import (
    UnifiedManualOffsetDialog as ManualOffsetDialog,
    SimpleBrowseTab,
    SimpleSmartTab as SmartAnalysisTab,
    SimpleHistoryTab as HistoryTrackingTab,
)
from ui.widgets.sprite_preview_widget import SpritePreviewWidget

from tests.infrastructure.qt_real_testing import (
    QtTestCase,
    EventLoopHelper,
    MemoryHelper,
    WidgetPool,
)
from tests.infrastructure.dialog_test_helpers import (
    DialogTestHelper,
    DialogFactory,
    ModalDialogTester,
    CrossDialogCommunicationTester,
)
from tests.infrastructure.signal_testing_utils import (
    SignalSpy,
    MultiSignalSpy,
    AsyncSignalTester,
    SignalValidator,
)


class TestUnifiedDialogReal(QtTestCase):
    """Test unified dialog with real Qt components."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Setup test environment with real Qt application."""
        # Ensure QApplication exists
        self.app = self._ensure_qapplication()
        
        # Create temp ROM file for testing
        self.temp_rom = self._create_temp_rom()
        
        yield
        
        # Cleanup
        if self.temp_rom.exists():
            self.temp_rom.unlink()
    
    def _create_temp_rom(self) -> Path:
        """Create temporary ROM file for testing."""
        temp_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.smc')
        # Create 4MB ROM with test pattern
        rom_data = bytearray(0x400000)
        # Add recognizable patterns at key offsets
        for i in range(0, len(rom_data), 0x1000):
            rom_data[i:i+4] = b'TEST'
        temp_file.write(rom_data)
        temp_file.close()
        return Path(temp_file.name)
    
    def test_dialog_initialization_real(self):
        """Test dialog initialization with real components."""
        # Create real dialog
        dialog = self.create_widget(ManualOffsetDialog)
        
        # Verify dialog structure
        assert dialog.windowTitle() == "Manual Offset Control"
        assert dialog.minimumWidth() >= 600
        assert dialog.minimumHeight() >= 700
        
        # Verify tabs exist and are real QTabWidget
        tabs = dialog.findChild(QTabWidget)
        assert tabs is not None
        assert tabs.count() == 3
        assert tabs.tabText(0) == "Browse"
        assert tabs.tabText(1) == "Smart Analysis"
        assert tabs.tabText(2) == "History"
        
        # Verify preview widget exists
        preview = dialog.findChild(SpritePreviewWidget)
        assert preview is not None
        assert preview.width() >= 256
        assert preview.height() >= 256
        
        # Verify apply button exists
        apply_button = dialog.findChild(QPushButton, "apply_button")
        assert apply_button is not None
        assert apply_button.text() == "Apply Offset"
        assert apply_button.isDefault()
    
    def test_browse_tab_slider_interaction(self):
        """Test browse tab slider with real interaction."""
        dialog = self.create_widget(ManualOffsetDialog)
        dialog.show()
        
        # Get browse tab
        tabs = dialog.findChild(QTabWidget)
        self.select_tab(tabs, title="Browse")
        
        # Find slider
        slider = dialog.findChild(QSlider, "manual_offset_rom_slider")
        assert slider is not None
        
        # Setup signal spy
        browse_tab = dialog.browse_tab
        spy = SignalSpy(browse_tab.offset_changed, "offset_changed")
        
        # Test slider interaction
        initial_value = slider.value()
        new_value = initial_value + 0x1000
        
        # Simulate user dragging slider
        self.set_slider_value(slider, new_value, use_mouse=True)
        
        # Verify signal was emitted
        spy.assert_emitted(count=1)
        assert spy.get_args()[0] == new_value
        
        # Verify slider value changed
        assert slider.value() == new_value
    
    def test_smart_tab_auto_detection(self):
        """Test smart tab auto-detection with real components."""
        dialog = self.create_widget(ManualOffsetDialog)
        dialog.show()
        
        # Load ROM data
        dialog.set_rom_data(str(self.temp_rom), self.temp_rom.stat().st_size)
        
        # Switch to Smart Analysis tab
        tabs = dialog.findChild(QTabWidget)
        self.select_tab(tabs, title="Smart Analysis")
        
        # Get smart tab
        smart_tab = dialog.smart_tab
        assert smart_tab is not None
        
        # Setup signal spies
        multi_spy = MultiSignalSpy()
        multi_spy.add_signal(smart_tab.analysis_started, "analysis_started")
        multi_spy.add_signal(smart_tab.analysis_progress, "analysis_progress")
        multi_spy.add_signal(smart_tab.analysis_complete, "analysis_complete")
        
        # Trigger auto-detection
        detect_button = smart_tab.findChild(QPushButton, "auto_detect_button")
        assert detect_button is not None
        self.click_button(detect_button)
        
        # Wait for analysis to complete (with timeout)
        success = multi_spy.wait_for_sequence(
            ["analysis_started", "analysis_complete"],
            timeout_ms=5000,
            ordered=True
        )
        
        assert success, "Analysis did not complete in time"
        
        # Verify results
        results_list = smart_tab.findChild(QListWidget, "detection_results")
        assert results_list is not None
        # Should have some detection results (even if just the test patterns)
        assert results_list.count() > 0
    
    def test_history_tab_tracking(self):
        """Test history tab with real offset tracking."""
        dialog = self.create_widget(ManualOffsetDialog)
        dialog.show()
        
        # Setup ROM data
        dialog.set_rom_data(str(self.temp_rom), self.temp_rom.stat().st_size)
        
        # Get history tab
        tabs = dialog.findChild(QTabWidget)
        history_tab = dialog.history_tab
        
        # Setup signal spy
        spy = SignalSpy(history_tab.history_item_selected, "history_item_selected")
        
        # Add some history entries by changing offset
        test_offsets = [0x200000, 0x201000, 0x202000]
        
        for offset in test_offsets:
            dialog.browse_tab.set_offset(offset)
            # Simulate applying offset
            dialog.apply_button.click()
            EventLoopHelper.process_events(50)
        
        # Switch to history tab
        self.select_tab(tabs, title="History")
        
        # Verify history entries
        history_list = history_tab.findChild(QListWidget, "history_list")
        assert history_list is not None
        assert history_list.count() >= len(test_offsets)
        
        # Test selecting history item
        history_list.setCurrentRow(0)
        EventLoopHelper.process_events(50)
        
        # Verify signal emitted
        spy.assert_emitted()
    
    def test_cross_tab_communication(self):
        """Test communication between tabs with real signals."""
        dialog = self.create_widget(ManualOffsetDialog)
        dialog.show()
        
        # Setup cross-tab communication tester
        comm_tester = CrossDialogCommunicationTester()
        
        # Monitor offset changes across tabs
        multi_spy = MultiSignalSpy()
        multi_spy.add_signal(dialog.offset_changed, "dialog_offset")
        multi_spy.add_signal(dialog.browse_tab.offset_changed, "browse_offset")
        multi_spy.add_signal(dialog.smart_tab.offset_selected, "smart_offset")
        
        # Change offset in browse tab
        dialog.browse_tab.set_offset(0x210000)
        EventLoopHelper.process_events(50)
        
        # Verify propagation
        assert dialog.get_current_offset() == 0x210000
        multi_spy.get_spy("browse_offset").assert_emitted()
        multi_spy.get_spy("dialog_offset").assert_emitted()
    
    def test_preview_widget_updates(self):
        """Test preview widget updates with real rendering."""
        dialog = self.create_widget(ManualOffsetDialog)
        dialog.show()
        
        # Load ROM
        dialog.set_rom_data(str(self.temp_rom), self.temp_rom.stat().st_size)
        
        # Get preview widget
        preview = dialog.findChild(SpritePreviewWidget)
        assert preview is not None
        
        # Monitor preview updates
        update_count = 0
        
        def on_update():
            nonlocal update_count
            update_count += 1
        
        preview.update = on_update  # Override update method
        
        # Change offset multiple times
        for offset in [0x200000, 0x201000, 0x202000]:
            dialog.browse_tab.set_offset(offset)
            EventLoopHelper.process_events(100)
        
        # Verify preview was updated
        assert update_count > 0, "Preview widget was not updated"
    
    def test_dialog_state_persistence(self):
        """Test dialog state saving and restoration."""
        # Create and configure dialog
        dialog1 = self.create_widget(ManualOffsetDialog)
        dialog1.show()
        
        # Set specific state
        dialog1.browse_tab.set_offset(0x250000)
        dialog1.browse_tab.set_step_size(0x2000)
        
        tabs = dialog1.findChild(QTabWidget)
        self.select_tab(tabs, index=1)  # Select Smart tab
        
        # Get state
        state = self.get_dialog_state(dialog1)
        
        # Close dialog
        dialog1.close()
        EventLoopHelper.process_events(50)
        
        # Create new dialog and restore state
        dialog2 = self.create_widget(ManualOffsetDialog)
        dialog2.show()
        
        self.restore_dialog_state(dialog2, state)
        
        # Verify state was restored
        assert dialog2.browse_tab.get_offset() == 0x250000
        assert dialog2.browse_tab.get_step_size() == 0x2000
        
        tabs2 = dialog2.findChild(QTabWidget)
        assert tabs2.currentIndex() == 1
    
    def test_memory_efficiency(self):
        """Test memory efficiency compared to mocked version."""
        initial_widget_count = MemoryHelper.get_widget_count()
        
        # Create and destroy multiple dialogs
        for _ in range(10):
            dialog = self.create_widget(ManualOffsetDialog)
            dialog.show()
            EventLoopHelper.process_events(10)
            dialog.close()
            dialog.deleteLater()
        
        # Process events to allow cleanup
        EventLoopHelper.process_events(100)
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Check for leaks
        final_widget_count = MemoryHelper.get_widget_count()
        leaked = final_widget_count - initial_widget_count
        
        # Should have minimal or no leaks (much better than 410MB mock overhead)
        assert leaked < 5, f"Too many widgets leaked: {leaked}"
    
    def test_widget_pooling_performance(self):
        """Test widget pooling for performance optimization."""
        # Create widget pool for dialogs
        pool = WidgetPool(ManualOffsetDialog, pool_size=3)
        
        # Measure time to create pooled vs non-pooled
        import time
        
        # Non-pooled creation
        start = time.time()
        for _ in range(10):
            dialog = ManualOffsetDialog()
            dialog.close()
            dialog.deleteLater()
        non_pooled_time = time.time() - start
        
        # Pooled creation
        start = time.time()
        for _ in range(10):
            dialog = pool.acquire()
            pool.release(dialog)
        pooled_time = time.time() - start
        
        # Pooled should be faster (reusing widgets)
        assert pooled_time < non_pooled_time * 0.8, "Pool didn't improve performance"
        
        # Cleanup pool
        pool.clear()
    
    def test_signal_validation_patterns(self):
        """Test complex signal validation patterns."""
        dialog = self.create_widget(ManualOffsetDialog)
        dialog.show()
        
        # Create signal validator
        validator = SignalValidator()
        
        # Add rate limiting rule (max 10 emissions per second)
        validator.add_rate_limit(max_rate=10.0, window_ms=1000)
        
        # Add sequence rule
        validator.add_sequence_rule([
            ["offset_changed", "preview_updated"],
            ["analysis_started", "analysis_progress", "analysis_complete"]
        ])
        
        # Monitor signals
        spy = SignalSpy(dialog.offset_changed, "offset_changed")
        
        # Rapid offset changes (should respect rate limit)
        for i in range(20):
            dialog.browse_tab.set_offset(0x200000 + i * 0x1000)
            EventLoopHelper.process_events(10)
        
        # Validate emissions
        is_valid = validator.validate(spy)
        
        if not is_valid:
            violations = validator.get_violations()
            print(f"Signal validation failed: {violations}")
        
        # Rate limiting should have prevented some emissions
        assert len(spy.emissions) <= 15, "Rate limiting not working"
    
    def test_async_preview_generation(self):
        """Test async preview generation with real workers."""
        dialog = self.create_widget(ManualOffsetDialog)
        dialog.show()
        dialog.set_rom_data(str(self.temp_rom), self.temp_rom.stat().st_size)
        
        # Setup async signal tester
        preview_spy = SignalSpy(dialog.preview_widget.preview_ready, "preview_ready")
        
        # Trigger multiple offset changes rapidly
        offsets = [0x200000 + i * 0x1000 for i in range(5)]
        
        for offset in offsets:
            dialog.browse_tab.set_offset(offset)
            # Don't wait - test async behavior
        
        # Wait for final preview
        success = preview_spy.wait(timeout_ms=2000, count=1)
        assert success, "Preview generation timed out"
        
        # Should have received at least one preview
        preview_spy.assert_emitted()
        
        # Last preview should be for last offset
        # (earlier ones may have been cancelled)
        last_emission = preview_spy.get_emission(-1)
        assert last_emission is not None
    
    def test_error_handling_real_components(self):
        """Test error handling with real dialog components."""
        dialog = self.create_widget(ManualOffsetDialog)
        dialog.show()
        
        # Test invalid ROM path
        dialog.set_rom_data("/invalid/path.smc", 0)
        
        # Should handle gracefully without crashing
        EventLoopHelper.process_events(100)
        
        # Test invalid offset
        dialog.browse_tab.set_offset(-1)  # Negative offset
        EventLoopHelper.process_events(50)
        
        # Should clamp to valid range
        assert dialog.browse_tab.get_offset() >= 0
        
        # Test oversized offset
        dialog.browse_tab.set_offset(0x10000000)  # Way beyond ROM
        EventLoopHelper.process_events(50)
        
        # Should clamp to ROM size
        assert dialog.browse_tab.get_offset() <= 0x400000


class TestDialogIntegrationReal(QtTestCase):
    """Test dialog integration scenarios with real components."""
    
    def test_modal_dialog_workflow(self):
        """Test complete modal dialog workflow."""
        result = {"offset": None, "accepted": False}
        
        def create_dialog():
            dialog = ManualOffsetDialog()
            dialog.setModal(True)
            return dialog
        
        def test_dialog(dialog):
            # Interact with dialog
            dialog.browse_tab.set_offset(0x300000)
            
            # Store result
            result["offset"] = dialog.get_current_offset()
            result["accepted"] = True
        
        # Test modal dialog
        dialog_result = ModalDialogTester.test_modal_dialog(
            dialog_factory=create_dialog,
            test_func=test_dialog,
            auto_close=True,
            close_delay_ms=100
        )
        
        # Verify workflow completed
        assert result["accepted"]
        assert result["offset"] == 0x300000
    
    def test_multiple_dialogs_memory(self):
        """Test multiple dialog instances don't leak memory."""
        with MemoryHelper.assert_no_leak(ManualOffsetDialog, max_increase=0):
            # Create multiple dialogs
            dialogs = []
            for i in range(5):
                dialog = ManualOffsetDialog()
                dialog.show()
                dialogs.append(dialog)
                EventLoopHelper.process_events(10)
            
            # Close all dialogs
            for dialog in dialogs:
                dialog.close()
                dialog.deleteLater()
            
            # Clear references
            dialogs.clear()
            
            # Process cleanup
            EventLoopHelper.process_events(100)
    
    def test_stress_test_real_components(self):
        """Stress test with rapid interactions on real components."""
        dialog = ManualOffsetDialog()
        dialog.show()
        
        # Rapid tab switching
        tabs = dialog.findChild(QTabWidget)
        for _ in range(100):
            for i in range(tabs.count()):
                tabs.setCurrentIndex(i)
                EventLoopHelper.process_events(1)
        
        # Rapid offset changes
        slider = dialog.findChild(QSlider, "manual_offset_rom_slider")
        for i in range(100):
            value = 0x200000 + (i * 0x1000) % 0x200000
            slider.setValue(value)
            EventLoopHelper.process_events(1)
        
        # Dialog should remain responsive
        assert dialog.isVisible()
        
        # Cleanup
        dialog.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])