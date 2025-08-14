"""
Integration tests for Qt signal/slot connections in SpritePal.

This module tests the critical signal/slot connections between UnifiedManualOffsetDialog
and ROMExtractionPanel, ensuring proper:
- Signal emission and reception
- Parameter types and values
- Connection timing and order
- Thread safety
- Connection lifecycle management
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, List, Optional, Tuple
from unittest.mock import MagicMock, Mock, patch

import pytest
from PySide6.QtCore import QObject, QThread, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtTest import QSignalSpy

from tests.infrastructure.qt_testing_framework import QtTestingFramework
from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from ui.rom_extraction_panel import ROMExtractionPanel, ManualOffsetDialogSingleton
from utils.logging_config import get_logger

logger = get_logger(__name__)


@pytest.fixture
def qt_framework():
    """Provide Qt testing framework."""
    return QtTestingFramework()


@pytest.fixture
def temp_rom_file():
    """Create a temporary ROM file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.sfc', delete=False) as f:
        # Write minimal ROM header
        f.write(b'\x00' * 0x8000)  # 32KB of zeros
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except:
        pass


@pytest.fixture
def mock_extraction_manager():
    """Create a mock extraction manager."""
    manager = MagicMock()
    manager.extract_sprite = MagicMock(return_value=(None, None))
    manager.get_sprite_at_offset = MagicMock(return_value=None)
    return manager


class SignalRecorder(QObject):
    """Helper class to record signal emissions with parameters."""
    
    def __init__(self):
        super().__init__()
        self.emissions: List[Tuple[str, tuple, float]] = []
        self.lock = QThread.currentThread()  # Thread safety check
        
    @Slot(int)
    def record_offset_changed(self, offset: int):
        """Record offset_changed signal."""
        self._record_signal('offset_changed', (offset,))
        
    @Slot(int, str)
    def record_sprite_found(self, offset: int, name: str):
        """Record sprite_found signal."""
        self._record_signal('sprite_found', (offset, name))
        
    def _record_signal(self, signal_name: str, args: tuple):
        """Record a signal emission with timestamp."""
        # Verify we're in the correct thread
        current_thread = QThread.currentThread()
        if current_thread != self.lock:
            logger.warning(f"Signal {signal_name} received in different thread!")
        
        timestamp = time.time()
        self.emissions.append((signal_name, args, timestamp))
        logger.debug(f"Recorded signal: {signal_name}{args} at {timestamp}")
        
    def clear(self):
        """Clear recorded emissions."""
        self.emissions.clear()
        
    def get_emissions(self, signal_name: Optional[str] = None) -> List[Tuple[tuple, float]]:
        """Get emissions for a specific signal or all."""
        if signal_name:
            return [(args, ts) for name, args, ts in self.emissions if name == signal_name]
        return [(args, ts) for _, args, ts in self.emissions]
        
    def count(self, signal_name: Optional[str] = None) -> int:
        """Count emissions for a specific signal or all."""
        if signal_name:
            return sum(1 for name, _, _ in self.emissions if name == signal_name)
        return len(self.emissions)


