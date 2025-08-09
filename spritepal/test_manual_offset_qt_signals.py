#!/usr/bin/env python3
"""
Test script to verify Qt signal/slot connections in manual offset dialog.
This tests the fixes for black flashing boxes during slider dragging.
"""

import sys
import os
from pathlib import Path

# Add spritepal to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from core.managers.extraction_manager import ExtractionManager
from utils.logging_config import get_logger

logger = get_logger(__name__)

def test_manual_offset_signals():
    """Test Qt signal connections and preview updates."""
    app = QApplication([])
    
    # Initialize managers
    from core.managers import initialize_managers
    initialize_managers()
    
    # Create dialog
    dialog = UnifiedManualOffsetDialog()
    
    # Create mock extraction manager
    class MockExtractor:
        def __init__(self):
            self.rom_injector = None
    
    class MockExtractionManager:
        def __init__(self):
            self.rom_path = "test.smc"
            self.rom_size = 0x400000
            self._extractor = MockExtractor()
        
        def get_rom_extractor(self):
            return self._extractor
    
    # Set up dialog with mock data
    manager = MockExtractionManager()
    dialog.set_rom_data(manager.rom_path, manager.rom_size, manager)
    
    # Show dialog
    dialog.show()
    
    # Test signal flow
    test_results = []
    
    def check_coordinator():
        """Check if coordinator is properly connected."""
        coordinator = dialog._smart_preview_coordinator
        if coordinator:
            test_results.append("✓ SmartPreviewCoordinator created")
            
            # Check if slider is connected
            if dialog.browse_tab and dialog.browse_tab.position_slider:
                slider = dialog.browse_tab.position_slider
                
                # Check signal connections by inspecting receivers
                # Note: PyQt6 doesn't expose receivers directly, but we can test by triggering
                test_results.append("✓ Slider exists in browse tab")
                
                # Test offset change signal
                original_offset = dialog.get_current_offset()
                new_offset = 0x210000
                
                # Track if preview was requested
                preview_requested = False
                original_request = coordinator.request_manual_preview
                
                def mock_request(offset):
                    nonlocal preview_requested
                    preview_requested = True
                    test_results.append(f"✓ Preview requested for offset 0x{offset:06X}")
                    original_request(offset)
                
                coordinator.request_manual_preview = mock_request
                
                # Trigger offset change via browse tab
                dialog.browse_tab.offset_changed.emit(new_offset)
                
                if preview_requested:
                    test_results.append("✓ offset_changed triggers preview request")
                else:
                    test_results.append("✗ offset_changed did NOT trigger preview request")
                
                # Test slider value change
                preview_requested = False
                slider.valueChanged.emit(0x220000)
                
                # Process events to allow signals to propagate
                app.processEvents()
                
                if preview_requested:
                    test_results.append("✓ Slider valueChanged triggers preview via offset_changed")
                else:
                    test_results.append("✗ Slider valueChanged did NOT trigger preview")
                    
                # Check if sliderMoved is connected for drag events
                try:
                    # Simulate drag by emitting sliderMoved
                    preview_requested = False
                    
                    # Mock the drag move handler
                    original_drag_move = coordinator._on_drag_move
                    drag_move_called = False
                    
                    def mock_drag_move(value):
                        nonlocal drag_move_called
                        drag_move_called = True
                        test_results.append(f"✓ _on_drag_move called with value 0x{value:06X}")
                        original_drag_move(value)
                    
                    coordinator._on_drag_move = mock_drag_move
                    
                    # Emit sliderMoved signal
                    slider.sliderMoved.emit(0x230000)
                    app.processEvents()
                    
                    if drag_move_called:
                        test_results.append("✓ sliderMoved connected to coordinator")
                    else:
                        test_results.append("✗ sliderMoved NOT connected to coordinator")
                        
                except Exception as e:
                    test_results.append(f"✗ Error testing sliderMoved: {e}")
                    
            else:
                test_results.append("✗ Slider not found in browse tab")
        else:
            test_results.append("✗ SmartPreviewCoordinator not created")
        
        # Print results
        print("\n" + "="*60)
        print("Qt Signal/Slot Connection Test Results")
        print("="*60)
        for result in test_results:
            print(result)
        print("="*60)
        
        # Analyze results
        passed = sum(1 for r in test_results if r.startswith("✓"))
        failed = sum(1 for r in test_results if r.startswith("✗"))
        
        print(f"\nPassed: {passed}/{passed+failed} tests")
        
        if failed == 0:
            print("\n✅ All Qt signal connections are working correctly!")
            print("The preview system should update properly during slider dragging.")
        else:
            print(f"\n⚠️ {failed} test(s) failed. Check the issues above.")
        
        # Close dialog and quit
        dialog.close()
        app.quit()
    
    # Run test after event loop starts
    QTimer.singleShot(100, check_coordinator)
    
    # Run app briefly
    app.exec()

if __name__ == "__main__":
    test_manual_offset_signals()