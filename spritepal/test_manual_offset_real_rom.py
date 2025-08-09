#!/usr/bin/env python3
"""
Test manual offset dialog with real ROM data to identify the black box issue.
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QDialog
from PyQt6.QtCore import Qt, QTimer

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from core.managers import initialize_managers, get_extraction_manager
from utils.logging_config import get_logger

logger = get_logger(__name__)


def test_manual_offset_dialog_real():
    """Test the manual offset dialog with actual ROM data."""
    print("\n=== Test: Manual Offset Dialog with Real ROM ===")
    
    app = QApplication.instance() or QApplication(sys.argv)
    
    # Initialize managers
    try:
        initialize_managers()
        extraction_manager = get_extraction_manager()
        print("✅ Managers initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize managers: {e}")
        return False
    
    # Look for a test ROM file
    test_rom = None
    rom_files = [
        "test_rom.sfc",
        "Kirby Super Star (USA).sfc", 
        "Kirby's Fun Pak (Europe).sfc",
        "test.smc", "test.sfc", "kirby.smc", "kirby.sfc"
    ]
    
    for filename in rom_files:
        if os.path.exists(filename):
            test_rom = filename
            break
    
    if not test_rom:
        print("⚠️ No test ROM found. Looking in parent directory...")
        parent_dir = Path(__file__).parent.parent
        for filename in rom_files:
            rom_path = parent_dir / filename
            if rom_path.exists():
                test_rom = str(rom_path)
                break
    
    if not test_rom:
        print("❌ No test ROM file found. Please provide a test.smc or kirby.smc file.")
        print("  This test needs a real ROM to reproduce the black box issue.")
        return False
    
    print(f"✅ Found test ROM: {test_rom}")
    
    # Load the ROM
    try:
        with open(test_rom, 'rb') as f:
            rom_data = f.read()
        extraction_manager.set_rom_data(rom_data)
        print(f"✅ ROM loaded: {len(rom_data)} bytes")
    except Exception as e:
        print(f"❌ Failed to load ROM: {e}")
        return False
    
    # Create dialog
    dialog = UnifiedManualOffsetDialog(parent=None)
    dialog.show()
    
    print("\n=== Testing Dialog Components ===")
    
    # Check preview widget
    preview = dialog.preview_widget
    if preview:
        print(f"✅ Preview widget exists: {type(preview)}")
        print(f"  - Visible: {preview.isVisible()}")
        print(f"  - Size: {preview.size()}")
        print(f"  - Current palette index: {preview.current_palette_index}")
        print(f"  - Palettes loaded: {len(preview.palettes) if preview.palettes else 0}")
    else:
        print("❌ No preview widget found!")
        return False
    
    # Check browse tab
    browse = dialog.browse_tab
    if browse:
        print(f"✅ Browse tab exists")
        print(f"  - Has ROM data: {browse._rom_data is not None}")
        print(f"  - ROM size: {len(browse._rom_data) if browse._rom_data else 0}")
    else:
        print("❌ No browse tab found!")
        return False
    
    # Test offset navigation
    print("\n=== Testing Offset Navigation ===")
    
    # Set an offset that should have sprite data
    test_offsets = [0x1000, 0x2000, 0x3000, 0x10000, 0x20000]
    
    for offset in test_offsets:
        if offset < len(rom_data):
            print(f"\nTesting offset 0x{offset:X}...")
            browse.offset_spin.setValue(offset)
            
            # Process events to trigger update
            app.processEvents()
            
            # Wait a bit for preview to update
            QTimer.singleShot(100, app.quit)
            app.exec()
            
            # Check preview state
            pixmap = preview.preview_label.pixmap()
            if pixmap and not pixmap.isNull():
                print(f"  ✅ Pixmap exists at offset 0x{offset:X}: {pixmap.width()}x{pixmap.height()}")
                
                # Check if it's actually showing content (not all black)
                # This would require more sophisticated checking
                break
            else:
                print(f"  ❌ No pixmap at offset 0x{offset:X}")
                # Check what's in preview_label
                label_text = preview.preview_label.text()
                if label_text:
                    print(f"     Label shows text instead: '{label_text}'")
    
    # Diagnostic output
    print("\n=== Preview Widget Diagnostic ===")
    diagnostic = preview.diagnose_display_issue()
    
    # Check if sprites are black
    if preview.sprite_pixmap:
        print(f"\n✅ sprite_pixmap exists: {preview.sprite_pixmap.width()}x{preview.sprite_pixmap.height()}")
    else:
        print("\n❌ No sprite_pixmap stored")
    
    # Test prev/next navigation
    print("\n=== Testing Prev/Next Navigation ===")
    
    # Try finding next sprite
    print("Attempting to find next sprite...")
    dialog._find_next_sprite()
    app.processEvents()
    QTimer.singleShot(100, app.quit)
    app.exec()
    
    new_offset = browse.offset_spin.value()
    print(f"Offset after 'Find Next': 0x{new_offset:X}")
    
    # Clean up
    dialog.close()
    
    return True


def main():
    """Run the test."""
    print("=" * 60)
    print("Testing Manual Offset Dialog with Real ROM Data")
    print("=" * 60)
    
    success = test_manual_offset_dialog_real()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Test completed. Check output for sprite display issues.")
    else:
        print("❌ Test failed or incomplete.")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)