@pytest.mark.gui
class TestDialogSignalConnections:
    """Test UnifiedManualOffsetDialog signal connections."""
    
    def test_dialog_signals_exist(self, qtbot):
        """Test that dialog has required signals."""
        dialog = UnifiedManualOffsetDialog(None)
        qtbot.addWidget(dialog)
        
        # Check signals exist
        assert hasattr(dialog, 'offset_changed')
        assert hasattr(dialog, 'sprite_found')
        
        # Check they are Qt signals
        assert isinstance(dialog.offset_changed, Signal)
        assert isinstance(dialog.sprite_found, Signal)
        
    def test_offset_changed_emission(self, qtbot):
        """Test offset_changed signal is emitted with correct value."""
        dialog = UnifiedManualOffsetDialog(None)
        qtbot.addWidget(dialog)
        
        # Create signal spy
        with qtbot.waitSignal(dialog.offset_changed, timeout=1000) as blocker:
            # Trigger offset change
            dialog.set_offset(0x1000)
            
        # Verify signal was emitted with correct value
        assert blocker.args == [0x1000]
        
    def test_sprite_found_emission(self, qtbot):
        """Test sprite_found signal is emitted with correct parameters."""
        dialog = UnifiedManualOffsetDialog(None)
        qtbot.addWidget(dialog)
        
        # Create signal spy
        with qtbot.waitSignal(dialog.sprite_found, timeout=1000) as blocker:
            # Trigger sprite found (simulate Apply button)
            dialog._apply_offset()
            
        # Verify signal was emitted with offset and name
        assert len(blocker.args) == 2
        assert isinstance(blocker.args[0], int)  # offset
        assert isinstance(blocker.args[1], str)  # sprite name
        
    def test_multiple_rapid_emissions(self, qtbot):
        """Test handling of multiple rapid signal emissions."""
        dialog = UnifiedManualOffsetDialog(None)
        qtbot.addWidget(dialog)
        
        recorder = SignalRecorder()
        dialog.offset_changed.connect(recorder.record_offset_changed)
        
        # Emit multiple signals rapidly
        offsets = [0x1000, 0x2000, 0x3000, 0x4000, 0x5000]
        for offset in offsets:
            dialog.set_offset(offset)
            
        # Process events to ensure all signals are delivered
        qtbot.wait(100)
        
        # Verify all signals were received
        emissions = recorder.get_emissions('offset_changed')
        received_offsets = [args[0] for args, _ in emissions]
        assert received_offsets == offsets
        
    def test_signal_connection_types(self, qtbot):
        """Test different Qt connection types for cross-thread safety."""
        dialog = UnifiedManualOffsetDialog(None)
        qtbot.addWidget(dialog)
        
        recorder = SignalRecorder()
        
        # Test AutoConnection (default)
        dialog.offset_changed.connect(recorder.record_offset_changed)
        
        # Test QueuedConnection (for cross-thread)
        dialog.sprite_found.connect(
            recorder.record_sprite_found, 
            Qt.ConnectionType.QueuedConnection
        )
        
        # Emit signals
        dialog.set_offset(0x1000)
        dialog._apply_offset()
        
        # Wait for queued connections
        qtbot.wait(100)
        
        # Verify both signals received
        assert recorder.count('offset_changed') == 1
        assert recorder.count('sprite_found') == 1


@pytest.mark.gui
class TestPanelSignalReception:
    """Test ROMExtractionPanel signal reception and handling."""
    
    @patch('ui.rom_extraction_panel.get_extraction_manager')
    def test_panel_connects_to_dialog_signals(self, mock_get_manager, qtbot, temp_rom_file):
        """Test that panel properly connects to dialog signals."""
        mock_get_manager.return_value = MagicMock()
        
        # Create panel
        panel = ROMExtractionPanel()
        qtbot.addWidget(panel)
        
        # Set ROM to enable dialog
        panel.rom_path = temp_rom_file
        panel.rom_size = 32768
        
        # Open dialog (creates connections)
        panel._open_manual_offset_dialog()
        
        # Get dialog instance
        dialog = ManualOffsetDialogSingleton.get_current_dialog()
        assert dialog is not None
        
        # Check connections exist
        # Note: Qt doesn't provide a direct way to check connections,
        # so we test by emitting and checking handler calls
        with patch.object(panel, '_on_dialog_offset_changed') as mock_handler:
            dialog.offset_changed.emit(0x2000)
            qtbot.wait(50)  # Allow signal delivery
            mock_handler.assert_called_once_with(0x2000)
            
    @patch('ui.rom_extraction_panel.get_extraction_manager')
    def test_panel_updates_on_offset_changed(self, mock_get_manager, qtbot, temp_rom_file):
        """Test that panel updates correctly when offset_changed is received."""
        mock_get_manager.return_value = MagicMock()
        
        panel = ROMExtractionPanel()
        qtbot.addWidget(panel)
        
        panel.rom_path = temp_rom_file
        panel.rom_size = 32768
        
        # Open dialog
        panel._open_manual_offset_dialog()
        dialog = ManualOffsetDialogSingleton.get_current_dialog()
        
        # Emit offset change
        test_offset = 0x3456
        dialog.offset_changed.emit(test_offset)
        qtbot.wait(50)
        
        # Verify panel state updated
        assert panel._manual_offset == test_offset
        assert f"0x{test_offset:06X}" in panel.manual_offset_status.text()
        
    @patch('ui.rom_extraction_panel.get_extraction_manager')
    def test_panel_handles_sprite_found(self, mock_get_manager, qtbot, temp_rom_file):
        """Test that panel handles sprite_found signal correctly."""
        mock_get_manager.return_value = MagicMock()
        
        panel = ROMExtractionPanel()
        qtbot.addWidget(panel)
        
        panel.rom_path = temp_rom_file
        panel.rom_size = 32768
        
        # Open dialog
        panel._open_manual_offset_dialog()
        dialog = ManualOffsetDialogSingleton.get_current_dialog()
        
        # Emit sprite found
        test_offset = 0x4000
        test_name = "test_sprite"
        dialog.sprite_found.emit(test_offset, test_name)
        qtbot.wait(50)
        
        # Verify panel state
        assert panel._manual_offset == test_offset
        assert "Selected sprite" in panel.manual_offset_status.text()
        assert f"0x{test_offset:06X}" in panel.manual_offset_status.text()


