"""
Integration tests for ManualOffsetDialogSingleton signal behavior.

This module tests the singleton pattern implementation and its impact on
signal/slot connections, ensuring:
- Singleton properly maintains single instance
- Signals are not duplicated across multiple access attempts
- Thread safety of singleton access
- Proper cleanup and reconnection behavior
"""
from __future__ import annotations

import gc
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import QApplication

from ui.rom_extraction_panel import ROMExtractionPanel, ManualOffsetDialogSingleton
from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from utils.logging_config import get_logger

logger = get_logger(__name__)

class SignalMonitor(QObject):
    """Monitor for tracking signal emissions from the singleton dialog."""
    
    def __init__(self):
        super().__init__()
        self.offset_changes: list[int] = []
        self.sprite_finds: list[tuple] = []
        self.emission_times: list[float] = []
        self.emission_threads: list[int] = []
        
    @Slot(int)
    def on_offset_changed(self, offset: int):
        """Track offset changes."""
        self.offset_changes.append(offset)
        self.emission_times.append(time.time())
        self.emission_threads.append(threading.get_ident())
        logger.debug(f"Monitor: offset_changed({offset})")
        
    @Slot(int, str)
    def on_sprite_found(self, offset: int, name: str):
        """Track sprite found events."""
        self.sprite_finds.append((offset, name))
        self.emission_times.append(time.time())
        self.emission_threads.append(threading.get_ident())
        logger.debug(f"Monitor: sprite_found({offset}, {name})")
        
    def reset(self):
        """Reset all tracked data."""
        self.offset_changes.clear()
        self.sprite_finds.clear()
        self.emission_times.clear()
        self.emission_threads.clear()
        
    def get_stats(self) -> dict:
        """Get statistics about tracked signals."""
        return {
            'offset_count': len(self.offset_changes),
            'sprite_count': len(self.sprite_finds),
            'total_emissions': len(self.emission_times),
            'unique_threads': len(set(self.emission_threads)),
            'time_span': max(self.emission_times) - min(self.emission_times) if self.emission_times else 0
        }

@pytest.fixture
def cleanup_singleton():
    """Ensure singleton is cleaned up after each test."""
    yield
    # Force cleanup of singleton
    ManualOffsetDialogSingleton._instance = None
    ManualOffsetDialogSingleton._lock = threading.Lock()
    gc.collect()

@pytest.fixture
def temp_rom():
    """Create a temporary ROM file."""
    with tempfile.NamedTemporaryFile(suffix='.sfc', delete=False) as f:
        f.write(b'\x00' * 0x8000)
        path = f.name
    yield path
    try:
        import os
        os.unlink(path)
    except Exception as e:
        # Caught exception during operation
        pass
@pytest.mark.gui
class TestSingletonBehavior:
    """Test the singleton pattern implementation."""
    
    def test_singleton_returns_same_instance(self, qtbot, cleanup_singleton):
        """Test that singleton always returns the same instance."""
        # Create first panel
        panel1 = ROMExtractionPanel()
        qtbot.addWidget(panel1)
        
        # Get first dialog instance
        dialog1 = ManualOffsetDialogSingleton.get_dialog(panel1)
        assert dialog1 is not None
        
        # Create second panel
        panel2 = ROMExtractionPanel()
        qtbot.addWidget(panel2)
        
        # Get second dialog instance
        dialog2 = ManualOffsetDialogSingleton.get_dialog(panel2)
        
        # Should be the same instance
        assert dialog1 is dialog2
        
        # Get from singleton directly
        dialog3 = ManualOffsetDialogSingleton.get_current_dialog()
        assert dialog1 is dialog3
        
    def test_singleton_thread_safety(self, qtbot, cleanup_singleton):
        """Test thread-safe access to singleton."""
        panel = ROMExtractionPanel()
        qtbot.addWidget(panel)
        
        dialogs = []
        errors = []
        
        def get_dialog_in_thread():
            try:
                dialog = ManualOffsetDialogSingleton.get_dialog(panel)
                return dialog
            except Exception as e:
                errors.append(e)
                return None
                
        # Try to get dialog from multiple threads simultaneously
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_dialog_in_thread) for _ in range(10)]
            
            for future in as_completed(futures):
                dialog = future.result()
                if dialog:
                    dialogs.append(dialog)
                    
        # No errors should occur
        assert len(errors) == 0
        
        # All should be the same instance
        if dialogs:
            first = dialogs[0]
            for dialog in dialogs[1:]:
                assert dialog is first
                
    def test_singleton_persistence_check(self, qtbot, cleanup_singleton):
        """Test singleton persistence checking methods."""
        # Initially no dialog exists
        assert not ManualOffsetDialogSingleton.is_dialog_open()
        assert ManualOffsetDialogSingleton.get_current_dialog() is None
        
        # Create panel and get dialog
        panel = ROMExtractionPanel()
        qtbot.addWidget(panel)
        dialog = ManualOffsetDialogSingleton.get_dialog(panel)
        
        # Now dialog exists but not shown
        assert ManualOffsetDialogSingleton.get_current_dialog() is not None
        assert not ManualOffsetDialogSingleton.is_dialog_open()
        
        # Show dialog
        dialog.show()
        qtbot.wait(50)
        
        # Now dialog is open
        assert ManualOffsetDialogSingleton.is_dialog_open()
        
        # Hide dialog
        dialog.hide()
        qtbot.wait(50)
        
        # Dialog exists but not open
        assert ManualOffsetDialogSingleton.get_current_dialog() is not None
        assert not ManualOffsetDialogSingleton.is_dialog_open()

