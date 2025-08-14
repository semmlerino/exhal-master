
import pytest

pytestmark = [
    pytest.mark.dialog,
    pytest.mark.gui,
    pytest.mark.integration,
    pytest.mark.qt_real,
    pytest.mark.requires_display,
    pytest.mark.signals_slots,
]
#!/usr/bin/env python3
"""
Test script to verify the refactored manual offset tab widgets.
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget

# Test importing the refactored modules
try:
    from ui.tabs.manual_offset import SimpleBrowseTab, SimpleSmartTab, SimpleHistoryTab
    print("✓ Successfully imported tab widgets from ui.tabs.manual_offset")
except ImportError as e:
    print(f"✗ Failed to import tab widgets: {e}")
    sys.exit(1)

# Test importing the main dialog
try:
    from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
    print("✓ Successfully imported UnifiedManualOffsetDialog")
except ImportError as e:
    print(f"✗ Failed to import dialog: {e}")
    sys.exit(1)


def test_tab_creation():
    """Test creating individual tab widgets."""
    app = QApplication(sys.argv)
    
    # Test creating each tab widget
    try:
        browse_tab = SimpleBrowseTab()
        print("✓ SimpleBrowseTab created successfully")
        
        # Test some methods
        browse_tab.set_rom_size(0x400000)
        browse_tab.set_offset(0x200000)
        assert browse_tab.get_current_offset() == 0x200000
        print("  - Methods working correctly")
        
    except Exception as e:
        print(f"✗ Failed to create SimpleBrowseTab: {e}")
        return False
    
    try:
        smart_tab = SimpleSmartTab()
        print("✓ SimpleSmartTab created successfully")
        
        # Test some methods
        smart_tab.set_sprite_regions([(0x100000, 0.95), (0x200000, 0.88)])
        assert not smart_tab.is_smart_mode_enabled()
        print("  - Methods working correctly")
        
    except Exception as e:
        print(f"✗ Failed to create SimpleSmartTab: {e}")
        return False
    
    try:
        history_tab = SimpleHistoryTab()
        print("✓ SimpleHistoryTab created successfully")
        
        # Test some methods
        history_tab.add_sprite(0x300000, 0.92)
        assert history_tab.get_sprite_count() == 1
        print("  - Methods working correctly")
        
    except Exception as e:
        print(f"✗ Failed to create SimpleHistoryTab: {e}")
        return False
    
    return True


def test_tab_integration():
    """Test tabs integrated in a window."""
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    window.setWindowTitle("Tab Integration Test")
    
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    
    tab_widget = QTabWidget()
    
    # Add all three tabs
    browse_tab = SimpleBrowseTab()
    smart_tab = SimpleSmartTab()
    history_tab = SimpleHistoryTab()
    
    tab_widget.addTab(browse_tab, "Browse")
    tab_widget.addTab(smart_tab, "Smart")
    tab_widget.addTab(history_tab, "History")
    
    layout.addWidget(tab_widget)
    window.setCentralWidget(central_widget)
    
    # Test signal connections
    signal_received = {"offset": None}
    
    def on_offset_changed(offset):
        signal_received["offset"] = offset
        print(f"  - Received offset_changed signal: 0x{offset:06X}")
    
    browse_tab.offset_changed.connect(on_offset_changed)
    browse_tab.set_offset(0x123456)
    
    if signal_received["offset"] == 0x123456:
        print("✓ Signal connections working correctly")
    else:
        print("✗ Signal connections not working")
        return False
    
    return True


def test_dialog_integration():
    """Test that the dialog still works with refactored tabs."""
    app = QApplication(sys.argv)
    
    try:
        # Initialize managers first
        from core.managers import initialize_managers
        initialize_managers()
        
        dialog = UnifiedManualOffsetDialog()
        print("✓ UnifiedManualOffsetDialog created with refactored tabs")
        
        # Check that tabs are present
        assert dialog.browse_tab is not None
        assert dialog.smart_tab is not None
        assert dialog.history_tab is not None
        print("  - All tabs present in dialog")
        
        # Test some dialog methods
        dialog.set_offset(0x400000)
        assert dialog.get_current_offset() == 0x400000
        print("  - Dialog methods working correctly")
        
    except Exception as e:
        print(f"✗ Failed to create dialog: {e}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("\n=== Testing Refactored Manual Offset Tabs ===\n")
    
    all_passed = True
    
    print("1. Testing individual tab creation...")
    if not test_tab_creation():
        all_passed = False
    
    print("\n2. Testing tab integration...")
    if not test_tab_integration():
        all_passed = False
    
    print("\n3. Testing dialog integration...")
    if not test_dialog_integration():
        all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("✅ All tests passed! Refactoring successful.")
    else:
        print("❌ Some tests failed. Please review the refactoring.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())