@pytest.mark.gui
class TestSignalConnectionLifecycle:
    """Test signal connection lifecycle and cleanup."""
    
    @patch('ui.rom_extraction_panel.get_extraction_manager')
    def test_no_duplicate_connections(self, mock_get_manager, qtbot, temp_rom_file):
        """Test that repeated dialog opens don't create duplicate connections."""
        mock_get_manager.return_value = MagicMock()
        
        panel = ROMExtractionPanel()
        qtbot.addWidget(panel)
        
        panel.rom_path = temp_rom_file
        panel.rom_size = 32768
        
        recorder = SignalRecorder()
        
        # Open dialog multiple times
        for _ in range(3):
            panel._open_manual_offset_dialog()
            dialog = ManualOffsetDialogSingleton.get_current_dialog()
            
            # Connect our recorder (simulating what might happen with duplicate connections)
            try:
                dialog.offset_changed.disconnect()
            except:
                pass  # No connections to disconnect
            dialog.offset_changed.connect(recorder.record_offset_changed)
            
            # Hide dialog (simulate closing)
            dialog.hide()
            
        # Now emit signal once
        dialog = ManualOffsetDialogSingleton.get_current_dialog()
        dialog.offset_changed.emit(0x5000)
        qtbot.wait(50)
        
        # Should only have one emission despite multiple opens
        assert recorder.count('offset_changed') == 1
        
    @patch('ui.rom_extraction_panel.get_extraction_manager')
    def test_signals_work_after_hide_show(self, mock_get_manager, qtbot, temp_rom_file):
        """Test signals still work after dialog is hidden and shown again."""
        mock_get_manager.return_value = MagicMock()
        
        panel = ROMExtractionPanel()
        qtbot.addWidget(panel)
        
        panel.rom_path = temp_rom_file
        panel.rom_size = 32768
        
        # Open dialog
        panel._open_manual_offset_dialog()
        dialog = ManualOffsetDialogSingleton.get_current_dialog()
        
        # Record initial emission
        with patch.object(panel, '_on_dialog_offset_changed') as mock_handler:
            dialog.offset_changed.emit(0x1000)
            qtbot.wait(50)
            assert mock_handler.call_count == 1
            
        # Hide and show dialog
        dialog.hide()
        qtbot.wait(100)
        dialog.show()
        qtbot.wait(100)
        
        # Test emission after hide/show
        with patch.object(panel, '_on_dialog_offset_changed') as mock_handler:
            dialog.offset_changed.emit(0x2000)
            qtbot.wait(50)
            assert mock_handler.call_count == 1
            
    def test_signal_cleanup_on_dialog_deletion(self, qtbot):
        """Test that signals are properly cleaned up when dialog is deleted."""
        # Create dialog and recorder
        dialog = UnifiedManualOffsetDialog(None)
        qtbot.addWidget(dialog)
        
        recorder = SignalRecorder()
        dialog.offset_changed.connect(recorder.record_offset_changed)
        
        # Emit signal to verify connection
        dialog.offset_changed.emit(0x1000)
        qtbot.wait(50)
        assert recorder.count() == 1
        
        # Delete dialog
        dialog.deleteLater()
        qtbot.wait(100)  # Wait for deletion
        
        # Recorder should still exist but no more signals
        assert recorder.count() == 1  # No new signals after deletion