@pytest.mark.gui
class TestSingletonSignalConnections:
    """Test signal connections through singleton pattern."""
    
    @patch('ui.rom_extraction_panel.get_extraction_manager')
    def test_single_connection_multiple_panels(self, mock_manager, qtbot, cleanup_singleton, temp_rom):
        """Test that signals are connected only once despite multiple panels."""
        mock_manager.return_value = MagicMock()
        
        # Create monitor
        monitor = SignalMonitor()
        
        # Create multiple panels
        panels = []
        for i in range(3):
            panel = ROMExtractionPanel()
            panel.rom_path = temp_rom
            panel.rom_size = 0x8000
            qtbot.addWidget(panel)
            panels.append(panel)
            
            # Each panel opens the dialog
            panel._open_manual_offset_dialog()
            
        # Get the singleton dialog
        dialog = ManualOffsetDialogSingleton.get_current_dialog()
        assert dialog is not None
        
        # Connect monitor to dialog signals
        dialog.offset_changed.connect(monitor.on_offset_changed)
        
        # Emit signal once
        dialog.offset_changed.emit(0x1000)
        qtbot.wait(50)
        
        # Should receive exactly one signal
        assert len(monitor.offset_changes) == 1
        assert monitor.offset_changes[0] == 0x1000
        
    @patch('ui.rom_extraction_panel.get_extraction_manager')
    def test_panel_signal_handlers_unique(self, mock_manager, qtbot, cleanup_singleton, temp_rom):
        """Test each panel's signal handlers are properly connected."""
        mock_manager.return_value = MagicMock()
        
        # Create two panels with ROM loaded
        panel1 = ROMExtractionPanel()
        panel1.rom_path = temp_rom
        panel1.rom_size = 0x8000
        qtbot.addWidget(panel1)
        
        panel2 = ROMExtractionPanel()
        panel2.rom_path = temp_rom
        panel2.rom_size = 0x8000
        qtbot.addWidget(panel2)
        
        # Track handler calls
        panel1_calls = []
        panel2_calls = []
        
        original_handler1 = panel1._on_dialog_offset_changed
        original_handler2 = panel2._on_dialog_offset_changed
        
        def track_panel1(offset):
            panel1_calls.append(offset)
            original_handler1(offset)
            
        def track_panel2(offset):
            panel2_calls.append(offset)
            original_handler2(offset)
            
        panel1._on_dialog_offset_changed = track_panel1
        panel2._on_dialog_offset_changed = track_panel2
        
        # Open dialog from both panels
        panel1._open_manual_offset_dialog()
        panel2._open_manual_offset_dialog()
        
        # Get singleton dialog
        dialog = ManualOffsetDialogSingleton.get_current_dialog()
        
        # Emit signal
        dialog.offset_changed.emit(0x2000)
        qtbot.wait(100)
        
        # Both panels should receive the signal
        assert 0x2000 in panel1_calls
        assert 0x2000 in panel2_calls
        
        # Each should receive it exactly once
        assert panel1_calls.count(0x2000) == 1
        assert panel2_calls.count(0x2000) == 1

