#!/usr/bin/env python3
from __future__ import annotations

"""
Test script for ResumeScanDialog pilot migration to feature flag system.

This script validates that ResumeScanDialog works identically with both:
1. Legacy DialogBase implementation
2. Composed DialogBaseMigrationAdapter implementation

Run this script to verify the feature flag system works correctly.
"""

import os
import sys
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtCore import QTimer

# Import the feature flag controls
from ui.components.base import (
    set_dialog_implementation,
    get_dialog_implementation,
    is_composed_dialogs_enabled
)

# Test data for the dialog
TEST_SCAN_INFO: dict[str, Any] = {
    "found_sprites": [
        {"offset": 0x1000, "size": 512},
        {"offset": 0x2000, "size": 256},
        {"offset": 0x3000, "size": 1024},
    ],
    "current_offset": 0x4800,
    "scan_range": {
        "start": 0x0000,
        "end": 0x10000,
        "step": 0x10
    },
    "completed": False,
    "total_found": 3
}

def test_dialog_creation(implementation: str) -> bool:
    """Test basic dialog creation and initialization."""
    print(f"\n[{implementation}] Testing dialog creation...")
    
    try:
        # Import must happen after setting the implementation
        from ui.dialogs.resume_scan_dialog import ResumeScanDialog
        
        # Create dialog
        dialog = ResumeScanDialog(TEST_SCAN_INFO, parent=None)
        
        # Verify basic properties
        assert dialog.windowTitle() == "Resume Sprite Scan?", f"Wrong title: {dialog.windowTitle()}"
        assert dialog.isModal() == True, "Dialog should be modal"
        assert dialog.user_choice == ResumeScanDialog.CANCEL, "Default choice should be CANCEL"
        
        # Verify buttons exist
        assert hasattr(dialog, 'resume_button'), "Missing resume_button"
        assert hasattr(dialog, 'fresh_button'), "Missing fresh_button"
        assert hasattr(dialog, 'cancel_button'), "Missing cancel_button"
        
        # Verify button text
        assert dialog.resume_button.text() == "Resume Scan", f"Wrong resume button text: {dialog.resume_button.text()}"
        assert dialog.fresh_button.text() == "Start Fresh", f"Wrong fresh button text: {dialog.fresh_button.text()}"
        assert dialog.cancel_button.text() == "Cancel", f"Wrong cancel button text: {dialog.cancel_button.text()}"
        
        # Clean up
        dialog.close()
        dialog.deleteLater()
        
        print(f"[{implementation}] ✓ Dialog creation successful")
        return True
        
    except Exception as e:
        print(f"[{implementation}] ✗ Dialog creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_button_functionality(implementation: str) -> bool:
    """Test button click functionality."""
    print(f"\n[{implementation}] Testing button functionality...")
    
    try:
        # Import must happen after setting the implementation
        from ui.dialogs.resume_scan_dialog import ResumeScanDialog
        
        # Test Resume button
        dialog = ResumeScanDialog(TEST_SCAN_INFO, parent=None)
        dialog.resume_button.click()
        assert dialog.user_choice == ResumeScanDialog.RESUME, f"Resume button failed: {dialog.user_choice}"
        dialog.close()
        dialog.deleteLater()
        
        # Test Start Fresh button
        dialog = ResumeScanDialog(TEST_SCAN_INFO, parent=None)
        dialog.fresh_button.click()
        assert dialog.user_choice == ResumeScanDialog.START_FRESH, f"Start fresh button failed: {dialog.user_choice}"
        dialog.close()
        dialog.deleteLater()
        
        # Test Cancel button
        dialog = ResumeScanDialog(TEST_SCAN_INFO, parent=None)
        dialog.cancel_button.click()
        assert dialog.user_choice == ResumeScanDialog.CANCEL, f"Cancel button failed: {dialog.user_choice}"
        dialog.close()
        dialog.deleteLater()
        
        print(f"[{implementation}] ✓ Button functionality successful")
        return True
        
    except Exception as e:
        print(f"[{implementation}] ✗ Button functionality failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_progress_formatting(implementation: str) -> bool:
    """Test progress info formatting."""
    print(f"\n[{implementation}] Testing progress formatting...")
    
    try:
        # Import must happen after setting the implementation
        from ui.dialogs.resume_scan_dialog import ResumeScanDialog
        
        dialog = ResumeScanDialog(TEST_SCAN_INFO, parent=None)
        
        # Get formatted progress info
        progress_info = dialog._format_progress_info()
        
        # Verify the format contains expected information
        assert "Progress:" in progress_info, "Missing progress percentage"
        assert "Sprites found: 3" in progress_info, "Missing sprite count"
        assert "Last position: 0x004800" in progress_info, "Missing last position"
        assert "Scan range: 0x000000 - 0x010000" in progress_info, "Missing scan range"
        
        # Calculate expected progress
        # (0x4800 - 0x0000) / (0x10000 - 0x0000) * 100 = 28.125%
        assert "28.1%" in progress_info, f"Wrong progress calculation in: {progress_info}"
        
        # Clean up
        dialog.close()
        dialog.deleteLater()
        
        print(f"[{implementation}] ✓ Progress formatting successful")
        return True
        
    except Exception as e:
        print(f"[{implementation}] ✗ Progress formatting failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_static_method(implementation: str) -> bool:
    """Test the static show_resume_dialog method."""
    print(f"\n[{implementation}] Testing static method...")
    
    try:
        # Import must happen after setting the implementation
        from ui.dialogs.resume_scan_dialog import ResumeScanDialog
        
        # Since we can't interact with the dialog in automated tests,
        # we'll just verify the method exists and can be called
        assert hasattr(ResumeScanDialog, 'show_resume_dialog'), "Missing static method"
        assert callable(ResumeScanDialog.show_resume_dialog), "Static method not callable"
        
        print(f"[{implementation}] ✓ Static method exists and is callable")
        return True
        
    except Exception as e:
        print(f"[{implementation}] ✗ Static method test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_tests_for_implementation(use_composed: bool) -> bool:
    """Run all tests for a specific implementation."""
    implementation = "composed" if use_composed else "legacy"
    
    print(f"\n{'='*60}")
    print(f"Testing with {implementation.upper()} implementation")
    print(f"{'='*60}")
    
    # Set the implementation
    set_dialog_implementation(use_composed)
    
    # Verify the implementation is set correctly
    actual_impl = get_dialog_implementation()
    if actual_impl != implementation:
        print(f"✗ Failed to set implementation to {implementation}, got {actual_impl}")
        return False
    
    print(f"✓ Implementation set to: {implementation}")
    print(f"  Feature flag enabled: {is_composed_dialogs_enabled()}")
    
    # Clear any cached imports
    if 'ui.dialogs.resume_scan_dialog' in sys.modules:
        del sys.modules['ui.dialogs.resume_scan_dialog']
    
    # Run all tests
    results = []
    results.append(test_dialog_creation(implementation))
    results.append(test_button_functionality(implementation))
    results.append(test_progress_formatting(implementation))
    results.append(test_static_method(implementation))
    
    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n[{implementation}] Summary: {passed}/{total} tests passed")
    
    return all(results)

def main():
    """Main test runner."""
    print("\n" + "="*60)
    print("ResumeScanDialog Feature Flag Migration Test")
    print("="*60)
    
    # Initialize Qt application
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Test both implementations
    legacy_success = run_tests_for_implementation(use_composed=False)
    composed_success = run_tests_for_implementation(use_composed=True)
    
    # Final summary
    print("\n" + "="*60)
    print("FINAL RESULTS")
    print("="*60)
    
    if legacy_success and composed_success:
        print("✓ SUCCESS: Both implementations work identically!")
        print("  The feature flag system is working correctly.")
        print("  ResumeScanDialog can be safely migrated.")
        exit_code = 0
    else:
        print("✗ FAILURE: Implementations differ!")
        if not legacy_success:
            print("  - Legacy implementation has issues")
        if not composed_success:
            print("  - Composed implementation has issues")
        exit_code = 1
    
    print("="*60)
    
    # Clean up
    app.quit()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()