@pytest.mark.gui
class TestCrossWidgetCoordination:
    """Test signal coordination between multiple widgets."""
    
    @patch('ui.rom_extraction_panel.get_extraction_manager')
    def test_dialog_panel_preview_coordination(self, mock_get_manager, qtbot, temp_rom_file):
        """Test coordination between dialog, panel, and preview widgets."""
        mock_get_manager.return_value = MagicMock()
        
        panel = ROMExtractionPanel()
        qtbot.addWidget(panel)
        
        panel.rom_path = temp_rom_file
        panel.rom_size = 32768
        
        # Open dialog
        panel._open_manual_offset_dialog()
        dialog = ManualOffsetDialogSingleton.get_current_dialog()
        
        # Track signal flow
        signal_flow = []
        
        def track_offset_change(offset):
            signal_flow.append(('panel_offset_changed', offset))
            panel._on_dialog_offset_changed(offset)  # Call original
            
        def track_sprite_found(offset, name):
            signal_flow.append(('panel_sprite_found', offset, name))
            panel._on_dialog_sprite_found(offset, name)  # Call original
            
        # Patch handlers to track flow
        with patch.object(panel, '_on_dialog_offset_changed', track_offset_change):
            with patch.object(panel, '_on_dialog_sprite_found', track_sprite_found):
                # Simulate user interaction flow
                dialog.set_offset(0x1000)
                qtbot.wait(50)
                
                dialog._apply_offset()
                qtbot.wait(50)
                
        # Verify signal flow order
        assert len(signal_flow) >= 2
        assert signal_flow[0][0] == 'panel_offset_changed'
        assert signal_flow[-1][0] == 'panel_sprite_found'
        
    @patch('ui.rom_extraction_panel.get_extraction_manager')
    def test_multiple_panels_single_dialog(self, mock_get_manager, qtbot, temp_rom_file):
        """Test that singleton dialog works correctly with multiple panels."""
        mock_get_manager.return_value = MagicMock()
        
        # Create two panels
        panel1 = ROMExtractionPanel()
        panel2 = ROMExtractionPanel()
        qtbot.addWidget(panel1)
        qtbot.addWidget(panel2)
        
        # Set ROM for both
        for panel in [panel1, panel2]:
            panel.rom_path = temp_rom_file
            panel.rom_size = 32768
            
        # Open dialog from panel1
        panel1._open_manual_offset_dialog()
        dialog1 = ManualOffsetDialogSingleton.get_current_dialog()
        
        # Open dialog from panel2 (should be same instance)
        panel2._open_manual_offset_dialog()
        dialog2 = ManualOffsetDialogSingleton.get_current_dialog()
        
        # Verify singleton
        assert dialog1 is dialog2
        
        # Emit signal and verify both panels receive it
        test_offset = 0x5000
        with patch.object(panel1, '_on_dialog_offset_changed') as mock1:
            with patch.object(panel2, '_on_dialog_offset_changed') as mock2:
                dialog1.offset_changed.emit(test_offset)
                qtbot.wait(100)
                
                # Both should receive the signal
                mock1.assert_called_with(test_offset)
                mock2.assert_called_with(test_offset)


@pytest.mark.gui
class TestThreadSafetyAndTiming:
    """Test thread safety and timing of signal emissions."""
    
    def test_signal_thread_affinity(self, qtbot):
        """Test that signals are emitted and received in correct threads."""
        dialog = UnifiedManualOffsetDialog(None)
        qtbot.addWidget(dialog)
        
        main_thread = QThread.currentThread()
        emission_thread = None
        reception_thread = None
        
        @Slot(int)
        def check_thread(offset):
            nonlocal reception_thread
            reception_thread = QThread.currentThread()
            
        dialog.offset_changed.connect(check_thread)
        
        # Emit from main thread
        emission_thread = QThread.currentThread()
        dialog.offset_changed.emit(0x1000)
        qtbot.wait(50)
        
        # Both should be in main thread for GUI operations
        assert emission_thread == main_thread
        assert reception_thread == main_thread
        
    def test_worker_thread_signal_emission(self, qtbot):
        """Test signal emission from worker thread to main thread."""
        dialog = UnifiedManualOffsetDialog(None)
        qtbot.addWidget(dialog)
        
        main_thread = QThread.currentThread()
        worker_emissions = []
        main_receptions = []
        
        class Worker(QObject):
            def __init__(self, dialog):
                super().__init__()
                self.dialog = dialog
                
            @Slot()
            def do_work(self):
                # This runs in worker thread
                worker_thread = QThread.currentThread()
                worker_emissions.append(worker_thread)
                
                # Emit signal from worker thread
                self.dialog.offset_changed.emit(0x2000)
                
        @Slot(int)
        def receive_in_main(offset):
            main_receptions.append(QThread.currentThread())
            
        # Connect to receive in main thread
        dialog.offset_changed.connect(receive_in_main, Qt.ConnectionType.QueuedConnection)
        
        # Create worker and thread
        worker = Worker(dialog)
        thread = QThread()
        worker.moveToThread(thread)
        
        # Connect and start
        thread.started.connect(worker.do_work)
        thread.start()
        
        # Wait for completion
        qtbot.wait(200)
        thread.quit()
        thread.wait()
        
        # Verify cross-thread signal delivery
        assert len(worker_emissions) == 1
        assert len(main_receptions) == 1
        assert worker_emissions[0] != main_thread  # Emitted from worker
        assert main_receptions[0] == main_thread   # Received in main
        
    def test_signal_emission_timing(self, qtbot):
        """Test timing and order of signal emissions."""
        dialog = UnifiedManualOffsetDialog(None)
        qtbot.addWidget(dialog)
        
        recorder = SignalRecorder()
        dialog.offset_changed.connect(recorder.record_offset_changed)
        dialog.sprite_found.connect(recorder.record_sprite_found)
        
        # Emit signals with timing
        start_time = time.time()
        
        dialog.offset_changed.emit(0x1000)
        qtbot.wait(50)
        
        dialog.offset_changed.emit(0x2000)
        qtbot.wait(50)
        
        dialog.sprite_found.emit(0x2000, "sprite_1")
        qtbot.wait(50)
        
        # Verify order and timing
        emissions = recorder.emissions
        assert len(emissions) == 3
        
        # Check order
        assert emissions[0][0] == 'offset_changed'
        assert emissions[1][0] == 'offset_changed'
        assert emissions[2][0] == 'sprite_found'
        
        # Check timing (should be sequential)
        for i in range(1, len(emissions)):
            assert emissions[i][2] > emissions[i-1][2]  # Later timestamp
            
    def test_high_frequency_emissions(self, qtbot):
        """Test handling of high-frequency signal emissions."""
        dialog = UnifiedManualOffsetDialog(None)
        qtbot.addWidget(dialog)
        
        received_count = 0
        
        @Slot(int)
        def count_receptions(offset):
            nonlocal received_count
            received_count += 1
            
        dialog.offset_changed.connect(count_receptions)
        
        # Emit many signals rapidly
        emission_count = 100
        for i in range(emission_count):
            dialog.offset_changed.emit(i * 100)
            
        # Process all events
        qtbot.wait(500)
        
        # All signals should be received
        assert received_count == emission_count