@pytest.mark.gui
class TestSingletonLifecycle:
    """Test singleton lifecycle and cleanup."""
    
    @patch('ui.rom_extraction_panel.get_extraction_manager')
    def test_dialog_survives_panel_deletion(self, mock_manager, qtbot, cleanup_singleton, temp_rom):
        """Test dialog survives when creating panel is deleted."""
        mock_manager.return_value = MagicMock()
        
        # Create panel and get dialog
        panel = ROMExtractionPanel()
        panel.rom_path = temp_rom
        panel.rom_size = 0x8000
        qtbot.addWidget(panel)
        
        panel._open_manual_offset_dialog()
        dialog = ManualOffsetDialogSingleton.get_current_dialog()
        
        # Connect monitor to verify signals still work
        monitor = SignalMonitor()
        dialog.offset_changed.connect(monitor.on_offset_changed)
        
        # Delete the panel
        panel.deleteLater()
        qtbot.wait(100)
        
        # Dialog should still exist
        assert ManualOffsetDialogSingleton.get_current_dialog() is not None
        
        # Signals should still work
        dialog.offset_changed.emit(0x3000)
        qtbot.wait(50)
        
        assert len(monitor.offset_changes) == 1
        assert monitor.offset_changes[0] == 0x3000
        
    def test_reconnection_after_reset(self, qtbot, cleanup_singleton):
        """Test reconnection works after singleton reset."""
        # Create first dialog
        panel1 = ROMExtractionPanel()
        qtbot.addWidget(panel1)
        dialog1 = ManualOffsetDialogSingleton.get_dialog(panel1)
        
        # Monitor first dialog
        monitor1 = SignalMonitor()
        dialog1.offset_changed.connect(monitor1.on_offset_changed)
        
        # Emit and verify
        dialog1.offset_changed.emit(0x1000)
        qtbot.wait(50)
        assert monitor1.offset_changes == [0x1000]
        
        # Force reset singleton
        ManualOffsetDialogSingleton._instance = None
        
        # Create new dialog
        panel2 = ROMExtractionPanel()
        qtbot.addWidget(panel2)
        dialog2 = ManualOffsetDialogSingleton.get_dialog(panel2)
        
        # Should be different instance
        assert dialog2 is not dialog1
        
        # Monitor new dialog
        monitor2 = SignalMonitor()
        dialog2.offset_changed.connect(monitor2.on_offset_changed)
        
        # Emit and verify new dialog works
        dialog2.offset_changed.emit(0x2000)
        qtbot.wait(50)
        assert monitor2.offset_changes == [0x2000]
        
        # Old monitor should not receive new signal
        assert monitor1.offset_changes == [0x1000]  # No change

