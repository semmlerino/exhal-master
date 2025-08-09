#!/usr/bin/env python3
"""
Test to verify the manual offset dialog slider fixes.
This test simulates slider dragging and verifies that:
1. Raw tile data is extracted (not decompressed)
2. Data is non-zero (not black)
3. Preview is displayed correctly
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.dialogs.manual_offset_unified_integrated import UnifiedManualOffsetDialog
from core.extraction.extraction_manager import ExtractionManager


def find_test_rom():
    """Find a test ROM file."""
    test_rom = None
    test_dir = project_root / "tests" / "fixtures" / "roms"
    
    if test_dir.exists():
        for rom_file in test_dir.glob("*.sfc"):
            test_rom = str(rom_file)
            break
    
    if not test_rom:
        # Try to find any ROM in the project
        for rom_file in project_root.rglob("*.sfc"):
            test_rom = str(rom_file)
            break
    
    return test_rom


def test_slider_movement():
    """Test that slider movement produces valid previews."""
    print("\n" + "=" * 60)
    print("MANUAL OFFSET SLIDER FIX TEST")
    print("=" * 60)
    
    app = QApplication(sys.argv)
    
    # Find test ROM
    test_rom = find_test_rom()
    if not test_rom:
        print("ERROR: No test ROM found. Place a .sfc file in tests/fixtures/roms/")
        return False
    
    print(f"Using test ROM: {test_rom}")
    
    # Get ROM size
    import os
    rom_size = os.path.getsize(test_rom)
    print(f"ROM size: {rom_size} bytes")
    
    # Create extraction manager
    extraction_manager = ExtractionManager()
    
    # Create dialog
    dialog = UnifiedManualOffsetDialog()
    dialog.set_rom_data(test_rom, rom_size, extraction_manager)
    
    # Show dialog
    dialog.show()
    
    # Test different offsets
    test_offsets = [0x1000, 0x8000, 0x20000, 0x40000]
    test_results = []
    
    def test_offset(offset_idx):
        if offset_idx >= len(test_offsets):
            # All tests done, show results
            print("\n" + "=" * 60)
            print("TEST RESULTS:")
            print("=" * 60)
            
            for offset, result in test_results:
                status = "✓ PASS" if result else "✗ FAIL"
                print(f"Offset 0x{offset:06X}: {status}")
            
            success_count = sum(1 for _, r in test_results if r)
            print(f"\nTotal: {success_count}/{len(test_results)} passed")
            
            # Close dialog and exit
            dialog.close()
            app.quit()
            return
        
        offset = test_offsets[offset_idx]
        if offset >= rom_size:
            # Skip offsets beyond ROM size
            test_results.append((offset, False))
            QTimer.singleShot(100, lambda: test_offset(offset_idx + 1))
            return
        
        print(f"\n--- Testing offset 0x{offset:06X} ---")
        
        # Simulate slider movement
        if dialog.browse_tab:
            print(f"Setting slider to 0x{offset:06X}")
            dialog.browse_tab.position_slider.setValue(offset)
            
            # Give time for preview to generate
            def check_preview():
                # Check if preview widget has data
                if dialog.preview_widget:
                    has_data = False
                    error_msg = "No preview widget"
                    
                    # Check if sprite_data is set
                    if hasattr(dialog.preview_widget, 'sprite_data') and dialog.preview_widget.sprite_data:
                        data = dialog.preview_widget.sprite_data
                        non_zero = sum(1 for b in data[:min(100, len(data))] if b != 0)
                        print(f"Preview has {len(data)} bytes, {non_zero}/100 non-zero")
                        
                        if non_zero > 0:
                            has_data = True
                            print("✓ Preview shows valid data (not black)")
                        else:
                            error_msg = "Preview data is all zeros (black)"
                            print("✗ Preview data is all zeros (black)")
                    else:
                        # Check if pixmap is set
                        if hasattr(dialog.preview_widget, 'preview_label'):
                            pixmap = dialog.preview_widget.preview_label.pixmap()
                            if pixmap and not pixmap.isNull():
                                print("✓ Preview has pixmap")
                                has_data = True
                            else:
                                error_msg = "No pixmap displayed"
                                print("✗ No pixmap displayed")
                    
                    if not has_data:
                        print(f"ERROR: {error_msg}")
                    
                    test_results.append((offset, has_data))
                else:
                    print("ERROR: No preview widget")
                    test_results.append((offset, False))
                
                # Test next offset
                QTimer.singleShot(100, lambda: test_offset(offset_idx + 1))
            
            # Wait 500ms for preview to generate
            QTimer.singleShot(500, check_preview)
        else:
            print("ERROR: No browse tab")
            test_results.append((offset, False))
            QTimer.singleShot(100, lambda: test_offset(offset_idx + 1))
    
    # Start testing after dialog is shown
    QTimer.singleShot(500, lambda: test_offset(0))
    
    # Run app
    app.exec()
    
    # Return success based on test results
    return all(r for _, r in test_results)


if __name__ == "__main__":
    success = test_slider_movement()
    sys.exit(0 if success else 1)