@pytest.mark.gui
class TestSignalBlockingAndError:
    """Test signal blocking and error conditions."""
    
    def test_blocked_signals(self, qtbot):
        """Test that blocked signals are not emitted."""
        dialog = UnifiedManualOffsetDialog(None)
        qtbot.addWidget(dialog)
        
        recorder = SignalRecorder()
        dialog.offset_changed.connect(recorder.record_offset_changed)
        
        # Block signals
        dialog.blockSignals(True)
        
        # Try to emit
        dialog.offset_changed.emit(0x1000)
        qtbot.wait(50)
        
        # Should not receive
        assert recorder.count() == 0
        
        # Unblock and emit
        dialog.blockSignals(False)
        dialog.offset_changed.emit(0x2000)
        qtbot.wait(50)
        
        # Now should receive
        assert recorder.count() == 1
        
    def test_exception_in_slot(self, qtbot):
        """Test that exceptions in slots don't break signal system."""
        dialog = UnifiedManualOffsetDialog(None)
        qtbot.addWidget(dialog)
        
        call_count = 0
        
        @Slot(int)
        def faulty_slot(offset):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Test exception")
                
        @Slot(int)
        def good_slot(offset):
            nonlocal call_count
            call_count += 10
            
        # Connect both slots
        dialog.offset_changed.connect(faulty_slot)
        dialog.offset_changed.connect(good_slot)
        
        # Emit signal
        dialog.offset_changed.emit(0x1000)
        qtbot.wait(50)
        
        # Both slots should be called despite exception
        assert call_count >= 11  # 1 from faulty, 10 from good
        
        # Emit again - faulty slot won't raise this time
        dialog.offset_changed.emit(0x2000)
        qtbot.wait(50)
        
        assert call_count >= 23  # 2 from faulty, 20 from good
        
    def test_deleted_receiver(self, qtbot):
        """Test that deleted receivers don't cause crashes."""
        dialog = UnifiedManualOffsetDialog(None)
        qtbot.addWidget(dialog)
        
        # Create receiver that will be deleted
        class Receiver(QObject):
            received = False
            
            @Slot(int)
            def receive(self, offset):
                Receiver.received = True
                
        receiver = Receiver()
        dialog.offset_changed.connect(receiver.receive)
        
        # Emit with valid receiver
        dialog.offset_changed.emit(0x1000)
        qtbot.wait(50)
        assert Receiver.received
        
        # Delete receiver
        Receiver.received = False
        receiver.deleteLater()
        qtbot.wait(100)
        
        # Emit again - should not crash
        dialog.offset_changed.emit(0x2000)
        qtbot.wait(50)
        
        # Should not have been received
        assert not Receiver.received


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])