@pytest.mark.gui
class TestSingletonSignalIntegrity:
    """Test signal integrity through singleton lifecycle."""
    
    @patch('ui.rom_extraction_panel.get_extraction_manager')
    def test_rapid_hide_show_signal_integrity(self, mock_manager, qtbot, cleanup_singleton, temp_rom):
        """Test signals remain intact through rapid hide/show cycles."""
        mock_manager.return_value = MagicMock()
        
        panel = ROMExtractionPanel()
        panel.rom_path = temp_rom
        panel.rom_size = 0x8000
        qtbot.addWidget(panel)
        
        panel._open_manual_offset_dialog()
        dialog = ManualOffsetDialogSingleton.get_current_dialog()
        
        monitor = SignalMonitor()
        dialog.offset_changed.connect(monitor.on_offset_changed)
        
        # Rapid hide/show cycles with signal emissions
        for i in range(5):
            dialog.show()
            qtbot.wait(20)
            dialog.offset_changed.emit(i * 1000)
            qtbot.wait(20)
            dialog.hide()
            qtbot.wait(20)
            
        # All signals should be received
        assert len(monitor.offset_changes) == 5
        assert monitor.offset_changes == [0, 1000, 2000, 3000, 4000]
        
    @patch('ui.rom_extraction_panel.get_extraction_manager')
    def test_concurrent_signal_emissions(self, mock_manager, qtbot, cleanup_singleton, temp_rom):
        """Test concurrent signal emissions from multiple sources."""
        mock_manager.return_value = MagicMock()
        
        # Create multiple panels
        panels = []
        for i in range(3):
            panel = ROMExtractionPanel()
            panel.rom_path = temp_rom
            panel.rom_size = 0x8000
            qtbot.addWidget(panel)
            panels.append(panel)
            panel._open_manual_offset_dialog()
            
        dialog = ManualOffsetDialogSingleton.get_current_dialog()
        monitor = SignalMonitor()
        
        # Connect monitor
        dialog.offset_changed.connect(monitor.on_offset_changed)
        dialog.sprite_found.connect(monitor.on_sprite_found)
        
        # Emit different signals rapidly
        for i in range(10):
            dialog.offset_changed.emit(i * 100)
            if i % 2 == 0:
                dialog.sprite_found.emit(i * 100, f"sprite_{i}")
                
        qtbot.wait(100)
        
        # Verify all signals received
        assert len(monitor.offset_changes) == 10
        assert len(monitor.sprite_finds) == 5
        
        # Verify order preserved
        assert monitor.offset_changes == [i * 100 for i in range(10)]
        assert monitor.sprite_finds == [(i * 100, f"sprite_{i}") for i in range(0, 10, 2)]
        
    def test_signal_uniqueness_verification(self, qtbot, cleanup_singleton):
        """Test that Qt.UniqueConnection prevents duplicate connections."""
        panel = ROMExtractionPanel()
        qtbot.addWidget(panel)
        
        dialog = ManualOffsetDialogSingleton.get_dialog(panel)
        monitor = SignalMonitor()
        
        # Try to connect multiple times with UniqueConnection
        for _ in range(5):
            dialog.offset_changed.connect(
                monitor.on_offset_changed,
                Qt.ConnectionType.UniqueConnection
            )
            
        # Emit once
        dialog.offset_changed.emit(0x5000)
        qtbot.wait(50)
        
        # Should only receive once despite multiple connection attempts
        assert len(monitor.offset_changes) == 1
        assert monitor.offset_changes[0] == 0x5000

@pytest.mark.gui
class TestSingletonErrorConditions:
    """Test error conditions and edge cases."""
    
    def test_dialog_creation_failure_handling(self, qtbot, cleanup_singleton):
        """Test handling of dialog creation failures."""
        
        # Mock dialog creation to fail
        with patch('ui.rom_extraction_panel.UnifiedManualOffsetDialog') as MockDialog:
            MockDialog.side_effect = Exception("Creation failed")
            
            panel = ROMExtractionPanel()
            qtbot.addWidget(panel)
            
            # Should handle the error gracefully
            with pytest.raises(Exception):
                ManualOffsetDialogSingleton.get_dialog(panel)
                
            # Singleton should not be in broken state
            assert ManualOffsetDialogSingleton.get_current_dialog() is None
            
    def test_signal_emission_after_deletion(self, qtbot, cleanup_singleton):
        """Test that signal emission after deletion doesn't crash."""
        panel = ROMExtractionPanel()
        qtbot.addWidget(panel)
        
        dialog = ManualOffsetDialogSingleton.get_dialog(panel)
        monitor = SignalMonitor()
        
        # Connect monitor
        dialog.offset_changed.connect(monitor.on_offset_changed)
        
        # Emit to verify connection
        dialog.offset_changed.emit(0x1000)
        qtbot.wait(50)
        assert len(monitor.offset_changes) == 1
        
        # Schedule dialog deletion
        dialog.deleteLater()
        qtbot.wait(200)  # Wait for deletion
        
        # Singleton should handle this
        assert ManualOffsetDialogSingleton.get_current_dialog() is None
        
        # Creating new dialog should work
        new_dialog = ManualOffsetDialogSingleton.get_dialog(panel)
        assert new_dialog is not None
        assert new_dialog is not dialog  # Different instance

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])